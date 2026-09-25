# Pilot human review guide

This covers the five pilot checks that need a person: **A3, A4, A5, B4, E2**
(PILOT_PLAN.md §3). Everything is local; nothing is uploaded anywhere.

## How to review

1. Open `pilot/review/index.html` in a browser (double-click it).
2. Type your name in the header.
3. For each item, look at the image and choose **Agree** or **Disagree**. A note
   is required when you disagree: say what is wrong. Progress is kept in your
   browser, so you can stop and come back.
4. Click **Export CSV** and save the file into `pilot/review/completed/`.
5. Run:

   ```powershell
   python scripts/ingest_review.py pilot/review/completed/review_*.csv
   ```

   Then re-run `scripts/validate_pilot.py`. The five checks will show the review
   outcome instead of "pending".

A second reviewer is optional but recommended for A4: each person exports their
own CSV and all files are passed to `ingest_review.py` together. An item passes
only if everyone who answered it agreed.

## Colour key (overlays)

| Colour | Meaning |
|---|---|
| Green | Ground-truth **ink box**: what engines are scored against |
| Blue | Layout box from the browser (should contain the green box) |
| Red, thick | Ignore region (clipped text); should only ever cover the half-visible chip in `m05-chat` |
| Orange | Icon (not text; never a ground-truth line) |
| Magenta | An engine's predicted line box (E2 only) |

## What each check asks, and when it passes

| Check | Items | Question | Pass criterion (unchanged from PILOT_PLAN) |
|---|---|---|---|
| **A3** completeness | 24 base overlays | Every visible piece of text has a green box, and no box sits on non-text | All items agreed |
| **A4** line text | All lines of 4 bases at the largest scale, plus a seeded ≥10% random sample of the other lines | The ground-truth string matches the rendered text exactly: every character, spaces collapsed to one | **Zero tolerance**: a single disagreement fails A4 and means a generator bug to fix |
| **A5** wrapping | Bases with paragraph text | One box per visible line of a wrapped paragraph, following the line breaks you see | All items agreed |
| **B4** overlays | 24 base overlays + 28 variant overlays (2 bases × 14 files) | Green boxes hug the letters with no shift or scale error, in every variant | All items agreed |
| **E2** engine boxes | 4 images × 6 engines | Engine boxes sit on the text they cover. Loose or tight is fine; a systematic shift or scale error is not | All items agreed |

Notes:
- **A4, stress lines:** items marked "stress line" (`Glyph check: Il1| O0o rn m 5S 8B`)
  are confusable on purpose. Judge them against the rendered glyphs, zooming in if
  needed.
- **A4, small crops:** crops from 1x renders are enlarged with nearest-neighbour
  scaling, so they look blocky. That's expected; judge the characters.
- **A4, separators:** `·` (middle dot) is the correct character where you see a
  raised dot, not a hyphen.
- **B4, 50% variants (V12, V13):** these use boxes measured on the downscaled image
  itself (amendment A2), so they are slightly wider than half the full-size box.
  That's intended.

## Time estimate

About **1.5 hours** for one reviewer:
- A4: about 270 line crops at a few seconds each (~45 min)
- A3, A5 and B4: about 50 overlays (~30 min)
- E2: 24 overlays (~10 min)
