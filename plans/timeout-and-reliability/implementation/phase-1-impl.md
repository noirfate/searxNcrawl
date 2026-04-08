---
type: planning
entity: implementation-plan
plan: "timeout-and-reliability"
phase: 1
status: draft
created: "2026-04-08"
updated: "2026-04-08"
---

# Implementation Plan: Phase 1 - Core Timeout Wrappers

> Implements [Phase 1](../phases/phase-1.md) of [timeout-and-reliability](../plan.md)

## Approach

Add outer `asyncio.wait_for()` guards at the two Crawl4AI invocation points (`crawl_page_async()` and `crawl_site_async()`) with phase-approved default constants. Preserve existing API signatures for this phase (timeout parameters are deferred to Phase 2), and enforce graceful behavior at higher layers:

- Single page crawl: timeout is raised (`TimeoutError`) from `crawl_page_async()`.
- Multi-page crawl: per-URL timeout is absorbed in `crawl_pages_async()` and mapped to failed `CrawledDocument` entries.
- Site crawl: timeout is converted to a graceful `SiteCrawlResult` error entry (no exception).
- MCP `crawl_site`: defensive `TimeoutError` catch that returns structured failed output consistent with existing crawl-tool error shape.

## Affected Modules

| Module | Change Type | Description |
|--------|-------------|-------------|
| `crawler/__init__.py` | modify | Add `DEFAULT_PAGE_TIMEOUT` and apply `asyncio.wait_for()` around `crawler.arun()` in `crawl_page_async()`; add explicit per-URL timeout handling branch in `crawl_pages_async()`. |
| `crawler/site.py` | modify | Add `DEFAULT_SITE_TIMEOUT`; wrap `crawler.arun()` in `crawl_site_async()`; convert timeout to graceful `SiteCrawlResult` with timeout error entry. |
| `crawler/mcp_server.py` | modify | Add defensive `try/except TimeoutError` around `crawl_site_async()` call and return structured failed output payload. |
| `tests/` (existing only) | verify | Re-run existing tests touching crawl wrappers and MCP forwarding to ensure behavior not regressed. |

## Required Context

| File | Why |
|------|-----|
| `plans/timeout-and-reliability/plan.md` | Global constraints, defaults, and phase ordering. |
| `plans/timeout-and-reliability/phases/phase-1.md` | Gated phase scope + acceptance criteria. |
| `crawler/__init__.py` | Source of `crawl_page_async()` and `crawl_pages_async()` timeout behavior. |
| `crawler/site.py` | Source of `crawl_site_async()` and `SiteCrawlResult` behavior. |
| `crawler/mcp_server.py` | `crawl_site` MCP tool output/error shaping. |
| `crawler/document.py` | `CrawledDocument` schema used for graceful failures. |
| `tests/test_init.py` | Wrapper behavior tests likely impacted by timeout wrapper insertion. |
| `tests/test_auth_core.py` | Auth + crawler construction behavior around `crawl_page_async()` and `crawl_site_async()`. |
| `tests/test_mcp_server.py` | MCP `crawl_site` forwarding and output-contract smoke coverage. |

## Implementation Steps

### Step 1: Add phase-approved timeout constants at module scope

- **What**:
  - Add `DEFAULT_PAGE_TIMEOUT = 30` in `crawler/__init__.py` near other module-level declarations (`__all__`, helper defs).
  - Add `DEFAULT_SITE_TIMEOUT = 120` in `crawler/site.py` near `LOGGER`.
- **Where**:
  - `crawler/__init__.py` (module scope, before `crawl_page_async`).
  - `crawler/site.py` (module scope, before `crawl_site_async`).
- **Why**: Keeps defaults centralized and adjustable without changing call signatures in Phase 1.
- **Considerations**:
  - Keep constants in their owning modules to avoid circular imports (`__init__.py` already imports from `.site`).

### Step 2: Wrap `crawl_page_async()` `crawler.arun()` calls with `asyncio.wait_for`

- **What**:
  - In both runtime branches (`AsyncWebCrawler()` and `AsyncWebCrawler(config=browser_cfg)`), replace direct `await crawler.arun(...)` with:
    - `await asyncio.wait_for(crawler.arun(url=url, config=run_config), timeout=DEFAULT_PAGE_TIMEOUT)`
  - Do **not** catch timeout in this function; let `TimeoutError` propagate as the function contract for single-page crawl timeout.
