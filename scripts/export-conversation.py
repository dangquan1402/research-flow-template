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
@page { size: A4; margin: 18mm 16mm; }
body {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
  font-size: 11pt; line-height: 1.5; color: #1f2328;
  max-width: 880px; margin: 24px auto; padding: 0 16px;
  background: #fafbfc;
}
h1 { font-size: 20pt; border-bottom: 2px solid #d0d7de; padding-bottom: 8px; }
.intro { background: #f6f8fa; border: 1px solid #d0d7de; border-radius: 8px; padding: 12px 16px; margin: 16px 0 24px; }
.turn { margin: 16px 0; padding: 12px 16px; border-radius: 8px; }
.turn.user { background: #ddf4ff; border-left: 4px solid #0969da; }
.turn.assistant { background: #ffffff; border: 1px solid #d0d7de; }
.turn.tool_result { background: #f6f8fa; border-left: 4px solid #57606a; font-size: 10pt; }
.turn .role { font-weight: 600; font-size: 9.5pt; text-transform: uppercase; letter-spacing: 0.05em; color: #57606a; margin-bottom: 8px; }
.turn.user .role { color: #0969da; }
.thinking { background: #fff8c5; border-left: 3px solid #d4a72c; padding: 8px 12px; margin: 8px 0; font-size: 10pt; color: #57606a; font-style: italic; }
.thinking::before { content: "💭 "; font-style: normal; }
details { background: #f6f8fa; border: 1px solid #d0d7de; border-radius: 6px; padding: 6px 12px; margin: 8px 0; font-size: 10pt; }
summary { cursor: pointer; font-weight: 600; user-select: none; color: #1f2328; }
summary code { background: rgba(175, 184, 193, 0.2); padding: 1px 5px; border-radius: 4px; font-size: 9.5pt; }
details[open] summary { margin-bottom: 8px; }
details .body { margin-top: 4px; }
pre {
  background: #0d1117; color: #c9d1d9;
  border-radius: 6px; padding: 10px 12px; overflow-x: auto;
  white-space: pre-wrap; word-break: break-word;
  font-family: ui-monospace, SFMono-Regular, "SF Mono", Menlo, monospace;
  font-size: 9.5pt; line-height: 1.4;
}
.turn.user pre { background: #0d1117; }
code {
  font-family: ui-monospace, SFMono-Regular, "SF Mono", Menlo, monospace;
  font-size: 9.5pt; background: rgba(175, 184, 193, 0.2); padding: 1px 5px; border-radius: 4px;
}
pre code { background: transparent; padding: 0; }
.tool-error { border-left: 3px solid #cf222e; }
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


def render_tool_use(block: dict, do_sanitize: bool) -> str:
    name = block["name"]
    inp = block.get("input", {})
    # Pick a useful summary line
    if name == "Bash":
        cmd = inp.get("command", "")
        if do_sanitize:
            cmd = sanitize(cmd)
        summary = f"🔧 <code>Bash</code> — <code>{html.escape(cmd[:120])}</code>"
        body = f"<pre><code>{html.escape(cmd)}</code></pre>"
    elif name in ("Edit", "Write"):
        path = inp.get("file_path", "")
        if do_sanitize:
            path = sanitize(path)
        summary = f"🔧 <code>{name}</code> — <code>{html.escape(path)}</code>"
        # Show truncated content
        if name == "Edit":
            old = inp.get("old_string", "")[:300]
            new = inp.get("new_string", "")[:300]
            if do_sanitize:
                old, new = sanitize(old), sanitize(new)
            body = (f"<p><b>old:</b></p><pre><code>{html.escape(old)}</code></pre>"
                    f"<p><b>new:</b></p><pre><code>{html.escape(new)}</code></pre>")
        else:
            content = inp.get("content", "")[:600]
            if do_sanitize:
                content = sanitize(content)
            body = f"<pre><code>{html.escape(content)}</code></pre>"
    elif name == "Read":
        path = inp.get("file_path", "")
        if do_sanitize:
            path = sanitize(path)
        summary = f"🔧 <code>Read</code> — <code>{html.escape(path)}</code>"
        body = f"<p>Read <code>{html.escape(path)}</code></p>"
    else:
        summary = f"🔧 <code>{html.escape(name)}</code>"
        raw = json.dumps(inp, indent=2)[:1000]
        if do_sanitize:
            raw = sanitize(raw)
        body = f"<pre><code>{html.escape(raw)}</code></pre>"
    return f"<details><summary>{summary}</summary><div class='body'>{body}</div></details>"


def render_tool_result(block: dict, do_sanitize: bool) -> str:
    text = block["text"]
    if do_sanitize:
        text = sanitize(text)
    # Truncate very long outputs
    if len(text) > 4000:
        text = text[:4000] + f"\n… ({len(text) - 4000:,} more chars truncated)"
    cls = "tool-error" if block.get("is_error") else ""
    label = "❌ result" if block.get("is_error") else "📤 result"
    return (f"<details class='{cls}'><summary>{label}</summary>"
            f"<div class='body'><pre><code>{html.escape(text)}</code></pre></div></details>")


def render_turn(role: str, blocks: list[dict], do_sanitize: bool) -> str:
    parts = [f"<div class='role'>{role}</div>"]
    for b in blocks:
        t = b["type"]
        if t == "text":
            text = b["text"]
            if do_sanitize:
                text = sanitize(text)
            parts.append(render_text_as_paragraphs(text))
        elif t == "thinking":
            text = b["text"]
            if do_sanitize:
                text = sanitize(text)
            parts.append(f"<div class='thinking'>{html.escape(text)}</div>")
        elif t == "tool_use":
            parts.append(render_tool_use(b, do_sanitize))
        elif t == "tool_result":
            parts.append(render_tool_result(b, do_sanitize))
    return f"<div class='turn {role}'>{''.join(parts)}</div>"


def render_html(turns: list[Turn], title: str, intro: str, do_sanitize: bool) -> str:
    body_parts = [f"<h1>{html.escape(title)}</h1>",
                  f"<div class='intro'>{intro}</div>"]
    for t in turns:
        body_parts.append(render_turn(t.role, t.blocks, do_sanitize))
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
