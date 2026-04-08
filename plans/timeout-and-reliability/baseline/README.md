# Baseline: docs.agno.com Site Crawl

**Date:** 2026-04-08
**Config:** max_depth=2, max_pages=10, current code (no timeout changes)
**Output:** `agno-baseline.json/crawl_results.json`

## Summary

| # | URL | Status | Markdown (chars) | Refs | Notes |
|---|-----|--------|-----------------:|-----:|-------|
| 1 | `/` | success | 849 | 17 | Good content |
| 2 | `` (no trailing slash) | success | 849 | 17 | Same as #1 (redirect duplicate) |
| 3 | `/workflows/overview` | success | **26** | 0 | **Almost empty — SPA/lazy-load issue** |
| 4 | `/agent-os/introduction` | success | **23** | 0 | **Almost empty — SPA/lazy-load issue** |
| 5 | `/agents/overview` | success | **23** | 0 | **Almost empty — SPA/lazy-load issue** |
| 6 | `/introduction` | success | **19** | 0 | **Almost empty — SPA/lazy-load issue** |
| 7 | `/teams/overview` | success | 5063 | 9 | Good content (dedup guardrail triggered: 20/39 sections removed) |
| 8 | `/production/overview` | success | **18** | 0 | **Almost empty — SPA/lazy-load issue** |
| 9 | `/first-agent` | success | 3887 | 7 | Good content (dedup guardrail triggered: 34/56 sections removed) |
| 10 | `/agent-os/control-plane` | success | 4202 | 5 | Good content |

## Key Observations

1. **5 out of 10 unique pages returned almost no content** (< 50 chars). These are likely SPA pages where the `wait_for` JS predicate (`document.querySelector('main') && innerText.length > 50`) never matches because the page either has no `<main>` element or content loads after the predicate check times out.

2. **Pages with good content** (849–5063 chars) all have proper `<main>` elements with substantial text.

3. **Dedup guardrail triggered** on 2 pages (#7, #9), removing >45% of sections. This is expected behavior but worth noting.

4. **Duplicate URL**: `/` and `` (no trailing slash) both crawled as separate pages with identical content.

## What to Compare After Phase 3

After adding `page_timeout=30000` to bound the `wait_for` predicate:
- Do the 5 "almost empty" pages (#3, #4, #5, #6, #8) return more content?
- If yes → `page_timeout` gives JS-rendered pages time to populate
- If no → these pages may need a different `wait_for` strategy or the content is truly behind authentication/dynamic loading
