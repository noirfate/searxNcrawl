---
type: planning
entity: implementation-plan
plan: "timeout-and-reliability"
phase: 4
status: draft
created: "2026-04-08"
updated: "2026-04-08"
---

# Implementation Plan: Phase 4 - Elapsed Logging + Search Retry

> Implements [Phase 4](../phases/phase-4.md) of [timeout-and-reliability](../plan.md)

## Approach

Add monotonic elapsed-time instrumentation at each crawl/search operation boundary and log final outcome with phase-specified message templates and levels. Keep behavior changes minimal: logging is additive, and the only control-flow change is a bounded retry loop in SearXNG `search()` that retries exactly once (max 2 total attempts) only for transient `httpx.RequestError` failures.

The retry loop will wrap the existing `async with _get_searxng_client() as client:` request block so request construction and HTTP status handling stay aligned with current code.

## Affected Modules

| Module | Change Type | Description |
|--------|-------------|-------------|
| `crawler/__init__.py` | modify | Add module logger + monotonic elapsed logging in `crawl_page_async()` and per-URL logging in `crawl_pages_async()` using required success/timeout message format. |
| `crawler/site.py` | modify | Add monotonic elapsed logging in `crawl_site_async()` for success and timeout outcomes. |
| `crawler/mcp_server.py` | modify | Add monotonic elapsed logging in `crawl()`, `crawl_site()`, and `search()`; implement `search()` retry/backoff loop for `httpx.RequestError` only. |
| `tests/test_init.py` | verify (likely unchanged) | Ensure wrapper behavior remains unchanged after adding logging/timeout-specific branches. |
| `tests/test_auth_core.py` | verify (likely unchanged) | Ensure auth/browser-config threading remains unchanged after instrumentation edits. |
| `tests/test_mcp_server.py` | verify (likely unchanged) | Ensure MCP tool forwarding/output shape remains unchanged while retry/logging code is added. |

## Required Context

| File | Why |
|------|-----|
| `plans/timeout-and-reliability/plan.md` | Confirms F-7/F-5 requirements and phase sequencing (Phase 5 owns dedicated tests). |
| `plans/timeout-and-reliability/phases/phase-4.md` | Gated phase scope, exact log strings, retry constraints, and acceptance criteria. |
| `crawler/__init__.py` | Contains `crawl_page_async()` and `crawl_pages_async()` where per-URL elapsed logging must be added. |
| `crawler/site.py` | Contains `crawl_site_async()` where site crawl elapsed logging must be added. |
| `crawler/mcp_server.py` | Contains `crawl`, `crawl_site`, and `search` tools; `search` is retry implementation anchor. |
| `tests/test_init.py` | Baseline wrapper behavior/kwargs forwarding coverage sensitive to signature/control-flow edits. |
| `tests/test_auth_core.py` | Baseline auth threading coverage for crawl page/site execution paths. |
| `tests/test_mcp_server.py` | Baseline MCP forwarding/output contract coverage for crawl/crawl_site behavior. |

## Implementation Steps

### Step 1: Add logging/time imports and module loggers at crawl entry modules

- **What**:
  - In `crawler/__init__.py`, add `import logging` and `import time` with existing imports and define `LOGGER = logging.getLogger(__name__)` at module scope.
  - In `crawler/site.py`, add `import time` (logging/`LOGGER` already exist).
  - In `crawler/mcp_server.py`, add `import asyncio` (for `asyncio.sleep`) and `import time`.
- **Where**:
  - `crawler/__init__.py` import block near current `import asyncio` and type imports (`37-40`), plus module-scope logger near `__all__`.
  - `crawler/site.py` import block (`5-10`).
  - `crawler/mcp_server.py` import block (`27-35`).
- **Why**: Provides required primitives for elapsed-time measurement (`time.monotonic`) and retry backoff (`asyncio.sleep`) while keeping logging style consistent with existing modules.
- **Considerations**:
  - Use `time.monotonic()` only (not wall-clock time).
  - Avoid changing public signatures in this phase.

### Step 2: Instrument `crawl_page_async()` and `crawl_pages_async()` with required elapsed logs

- **What**:
  - In `crawl_page_async()`, capture `start = time.monotonic()` at function start.
  - On successful document build/return path, compute elapsed and log:
    - `LOGGER.info("Crawled %s in %.1fs", url, elapsed)`
  - Add timeout outcome logging before timeout propagates/returns:
    - `LOGGER.warning("Timeout crawling %s after %.1fs", url, elapsed)`
  - In `crawl_pages_async()` inner `crawl_one(url)`, ensure each URL emits one elapsed outcome log in required format:
    - success: INFO `Crawled {url} in {elapsed:.1f}s`
    - timeout: WARNING `Timeout crawling {url} after {elapsed:.1f}s`
    - non-timeout failures remain existing failed-document behavior (no new retry here).
