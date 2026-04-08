---
type: planning
entity: phase
plan: "timeout-and-reliability"
phase: 4
status: completed  # pending | in_progress | completed | skipped
created: "2026-04-08"
updated: "2026-04-08"
---

# Phase 4: Elapsed Logging + Search Retry

> Part of [timeout-and-reliability](../plan.md)

## Objective

Add elapsed-time logging to all crawl and search operations for observability, and add retry with exponential backoff for transient SearXNG search failures.

Fixes findings **F-7** (Minor) and **F-5** (Note) from the review.

## Scope

### Includes

- Elapsed-time logging:
  - `crawler/__init__.py`: log duration for `crawl_page_async()` and `crawl_pages_async()` (per-URL)
  - `crawler/site.py`: log duration for `crawl_site_async()`
  - `crawler/mcp_server.py`: log duration for `search()` tool
  - Format: `Crawled {url} in {elapsed:.1f}s` (success) or `Timeout crawling {url} after {elapsed:.1f}s` (timeout)
- Search retry:
  - `crawler/mcp_server.py`: wrap SearXNG search request in retry loop (max 2 attempts, 0.5s backoff)
  - Retry only on `httpx.RequestError` (transient network errors)
  - Do NOT retry on `httpx.HTTPStatusError` (auth failures, server errors)

### Excludes (deferred to later phases)

- No changes to crawl retry (only search retry in this phase)
- No structured/metrics logging (simple `LOGGER.info`/`LOGGER.warning` is sufficient)

## Prerequisites

- [ ] None — independent of other phases (can run in parallel with P1, P2, P3)

## Deliverables

- [ ] Per-operation elapsed time logged for all crawl and search paths
- [ ] Search tool retries once on transient network errors with 0.5s backoff
- [ ] Existing tests continue to pass

## Acceptance Criteria

- [ ] Successful crawl logs: `Crawled {url} in X.Xs`
- [ ] Timed-out crawl logs: `Timeout crawling {url} after X.Xs`
- [ ] Mock transient `httpx.RequestError` on first attempt → search succeeds on retry
- [ ] Mock persistent `httpx.RequestError` on both attempts → search returns error JSON
- [ ] Existing tests continue to pass

## Dependencies on Other Phases

| Phase | Relationship | Notes |
|-------|-------------|-------|
| Phase 1 | parallel | Independent, but logging should cover timeout paths |
| Phase 2 | parallel | Independent |
| Phase 3 | parallel | Independent |
| Phase 5 | blocks | Tests should verify logging output and retry behavior |

## Notes

- Use `time.monotonic()` for elapsed time measurement (not affected by system clock changes).
- Log level: `INFO` for success, `WARNING` for timeout, `ERROR` for search failures after retry.
- Search retry: `max_retries=2` means 1 retry after initial attempt. Backoff: `0.5 * attempt` seconds (0.5s then 1.0s if extended).
