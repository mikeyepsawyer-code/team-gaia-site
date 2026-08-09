# Gold Styles Audit — v1
Compiled Aug 9, 2026. Source: full scan of index.html, cover_build.py,
COVER_PRODUCTION_STANDARD.txt, and assets/effects/gold-shimmer-snippet.html.

This is a catalog, not a recommendation — it's the "gather" step before we
pick winners and build demo sheets.

---

## 1. THE GOLD TREATMENTS (9 distinct, found live in the codebase)

### A. Gold Foil Shimmer (`shimmer-final` / `GOLD_FOIL_STOPS`)
- **Where it lives:** the animated web treatment — baked into every shimmer
  MP4 (BOOKS, ADULT, TITLES, Nike card title).
- **Structure:** 25° linear gradient, 17 stops, cycling dark-bronze →
  bright-cream → amber three times across the box, animated back-and-forth
  (never loops — avoids a seam). Six radial "sparkle" highlights layered
  underneath.
- **Character:** busy/alive in motion, reads as genuine shifting foil. Was
  found too busy as a frozen single frame — that's why #B exists.
- **Has a reference sheet?** No — it's video-only, can't be demo-sheeted the
  same way as a static render.

### B. Static Gold Foil (`STATIC_GOLD_FOIL_STOPS`)
- **Where it lives:** default title/subtitle/author treatment for static
  JPEG covers, via `apply_chiseled_gold()`.
- **Structure:** calmer 7-stop version of A — one cream highlight, warm
  yellow-gold shoulders, umber shadow ends. Single highlight band instead
  of three.
- **Character:** the "Beveled Gold" treatment — chiseled emboss bevel
  (real distance-transform facets) + airbrush + catch-light. **This is
  almost certainly what's live on Fountain of Youth v5** — the one you
  called our best work.
- **Has a reference sheet?** **Yes** — `BEVELED_GOLD_reference_sheet.jpg`,
  3 backgrounds × multiple sizes, already built (Aug 7).

### C. Pastel Gold (`PASTEL_GOLD_FOIL_STOPS`)
- **Where it lives:** same pipeline as B, swapped in for light/watercolor
  covers where B's near-black shadow reads too heavy.
- **Structure:** identical shape to B, all stops raised toward midtone —
  no near-black anywhere.
- **Has a reference sheet?** No.

### D. Kintsugi Gold Function (`gold_text`, §3D)
- **Where it lives:** Kintsugi cover only (documented "approved" standard).
- **Structure:** ink-extent-based sine curve, single lerp (mid-gold →
  highlight-gold), flat hold from 70–100% of letter height, no shadow stop
  at all.
- **Character:** flatter, cleaner, less dimensional than the foil family —
  no bevel, no shadow band.
- **Has a reference sheet?** No.

### E. Radiant Sensitivity Metallic System (§3C)
- **Where it lives:** Radiant Sensitivity cover; documented as a general
  "metallic gradient system" so may be reused elsewhere.
- **Structure:** 5-stop *vertical* gradient (not angled) — shadow → midtone
  → highlight plateau (center) → midtone → deep shadow. Comes in a GOLD
  variant (base 225,170,45) and a COPPER variant (base 210,105,30).
- **Character:** simple front-lit metallic look, more traditional "embossed
  medal" than "foil sheet."
- **Has a reference sheet?** No.

### F. Art Amōre — "Amore" Burnished Gold
- **Where it lives:** Art Amōre cover, the script word only.
- **Structure:** 7 solid offset layers + 2 translucent overlay passes,
  darker/warmer base (200,162,42) than the foil family, heavy drop-shadow
  feel from the layer stack.
- **Character:** the warmest/darkest of all the golds — reads more antique
  bronze than bright foil.
- **Has a reference sheet?** No.

### G. Art Amōre — "Subtle Art Of" Black Granite + Gold Highlight
- **Where it lives:** Art Amōre cover, the non-script line.
- **Structure:** mostly dark granite fill; only the two innermost offset
  layers are gold, used as a thin edge highlight, not a fill.
- **Character:** not really a "gold text" — gold as accent/rim light only.
  Worth keeping in the catalog but it's a different category from the rest.
- **Has a reference sheet?** No.

### H. Fountain of Youth — Author Gold Metallic
- **Where it lives:** Fountain of Youth cover, "Michael Sawyer" only (the
  title itself is a water-blue gradient, not gold).
- **Structure:** 3-stop metallic (108,81,22) → (255,248,170) → (91,62,12).
- **Has a reference sheet?** No.

### I. Website inline CSS golds (2 variants, not from cover_build.py at all)
- **"Ecstasy is not hedonism…" gradient** (135°, 8 stops, base #9a7020,
  peak #fff8c0/#ffee80) — the one you flagged as very strong at
  medium-small sizes.
- **"Michael writes…" gradient** (135°, 7 stops, base #784614, peak
  #fff2c0) — close cousin of the above but leans copper-warmer, no
  reference sheet comparing them side by side exists.
- These were hand-written directly in index.html and never run through
  the cover pipeline, so they're visually close to but not identical to
  any of A–H.

---

## 2. GAP: NAMED COLORWAYS NOT FOUND IN CODE

Memory references **Classic Gold, Shadow Gold, Painted Gold, and Olive
Shadow** as named colorways alongside Beveled Gold and Pastel Gold. Only
Beveled Gold (B) and Pastel Gold (C) exist as saved constants in
`cover_build.py`. The other three were likely one-off inline parameters
from past sessions that were never promoted to named, reusable stops —
meaning their exact values aren't recoverable from the repo as it stands.
If you want them back, we'd be reconstructing from memory/description
rather than pulling a stored value.

---

## 3. FONTS CURRENTLY TOUCHING GOLD TEXT (7 found — over your ~6 target)

| Font | Where used |
|---|---|
| Cinzel (400 + 700) | Titles, "SUBTLE ART OF," Fountain of Youth title, section headers |
| Cormorant Garamond (+ italic) | Subtitles, most homepage tags/quotes |
| Parisienne | "Amore," other script title words |
| Liberation Serif Italic | Some subtitles (system font) |
| Lora Variable | Author name across most covers (system font) |
| Qwitcher Grypen | "Tender" (Spank Me Tender) — flagged in the standard itself as "good enough for now, revisit" |
| Permanent Marker | "SPANK ME" |

Only Cinzel is actually vendored in the repo (`assets/fonts/`). Everything
else is fetched via `@fontsource`/system fonts at build time.

---

## 4. SUGGESTED NEXT STEP

Once you've looked this over: pick which 5–6 of the 9 treatments (plus
maybe a resurrected Shadow/Painted Gold if you want to reconstruct them)
are worth carrying forward, and I'll build reference sheets for each,
matching the Beveled Gold sheet's format — same font, same size steps,
same 3 background tones — so they can be compared apples-to-apples before
we standardize.
