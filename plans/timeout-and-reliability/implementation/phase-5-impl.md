---
type: planning
entity: implementation-plan
plan: "timeout-and-reliability"
phase: 5
status: draft
created: "2026-04-08"
updated: "2026-04-08"
---

# Implementation Plan: Phase 5 - Tests

> Implements [Phase 5](../phases/phase-5.md) of [timeout-and-reliability](../plan.md)

## Approach

Add focused async unit tests for timeout and retry behavior without real network usage. Keep tests fast by using short timeout values (for example `0.1s`) and monkeypatched async fakes.

This phase adds coverage for behavior introduced in Phases 1-4: timeout raising for single-page crawl, per-URL timeout isolation in batch crawl, graceful timeout handling in site crawl, MCP timeout parameter forwarding, cancellation cleanup (`__aexit__` still runs on timeout), and search retry behavior for transient vs persistent `httpx.RequestError`.

## Affected Modules

| Module | Change Type | Description |
|--------|-------------|-------------|
| `tests/test_timeout.py` | create | New timeout/reliability test module covering crawl wrappers and MCP timeout forwarding. |
| `tests/test_mcp_server.py` | modify | Add search retry tests for transient and persistent `httpx.RequestError` behavior. |
| `crawler/__init__.py` | verify (no code change intended) | Target of timeout/cancellation tests (`crawl_page_async`, `crawl_pages_async`). |
| `crawler/site.py` | verify (no code change intended) | Target of graceful site-timeout test (`crawl_site_async`). |
| `crawler/mcp_server.py` | verify (no code change intended) | Target of MCP timeout forwarding and search retry tests. |

## Required Context

| File | Why |
|------|-----|
| `plans/timeout-and-reliability/plan.md` | Global reliability requirements and test strategy (new tests + regression mandate). |
| `plans/timeout-and-reliability/phases/phase-5.md` | Gated phase scope, deliverables, and acceptance criteria for tests. |
| `plans/timeout-and-reliability/implementation/phase-1-impl.md` | Expected timeout semantics for `crawl_page_async`, `crawl_pages_async`, `crawl_site_async`. |
| `plans/timeout-and-reliability/implementation/phase-2-impl.md` | Expected MCP `timeout` parameter forwarding in `crawl` and `crawl_site`. |
| `plans/timeout-and-reliability/implementation/phase-3-impl.md` | Context for bounded-wait reliability behavior and no-regression expectations. |
| `plans/timeout-and-reliability/implementation/phase-4-impl.md` | Expected search retry behavior (`RequestError` retry once, then fail). |
| `tests/test_init.py` | Existing async crawl test style and monkeypatch patterns for wrappers. |
| `tests/test_mcp_server.py` | Existing MCP test style and output assertions; placement for search retry tests. |
| `tests/test_auth_core.py` | Existing auth/runtime-path test patterns that must remain valid. |
| `crawler/__init__.py` | Current signatures and behavior for `crawl_page_async`/`crawl_pages_async` under test. |
| `crawler/site.py` | Current `SiteCrawlResult` error/stats contract for site-timeout assertions. |
| `crawler/mcp_server.py` | Current MCP tool call shapes and `search()` exception/retry behavior under test. |

## Implementation Steps

### Step 1: Create timeout test module scaffold with reusable async fakes

- **What**: Create `tests/test_timeout.py` with imports and helper fakes used across timeout tests:
  - `import asyncio`, `import json`, `from types import SimpleNamespace`, `import pytest`, `import httpx`, `import crawler`, `from crawler import mcp_server`, and `import crawler.site as site_module`.
  - Add a hanging async function for crawl hangs:
    - `async def hanging_arun(*args, **kwargs): await asyncio.sleep(999)`
  - Add a small helper for successful fake docs/results to keep assertions concise.
- **Where**: `tests/test_timeout.py` (new file).
- **Why**: Centralizes deterministic fast test helpers and avoids repetitive monkeypatch logic.
- **Considerations**: Keep all tests fully isolated (no real network, no long sleeps, no shared mutable state across tests).

### Step 2: Add single-page timeout and cancellation-safety tests

- **What**:
  1. Add `test_crawl_page_async_hanging_arun_raises_timeout_error`:
     - Monkeypatch `crawler.AsyncWebCrawler` to a dummy async context manager whose `arun()` delegates to `hanging_arun`.
     - Invoke `await crawler.crawl_page_async("https://example.com", timeout=0.1)`.
     - Assert timeout with `with pytest.raises(asyncio.TimeoutError): ...`.
  2. Add `test_crawl_page_async_timeout_still_calls_aexit`:
     - Dummy `AsyncWebCrawler` sets a flag in `__aexit__`.
     - `arun()` hangs (`await asyncio.sleep(999)`) and call uses tiny timeout (`timeout=0.1`).
     - Assert `pytest.raises(asyncio.TimeoutError)` and then assert `__aexit__` flag is `True`.
