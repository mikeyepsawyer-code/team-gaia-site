# Proportional vs. absolute measurement

**Applies to:** any build with more than one size-sensitive dimension —
page layout, print/export dimensions, UI components, physical
fabrication specs, timing/pacing in audio or video.

## The instruction

Before doing any sizing or layout math, classify every measurement
involved as one of two kinds, out loud, before touching a formula:

- **Proportional** — this must scale with whatever it's relative to
  (container size, page size, total duration, total budget). If the
  container gets bigger, this should get bigger by the same factor.
- **Absolute** — this must stay a fixed real size no matter what else
  changes. If the container gets bigger, this should NOT change.

Do this classification explicitly, in writing, before deriving any
formula — not as an assumption carried in your head. Then keep the
two kinds in separate variables/formulas rather than letting an
absolute quantity get pulled into a proportional calculation (or vice
versa) partway through.

## Why this matters

The failure mode is quiet: a ratio or size that was only ever correct
at one specific reference size (the one you happened to test or
design at) will look right in the preview you checked and wrong at
every other size, zoom level, or export target. It's not caught by
reviewing the formula — the formula looks fine — it's only caught by
checking the actual output at more than one scale.

## How to verify

Don't trust one preview. Generate or render the output at two or
three different sizes/scales/durations and directly measure the
specific relationships that are supposed to hold (a ratio, an
alignment, an absolute size) at each one. If a ratio-critical
measurement isn't exactly right at every scale you check, something
proportional and something absolute got mixed together.

*Last updated: 2026-09-09*
