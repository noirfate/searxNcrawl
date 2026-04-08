---
type: planning
entity: implementation-plan
plan: "timeout-and-reliability"
phase: 2
status: draft
created: "2026-04-08"
updated: "2026-04-08"
---

# Implementation Plan: Phase 2 - MCP Tool Timeout Parameters

> Implements [Phase 2](../phases/phase-2.md) of [timeout-and-reliability](../plan.md)

## Approach

Expose `timeout` as explicit MCP tool parameters in `crawl` and `crawl_site`, validate at tool boundary (`timeout >= 1`), and thread values through existing async wrappers so timeout behavior is configurable per request without changing default behavior.

This phase is interface-plumbing focused: MCP schema + wrapper signatures + forwarding. Timeout enforcement mechanics (`asyncio.wait_for` + graceful timeout semantics) remain Phase 1 concerns and are consumed here.

## Affected Modules

| Module | Change Type | Description |
|--------|-------------|-------------|
| `crawler/mcp_server.py` | modify | Add `timeout` parameters to MCP tools (`crawl`, `crawl_site`), validate values, update docstrings/schema descriptions, and forward timeout to crawl wrappers. |
| `crawler/__init__.py` | modify | Extend `crawl_page_async()`, `crawl_pages_async()`, and `crawl_site_async()` signatures with optional `timeout`; thread value to underlying calls. |
| `crawler/site.py` | modify | Extend `crawl_site_async()` signature with optional `timeout` and pass it to the timeout wrapper logic introduced in Phase 1. |
| `tests/test_mcp_server.py` | verify (no required code change expected) | Existing MCP forwarding tests are the first regression surface for signature changes and tool argument threading. |
| `tests/test_init.py` | verify (no required code change expected) | Existing wrapper forwarding tests may need fixture signature updates if monkeypatched fakes become strict about kwargs. |
| `tests/test_auth_core.py` | verify (no required code change expected) | Existing auth/config threading tests ensure timeout plumbing does not alter current auth behavior. |

## Required Context

| File | Why |
|------|-----|
| `plans/timeout-and-reliability/plan.md` | Global defaults/constraints and phase sequencing (Phase 2 depends on Phase 1 mechanics). |
| `plans/timeout-and-reliability/phases/phase-2.md` | Gated scope, deliverables, acceptance criteria for this phase. |
| `plans/timeout-and-reliability/implementation/phase-1-impl.md` | Expected timeout constants and enforcement behavior that Phase 2 should parameterize, not re-invent. |
| `crawler/mcp_server.py` | MCP tool schemas, docstrings, and forwarding callsites for `crawl` and `crawl_site`. |
| `crawler/__init__.py` | Public async wrappers (`crawl_page_async`, `crawl_pages_async`, `crawl_site_async`) that need timeout parameters threaded through. |
| `crawler/site.py` | Site crawl implementation (`crawl_site_async`) where site-level timeout is consumed. |
| `tests/test_mcp_server.py` | Existing MCP forwarding behavior and monkeypatch signatures impacted by added kwargs. |
| `tests/test_init.py` | Existing wrapper behavior tests that can regress if timeout kwarg forwarding changes defaults or call shapes. |
| `tests/test_auth_core.py` | Existing auth path coverage to ensure timeout forwarding is additive and does not affect auth config threading. |

## Implementation Steps

### Step 1: Add timeout parameter + validation to MCP `crawl` tool

- **What**:
  - Update `crawl(...)` signature in `crawler/mcp_server.py` to include `timeout: int = 30`.
  - Add boundary validation before crawl execution:
    - `if timeout < 1: raise ValueError("timeout must be >= 1")`
  - Update docstring `Args` so schema/docs clearly describe timeout semantics:
    - `timeout: Per-URL timeout in seconds (default: 30, must be >= 1)`.
- **Where**: `crawler/mcp_server.py`, symbol `crawl` (current region around `188-262`).
- **Why**: Exposes configurable per-URL timeout in MCP schema and enforces contract early with clear error messaging.
- **Considerations**:
  - Validation should happen at tool boundary to fail fast before any crawler setup/network I/O.
  - Keep current output-format fallback behavior unchanged.

### Step 2: Thread `crawl` timeout into page/batch wrappers