- **Where**: `tests/test_timeout.py`.
- **Why**: Verifies timeout behavior and cancellation cleanup safety at the single-page wrapper boundary.
- **Considerations**: Ensure the dummy context manager returns `False` from `__aexit__` so exceptions are not swallowed.

### Step 3: Add batch and site timeout behavior tests

- **What**:
  1. Add `test_crawl_pages_async_one_hanging_url_returns_failed_doc_and_others_succeed`:
     - Monkeypatch `crawler.crawl_page_async` so one target URL hangs long enough to timeout and others return success docs.
     - Run `docs = await crawler.crawl_pages_async([...], timeout=0.1)`.
     - Assert successful URLs have `status == "success"`.
     - Assert hanging URL result has `status == "failed"` and timeout-specific `error_message` (contains `Timeout`/`timeout`).
  2. Add `test_crawl_site_async_hanging_arun_returns_graceful_error_result`:
     - Monkeypatch `site_module.AsyncWebCrawler` so `arun()` hangs.
     - Call `result = await site_module.crawl_site_async("https://example.com", timeout=0.1)`.
     - Assert returned type/shape is graceful (no exception):
       - `result.documents == []`
       - `result.errors` contains at least one entry for the seed URL
       - `result.stats["error_count"] >= 1`
- **Where**: `tests/test_timeout.py`.
- **Why**: Covers required per-URL isolation and graceful site-timeout semantics from earlier phases.
- **Considerations**: Keep assertions robust to exact timeout string wording by matching key fragments (`Timeout` and URL) rather than full literal if wording may evolve.

### Step 4: Add MCP timeout parameter forwarding tests

- **What**:
  1. Add `test_mcp_crawl_forwards_custom_timeout`:
     - Monkeypatch `crawler.crawl_page_async` and `crawler.crawl_pages_async` fakes that capture received kwargs.
     - Call `await mcp_server.crawl(urls=["https://example.com"], timeout=7, output_format="json")`.
     - Assert captured timeout is `7`.
  2. Add `test_mcp_crawl_site_forwards_custom_timeout`:
     - Monkeypatch `crawler.crawl_site_async` fake that captures kwargs and returns a minimal valid site result.
     - Call `await mcp_server.crawl_site(url="https://example.com", timeout=17, output_format="json")`.
     - Assert captured timeout is `17`.
- **Where**: `tests/test_timeout.py`.
- **Why**: Verifies MCP interface-level timeout configurability is actually threaded into runtime wrappers.
- **Considerations**: Keep output parsing minimal; these tests validate forwarding, not full output serialization.

### Step 5: Add search retry tests in MCP test module

- **What**:
  1. Add `tests/test_mcp_server.py::test_search_retries_once_on_transient_request_error`:
     - Monkeypatch `mcp_server._get_searxng_client` to return a dummy async client context manager.
     - Dummy `get()` behavior: first call raises `httpx.RequestError`, second call returns successful response object with JSON payload.
     - Call `out = await mcp_server.search(query="retry-me")`; parse JSON and assert success payload is returned.
     - Assert `get()` call count is `2`.
  2. Add `tests/test_mcp_server.py::test_search_returns_error_after_persistent_request_error`:
     - Same client patch pattern, but `get()` always raises `httpx.RequestError`.
     - Call search and assert returned JSON includes `"error"` and `"query"` keys (error shape), with retries exhausted.
     - Assert call count equals configured max attempts.
- **Where**: `tests/test_mcp_server.py` (append near existing MCP tests).
- **Why**: Directly verifies Phase 4 retry control flow and final error behavior.
- **Considerations**: If retry uses backoff sleep, monkeypatch `asyncio.sleep` in `crawler.mcp_server` to a no-op async function to keep tests fast and deterministic.

### Step 6: Run full regression suite and keep existing tests intact

- **What**: Run full `tests/` suite after adding the new tests and only adjust test doubles where required by intentional timeout/retry interface changes.
- **Where**: Entire `tests/` directory.
- **Why**: Phase acceptance requires all existing tests to continue to pass.
- **Considerations**: No skipping, deleting, or weakening existing tests to make new timeout tests pass.

## Testing Plan

