# Project Knowledge — Index

GitHub is now canonical for the charter and all project knowledge, tool
documentation, cover work, book texts, and derived previews. Google Drive is
reserved for one thing only: live fine-editing of manuscript text in
progress (Google Docs, tap-to-edit on mobile). Read in this order at the
start of a session:

## 1. Charter (always read first, in full)
`charter/v[latest]_INNER_COUNCIL_CHARTER.txt` — fetch the most recent
version by filename. This is the orientation document: council members,
protocols, catalog, book status register, Drive/GitHub structure.

## 2. Domain-specific knowledge (load only what the task needs)
- **Cover production**: `project-knowledge/COVER_PRODUCTION_STANDARD.txt`
  — physical spec, typography, gold-text builds, bleed standard, per-cover
  frozen parameters, and (Section 8) compositing/ghosted-art learnings.
- **Gold shimmer title effect**: `assets/effects/README.md` and
  `assets/effects/gold-shimmer-snippet.html` — the approved animated title
  technique, its known-limits, and the Aug 1 2026 dark-mode-repaint
  postmortem (read before touching this effect).
- **Website operations**: folded into the charter itself (Section 6A) —
  no separate file.
- **YouTube operations**: NOT YET MIGRATED. Still Project-Knowledge-only as
  of Aug 2 2026 pending Michael providing its content for a GitHub copy.

## 3. Fast lookups
- `CATALOG_REGISTER.txt` (repo root) — one line per book: Drive folder ID,
  cover version, preview URL.

## 4. What stays OFF GitHub, permanently
- **The GitHub PAT itself.** Never commit it — GitHub's own secret scanning
  blocks this anyway. Lives only in Project Knowledge file "Pat".
- Anything containing real credentials or private keys.

## 5. What stays on Drive
- Manuscripts actively being written/edited (native Google Docs only, for
  mobile tap-to-edit).
- Nothing else is canonical there — Drive is a workspace, not an archive.
  GitHub is the archive.

## Cover art / book text / derived previews
All live under existing repo folders:
- `covers/[book-slug]/` — full-resolution approved cover archives
- `manuscripts/[book-slug]/` — manuscript text archives + review PDFs
- Root-level `[book-slug]-preview.html` files — live preview pages
- `images/` — web-optimized cards, calling cards, cover-art source
  packages (e.g. the Enchante Nike cover project package)