- **What**:
  - In `crawl(...)`, forward `timeout` in both execution branches:
    - single URL: `crawl_page_async(..., timeout=timeout, ...)`
    - multi URL: `crawl_pages_async(..., timeout=timeout, ...)`
  - Extend wrapper signatures in `crawler/__init__.py`:
    - `crawl_page_async(..., timeout: Optional[int] = None)`
    - `crawl_pages_async(..., timeout: Optional[int] = None)`
  - In `crawl_pages_async()` inner `crawl_one`, forward `timeout` into `crawl_page_async(...)`.
  - Docstrings in `crawler/__init__.py` should describe timeout as per-URL and optional override.
- **Where**:
  - `crawler/mcp_server.py` (`crawl` tool callsites).
  - `crawler/__init__.py` (`crawl_page_async`, `crawl_pages_async`, inner `crawl_one`).
- **Why**: MCP-provided timeout must reach the actual execution path; otherwise schema exposure would be non-functional.
- **Considerations**:
  - Preserve existing defaults by interpreting `timeout=None` as “use module default constant” in Phase 1 timeout wrapper logic.
  - Keep `crawl_pages_async` behavior per-URL (not batch-global), consistent with Phase 1 and phase intent.

### Step 3: Add timeout parameter + validation to MCP `crawl_site` tool

- **What**:
  - Update `crawl_site(...)` signature in `crawler/mcp_server.py` to include `timeout: int = 120`.
  - Add validation:
    - `if timeout < 1: raise ValueError("timeout must be >= 1")`
  - Update docstring `Args` text:
    - `timeout: Overall site crawl timeout in seconds (default: 120, must be >= 1)`.
- **Where**: `crawler/mcp_server.py`, symbol `crawl_site` (current region around `265-343`).
- **Why**: Exposes site-crawl timeout in MCP schema with explicit type/default/rules.
- **Considerations**:
  - Maintain parity in validation style/message with `crawl` to keep API consistent.

### Step 4: Thread site timeout through wrappers to site implementation

- **What**:
  - Forward `timeout` from MCP `crawl_site(...)` to `crawl_site_async(...)` call.
  - Extend wrapper signatures:
    - `crawler/__init__.py::crawl_site_async(..., timeout: Optional[int] = None)`
    - `crawler/site.py::crawl_site_async(..., timeout: Optional[int] = None)`
  - Ensure `crawler/__init__.py::crawl_site_async` forwards timeout to `crawler.site._crawl_site_async`.
  - Ensure `crawler/site.py::crawl_site_async` consumes optional override in timeout wrapper branch from Phase 1 (site default 120 when `None`).
- **Where**:
  - `crawler/mcp_server.py` (`crawl_site_async(...)` invocation).
  - `crawler/__init__.py` (`crawl_site_async` wrapper).
  - `crawler/site.py` (`crawl_site_async` implementation).
- **Why**: Completes end-to-end parameter threading so MCP-provided site timeout controls runtime behavior.
- **Considerations**:
  - Keep graceful timeout result contract unchanged (Phase 1 behavior): this phase should only make timeout value configurable.

### Step 5: Keep wrapper/API compatibility and update any strict test doubles

- **What**:
  - Verify existing monkeypatched async fakes in tests accept the new `timeout` kwarg where calls now include it.
  - If any test fake has strict kwargs and fails, update fake signatures minimally (no semantic weakening).
- **Where**: Primarily `tests/test_mcp_server.py` and `tests/test_init.py` monkeypatch helper functions.
- **Why**: Signature evolution commonly breaks strict test doubles even when production behavior is correct.
- **Considerations**:
  - Do not relax assertions that verify auth/dedup forwarding; just extend fixtures for timeout kwargs.

## Testing Plan

| Test Type | What to Test | Expected Outcome |
|-----------|-------------|-----------------|
| Manual async smoke | Invoke `mcp_server.crawl(urls=[...], timeout=10)` and `mcp_server.crawl_site(url=..., timeout=60)` with monkeypatched crawler wrappers capturing kwargs. Also call each tool with `timeout=0`. | Valid timeout values are forwarded (`10` and `60` observed at wrapper callsites). Invalid timeout raises `ValueError` with clear message (`timeout must be >= 1`). |
| Regression (existing tests) | Re-run existing wrapper/auth/MCP tests after signature updates. | Existing tests pass without disabling/weakening assertions. |

