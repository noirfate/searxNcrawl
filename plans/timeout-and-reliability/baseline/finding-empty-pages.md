# Bas Finding: 50% of docs.agno.com Pages Return Almost No Content

**Date:** 2026-04-08
**Context:** Baseline site crawl of `https://docs.agno.com/` (max_pages=10, max_depth=2)

## Finding

5 out of 10 crawled pages returned < 50 characters of markdown content:

- `/workflows/overview` — 26 chars
- `/agent-os/introduction` — 23 chars
- `/agents/overview` — 23 chars
- `/introduction` — 19 chars
- `/production/overview` — 18 chars

## Root Cause

The `wait_for` JS predicate in `build_markdown_run_config()` requires:
```
document.querySelector('main') && document.querySelector('main').innerText.trim().length > 50
```

These pages either lack a `<main>` element or their content loads dynamically after the predicate check. Without a `page_timeout` bound, the predicate could wait indefinitely. In practice, Crawl4AI's default timeout eventually expires, but the page returns with only the `<title>` element's text.

## Relevance to Plan

Phase 3 adds `page_timeout=30000` to `build_markdown_run_config()`, which bounds this wait to 30s. After Phase 3, we should re-run this baseline crawl to verify whether the 5 empty pages return more content with a bounded wait.

## Baseline Data

Full JSON output: `plans/timeout-and-reliability/baseline/agno-baseline.json/crawl_results.json`
