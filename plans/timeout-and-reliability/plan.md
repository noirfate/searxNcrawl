---
type: planning
entity: plan
plan: "timeout-and-reliability"
status: completed  # draft | active | completed | abandoned
created: "2026-04-08"
updated: "2026-04-08"
---

# Plan: Timeout & Reliability

## Objective

Add timeout protection, reliability improvements, and observability to all MCP crawl and search operations so that no single hanging URL or misconfigured page can freeze the entire MCP server or its consumers.

## Motivation

Discovered during mark_down_edit PoC testing: crawl MCP tool calls hang indefinitely when target pages stall, freezing the entire agent/streaming pipeline. The MCP server has no timeout protection around crawl operations. Any MCP consumer waiting for a result will freeze. Search operations have a hardcoded 30s HTTP timeout and are not affected.

Review documented in [docs/reviews/timeout-and-reliability-review.md](../../docs/reviews/timeout-and-reliability-review.md) identifies 7 findings (F-1 through F-7) across 5 priority levels.

## Requirements

### Functional

- [ ] F-1: Wrap all `crawler.arun()` calls with `asyncio.wait_for()` timeouts
- [ ] F-6: Per-URL timeout in multi-URL crawl so one hanging URL does not block the batch
- [ ] F-4: Expose timeout parameters in MCP tool schemas (`crawl`, `crawl_site`)
- [ ] F-2: Replace `wait_until="networkidle"` with bounded wait in discovery config
- [ ] F-3: Bound `wait_for` JS predicate with `page_timeout` in markdown config
- [ ] F-7: Add elapsed-time logging for all crawl/search operations
- [ ] F-5: Add retry with backoff for transient SearXNG search failures

### Non-Functional

- Default per-URL timeout: 30 seconds
- Default site crawl timeout: 120 seconds
- Timeouts must be configurable via MCP tool parameters
- Failed/timed-out URLs must return graceful error documents, not raise unhandled exceptions
- All existing tests must continue to pass
- New unit tests for timeout behavior and search retry

## Scope

### In Scope

- `crawler/__init__.py` — timeout wrappers for `crawl_page_async`, `crawl_pages_async`
- `crawler/site.py` — timeout wrapper for `crawl_site_async`
- `crawler/config.py` — replace `networkidle`, add `page_timeout` to `wait_for`
- `crawler/mcp_server.py` — expose timeout parameters, add search retry, elapsed logging
- `tests/` — new unit tests for timeout and retry behavior

### Out of Scope

- Changes to Crawl4AI library itself
- Consumer-side mitigations (already done in mark_down_edit)
- CLI timeout parameters (CLI is not the primary attack surface)
- Performance optimization beyond timeout/reliability

## Definition of Done

- [ ] All `crawler.arun()` calls are wrapped with `asyncio.wait_for()` or equivalent timeout
- [ ] Multi-URL crawl handles per-URL timeouts independently (one hang does not block others)
- [ ] MCP tools `crawl` and `crawl_site` accept optional `timeout` parameters
- [ ] Discovery config uses `domcontentloaded` instead of `networkidle`
- [ ] `wait_for` JS predicate is bounded by `page_timeout`
- [ ] Elapsed-time logging present in all crawl/search paths
- [ ] Search tool retries on transient `httpx.RequestError` with exponential backoff
- [ ] All existing tests pass
- [ ] New unit tests cover: timeout on hang, per-URL timeout in batch, search retry

## Testing Strategy

1. **Unit test**: Mock `crawler.arun()` to hang → verify `asyncio.TimeoutError` raised within expected time
2. **Unit test**: Multi-URL crawl with one hanging mock → verify other URLs complete, hanging URL returns timeout error
3. **Unit test**: Search retry on transient `httpx.RequestError` → verify retry succeeds on second attempt
4. **Integration test** (optional): Crawl a known slow/broken URL → verify timeout behavior end-to-end
5. **Regression**: Run full existing test suite between phases

## Phases

| Phase | Title | Scope | Status |
|-------|-------|-------|--------|
| 1 | [Core Timeout Wrappers](phases/phase-1.md) | `asyncio.wait_for()` around `crawler.arun()` in `__init__.py` and `site.py`; per-URL timeout in `crawl_pages_async()` | completed |
| 2 | [MCP Tool Timeout Parameters](phases/phase-2.md) | Add `timeout` parameter to `crawl` and `crawl_site` MCP tools; thread through to underlying functions | completed |
| 3 | [Replace networkidle + Bound wait_for](phases/phase-3.md) | Add `page_timeout=30000` to `build_markdown_run_config()` (active path); fix `networkidle` in discovery config (defensive) | completed |
| 4 | [Elapsed Logging + Search Retry](phases/phase-4.md) | Add `time.monotonic()` logging to all crawl/search paths; add retry loop with backoff for SearXNG search | completed |
| 5 | [Tests](phases/phase-5.md) | Unit tests for timeout behavior, per-URL batch timeout, search retry | completed |

## Risks & Open Questions

| Risk/Question | Impact | Mitigation/Answer |
|---------------|--------|-------------------|
| Crawl4AI `page_timeout` behavior may differ from `asyncio.wait_for()` | Medium | Use both: `page_timeout` as inner bound, `asyncio.wait_for()` as outer bound |
| 30s default may be too aggressive for some slow sites | Low | Configurable via MCP tool parameter; users can increase as needed |
| `domcontentloaded` may return before dynamic content loads | Medium | Acceptable trade-off; `wait_for` predicate + `page_timeout` provides content check with bound |
| `asyncio.wait_for()` cancels the inner task — may leave Playwright browser in bad state | Medium | Each crawl creates its own `AsyncWebCrawler` context manager; cancellation should clean up. Test verifies `__aexit__` runs. |
| `crawl_site_async()` timeout must return graceful error, not raise exception | Medium | Phase 1: catch timeout in site.py and return `SiteCrawlResult` with error entry; MCP tool also catches for structured output |

## Changelog

### 2026-04-08

- Plan created based on [docs/reviews/timeout-and-reliability-review.md](../../docs/reviews/timeout-and-reliability-review.md)
- Plan review completed; 2 Major issues fixed (F-2 retargeted to `build_markdown_run_config()`, crawl_site timeout contract clarified)
- All 5 implementation plans authored and verified against current code
- All 5 phases executed successfully; 60/60 tests pass (54 existing + 6 new timeout tests)
- Plan completed
