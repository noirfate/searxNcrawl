---
type: planning
entity: phase
plan: "timeout-and-reliability"
phase: 1
status: completed  # pending | in_progress | completed | skipped
created: "2026-04-08"
updated: "2026-04-08"
---

# Phase 1: Core Timeout Wrappers

> Part of [timeout-and-reliability](../plan.md)

## Objective

Add `asyncio.wait_for()` timeout protection around all `crawler.arun()` calls so that no single page crawl can hang indefinitely. Implement per-URL timeouts in multi-URL crawl so one hanging URL does not block the entire batch.

Fixes findings **F-1** (Critical) and **F-6** (Major) from the review.

## Scope

### Includes

- `crawler/__init__.py`:
  - Wrap `crawler.arun()` in `crawl_page_async()` with `asyncio.wait_for(timeout=30)`
  - Add per-URL timeout wrapper in `crawl_pages_async()` — each `crawl_one()` task gets its own timeout
  - Timed-out URLs return a `CrawledDocument` with `status="failed"` and `error_message="Timeout after Xs"`
- `crawler/site.py`:
  - Wrap `crawler.arun()` in `crawl_site_async()` with `asyncio.wait_for(timeout=120)`
  - On timeout, return a `SiteCrawlResult` with empty documents and an error entry (graceful failure, not raised exception)
- `crawler/mcp_server.py`:
  - `crawl_site` tool: wrap `crawl_site_async()` call in try/except `TimeoutError` → return structured error output (consistent with `crawl` tool's error handling)

### Excludes (deferred to later phases)

- MCP tool parameter exposure (Phase 2)
- Config changes for `networkidle`/`wait_for` (Phase 3)
- Elapsed-time logging (Phase 4)
- Tests (Phase 5)

## Prerequisites

- [ ] None — this is the first phase

## Deliverables

- [ ] `crawl_page_async()` raises `asyncio.TimeoutError` after 30s default
- [ ] `crawl_pages_async()` handles per-URL timeouts gracefully (failed document, not exception)
- [ ] `crawl_site_async()` returns `SiteCrawlResult` with error entry on timeout (graceful failure, not raised exception)
- [ ] `crawl_site` MCP tool catches `TimeoutError` and returns structured error output
- [ ] Timeout values defined as module-level constants for easy adjustment

## Acceptance Criteria

- [ ] Mock `crawler.arun()` to never return → `crawl_page_async()` raises `TimeoutError` within ~31s
- [ ] Mock one URL in a batch to hang → other URLs complete, hung URL returns failed document
- [ ] `crawl_site_async()` with hanging mock → returns `SiteCrawlResult` with error entry within ~121s (no exception raised)
- [ ] MCP `crawl_site` tool with hanging mock → returns structured error output (not MCP-level failure)
- [ ] Existing tests continue to pass

## Dependencies on Other Phases

| Phase | Relationship | Notes |
|-------|-------------|-------|
| Phase 2 | blocked-by | Phase 2 will expose these timeouts as MCP parameters |
| Phase 3 | parallel | Config changes are independent |
| Phase 4 | parallel | Logging is independent |
| Phase 5 | blocks | Tests validate this phase's behavior |

## Notes

- Default constants: `DEFAULT_PAGE_TIMEOUT = 30`, `DEFAULT_SITE_TIMEOUT = 120`
- `asyncio.wait_for()` cancels the inner coroutine on timeout. Since each crawl uses its own `AsyncWebCrawler` context manager, cleanup should be handled by the context manager's `__aexit__`.
- For `crawl_pages_async()`, the per-URL timeout wrapper should catch `TimeoutError` and return a failed `CrawledDocument` rather than propagating the exception — this keeps the batch resilient.
- The `crawl_one()` inner function in `crawl_pages_async()` already catches `Exception` and returns a failed document. The `TimeoutError` wrapper should be inside this function so it gets caught by the existing error handler.
