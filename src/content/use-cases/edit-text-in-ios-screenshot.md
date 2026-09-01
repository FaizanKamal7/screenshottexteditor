---
title: 'Edit Text in an iOS Screenshot'
metaDescription: 'Change text in an iPhone screenshot without it looking edited. Matches SF Pro rendering, retina scale, and iOS anti-aliasing down to the pixel.'
platform: ios
eyebrow: 'iOS & iPadOS'
heroHeadline: 'Edit iOS screenshot text without it ever looking edited.'
heroSubhead: 'iOS screenshots are unforgiving — 3x retina text is small, crisp, and instantly reveals a bad edit. We detect the actual scale factor, match the SF Pro substitute at the right weight and size, and re-render at native resolution.'
painPoints:
  - 'Small SF Pro text at 3x retina scale is dense enough that a slightly-off weight or size is immediately visible, especially at 400% zoom.'
  - 'macOS and iOS both apply stem-darkening that makes text render heavier than the same nominal weight looks on Windows — most editing tools ignore this entirely.'
  - 'Status bar, navigation bar, and button-label text all sit on different backgrounds — flat, blurred, and colored — and each needs a different erase strategy.'
related:
  - 'localize-app-store-screenshots'
  - 'change-text-in-png'
  - 'redact-demo-data-in-screenshots'
---

## How it works

We can't legally bundle SF Pro, so we ship Inter as a metric-compatible open substitute and label it honestly in the editor — no silent substitution. Before matching, a quick platform check confirms this is an iOS screenshot so the font search starts from the right family instead of scanning thousands of candidates blind.

From there it's the same deterministic pipeline as everywhere else on the site: detect the text region and its scale factor, separate the glyphs from the background pixel-by-pixel, render the substitute font at a range of sizes and weights and score each render against the original, then erase and re-render only once we've found a match good enough to trust. If nothing scores high enough, the region gets flagged low-confidence instead of shipped — a visible warning beats an invisible failure.
