# HemeAtlas — Claude Code Context

Public hematology atlas for peripheral blood cell morphology training. Static site on GitHub Pages — no backend, no build step, no auth.

**Live:** https://cai-luke.github.io/HemeAtlas
**Repo:** https://github.com/cai-Luke/HemeAtlas

---

## Repository Structure

```
HemeAtlas/
├── index.html          ← Student Training Atlas (public-facing app)
├── admin.html          ← Curator tool (database maintenance)
├── data/
│   └── atlas.csv       ← CSV database (13,934 records, all finalized)
├── images/
│   ├── CW_00001.jpg … CW_01725.jpg   ← Cell Wiki (1,725 images)
│   └── KO_00001.jpg … KO_12209.jpg   ← KU-Optofil (12,209 images)
├── ko_filename_map.csv                ← KU-Optofil provenance (local only)
└── CLAUDE.md                          ← This file
```

Both HTML files are single-file apps (HTML + CSS + JS inline). No frameworks, no build tools.

---

## How the Site Works

1. User opens `index.html` (or `admin.html`) in browser
2. App fetches `./data/atlas.csv` via `fetch()` on page load
3. CSV parsed client-side; only `path_status = finalized` records appear
4. Images loaded as `./images/{filename}` (no blob URLs)
5. `const IMAGE_BASE = './images/'` in both files — change this if images move to a CDN

---

## CSV Schema

33 columns. Key fields:

| Field | Purpose |
|---|---|
| `image_id` | Unique ID. Prefixes: `CW_` (Cell Wiki), `KO_` (KU-Optofil), `USR_` (user-added) |
| `filename` | Image filename, becomes URL path segment |
| `path_label` | Cell type — the primary display label |
| `path_status` | Must be `finalized` to appear in either tool |
| `path_confidence` | `classic` or `borderline` |
| `path_commentary` | Teaching notes shown to students |
| `correction_label` | Overrides `path_label` when set |
| `tags` | Morphology/aberration tags (comma-separated) |
| `case_tag` | Source ID: `cellwiki`, `cellwiki-AML`, `ku-optofil`, etc. |
| `tech_note` | Internal notes |

Other columns exist for schema compatibility with the parent project but are blank in this fork: `uploaded_by`, `upload_date`, `tech_label`, `tech_id`, `tech_date`, `tech_status`, `image_quality`, `audit_trail_json`, etc.

### Valid Cell Types

`NEUTROPHIL` · `BAND` · `LYMPHOCYTE` · `REACTIVE LYMP` · `MONOCYTE` · `EOSINOPHIL` · `BASOPHIL` · `BLAST` · `PROMYELOCYTE` · `MYELOCYTE` · `METAMYELOCYTE` · `NRBC` · `PLASMA` · `OTHER`

### Current Census (by effective label)

| Cell Type | Count | Cell Type | Count |
|---|---|---|---|
| LYMPHOCYTE | 5,818 | BAND | 235 |
| EOSINOPHIL | 1,912 | METAMYELOCYTE | 294 |
| REACTIVE LYMP | 1,538 | MYELOCYTE | 134 |
| MONOCYTE | 1,587 | PROMYELOCYTE | 167 |
| BLAST | 988 | PLASMA | 142 |
| BASOPHIL | 570 | OTHER | 54 |
| NRBC | 302 | NEUTROPHIL | 193 |

---

## Curator Workflow (admin.html)

1. Open `admin.html` (locally or on live site)
2. Browse, tag, exclude, relabel, set confidence, add commentary
3. **Export CSV** → downloads as `atlas.csv`; a modal appears with ready-to-paste deploy commands and a Copy button
4. Paste commands into Terminal — they copy the file, commit, and push in one go

### Adding New Images (Batch Import)

1. Use Batch Import in `admin.html` — assign cell type, preview, finalize
2. Exported CSV will include new `USR_` records
3. Copy image files into `./images/`
4. `USR_` IDs auto-increment from highest existing USR_ number
5. `git add -A && git commit -m "Add new images" && git push origin main`

---

## Data Sources & Licensing

**Cell Wiki** (CW_ prefix, 1,725 records): Scraped from cellwiki.net. Educational use with attribution. Includes normal morphology + disease-specific pathology + 44 aberration tags.

