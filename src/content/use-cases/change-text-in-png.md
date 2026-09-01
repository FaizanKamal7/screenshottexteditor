---
title: 'Change Text in a PNG'
metaDescription: 'Change text in any PNG screenshot and get a pixel-accurate result — same font, size, color, and background, no visible edit.'
platform: general
eyebrow: 'Any screenshot, PNG or JPEG'
heroHeadline: 'Change text in a screenshot. Keep every other pixel exactly the same.'
heroSubhead: 'Drop in a PNG or JPEG, click the text you want to change, type the replacement. We detect the font, size, color, and background well enough to erase the old text and rebuild the new text so it belongs.'
painPoints:
  - 'General-purpose photo editors treat text as pixels to smear or clone-stamp, which falls apart the moment you zoom in on a UI element.'
  - 'AI image generators can redraw a whole scene convincingly but struggle to reproduce crisp, small UI text exactly — letterforms drift, kerning drifts, and it shows.'
  - 'Re-typing a screenshot from scratch in Figma means rebuilding a layout you didn’t design and don’t have the source file for.'
related:
  - 'localize-app-store-screenshots'
  - 'edit-text-in-ios-screenshot'
  - 'edit-text-in-android-screenshot'
---

## How it works

This is the general entry point to the same pipeline every page on this site uses. We detect text at the line level with per-character boxes, measure the image's scale factor, and separate glyph pixels from background with a real alpha mask — not a rough rectangle crop.

From there we don't guess at a font with a neural net: we render your original text in a short list of platform-appropriate candidate fonts and score each render against the real alpha mask, refining size and letter-spacing until the score stops improving. Once we're confident the reproduction is close enough, we erase the original with a matching fill (flat color, gradient, or — only as a last resort — inpainting) and render your replacement in its place, matched to the same baseline and anti-aliasing. If the match score comes in low, we say so instead of shipping a guess.
