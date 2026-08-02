# assets/effects/

Reusable visual effect snippets for the site, separate from cover art
and static images.

# assets/effects/

Reusable visual effect snippets for the site, separate from cover art
and static images.

## gold-shimmer-snippet.html — APPROVED, July 26 2026
Dimensional, animated gold text treatment for book titles. Clean,
drop-in code with full usage instructions and known-issue notes
written directly into the file — read it before touching this effect.

ROOT CAUSE FOUND Aug 1 2026 (READ THIS FIRST): a full day was lost
chasing what looked like a rendering bug in Samsung Internet — gold
titles showing up as flat dark maroon/brown, no gradient variation.
Five completely different CSS/SVG techniques were tried; all failed
the same way. The actual cause was Samsung Internet's "Dark mode for
websites" feature repainting the page's colors algorithmically,
because it didn't recognize this site as already being dark-themed
by design. It wasn't a code bug at all.

THE FIX: index.html's <head> now has:
  <meta name="color-scheme" content="dark">
and the stylesheet has `color-scheme: dark;` on the html selector.
This tells the browser the page supplies its own dark theme, so
force-dark/auto-dark algorithms (Samsung Internet, and the same
feature exists in stock Android Chrome and most Android browsers)
leave its colors alone. If any NEW page is added to this site
(a preview page, a test page, anything with its own <head>), it
needs this same meta tag or it will be vulnerable to the exact same
bug. Don't re-diagnose this as a CSS/layer/gradient problem — check
this meta tag is present first.

Everything below this point is prior, now-superseded debugging from
before the real cause was found. Kept for history, not as guidance:
the specific CSS changes described did have real (minor) side effects
worth knowing about, but none of them were the actual bug.

  - July 26 2026: `fixed` was removed from background-attachment to
    fix a scroll-position cutoff bug on below-the-fold titles. Genuine
    fix for a real (separate, minor) issue — not related to the dark
    mode bug above.
  - Aug 1 2026: background-size was briefly enlarged from 1200px 220px
    to 1200px 100vh. This was a real mistake (compressed the gradient's
    visible range) and was reverted same day — but it was never the
    cause of the "dark and muddy on Samsung" symptom either. That was
    dark mode the whole time.

See also `gold-shimmer-demo.html` for the full comparison of variants
that were tried and rejected along the way (useful if revisiting any
design decision, e.g. why it's back-and-forth motion instead of a
one-directional loop).

Referenced in: v5.2_INNER_COUNCIL_CHARTER (or later), Section 6A —
Website Operations, under REPO STRUCTURE.
