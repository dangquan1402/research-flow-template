---
name: import
description: Bulk-import an existing project into the research flow — copies artifacts into sources/, extracts entities/findings, scaffolds memory, and optionally creates a research goal
user_invocable: true
---

# /import — Import an Existing Project

Use this when you have an existing project (code repo, research notes, docs folder, dataset) and want to bring it into the research flow as structured working memory.

**Difference from `/analyze`:** `/analyze` ingests one source at a time interactively. `/import` bulk-ingests a whole project in one pass — it maps the structure, classifies artifacts, copies them to `sources/`, and builds initial memory in one operation.

---

## Gather Information

Ask the user for:

1. **Source path or URL** — Local directory path, git remote URL, or glob pattern (e.g. `../my-project`, `https://github.com/org/repo`, `./docs/**/*.md`)
2. **What to import** — Everything? Specific subdirectories? File types? (code, docs, notebooks, data, notes)
3. **Research goal** (optional) — Should we create a `/research` goal for this project, or attach it to an existing one?
4. **Slug** — Short identifier for this project (used in file names, e.g. `my-project`)
5. **Depth of analysis** — Quick (summary + key files only) or deep (extract findings from every file)?

---

## Workflow

### Step 1: Resolve and Inspect the Source

**If local path:**
```bash
ls -la <path>
find <path> -type f | head -60   # preview structure
```

**If git remote:**
```bash
# Clone to a temp location — do NOT clone into this repo
git clone --depth 1 <url> /tmp/import-<slug>
ls -la /tmp/import-<slug>
```

Build a mental map of the project:
- What kind of project is it? (ML, web, research, data pipeline, etc.)
- What are the key directories and file types?
- How large is it? (file count, rough size)
- Does it have existing docs, READMEs, notebooks, or notes?

---

### Step 2: Classify Artifacts

Walk the source and group files into import tiers:

| Tier | What | Action |
|------|------|--------|
| **Primary** | READMEs, design docs, research notes, papers, notebooks | Copy to `sources/` + deep analysis |
| **Code** | Source files (`.py`, `.ts`, etc.) | Copy key files to `sources/code/` + summarize architecture |
| **Data** | Datasets, CSVs, result files | Note existence + metadata only (don't copy large files) |
| **Config** | pyproject.toml, package.json, YAML configs | Copy to `sources/config/` + extract deps/settings |
| **Skip** | `.git/`, `node_modules/`, `__pycache__/`, build artifacts | Ignore entirely |

---

### Step 3: Copy Artifacts to sources/

Create a subdirectory: `sources/<slug>/`

For each **Primary** and **Code** file to import:
```bash
cp <source-file> sources/<slug>/<relative-path>
```

For large files (>500KB) or binary data: do **not** copy. Instead create a pointer file:
```
sources/<slug>/<filename>.ref.md
```
with metadata (original path, size, format, description).

Sources are **immutable** after creation. Never modify files in `sources/` after this step.

Create a manifest: `sources/<slug>/MANIFEST.md`
```markdown
---
title: "Import: <project-name>"
created: <today>
slug: <slug>
origin: <path-or-url>
imported_by: <current-branch>
---

## Project Overview
<2-3 sentence description>

## Files Imported
| File | Type | Notes |
|------|------|-------|
| ... | ... | ... |

## Files Skipped
| File/Dir | Reason |
|----------|--------|
| node_modules/ | dependency cache |
| ... | ... |
```

---

### Step 4: Extract Entities

Read each imported Primary file. For every significant entity (person, org, concept, tool, library, dataset, model):

1. Check `memory/entity-registry.json` — skip if already registered
2. If new: create `memory/entities/<entity-slug>.md` using the template in `docs/memory-page-template.md`
3. Register in `memory/entity-registry.json`

Pay special attention to:
- **Tools and libraries** used (from imports, package files, READMEs)
- **Models and architectures** referenced
- **Datasets** mentioned
- **Authors / contributors** (from git log, paper headers, READMEs)
- **Key concepts** the project is built around

---

### Step 5: Extract Findings

For each significant insight, design decision, or result found in the imported material:

Create `memory/findings/<finding-slug>.md` using the finding template.

Look for findings in:
- README "results" or "benchmarks" sections
- Notebooks with output cells
- Comments explaining *why* decisions were made
- Existing docs or design notes
- Git commit messages (if cloned)

**Apply verification gates** on each finding:
- `source` — directly stated in the imported material → cite the file
- `analysis` — inferred from code/structure → show reasoning
- `unverified` — mentioned but not validated
- `gap` — implied by what's missing

**Apply FUNGI counter-argument** — every finding needs "What would disprove this?"

---

### Step 6: Identify Open Questions

From the imported project, identify what was unresolved, TODOs, or areas that need research:

Look for:
- TODO/FIXME comments in code
- "Future work" sections in docs
- Failing or skipped tests
- Missing documentation
- Hardcoded values that suggest unknowns

For each, create `memory/open-questions/<question-slug>.md`.

---

### Step 7: Optionally Create a Research Goal

If the user wants a research goal for this project, run the `/research` workflow:

```bash
git checkout main
git checkout -b research/GH-<issue-number>-<slug>
```

Otherwise, commit the import to the current branch.

---

### Step 8: Update Memory Index and Log

Update `memory/index.md` — add all new entities, findings, open questions, and the source manifest.

Append to `memory/log.md`:
```
## [<today>] import | <project-name>
- Origin: <path-or-url>
- Source manifest: sources/<slug>/MANIFEST.md
- Files imported: <count>
- Entities created: <count> (<list>)
- Findings created: <count> (<list>)
- Open questions created: <count> (<list>)
- Branch: <current-branch>
```

---

### Step 9: Commit

```bash
git add sources/<slug>/ memory/
git commit -m "research(<slug>): import existing project — <count> findings, <count> entities"
git push
```

---

## Output

Report to user:
- **Import summary:** files copied, files skipped, manifest path
- **Entities discovered:** list with one-line descriptions
- **Findings extracted:** list with confidence levels
- **Open questions identified:** list with priorities
- **Recommended next step:** `/analyze` a specific file in depth, or `/research` to define a goal around this project

---

## Notes

- If the project is very large (>200 files), ask the user to narrow the scope before importing — deep analysis of everything will be slow and noisy.
- If importing a git repo, always clone to `/tmp/` first. Never clone inside this repo.
- Prefer depth over breadth: 5 well-documented findings beat 50 shallow ones.
- If the project already has structured notes (e.g. a `docs/` or `notes/` folder), prioritize those over raw code.
