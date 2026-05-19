"""Export a Claude Code session as a chat-style HTML transcript.

Reads a `~/.claude/projects/<encoded-cwd>/<session>.jsonl` file, walks events in
timestamp order, and renders user/assistant turns into a single HTML page. Tool
calls and results render as collapsed `<details>` blocks so the conversation
flow stays readable.

Designed for producing didactic tutorials: a new researcher can read the
*actual* interaction that produced an outcome (e.g., the quickstart canary run)
rather than the polished after-the-fact docs.

Usage:
    uv run python scripts/export-conversation.py \\
        --session ~/.claude/projects/<encoded-cwd>/<session-uuid>.jsonl \\
        --start-prompt "ok update the template work flow" \\
        --out docs-pdf/html/quickstart-tutorial.html

Flags:
    --start-prompt  Substring of a user message that marks the start of the slice
    --end-prompt    Optional; defaults to end of file
    --title         Page title (default: "Conversation Transcript")
    --no-sanitize   Disable all secret-scrubbing (default: scrub on)
"""

from __future__ import annotations

import argparse
import ast
import html
import json
import re
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

Replacement = str | Callable[[re.Match[str]], str]


# ----- sanitization -----

# Order matters: longest patterns first so they don't get half-replaced.
SANITIZE_RULES: list[tuple[re.Pattern[str], Replacement]] = [
    # GitHub personal access tokens (gho_, ghp_, ghs_, github_pat_) — also catches truncated/elided forms
    (re.compile(r"\b(?:gh[opsu]_|github_pat_)[A-Za-z0-9_]{3,}\.{0,3}"), "gho_REDACTED"),
    # SSH public-key material (long base64 blob in ssh-rsa/ssh-ed25519 strings)
    (re.compile(r"(ssh-(?:rsa|ed25519|dss|ecdsa))\s+[A-Za-z0-9+/=]{40,}(\s+\S+)?"),
     r"\1 <PUBKEY-REDACTED>"),
    # Private SSH key paths under ~/.ssh/
    (re.compile(r"~/\.ssh/[A-Za-z0-9_.-]+(?!\.pub)\b"), "~/.ssh/<your-ssh-key>"),
    (re.compile(r"/Users/[^/]+/\.ssh/[A-Za-z0-9_.-]+(?!\.pub)\b"), "~/.ssh/<your-ssh-key>"),
    # Vast.ai host:port pairs (ssh\d+.vast.ai:NNNNN)
    (re.compile(r"\bssh\d+\.vast\.ai\b"), "<vast-host>"),
    (re.compile(r"-[pP]\s+\d{4,5}\b"), lambda m: f"{m.group(0)[:2]} <port>"),
    # Vast.ai instance IDs (8-digit numbers near 'instance', 'destroy', etc.)
    (re.compile(r"(instance\s+|destroy\s+instance\s+|new_contract['\"]?:\s*)\d{6,9}"),
     r"\1<INSTANCE_ID>"),
    (re.compile(r"\b37056539\b"), "<INSTANCE_ID>"),  # this session's specific ID
    (re.compile(r"\b8936966\b"), "<OFFER_ID>"),
    # Personal identifiers (catch full + truncated forms)
    (re.compile(r"\bquandang(13)?\b"), "<user>"),
    (re.compile(r"\bthaovan1603(@gmail\.com)?\b"), "<user-email>"),
    (re.compile(r"\bquan@maestrolabs(\.ai)?\b"), "<user>@<host>"),
    # IP addresses
    (re.compile(r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b"), "<ip>"),
]


def sanitize(text: str) -> str:
    for pattern, replacement in SANITIZE_RULES:
        text = pattern.sub(replacement, text)
    return text


# ----- parsing -----


def parse_message_field(raw: str | dict) -> dict:
    """Message field may be a real dict (newer transcripts) or a Python-repr string."""
    if isinstance(raw, dict):
        return raw
    if not isinstance(raw, str):
        return {"role": "unknown", "content": str(raw)}
    try:
        return ast.literal_eval(raw)
    except (ValueError, SyntaxError):
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return {"role": "unknown", "content": raw}


@dataclass
class Turn:
    role: str  # "user" | "assistant" | "tool_result" | "system"
    blocks: list[dict]  # rendered content blocks
    timestamp: str


def extract_text_and_tools(content: list | str) -> list[dict]:
    """Normalize message content into a list of typed blocks."""
    if isinstance(content, str):
        return [{"type": "text", "text": content}]
    out = []
    for block in content:
        if not isinstance(block, dict):
            continue
        t = block.get("type")
        if t == "text":
            out.append({"type": "text", "text": block.get("text", "")})
        elif t == "thinking":
            out.append({"type": "thinking", "text": block.get("thinking", "")})
        elif t == "tool_use":
            out.append({
                "type": "tool_use",
                "name": block.get("name", "?"),
                "input": block.get("input", {}),
                "id": block.get("id", ""),
            })
        elif t == "tool_result":
            content_val = block.get("content", "")
            if isinstance(content_val, list):
                content_val = "\n".join(
                    b.get("text", "") if isinstance(b, dict) else str(b)
                    for b in content_val
                )
            out.append({
                "type": "tool_result",
                "tool_use_id": block.get("tool_use_id", ""),
                "text": str(content_val),
                "is_error": block.get("is_error", False),
            })
    return out


def load_session(path: Path) -> list[dict]:
    events = []
    for line in path.read_text().splitlines():
        if not line.strip():
            continue
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return events


def find_slice(events: list[dict], start_prompt: str, end_prompt: str | None) -> list[dict]:
    """Return events from the first user message containing start_prompt onward."""
    start_idx = None
    end_idx = len(events)
    for i, ev in enumerate(events):
        if ev.get("type") != "user":
            continue
        msg = parse_message_field(ev.get("message", "{}"))
        content = msg.get("content", "")
        text = content if isinstance(content, str) else json.dumps(content)
        if start_idx is None and start_prompt in text:
            start_idx = i
        elif start_idx is not None and end_prompt and end_prompt in text:
            end_idx = i
            break
    if start_idx is None:
        raise SystemExit(f"start-prompt {start_prompt!r} not found in transcript")
    return events[start_idx:end_idx]


# ----- HTML rendering -----


CSS = """
:root {
  --bg: #1c1c1c;
  --bg-soft: #232323;
  --fg: #d4d4d4;
  --muted: #888888;
  --dim: #5a5a5a;
  --user: #58a6ff;        /* blue '>' prompt */
  --dot: #d4d4d4;         /* '⏺' for assistant text */
  --tool: #d39e3a;        /* '⏺' for tool calls — Claude Code amber */
  --result: #6a7079;      /* '⎿' for tool output gutter */
  --thinking: #b58bd6;
  --error: #f47067;
  --accent: #2ea043;
  --rule: #2a2a2a;
}
@page { size: A4; margin: 14mm 14mm; }
* { box-sizing: border-box; }
html { -webkit-text-size-adjust: 100%; }
body {
  font-family: ui-monospace, "SF Mono", "JetBrains Mono", Menlo, Monaco,
               Consolas, "Liberation Mono", monospace;
  font-size: 13px; line-height: 1.55; color: var(--fg);
  max-width: 880px; margin: 0 auto; padding: 36px 28px 80px;
  background: var(--bg);
  font-feature-settings: "calt" 0;  /* no fancy ligatures, terminal feel */
  -webkit-font-smoothing: antialiased;
}
h1 {
  font-size: 16px; font-weight: 600; color: var(--fg);
  margin: 0 0 4px; letter-spacing: 0; font-family: inherit;
}
h1::before { content: "# "; color: var(--muted); }
.intro {
  color: var(--muted); font-size: 12.5px; line-height: 1.55;
  margin: 0 0 28px; padding: 0; border: none; background: transparent;
}
.intro code { font-size: 12px; }
hr.section { border: 0; border-top: 1px dashed var(--rule); margin: 28px 0; }

/* The transcript itself */
.turn { margin: 14px 0; padding: 0; position: relative; }
.turn .role { display: none; }  /* role labels replaced by ⏺ / > glyphs */

/* User prompt — '>' marker, slightly brighter */
.turn.user { color: var(--fg); margin-top: 22px; padding-left: 18px; position: relative; }
.turn.user::before {
  content: ">"; position: absolute; left: 0; top: 0;
  color: var(--user); font-weight: 600;
}
.turn.user p { margin: 0 0 4px; white-space: pre-wrap; }

/* Assistant text block — '⏺' marker */
.turn.assistant { padding-left: 18px; position: relative; }
.turn.assistant > p:first-of-type::before,
.turn.assistant > h1:first-of-type::before,
.turn.assistant > h2:first-of-type::before,
.turn.assistant > h3:first-of-type::before,
.turn.assistant > ul:first-of-type::before,
.turn.assistant > ol:first-of-type::before {
  content: "⏺"; position: absolute; left: 0;
  color: var(--dot);
}
.turn p, .turn ul, .turn ol { margin: 0 0 8px; }
.turn p:last-child, .turn ul:last-child, .turn ol:last-child { margin-bottom: 0; }
.turn ul, .turn ol { padding-left: 1.4em; }
.turn blockquote {
  border-left: 2px solid var(--rule); padding: 0 0 0 12px;
  color: var(--muted); margin: 8px 0; font-style: normal;
}
.turn strong { color: #f0f0f0; font-weight: 600; }
.turn em { color: var(--muted); }

/* Thinking — dim, italic, prefixed with subtle marker */
.thinking {
  color: var(--dim); font-style: italic; margin: 8px 0 12px 18px;
  padding-left: 14px; border-left: 1px dashed var(--rule);
  font-size: 12.5px;
}
.thinking::before {
  content: "✻ Thinking…"; display: block; color: var(--thinking);
  font-style: normal; font-size: 11px; margin-bottom: 4px;
  letter-spacing: 0.02em;
}
.thinking .body p { margin: 0 0 4px; }

/* Tool call block — '⏺' (amber) with Name(args) signature */
details {
  margin: 6px 0 6px 18px; padding: 0; border: none; background: transparent;
  position: relative;
}
details::before {
  content: "⏺"; position: absolute; left: -18px; top: 0;
  color: var(--tool);
}
summary {
  cursor: pointer; padding: 0; user-select: none; list-style: none;
  font-family: inherit; font-size: 13px; color: var(--fg);
  white-space: pre-wrap; word-break: break-word;
}
summary::-webkit-details-marker { display: none; }
summary .tool-label {
  color: var(--tool); font-weight: 500;
}
summary .tool-target {
  color: var(--muted);
}
summary .tool-target::before { content: "("; color: var(--dim); }
summary .tool-target::after { content: ")"; color: var(--dim); }

/* Tool body (open) — left gutter with ⎿ marker on first child */
details .body {
  margin: 4px 0 0 14px; padding: 0 0 0 14px;
  border-left: 1px solid var(--rule);
  color: var(--muted); font-size: 12.5px;
  position: relative;
}
details .body::before {
  content: "⎿"; position: absolute; left: -2px; top: -2px;
  color: var(--result); background: var(--bg); padding: 0 2px;
}
details .body p {
  margin: 4px 0; color: var(--muted); font-size: 11.5px;
  text-transform: uppercase; letter-spacing: 0.06em;
}
details.tool-error::before { color: var(--error); }
details.tool-error summary .tool-label { color: var(--error); }

/* Code blocks */
code {
  font-family: inherit; font-size: 0.95em; color: var(--fg);
  background: transparent; padding: 0;
}
pre {
  background: var(--bg-soft); color: var(--fg);
  border: 1px solid var(--rule); border-radius: 4px;
  padding: 8px 10px; overflow-x: auto;
  white-space: pre-wrap; word-break: break-word;
  font-family: inherit; font-size: 12px; line-height: 1.5;
  margin: 6px 0;
}
pre code { background: transparent; padding: 0; font-size: inherit; color: var(--fg); }
.turn pre { background: var(--bg-soft); }

/* Inline code accent inside narrative text */
.turn p code, .turn li code, .intro code {
  background: var(--bg-soft); padding: 1px 5px; border-radius: 3px;
  color: var(--fg); border: 1px solid var(--rule);
}

a { color: var(--user); text-decoration: none; }
a:hover { text-decoration: underline; }

/* Tables (rare, but the original docs use them) */
table { border-collapse: collapse; margin: 8px 0; font-size: 12px; }
th, td { border: 1px solid var(--rule); padding: 4px 8px; text-align: left; }
th { background: var(--bg-soft); color: var(--fg); }

/* Truncation hint */
.trunc {
  color: var(--dim); font-style: italic; font-size: 11.5px;
  margin: 4px 0 0; padding: 0;
}

/* Print: keep it readable on paper */
@media print {
  body { background: white; color: #1f2328; padding: 0; max-width: none; }
  h1, h1::before { color: #1f2328; }
  .turn { color: #1f2328; }
  .turn.user::before { color: #0969da; }
  .turn.assistant > p:first-of-type::before,
  .turn.assistant > h1:first-of-type::before,
  .turn.assistant > h2:first-of-type::before,
  .turn.assistant > h3:first-of-type::before,
  .turn.assistant > ul:first-of-type::before,
  .turn.assistant > ol:first-of-type::before { color: #1f2328; }
  details::before { color: #bf6b00; }
  summary .tool-label { color: #bf6b00; }
  .thinking { color: #57606a; }
  .thinking::before { color: #8250df; }
  pre, .turn pre, .turn p code { background: #f6f8fa; border-color: #d0d7de; color: #1f2328; }
  details .body, details .body::before { color: #57606a; }
  details .body::before { background: white; }
  .turn { page-break-inside: avoid; }
  details { page-break-inside: avoid; }
  /* Auto-open every tool block when printed */
  details > .body { display: block !important; }
}
"""


def render_text_as_paragraphs(text: str) -> str:
    """Render plain text with simple paragraph + code-fence handling."""
    parts = []
    in_code = False
    buf: list[str] = []

    def flush_para():
        if not buf:
            return
        joined = "\n".join(buf).strip()
        if joined:
            # convert backtick inline code
            esc = html.escape(joined)
            esc = re.sub(r"`([^`]+)`", r"<code>\1</code>", esc)
            esc = esc.replace("\n", "<br>")
            parts.append(f"<p>{esc}</p>")
        buf.clear()

    for line in text.splitlines():
        if line.strip().startswith("```"):
            if in_code:
                parts.append(f"<pre><code>{html.escape(chr(10).join(buf))}</code></pre>")
                buf.clear()
                in_code = False
            else:
                flush_para()
                in_code = True
            continue
        if in_code:
            buf.append(line)
        else:
            if line.strip() == "":
                flush_para()
            else:
                buf.append(line)
    if in_code:
        parts.append(f"<pre><code>{html.escape(chr(10).join(buf))}</code></pre>")
    else:
        flush_para()
    return "\n".join(parts)


def _summary_line(label: str, target: str) -> str:
    """Format like Claude Code: 'Tool(args)' with parens added by CSS."""
    label_html = f"<span class='tool-label'>{html.escape(label)}</span>"
    target_html = (f"<span class='tool-target'>{html.escape(target)}</span>"
                   if target else "<span class='tool-target'></span>")
    return label_html + target_html


def render_tool_use(block: dict, do_sanitize: bool,
                    pending_results: dict[str, dict]) -> str:
    name = block["name"]
    inp = block.get("input", {})
    tool_id = block.get("id", "")
    if name == "Bash":
        cmd = inp.get("command", "")
        if do_sanitize:
            cmd = sanitize(cmd)
        summary = _summary_line("Bash", cmd.replace("\n", " ⏎ ")[:140])
        body_parts = [f"<pre><code>{html.escape(cmd)}</code></pre>"]
    elif name == "Edit":
        path = inp.get("file_path", "")
        if do_sanitize:
            path = sanitize(path)
        summary = _summary_line("Edit", path)
        old = inp.get("old_string", "")[:400]
        new = inp.get("new_string", "")[:400]
        if do_sanitize:
            old, new = sanitize(old), sanitize(new)
        body_parts = [
            f"<p>− old</p><pre><code>{html.escape(old)}</code></pre>",
            f"<p>+ new</p><pre><code>{html.escape(new)}</code></pre>",
        ]
    elif name == "Write":
        path = inp.get("file_path", "")
        if do_sanitize:
            path = sanitize(path)
        summary = _summary_line("Write", path)
        content = inp.get("content", "")[:800]
        if do_sanitize:
            content = sanitize(content)
        body_parts = [f"<pre><code>{html.escape(content)}</code></pre>"]
    elif name == "Read":
        path = inp.get("file_path", "")
        if do_sanitize:
            path = sanitize(path)
        summary = _summary_line("Read", path)
        body_parts = []
    elif name in ("TaskCreate", "TaskUpdate"):
        subject = inp.get("subject") or inp.get("status") or ""
        if do_sanitize:
            subject = sanitize(str(subject))
        summary = _summary_line("Task", str(subject))
        body_parts = []
    elif name == "AskUserQuestion":
        questions = inp.get("questions", [])
        first_q = questions[0].get("question", "") if questions else ""
        if do_sanitize:
            first_q = sanitize(first_q)
        summary = _summary_line("AskUserQuestion", first_q[:140])
        body_parts = []
    else:
        summary = _summary_line(name, "")
        raw = json.dumps(inp, indent=2)[:1000]
        if do_sanitize:
            raw = sanitize(raw)
        body_parts = [f"<pre><code>{html.escape(raw)}</code></pre>"]

    # Attach the matching tool_result, formatted Claude-Code-style
    result = pending_results.pop(tool_id, None)
    if result is not None:
        text = result["text"]
        if do_sanitize:
            text = sanitize(text)
        original_lines = text.count("\n") + 1
        max_lines = 30
        if original_lines > max_lines:
            kept = "\n".join(text.split("\n")[:max_lines])
            extra = original_lines - max_lines
            text_html = (f"<pre><code>{html.escape(kept)}</code></pre>"
                         f"<p class='trunc'>… +{extra} lines (ctrl+o to expand)</p>")
        elif text.strip():
            text_html = f"<pre><code>{html.escape(text)}</code></pre>"
        else:
            text_html = ""
        if text_html:
            body_parts.append(text_html)

    error_cls = " tool-error" if (result and result.get("is_error")) else ""
    body = "".join(body_parts)
    if not body:
        # No body — close the details tag immediately. Don't render empty .body
        # because the ⎿ glyph attached to it would look orphaned.
        return (f"<details class='{error_cls.strip()} no-body' open>"
                f"<summary>{summary}</summary></details>")
    return (f"<details class='{error_cls.strip()}' open>"
            f"<summary>{summary}</summary>"
            f"<div class='body'>{body}</div></details>")


def render_tool_result(block: dict, do_sanitize: bool) -> str:
    # Tool results are folded into their parent tool_use via pending_results.
    # This standalone renderer is only used for orphans.
    text = block["text"]
    if do_sanitize:
        text = sanitize(text)
    lines = text.count("\n") + 1
    if lines > 30:
        kept = "\n".join(text.split("\n")[:30])
        text_html = (f"<pre><code>{html.escape(kept)}</code></pre>"
                     f"<p class='trunc'>… +{lines - 30} lines (ctrl+o to expand)</p>")
    else:
        text_html = f"<pre><code>{html.escape(text)}</code></pre>"
    cls = "tool-error" if block.get("is_error") else ""
    return (f"<details class='{cls}' open><summary>{_summary_line('Result', '')}</summary>"
            f"<div class='body'>{text_html}</div></details>")


def render_turn(role: str, blocks: list[dict], do_sanitize: bool,
                pending_results: dict[str, dict]) -> str:
    parts = [f"<div class='role'>{role}</div>"]
    for b in blocks:
        t = b["type"]
        if t == "text":
            text = b["text"]
            if do_sanitize:
                text = sanitize(text)
            parts.append(render_text_as_paragraphs(text))
        elif t == "thinking":
            text = b["text"].strip()
            if not text:
                continue
            if do_sanitize:
                text = sanitize(text)
            parts.append(f"<div class='thinking'><div class='body'>"
                         f"{render_text_as_paragraphs(text)}</div></div>")
        elif t == "tool_use":
            parts.append(render_tool_use(b, do_sanitize, pending_results))
        elif t == "tool_result":
            parts.append(render_tool_result(b, do_sanitize))
    return f"<div class='turn {role}'>{''.join(parts)}</div>"


def collect_results(turns: list[Turn]) -> dict[str, dict]:
    """Build a tool_use_id → result block lookup so tool_use can inline its output."""
    results: dict[str, dict] = {}
    for t in turns:
        for b in t.blocks:
            if b["type"] == "tool_result":
                results[b["tool_use_id"]] = b
    return results


def render_html(turns: list[Turn], title: str, intro: str, do_sanitize: bool) -> str:
    pending_results = collect_results(turns)
    body_parts = [
        f"<h1>{html.escape(title)}</h1>",
        f"<p class='intro'>{intro}</p>",
    ]
    for t in turns:
        # Skip pure-tool_result turns — their content is folded into the parent tool_use
        if all(b["type"] == "tool_result" for b in t.blocks):
            continue
        # Skip turns whose only content is empty/whitespace text or empty thinking
        rendered_blocks = []
        for b in t.blocks:
            if b["type"] == "text" and not b.get("text", "").strip():
                continue
            if b["type"] == "thinking" and not b.get("text", "").strip():
                continue
            rendered_blocks.append(b)
        if not rendered_blocks:
            continue
        body_parts.append(render_turn(t.role, rendered_blocks, do_sanitize, pending_results))
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>{html.escape(title)}</title>
<style>{CSS}</style>
</head>
<body>
{chr(10).join(body_parts)}
</body>
</html>
"""


def build_turns(events: list[dict]) -> list[Turn]:
    turns: list[Turn] = []
    for ev in events:
        t = ev.get("type")
        if t not in ("user", "assistant"):
            continue
        msg = parse_message_field(ev.get("message", "{}"))
        role = msg.get("role", t)
        content = msg.get("content", "")
        blocks = extract_text_and_tools(content)
        if not blocks:
            continue
        # Tool-result blocks come in user-role messages; reclassify
        if blocks and all(b["type"] == "tool_result" for b in blocks):
            role = "tool_result"
        # Skip system-reminder-only user messages
        if role == "user":
            joined = " ".join(b.get("text", "") for b in blocks if b["type"] == "text")
            if joined.strip().startswith("<system-reminder>") and "</system-reminder>" in joined[-50:]:
                continue
        turns.append(Turn(role=role, blocks=blocks, timestamp=ev.get("timestamp", "")))
    return turns


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--session", required=True, type=Path)
    ap.add_argument("--start-prompt", required=True)
    ap.add_argument("--end-prompt", default=None)
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--title", default="Conversation Transcript")
    ap.add_argument("--intro", default="An exported Claude Code conversation. "
                                       "Tool calls and results are collapsed by default — click to expand.")
    ap.add_argument("--no-sanitize", action="store_true")
    args = ap.parse_args()

    events = load_session(args.session)
    sliced = find_slice(events, args.start_prompt, args.end_prompt)
    turns = build_turns(sliced)
    do_sanitize = not args.no_sanitize
    out_html = render_html(turns, args.title, args.intro, do_sanitize)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(out_html, encoding="utf-8")
    print(f"wrote {args.out} ({len(turns)} turns, {args.out.stat().st_size:,} bytes, "
          f"sanitize={'on' if do_sanitize else 'off'})")


if __name__ == "__main__":
    main()