**Verify command (single command):**

```bash
python -m pytest -q tests/test_mcp_server.py tests/test_init.py tests/test_auth_core.py
```

### Test Integrity Constraints

- `tests/test_mcp_server.py::test_mcp_crawl_forwards_dedup_mode` and `::test_mcp_crawl_site_forwards_dedup_mode` are directly affected by MCP call signatures; assertions on `dedup_mode` and `auth` must remain intact.
- `tests/test_init.py::test_crawl_pages_async_defaults_to_exact` is affected by internal `crawl_page_async(...)` call shape; dedup default semantics must remain unchanged.
- `tests/test_init.py::test_crawl_pages_async_forwards_auth_to_crawl_page` must continue proving auth forwarding; timeout plumbing must not alter resolved auth object behavior.
- `tests/test_auth_core.py::test_crawl_page_async_no_auth_keeps_existing_runtime_path`, `::test_crawl_page_async_threads_storage_state_to_browser_config`, and `::test_crawl_site_async_threads_resolved_storage_state` must continue to pass, ensuring timeout additions are additive and do not alter auth/browser config flow.
- No existing tests should be deleted, skipped, or relaxed for this phase.

## Rollback Strategy

1. Revert MCP signature/validation edits in `crawler/mcp_server.py` first if tool schema or client compatibility issues appear.
2. Revert optional `timeout` parameters in wrapper signatures (`crawler/__init__.py`, `crawler/site.py`) if they introduce unexpected call-chain regressions.
3. Keep timeout defaults/enforcement from Phase 1 untouched during rollback unless independently broken.
4. Re-run the verify command to confirm baseline behavior restoration.

## Open Decisions

| Decision | Options | Chosen | Rationale |
|----------|---------|--------|-----------|
| Timeout validation location | MCP boundary only vs wrappers + MCP | MCP boundary only (Phase 2) | Phase intent explicitly scopes validation to tool parameter contract; wrappers remain callable by non-MCP code and can preserve optional semantics. |
| Validation error message | Distinct per tool vs shared message | Shared: `timeout must be >= 1` | Consistent UX and easier testing/documentation. |

## Reality Check

### Code Anchors Used

| File | Symbol/Area | Why it matters |
|------|-------------|----------------|
| `crawler/mcp_server.py:188-262` | `crawl` tool signature/docstring/calls | Primary MCP schema surface for per-URL timeout parameter and forwarding. |
| `crawler/mcp_server.py:265-343` | `crawl_site` tool signature/docstring/calls | Primary MCP schema surface for site timeout parameter and forwarding. |
| `crawler/__init__.py:94-135` | `crawl_page_async()` | Wrapper that must accept optional timeout and apply/forward it to page crawl runtime. |
| `crawler/__init__.py:183-228` | `crawl_pages_async()` and inner `crawl_one()` | Batch per-URL forwarding path where timeout must be threaded to each page call. |
| `crawler/__init__.py:250-267` | `crawl_site_async()` wrapper | Bridge from package API to site module implementation; needs timeout passthrough. |
| `crawler/site.py:63-180` | `crawl_site_async()` | Site crawl implementation point that consumes optional timeout override. |
| `tests/test_mcp_server.py:25-77` | MCP forwarding tests | First regression indicators for MCP signature and forwarding changes. |
| `tests/test_init.py:39-106` | batch wrapper forwarding tests | Ensures timeout threading does not regress dedup/auth behavior. |
| `tests/test_auth_core.py:49-166` | auth + runtime threading tests | Guards against incidental behavior changes while adding timeout kwargs. |

### Mismatches / Notes

- **Mismatch vs Phase 1 context:** current checked-in code at the anchors above does **not** yet show Phase 1 timeout constants/wrappers (`DEFAULT_PAGE_TIMEOUT`, `DEFAULT_SITE_TIMEOUT`, `asyncio.wait_for` branches). Phase 2 assumes those mechanics exist. Implementing agent should confirm branch state before coding:
  - If Phase 1 changes are on another branch/unmerged, merge/cherry-pick Phase 1 first.
  - Do not expand Phase 2 scope by re-implementing Phase 1 unless explicitly instructed.
- Existing test suite currently has no explicit assertions for timeout parameter forwarding/validation behavior; this matches plan sequencing where dedicated timeout tests are introduced in Phase 5.