| Test Type | What to Test | Expected Outcome |
|-----------|-------------|-----------------|
| New unit tests (`tests/test_timeout.py`) | `crawl_page_async` timeout raising, batch per-URL timeout isolation, site timeout graceful result, MCP timeout forwarding, cancellation `__aexit__` safety. | Required timeout/reliability behavior is covered with fast deterministic tests and no real network calls. |
| New unit tests (`tests/test_mcp_server.py`) | Search retry behavior for transient vs persistent `httpx.RequestError`. | Transient error succeeds on second attempt; persistent error returns structured error JSON after retries. |
| Regression (full suite) | All existing tests in `tests/` after new tests are added. | No regressions; pre-existing tests remain passing unchanged. |

**Verify command (single command):**

```bash
python -m pytest -q tests/
```

### Test Integrity Constraints

- `tests/test_init.py` existing tests must remain untouched, especially:
  - `test_crawl_page_async_forwards_dedup_mode`
  - `test_crawl_pages_async_defaults_to_exact`
  - `test_crawl_site_wrapper_forwards_dedup_mode`
  - `test_crawl_pages_async_forwards_auth_to_crawl_page`
- `tests/test_auth_core.py` existing auth-path tests must remain untouched, especially:
  - `test_crawl_page_async_no_auth_keeps_existing_runtime_path`
  - `test_crawl_page_async_threads_storage_state_to_browser_config`
  - `test_crawl_site_async_threads_resolved_storage_state`
- Existing `tests/test_mcp_server.py` forwarding/output tests must remain valid and not be weakened:
  - `test_mcp_crawl_forwards_dedup_mode`
  - `test_mcp_crawl_site_forwards_dedup_mode`
  - `test_mcp_json_output_includes_builder_guardrail_metadata`
  - `test_mcp_crawl_auth_error_propagates_from_resolver`
- No existing tests may be deleted, skipped, or relaxed to satisfy new timeout/retry assertions.

## Rollback Strategy

1. Remove newly added tests in isolated commits if they are invalid for current runtime behavior.
2. Revert only Phase 5 test additions (`tests/test_timeout.py` and search-retry test blocks in `tests/test_mcp_server.py`) without touching production code.
3. Re-run `python -m pytest -q tests/` to confirm baseline restoration.

## Open Decisions

| Decision | Options | Chosen | Rationale |
|----------|---------|--------|-----------|
| Location for search retry tests | `tests/test_timeout.py` vs `tests/test_mcp_server.py` | `tests/test_mcp_server.py` | Keeps MCP search behavior tests co-located with existing MCP tool tests and helper patterns. |
| Timeout assertions strictness | Exact error string match vs key-fragment match | Key-fragment match (`Timeout` + URL/failed status) | Preserves behavioral verification while avoiding brittle failures from minor message wording changes. |

## Reality Check

### Code Anchors Used

| File | Symbol/Area | Why it matters |
|------|-------------|----------------|
| `plans/timeout-and-reliability/phases/phase-5.md:23-33` | Required test list | Defines exact behaviors/tests this implementation plan must cover. |
| `tests/test_init.py:11-106` | Existing wrapper monkeypatch patterns | Provides baseline style for async fakes and forwarding assertions. |
| `tests/test_mcp_server.py:24-137` | Existing MCP test style | Provides established monkeypatch/output assertion patterns for MCP tools. |
| `tests/test_auth_core.py:48-166` | Context-manager/auth runtime tests | Demonstrates dummy `AsyncWebCrawler` patterns used for cancellation/cleanup-style assertions. |
| `crawler/__init__.py:94-135` | `crawl_page_async` | Timeout raising + cancellation cleanup target. |
| `crawler/__init__.py:183-227` | `crawl_pages_async` | Per-URL failure isolation behavior target for hanging URL test. |
| `crawler/site.py:63-180` | `crawl_site_async` | Graceful site-timeout result contract target. |
| `crawler/mcp_server.py:188-343` | `crawl`, `crawl_site` tools | Timeout parameter forwarding behavior under MCP tests. |
| `crawler/mcp_server.py:368-470` | `search` tool | Retry behavior target for transient/persistent `httpx.RequestError` tests. |

### Mismatches / Notes

- Current checked-in code at the anchors does **not** yet include prior-phase timeout/retry interfaces (no `timeout` params in crawl wrappers/MCP tools and no search retry loop). Phase 5 tests assume Phases 1-4 are implemented first.
- Because of that mismatch, implementing agent should either (a) run this phase after merging Phase 1-4 changes, or (b) gate individual tests with explicit branch-state checks only if instructed by the primary (preferred: sequence correctly, no temporary weakening).
