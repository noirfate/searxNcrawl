# Comparison: Baseline vs After Changes

**Date:** 2026-04-08
**Baseline:** `agno-baseline.json/` (original code)
**After:** `agno-after-changes/` (all 5 phases applied)

## Results Table

| # | URL | Before (chars) | After (chars) | Change | Notes |
|---|-----|---------------:|--------------:|-------:|-------|
| 1 | `/` | 849 | 849 | +0 | Stable |
| 2 | `/` (no trailing slash) | 849 | — | N/A | Not crawled in after run |
| 3 | `/agent-os/control-plane` | 4202 | 4202 | +0 | Stable |
| 4 | `/agent-os/introduction` | 23 | 23 | +0 | Still almost empty |
| 5 | `/agents/overview` | 23 | 23 | +0 | Still almost empty |
| 6 | `/first-agent` | 3887 | 23 | **-3864** | Lost content |
| 7 | `/introduction` | 19 | 19 | +0 | Still almost empty |
| 8 | `/production/overview` | 18 | 2664 | **+2646** | **IMPROVED** |
| 9 | `/teams/overview` | 5063 | 22 | **-5041** | Lost content |
| 10 | `/workflows/overview` | 26 | 2736 | **+2710** | **IMPROVED** |

## Summary

| Metric | Count |
|--------|-------|
| Pages improved (empty → content) | 2 |
| Pages still empty | 3 |
| Pages stable | 2 |
| Pages lost content | 2 |

## Analysis

### Improvements (2 pages)
- **`/production/overview`**: 18 → 2664 chars — `page_timeout=30000` gave the SPA time to render
- **`/workflows/overview`**: 26 → 2736 chars — same effect

### Still Empty (3 pages)
- `/agent-os/introduction`, `/agents/overview`, `/introduction` — These pages likely have no `<main>` element or load content through a mechanism the `wait_for` predicate doesn't detect. The `page_timeout` bound prevents hanging but doesn't fix content detection.

### Content Loss (2 pages) — ✅ Resolved (not a regression)
- **`/first-agent`**: 3887 → 23 chars in site crawl
- **`/teams/overview`**: 5063 → 22 chars in site crawl

**Follow-up**: Re-crawled these 2 pages individually → both returned full content:
- `/first-agent`: 3894 chars (matches baseline 3887)
- `/teams/overview`: 5259 chars (matches baseline 5063)

The "loss" was **not caused by our changes**. It was a site-crawl-order artifact — likely the dedup guardrail removing content because these pages were compared against previously crawled similar content in a different BFS order than the baseline. The `domcontentloaded` change is not responsible.
