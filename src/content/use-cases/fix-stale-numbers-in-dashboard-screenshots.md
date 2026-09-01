---
title: 'Fix Stale Numbers in Dashboard Screenshots'
metaDescription: 'Update outdated metrics in a dashboard screenshot for a deck or doc without re-opening the app or rebuilding the slide.'
platform: web
eyebrow: 'Decks & docs'
heroHeadline: 'The dashboard screenshot is a year old. The number in it doesn’t have to be.'
heroSubhead: 'A quarterly deck, a case study, an onboarding doc — all full of dashboard screenshots with numbers that quietly went stale. Update the figure in place instead of re-logging into the product, re-arranging the browser window, and re-taking the shot.'
painPoints:
  - 'The dashboard state that produced the original screenshot may not exist anymore — different account, different quarter, different UI.'
  - 'Re-taking the screenshot means matching browser chrome, zoom level, and window size all over again to get something that still fits the slide.'
  - 'A single deck can carry the same stale metric across a dozen slides, each needing the same manual fix.'
related:
  - 'change-text-in-png'
  - 'redact-demo-data-in-screenshots'
  - 'edit-text-in-android-screenshot'
---

## How it works

Web dashboards mostly render in Inter or the browser's system-ui stack, both handled directly. We detect the number as a text region like any other, measure the actual color and weight it's rendered in — including on a colored KPI card or pill, which we detect as a distinct UI element before touching the text — and rebuild it once your replacement figure is typed in.

Because the pipeline works region-by-region, you can update one number, a whole label-and-value block, or every stale metric across a screenshot in one pass, and export straight back into your deck.