- **Where**:
  - `crawler/__init__.py`, `crawl_page_async()`.
- **Why**: Satisfies phase deliverable: single page timeout should raise.
- **Considerations**:
  - Keep existing auth/browser config branching intact.
  - Keep post-processing (`_extract_first_result`, `build_document_from_result`) unchanged.

### Step 3: Make multi-URL crawl resilient to per-URL timeout

- **What**:
  - In inner `crawl_one()` in `crawl_pages_async()`, add a dedicated timeout branch before generic exception handling:
    - `except TimeoutError:` → return failed `CrawledDocument` with:
      - `request_url=url`
      - `final_url=url`
      - `status="failed"`
      - `markdown=""`
      - `error_message=f"Timeout after {DEFAULT_PAGE_TIMEOUT}s"`
  - Keep existing broad `except Exception as exc:` fallback for non-timeout failures.
- **Where**:
  - `crawler/__init__.py`, `crawl_pages_async()` inner `crawl_one`.
- **Why**: Enforces per-URL failure isolation so one hung URL does not block the batch.
- **Considerations**:
  - Timeout handling must occur inside `crawl_one()` so `asyncio.gather(*tasks)` still completes all URLs.
  - Keep output ordering and semaphore behavior unchanged.

### Step 4: Add timeout guard + graceful timeout result to `crawl_site_async()`

- **What**:
  - Replace direct `crawl_result = await crawler.arun(...)` with:
    - `crawl_result = await asyncio.wait_for(crawler.arun(url=seed_url, config=config), timeout=DEFAULT_SITE_TIMEOUT)`
  - Add `except TimeoutError:` around that call and return early with:
    - `documents=[]`
    - `errors=[{"url": seed_url, "error": f"Timeout after {DEFAULT_SITE_TIMEOUT}s", "stage": "crawl_timeout"}]`
    - `stats={"total_pages": 0, "successful_pages": 0, "failed_pages": 0, "error_count": 1}`
- **Where**:
  - `crawler/site.py`, `crawl_site_async()` inside `async with AsyncWebCrawler(...) as crawler:` block.
- **Why**: Phase requires graceful site timeout (result object, not exception).
- **Considerations**:
  - Keep existing build-stage/crawl-stage error collection format and keys (`url`, `error`, `stage`) for consistency.
  - Ensure timeout early-return path preserves `SiteCrawlResult` type contract.

### Step 5: Add defensive timeout catch in MCP `crawl_site` tool

- **What**:
  - Wrap `result = await crawl_site_async(...)` in `try/except TimeoutError`.
  - In except path, return structured error output via `_format_output` using one failed `CrawledDocument` (matching existing crawl-tool error pattern), e.g.:
    - `request_url=url`, `final_url=url`, `status="failed"`, `markdown=""`, `error_message=f"Timeout after {DEFAULT_SITE_TIMEOUT}s"` (or `str(exc)` fallback if non-empty).
    - include `stats={"total_pages": 1, "successful_pages": 0, "failed_pages": 1, "error_count": 1}` for JSON parity.
- **Where**:
  - `crawler/mcp_server.py`, `crawl_site` tool body around current `crawl_site_async(...)` invocation.
- **Why**: Prevents MCP-level failure if timeout bubbles; keeps response contract machine-parseable.
- **Considerations**:
  - Keep format consistent with `_format_output` output used elsewhere.
  - This catch is primarily defensive because `crawl_site_async()` becomes graceful in Step 4.

## Testing Plan

| Test Type | What to Test | Expected Outcome |
|-----------|-------------|-----------------|
| Manual async smoke | Monkeypatch crawler runtime to hang and set tiny timeout constants, then invoke: (1) `crawl_page_async`, (2) `crawl_pages_async`, (3) `crawl_site_async`, (4) MCP `crawl_site`. | (1) raises `TimeoutError`; (2) returns failed timed-out document while batch completes; (3) returns `SiteCrawlResult` with timeout error entry and empty docs; (4) returns structured failed MCP payload, not tool crash. |
| Regression (existing tests) | Re-run existing test modules that cover wrappers/auth/MCP formatting. | All pre-existing tests continue to pass unchanged. |

