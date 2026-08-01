# assets/effects/

Reusable visual effect snippets for the site, separate from cover art
and static images.

## gold-shimmer-snippet.html — APPROVED, July 26 2026
Dimensional, animated gold text treatment for book titles. Clean,
drop-in code with full usage instructions and known-issue notes
written directly into the file — read it before touching this effect.

DO NOT change background-attachment or background-size on the face layer
without reading the "KNOWN LIMITS" block inside the file in full first —
this effect has been broken twice by well-intentioned edits to those two
properties:
  1. July 26 2026: `fixed` was removed to fix a scroll-position cutoff
     bug. Not currently an issue (no title wraps to two lines), but if
     it recurs, don't do this — see fix #2 below.
  2. Aug 1 2026: background-size was enlarged from 1200px 220px to
     1200px 100vh to try to fix the same cutoff concern. This actually
     broke the gradient — stretching the box compressed the visible
     color range down to the dark end, making every title look dark
     and muddy. Reverted same day.
The correct fix for a below-the-fold cutoff, if one ever shows up again,
is to compute each element's own background-position-y in JS from its
live getBoundingClientRect().top — not to touch background-size.

See also `gold-shimmer-demo.html` for the full comparison of variants
that were tried and rejected along the way (useful if revisiting any
design decision, e.g. why it's back-and-forth motion instead of a
one-directional loop).

Referenced in: v5.2_INNER_COUNCIL_CHARTER (or later), Section 6A —
Website Operations, under REPO STRUCTURE.
