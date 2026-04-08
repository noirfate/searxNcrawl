---
type: planning
entity: phase
plan: "timeout-and-reliability"
phase: 5
status: completed  # pending | in_progress | completed | skipped
created: "2026-04-08"
updated: "2026-04-08"
---

# Phase 5: Tests

> Part of [timeout-and-reliability](../plan.md)

## Objective

Add unit tests that verify timeout behavior, per-URL batch timeout handling, and search retry. Ensure all existing tests continue to pass.

## Scope

### Includes

- New test file: `tests/test_timeout.py`:
  - Test: `crawl_page_async` with hanging mock → raises `TimeoutError` within expected time
  - Test: `crawl_pages_async` with one hanging URL → other URLs succeed, hanging URL returns failed document
  - Test: `crawl_site_async` with hanging mock → returns `SiteCrawlResult` with error entry (graceful failure)
  - Test: MCP `crawl` tool with custom `timeout` parameter → uses provided value
  - Test: MCP `crawl_site` tool with custom `timeout` parameter → uses provided value
  - Test: Cancellation safety — dummy `AsyncWebCrawler` context manager verifies `__aexit__` runs on timeout
- New test file or additions to `tests/test_mcp_server.py`:
  - Test: Search retry on transient `httpx.RequestError` → succeeds on second attempt
  - Test: Search with persistent `httpx.RequestError` → returns error JSON after retries
- Regression: Run full existing test suite

### Excludes

- Integration tests against real slow/broken URLs (manual verification only)
- Performance benchmarking

## Prerequisites

- [ ] Phase 1 complete (timeout wrappers)
- [ ] Phase 2 complete (MCP timeout parameters)
- [ ] Phase 3 complete (config changes)
- [ ] Phase 4 complete (search retry)

## Deliverables

- [ ] `tests/test_timeout.py` with timeout behavior tests
- [ ] Search retry tests in `tests/test_mcp_server.py` or `tests/test_timeout.py`
- [ ] Full existing test suite passes

## Acceptance Criteria

- [ ] All new tests pass
- [ ] All existing tests pass (`pytest tests/`)
- [ ] Timeout tests complete in reasonable time (use fast timeouts like 0.1s in tests, not 30s)
- [ ] Tests use `monkeypatch` to mock `crawler.arun()` — no real network calls

## Dependencies on Other Phases

| Phase | Relationship | Notes |
|-------|-------------|-------|
| Phase 1 | blocked-by | Tests verify timeout wrapper behavior |
| Phase 2 | blocked-by | Tests verify MCP parameter forwarding |
| Phase 3 | blocked-by | Tests verify config changes don't break behavior |
| Phase 4 | blocked-by | Tests verify search retry |

## Notes

- Use very short timeouts in tests (e.g., 0.1s) to keep test execution fast.
- Mock `AsyncWebCrawler.arun()` with an async function that never returns (for hang tests).
- Mock `httpx.AsyncClient.get()` with `httpx.RequestError` for search retry tests.
- Consider using `pytest.raises(asyncio.TimeoutError)` for timeout assertions.