**Verify command (single command):**

```bash
python -m pytest -q tests/test_init.py tests/test_auth_core.py tests/test_mcp_server.py
```

### Test Integrity Constraints

- `tests/test_init.py::test_crawl_page_async_forwards_dedup_mode` and `::test_crawl_pages_async_defaults_to_exact` must remain valid; timeout wrappers must not alter dedup/auth forwarding semantics.
- `tests/test_auth_core.py::test_crawl_page_async_no_auth_keeps_existing_runtime_path` and `::test_crawl_page_async_threads_storage_state_to_browser_config` are sensitive to `crawl_page_async()` internals; preserve crawler construction and config threading.
- `tests/test_auth_core.py::test_crawl_site_async_threads_resolved_storage_state` must still pass; adding timeout wrapper must not change auth→`BrowserConfig` behavior.
- `tests/test_mcp_server.py::test_mcp_crawl_site_forwards_dedup_mode` must remain intact; MCP timeout catch must not change normal success path or argument forwarding.
- No existing tests should be deleted/disabled/relaxed in this phase (new timeout-focused tests are deferred to Phase 5).

## Rollback Strategy

If regressions appear:

1. Revert timeout wrappers in `crawl_page_async()` and `crawl_site_async()` first (highest behavioral impact).
2. Keep constants in place if harmless, or remove them in same rollback commit if needed for clean revert.
3. Revert MCP `crawl_site` defensive timeout catch if it changes output contract unexpectedly.
4. Re-run the verify command to confirm baseline behavior restoration.

## Open Decisions

| Decision | Options | Chosen | Rationale |
|----------|---------|--------|-----------|
| Location of timeout constants | both in one module vs split by ownership | Split (`DEFAULT_PAGE_TIMEOUT` in `crawler/__init__.py`, `DEFAULT_SITE_TIMEOUT` in `crawler/site.py`) | Avoid circular imports and keep constants close to call sites. |
| Timeout error stage name in `SiteCrawlResult.errors` | `crawl`, `timeout`, `crawl_timeout` | `crawl_timeout` | Distinguishes timeout from general crawl failures while preserving existing error-entry shape. |

## Reality Check

### Code Anchors Used

| File | Symbol/Area | Why it matters |
|------|-------------|----------------|
| `crawler/__init__.py:94-134` | `crawl_page_async()` | Contains direct `crawler.arun()` awaits that currently have no timeout guard. |
| `crawler/__init__.py:183-227` | `crawl_pages_async()` / inner `crawl_one()` | Existing per-URL exception handling location for graceful failed `CrawledDocument` return. |
| `crawler/site.py:35-42` | `SiteCrawlResult` dataclass | Defines timeout-graceful return shape (`documents`, `errors`, `stats`). |
| `crawler/site.py:63-180` | `crawl_site_async()` | Current site crawl path invokes `crawler.arun()` directly and builds `errors`/`stats` structures. |
| `crawler/document.py:18-31` | `CrawledDocument` dataclass | Defines required fields for structured failed outputs. |
| `crawler/mcp_server.py:150-180` | `_format_output()` | Canonical structured output formatter for MCP crawl tools. |
| `crawler/mcp_server.py:265-343` | `crawl_site` MCP tool | Current site tool lacks explicit timeout handling around `crawl_site_async()`. |
| `tests/test_init.py` | wrapper behavior tests | Validates forwarding behavior that must remain unchanged.
| `tests/test_auth_core.py` | auth + crawler config tests | Ensures timeout wrapper edits do not break auth/config threading.
| `tests/test_mcp_server.py` | MCP crawl/crawl_site tests | Ensures MCP output/forwarding behavior remains stable.

### Mismatches / Notes

- Phase intent requires MCP `crawl_site` to catch `TimeoutError`, but with this phase’s graceful timeout return in `crawl_site_async()`, that exception path should be rare/unreached in normal operation. Keep the MCP catch as a defensive guardrail.
- Existing tests do not currently assert timeout-specific behavior; this is consistent with plan sequencing (dedicated timeout tests in Phase 5).
