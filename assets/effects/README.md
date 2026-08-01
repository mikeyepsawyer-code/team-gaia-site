# assets/effects/

Reusable visual effect snippets for the site, separate from cover art
and static images.

## gold-shimmer-snippet.html — APPROVED, July 26 2026
Dimensional, animated gold text treatment for book titles. Clean,
drop-in code with full usage instructions and known-issue notes
written directly into the file — read it before touching this effect.

REGRESSED July 26, FIXED Aug 1 2026 — before changing background-attachment
or background-size on the face layer, read the "KNOWN LIMITS" block inside
the file in full. A same-day fix for one bug (titles going blank below the
fold) deleted `background-attachment: fixed` outright instead of just
enlarging that layer's background-size, which silently reopened a
different, already-solved bug (two-line shimmer desync). It went live and
sat broken for 6 days before anyone caught it visually. The two known bugs
share one root cause and one correct fix — do not "solve" one by removing
`fixed`.

See also `gold-shimmer-demo.html` for the full comparison of variants
that were tried and rejected along the way (useful if revisiting any
design decision, e.g. why it's back-and-forth motion instead of a
one-directional loop).

Referenced in: v5.2_INNER_COUNCIL_CHARTER (or later), Section 6A —
Website Operations, under REPO STRUCTURE.