- **Where**:
  - `crawler/__init__.py`, `crawl_page_async()` (`94-135`) and `crawl_pages_async()` inner `crawl_one` (`207-225`).
- **Why**: Covers phase-required elapsed observability for single and batch crawl operations using per-URL logs.
- **Considerations**:
  - Do not alter existing returned `CrawledDocument` shape for errors.
  - If Phase 1 timeout branches are already present, place WARNING logging in those branches; if absent, add a narrow `except TimeoutError` branch before generic exceptions to preserve required timeout message format.

### Step 3: Instrument `crawl_site_async()` with monotonic elapsed logs

- **What**:
  - Capture `start = time.monotonic()` near beginning of `crawl_site_async()`.
  - Log success completion (after crawl result/stats computed) at INFO:
    - `LOGGER.info("Crawled %s in %.1fs", seed_url, elapsed)`
  - Log timeout completion at WARNING in timeout path:
    - `LOGGER.warning("Timeout crawling %s after %.1fs", seed_url, elapsed)`
- **Where**:
  - `crawler/site.py`, `crawl_site_async()` (`63-180`), using `seed_url` as `{url}` placeholder.
- **Why**: Site crawl is explicitly in Phase 4 scope and needs same normalized success/timeout messaging.
- **Considerations**:
  - Keep existing stats/error payload semantics unchanged.
  - Do not remove existing debug/info progress logs; add final elapsed outcome log in addition.

### Step 4: Add elapsed logging in MCP crawl tools (`crawl`, `crawl_site`)

- **What**:
  - In `crawler/mcp_server.py::crawl` and `::crawl_site`, capture monotonic start time at tool entry.
  - After underlying crawl call(s) complete, emit per-URL outcome logs using phase format:
    - For each successful doc: INFO `Crawled {url} in {elapsed:.1f}s`
    - For timeout docs/exceptions: WARNING `Timeout crawling {url} after {elapsed:.1f}s`
  - Keep existing summary logs (`Completed: ...`, `Site crawl complete: ...`) and output formatting unchanged.
- **Where**:
  - `crawler/mcp_server.py`, `crawl` (`188-262`) and `crawl_site` (`265-343`).
- **Why**: Phase explicitly requires elapsed logging for MCP-exposed crawl operations, not only lower-level wrappers.
- **Considerations**:
  - Timeout detection for existing failed docs should be conservative (e.g., explicit timeout exception path and/or normalized timeout error string check) so non-timeout failures are not mislabeled.
  - Keep log duplication manageable: one outcome log per requested URL is sufficient.

### Step 5: Implement `search()` retry loop with bounded backoff and elapsed logging

- **What**:
  - In `crawler/mcp_server.py::search`, define retry constants in function scope (or module scope):
    - `max_attempts = 2`
    - `base_backoff = 0.5`
  - Wrap the existing request block (`async with _get_searxng_client() as client: ...`) in `for attempt in range(1, max_attempts + 1):`.
  - Retry rule:
    - On `httpx.RequestError` **only**: if `attempt < max_attempts`, `await asyncio.sleep(base_backoff * (2 ** (attempt - 1)))` then retry.
    - On final `httpx.RequestError`: log ERROR and return existing error JSON shape.
    - On `httpx.HTTPStatusError`: do not retry; keep current auth/status-specific error mapping and return immediately.
  - Add elapsed-time logging for search operation:
    - success: INFO with elapsed (`Search for '{query}' completed in X.Xs` or equivalent success message with elapsed)
    - final failure after retries: ERROR with elapsed (include attempt count).
- **Where**:
  - `crawler/mcp_server.py`, `search` tool (`368-470`), specifically replacing single `try/except` around lines `434-470`.
- **Why**: Implements F-5 transient resilience without masking persistent API/status errors and adds F-7 observability for search latency.
- **Considerations**:
  - Keep result limiting (`max_results`) logic exactly as-is after successful response parse.
  - Ensure `HTTPStatusError` branch executes outside RequestError retry loop semantics (no accidental retry on 401/5xx).

## Testing Plan

| Test Type | What to Test | Expected Outcome |
|-----------|-------------|-----------------|
| Manual logging verification | Invoke `crawl`, `crawl_site`, and `search` with controlled monkeypatched behaviors (fast success, forced timeout, transient `RequestError` then success, persistent `RequestError`, and `HTTPStatusError`) while capturing logs (`caplog` or temporary logging handler). | Success paths emit INFO elapsed logs; timeout paths emit WARNING with exact timeout message format; persistent search request failures emit ERROR after retry; `HTTPStatusError` path is not retried. |
| Regression (existing tests) | Re-run existing wrapper/auth/MCP tests after logging/retry changes. | Existing tests continue passing without disabling or weakening assertions. |

**Verify command (single command):**

