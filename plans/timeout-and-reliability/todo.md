---
type: planning
entity: todo
plan: "timeout-and-reliability"
updated: "2026-04-08"
---

# Todo: timeout-and-reliability

> Tracking [timeout-and-reliability](plan.md)

## Plan Completed

All 5 phases have been executed and verified. 60/60 tests pass.

### Completed

- [x] Phase 1: Core Timeout Wrappers — `asyncio.wait_for()` around `crawler.arun()`, per-URL timeout in batch (2026-04-08)
- [x] Phase 2: MCP Tool Timeout Parameters — `timeout` param added to `crawl` and `crawl_site` tools with validation (2026-04-08)
- [x] Phase 3: Replace networkidle + Bound wait_for — `page_timeout=30000` in markdown config, `domcontentloaded` in discovery (2026-04-08)
- [x] Phase 4: Elapsed Logging + Search Retry — `time.monotonic()` logging in all crawl/search paths, search retry on `RequestError` (2026-04-08)
- [x] Phase 5: Tests — 6 new tests in `tests/test_timeout.py` covering timeout behavior and search retry (2026-04-08)

### Pending / Blocked

<!-- none -->

## Changelog

<!-- Append-only log of significant changes and decisions -->

### 2026-04-08

- Plan created with 5 phases
- User confirmed: 5-phase structure, use Crawl4AI `page_timeout` for wait_for bound, 30s/120s default timeouts
- Plan review completed; 2 Major issues fixed (F-2 retargeted, crawl_site timeout contract clarified)
- All 5 implementation plans authored and verified against current code
- All 5 phases executed successfully; 60/60 tests pass (54 existing + 6 new timeout tests)
- Plan completed
