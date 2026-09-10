# Solving for shared targets, not approximating toward them

**Applies to:** any build where two independently-constructed pieces
need to visually or functionally meet — two halves of a layout, a
spine meeting a cover, a transition between scenes, a citation
matching a source, a component meeting an API contract.

## The instruction

When two things need to meet at a specific point, don't estimate
where that point is and nudge each piece toward the estimate. Instead:

1. Identify the exact target precisely — and confirm it's the RIGHT
   target. If a person refers to "the edge" or "the bottom line,"
   check whether they mean a visible feature or an invisible
   structural boundary near it — these are easy to conflate and a
   wrong-but-plausible target produces a result that looks deliberate.
2. Once the target is confirmed, derive the dependent measurement
   algebraically FROM that target, not from a ratio or offset borrowed
   from a different reference case.
3. Verify the two pieces actually meet by direct measurement, not by
   eye — a small visible gap or overlap is often sub-pixel/sub-unit
   in the underlying numbers and easy to miss visually while still
   being wrong.

## Why this matters

An approximation (a scaled-down ratio, a "close enough" offset copied
from a similar case) can produce something that LOOKS like an exact
match without being one — the mismatch only shows up when someone
checks closely, or when the scale/context changes. Worse, if the
target itself was misidentified, the result can be verified as
"exact" against the wrong reference and still be visibly wrong to
someone comparing it against what they actually meant.

*Last updated: 2026-09-09*