```bash
python -m pytest -q tests/test_mcp_server.py tests/test_init.py tests/test_auth_core.py
```

### Test Integrity Constraints

- `tests/test_mcp_server.py::test_mcp_crawl_forwards_dedup_mode` and `::test_mcp_crawl_site_forwards_dedup_mode` are affected by edits in MCP tool bodies; forwarding semantics (`dedup_mode`, `auth`) must remain unchanged.
- `tests/test_mcp_server.py::test_mcp_json_output_includes_builder_guardrail_metadata` must remain unchanged; elapsed logging and retry logic must not mutate output payload schema.
- `tests/test_mcp_server.py::test_mcp_crawl_auth_error_propagates_from_resolver` must keep failed-doc JSON shape unchanged in crawl error paths.
- `tests/test_init.py::test_crawl_pages_async_defaults_to_exact` and `::test_crawl_pages_async_forwards_auth_to_crawl_page` are affected by `crawl_pages_async` control-flow instrumentation; defaults/auth forwarding must remain unchanged.
- `tests/test_auth_core.py::test_crawl_page_async_no_auth_keeps_existing_runtime_path` and `::test_crawl_site_async_threads_resolved_storage_state` must continue to pass; added logging/time code must not alter crawler construction/auth propagation.
- No existing tests should be deleted, skipped, or relaxed in this phase. New dedicated retry/logging assertions are deferred to Phase 5.

## Rollback Strategy

1. Revert retry-loop edits in `crawler/mcp_server.py::search` first if behavior regresses (highest control-flow risk).
2. Revert elapsed logging insertions in `crawler/__init__.py`, `crawler/site.py`, and MCP crawl tools if log volume/format causes issues.
3. Keep unrelated timeout/config behavior from prior phases untouched during rollback.
4. Re-run verify command to confirm baseline behavior restoration.

## Open Decisions

| Decision | Options | Chosen | Rationale |
|----------|---------|--------|-----------|
| Search retry backoff expression | Fixed 0.5s for single retry vs generic exponential formula | Exponential formula with base 0.5 (`0.5 * 2**(attempt-1)`) | Meets current phase behavior (0.5s before second attempt) and stays extensible if max attempts increases later. |
| Placement of crawl elapsed logs | Only low-level wrappers vs wrappers + MCP tools | Both layers (as phase scope states) | Phase doc explicitly includes both wrapper functions and MCP tools; dual instrumentation ensures observability for direct API and MCP call paths. |

## Reality Check

### Code Anchors Used

| File | Symbol/Area | Why it matters |
|------|-------------|----------------|
| `crawler/__init__.py:94-135` | `crawl_page_async()` | Primary single-URL crawl path where elapsed success/timeout logs must be emitted. |
| `crawler/__init__.py:183-227` | `crawl_pages_async()` / inner `crawl_one` | Per-URL batch outcome point for required success/timeout logging format. |
| `crawler/site.py:63-180` | `crawl_site_async()` | Site crawl lifecycle and final stats path; target for elapsed success/timeout logs. |
| `crawler/mcp_server.py:188-262` | `crawl` tool | MCP crawl entrypoint requiring elapsed logging in phase scope. |
| `crawler/mcp_server.py:265-343` | `crawl_site` tool | MCP site-crawl entrypoint requiring elapsed logging in phase scope. |
| `crawler/mcp_server.py:368-470` | `search` tool | Current single-attempt request flow and exception branches to be converted into retry-on-RequestError only. |
| `crawler/mcp_server.py:351-365` | `_get_searxng_client()` | Confirms retry should wrap client context/request block, not alter client factory behavior. |
| `tests/test_mcp_server.py:24-137` | MCP forwarding/output tests | Regression surface for MCP tool body edits. |
| `tests/test_init.py:11-106` | wrapper forwarding tests | Regression surface for `crawl_pages_async` and wrapper instrumentation edits. |
| `tests/test_auth_core.py:48-166` | auth threading tests | Ensures instrumentation does not alter auth/browser config behavior. |

### Mismatches / Notes

- Current checked-in code does **not** yet show prior-phase timeout branches/timeout params in these anchors (e.g., no explicit `timeout` args in `crawl`/`crawl_site` and no `TimeoutError` handling in `crawl_page_async`/`crawl_site_async`). Because Phase 4 is parallelizable, implementer should keep Phase 4 scoped to logging + search retry and avoid re-implementing unrelated Phase 1/2 scope unless explicitly requested.
- Phase intent requires exact crawl log templates (`Crawled ...`, `Timeout crawling ...`). Search logging did not provide an exact string template in phase doc; plan keeps level requirements strict (INFO success, ERROR final failure) and recommends including elapsed seconds consistently.
- Existing tests currently do not assert elapsed-log content or search retry behavior; this aligns with plan sequencing where Phase 5 is dedicated to test expansion.