**KU-Optofil** (KO_ prefix, 12,209 records): Yarıkan et al. 2026, DOI: 10.1038/s41597-026-06761-y. CC BY 4.0 per Zenodo; paper states CC BY-NC-ND 4.0 — **license confirmation pending with authors.** 10 cell classes from Sysmex DI-60. No tags. Segmented neutrophils excluded from import.

Attribution is rendered in the student atlas footer.

---

## Development Conventions

- **Single-file HTML** — all CSS and JS inline. Do not extract into separate files.
- **No build step** — raw HTML served by GitHub Pages.
- **Chunked rendering** — both tools use IntersectionObserver to load 60 cards at a time. Essential at 14k images.
- **Validation** — after editing HTML, validate syntax with `node -e "require('acorn').parse(fs.readFileSync('index.html','utf8').match(/<script[^>]*>([\s\S]*?)<\/script>/i)[1], {ecmaVersion:2020, sourceType:'script'})"` (or equivalent). A previous escaped-backtick bug silently broke the entire script.
- **CSV integrity** — every `filename` in atlas.csv must have a corresponding file in `./images/`. Every image in `./images/` should have a record in atlas.csv.
- **Git** — repo uses HTTPS remote with personal access token (classic, `repo` scope).

---

## Known Issues & Open Items

- [ ] Confirm KU-Optofil license with dataset authors before broad public launch
- [ ] `image_quality` field exists in schema but is not surfaced in UI — kept for compatibility
- [ ] KO_ records have no tags — tagging pass would improve search/filtering
- [ ] No automated CI/CD — validation is manual

---

## Key Technical Details

- **Poisson-weighted trainer** — `buildWeightedQueue()` balances cell type exposure despite class imbalance
- **Image augmentation** — trainer randomly rotates/flips to prevent orientation memorization
- **Cell adjacency map** — `ADJACENT` constant defines confusable pairs for Compare mode
- **Batch Import** — uses blob URLs for local preview only; finalized records use static URLs
- **Permalink support** — curator supports URL hash navigation to specific records
- **Excluded cell isolation** — `path_status = 'excluded'` records are filtered out of every regular view (cell types, tags, flagged, corrected, search). They only appear in a dedicated **Excluded** section at the bottom of the curator sidebar, which shows a per-cell-type breakdown. View keys: `excluded` (all) and `excluded:BLAST` etc. (by type). `renderSidebarExcluded()` rebuilds this section on every `setView()` call.
- **CSV export filename** — exports as `atlas.csv` (not timestamped) so it can be dropped directly into `data/` without renaming. Post-export modal shows the deploy command block with a clipboard Copy button; persists until dismissed.
- **Tag Reference poster** (`index.html`) — "🏷 Tag Reference" sidebar button (shown when tags exist) opens a full-width poster view inside `.main`. Nine collapsible accordion groups ordered by clinical category, all collapsed by default. Each group lists tags with count + 1–2 thumbnails; clicking a tag expands an inline image grid with the same IntersectionObserver chunked rendering (60/batch) as the main grid. `TAG_GROUPS` constant defines the groups and tag order. `showTagPoster()` / `hidePoster()` / `leavePoster()` manage state; `setMode()` and `setView()` both call `hidePoster()` on navigation away.
- **Differential Counter** (`index.html`) — "Diff Counter" mode tab. Digital replacement for a mechanical differential counter for use at the microscope. `DC` state object tracks counts, history, RBC grades, and lock state. `DC_WBC` = CELLS minus NRBC (14 types). `RBC_GROUPS` / `RBC_FEATURES` define 16 morphology features grouped by category (Size, Color, Shape, Distribution, Inclusions), each graded None/1+/2+/3+. WBC counter locks at 100; NRBC counted separately and stays active after lock. Undo (Backspace) walks back through `DC.history`. Click RBC panel to activate keyboard nav (↑↓ to move focus, 0–3 to set grade, Esc to exit). Key mappings reuse `KEY_TO_CELL` from the trainer. Print report opens a new window with a clean formatted HTML report (non-zero rows only). CSV export includes all WBC types plus non-None RBC findings. `dcInit()` lazy-initializes on first entry to the mode. `setMode('diff')` calls `dcInit()`.
