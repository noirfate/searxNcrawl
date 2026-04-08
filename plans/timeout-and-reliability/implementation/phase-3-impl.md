---
type: planning
entity: implementation-plan
plan: "timeout-and-reliability"
phase: 3
status: draft
created: "2026-04-08"
updated: "2026-04-08"
---

# Implementation Plan: Phase 3 - Replace networkidle + Bound wait_for

> Implements [Phase 3](../phases/phase-3.md) of [timeout-and-reliability](../plan.md)

## Approach

Make a focused config-only reliability change in `crawler/config.py` so both run-config builders are time-bounded at the Crawl4AI layer:

- Active crawl path: add `page_timeout=30000` to `build_markdown_run_config()` (used by `crawl_page_async()` and `crawl_site_async()`).
- Defensive future path: in `build_discovery_run_config()`, replace `wait_until="networkidle"` with `wait_until="domcontentloaded"` and add `page_timeout=30000`.

Keep the existing `wait_for` predicate unchanged; the new `page_timeout` bounds the predicate wait so it cannot hang indefinitely.

## Affected Modules

| Module | Change Type | Description |
|--------|-------------|-------------|
| `crawler/config.py` | modify | Add `page_timeout=30000` to both `build_markdown_run_config()` and `build_discovery_run_config()`, and switch discovery `wait_until` to `domcontentloaded`. |
| `crawler/__init__.py` | verify (no code change expected) | Confirm active crawl entrypoints still build run config via `build_markdown_run_config()`. |
| `crawler/site.py` | verify (no code change expected) | Confirm site crawl path uses `build_markdown_run_config()` (not discovery config). |

## Required Context

| File | Why |
|------|-----|
| `plans/timeout-and-reliability/plan.md` | Global reliability requirements and phase sequencing constraints. |
| `plans/timeout-and-reliability/phases/phase-3.md` | Gated scope/deliverables for this phase. |
| `plans/timeout-and-reliability/baseline/finding-empty-pages.md` | Baseline evidence (5/10 docs.agno pages with `<50` chars) motivating bounded waits. |
| `crawler/config.py` | Contains both target builders: `build_markdown_run_config()` and `build_discovery_run_config()`. |
| `crawler/__init__.py` | Confirms `crawl_page_async()` and `crawl_pages_async()` default to `build_markdown_run_config()`. |
| `crawler/site.py` | Confirms `crawl_site_async()` builds config via `build_markdown_run_config()`. |
| `pyproject.toml` | Confirms dependency range is `crawl4ai>=0.7.4` (not pinned), relevant when validating `page_timeout` support against 0.8.0 docs. |

## Implementation Steps

### Step 1: Add `page_timeout=30000` to active markdown run config

- **What**: In `build_markdown_run_config()`, add `page_timeout=30000` in the `CrawlerRunConfig(...)` constructor, alongside existing navigation/wait options.
- **Where**: `crawler/config.py`, symbol `build_markdown_run_config` (currently around `157-182`).
- **Why**: This is the config actually used by `crawl_page_async()` and `crawl_site_async()`; adding `page_timeout` bounds both navigation completion and the existing JS `wait_for` predicate.
- **Considerations**:
  - Keep current `wait_for="js:() => document.querySelector('main') && ... > 50"` unchanged.
  - Use exact phase-approved value `30000` (milliseconds), not a new constant in this phase.

### Step 2: Make discovery config defensive and bounded

- **What**:
  - In `build_discovery_run_config()`, change `wait_until="networkidle"` to `wait_until="domcontentloaded"`.
  - Add `page_timeout=30000` in the same `CrawlerRunConfig(...)` constructor.
- **Where**: `crawler/config.py`, symbol `build_discovery_run_config` (currently around `185-208`).
- **Why**: `networkidle` can stall indefinitely on pages with continuous network chatter; this defensive update prevents future hangs if discovery config is wired in later.
- **Considerations**:
  - Keep this phase scoped to config behavior only; do not wire discovery config into active crawl flow here.
  - Preserve all existing selector/filter settings.

### Step 3: Re-verify active call chain after edit (no path changes)

- **What**: Confirm no callsite regressions: `crawl_page_async()`, `crawl_pages_async()`, and `site.crawl_site_async()` continue using `build_markdown_run_config()` defaults.
- **Where**:
  - `crawler/__init__.py` (`crawl_page_async`, `crawl_pages_async`)
  - `crawler/site.py` (`crawl_site_async`)
- **Why**: Phase intent depends on the markdown config being the active runtime path.
- **Considerations**:
  - `build_discovery_run_config()` remains unused in current code; this is expected and should be documented, not changed.

## Testing Plan

| Test Type | What to Test | Expected Outcome |
|-----------|-------------|-----------------|
| Manual config + runtime smoke | (1) Programmatically assert `build_markdown_run_config().page_timeout == 30000`; (2) assert discovery config has `wait_until == "domcontentloaded"` and `page_timeout == 30000`; (3) run a real `crawl_page_async()` against a historically thin page (e.g., `https://docs.agno.com/introduction`) and assert completion is bounded (non-hanging) with deterministic result shape. | Config fields reflect phase intent exactly; crawl returns/errs within bounded time rather than hanging indefinitely. |
| Regression (existing tests) | Re-run core wrapper/auth/MCP tests to ensure config edits do not break call signatures or result shaping. | Existing tests continue to pass unchanged. |

**Verify command (single command):**

```bash
python -c "import asyncio, time; from crawler.config import build_markdown_run_config, build_discovery_run_config; from crawler import crawl_page_async; m=build_markdown_run_config(); d=build_discovery_run_config(); assert getattr(m, 'page_timeout', None)==30000, f'markdown page_timeout={getattr(m, \"page_timeout\", None)}'; assert getattr(d, 'wait_until', None)=='domcontentloaded', f'discovery wait_until={getattr(d, \"wait_until\", None)}'; assert getattr(d, 'page_timeout', None)==30000, f'discovery page_timeout={getattr(d, \"page_timeout\", None)}'; t=time.monotonic(); doc=asyncio.run(crawl_page_async('https://docs.agno.com/introduction')); elapsed=time.monotonic()-t; print({'status': doc.status, 'chars': len(doc.markdown), 'elapsed_s': round(elapsed, 2)}); assert elapsed < 45"
```

### Test Integrity Constraints

- No existing tests are expected to require updates for this phase (behavioral changes are runtime waiting semantics, not API shape changes).
- `tests/test_init.py` and `tests/test_auth_core.py` should remain untouched; they exercise wrapper/auth behavior and provide regression confidence that config edits did not alter call contracts.
- `tests/test_mcp_server.py` should remain untouched; MCP forwarding/output behavior is not changed in this phase.
- Phase 5 owns dedicated timeout-behavior unit tests; do not weaken or skip existing tests now.

## Rollback Strategy

1. Revert only the `CrawlerRunConfig(...)` field edits in `crawler/config.py`:
   - remove `page_timeout=30000` from markdown/discovery builders,
   - restore discovery `wait_until` to prior value.
2. Keep other files untouched (this phase should not change callsites).
3. Re-run the verify command to confirm pre-phase behavior restoration.

## Open Decisions

| Decision | Options | Chosen | Rationale |
|----------|---------|--------|-----------|
| `page_timeout` representation in this phase | Inline literal `30000` vs introducing a new shared constant | Inline literal `30000` | Matches gated scope exactly and minimizes unrelated refactor risk. |
| Discovery config posture | Leave as-is (`networkidle`) vs defensive hardening now | Defensive hardening now (`domcontentloaded` + `page_timeout=30000`) | Explicit Phase 3 deliverable; prevents future reintroduction of unbounded waits if discovery path is enabled. |

## Reality Check

### Code Anchors Used

| File | Symbol/Area | Why it matters |
|------|-------------|----------------|
| `crawler/config.py:157-182` | `build_markdown_run_config()` | Primary active run config where `page_timeout=30000` must be added. |
| `crawler/config.py:185-208` | `build_discovery_run_config()` | Discovery config currently uses `wait_until="networkidle"`; target is `domcontentloaded` + `page_timeout=30000`. |
| `crawler/__init__.py:114` | `crawl_page_async()` default `run_config = config or build_markdown_run_config()` | Confirms markdown config is active for single-page path. |
| `crawler/__init__.py:203` | `crawl_pages_async()` default `run_config = config or build_markdown_run_config()` | Confirms batch path also depends on markdown config defaults. |
| `crawler/site.py:100` | `crawl_site_async()` `config = build_markdown_run_config()` | Confirms site crawl path uses markdown config, not discovery config. |
| `plans/timeout-and-reliability/baseline/finding-empty-pages.md:8-27` | docs.agno baseline finding | Grounds reliability motivation: 5/10 pages returned `<50` chars and need bounded JS wait behavior. |
| `https://docs.crawl4ai.com/api/parameters/` | `CrawlerRunConfig` navigation/timing parameters | Confirms `page_timeout` is a valid `CrawlerRunConfig` parameter and documents `wait_until` semantics. |

### Mismatches / Notes

- **Version pin mismatch:** Repository dependency is `crawl4ai>=0.7.4` (`pyproject.toml:8`), not pinned to `0.8.0`. Plan is grounded against Crawl4AI docs indicating `page_timeout` is valid; implementing agent should avoid introducing behavior that depends on undocumented 0.8-only semantics.
- **Local environment gap:** `crawl4ai` is not installed in this execution environment, so runtime signature introspection could not be performed here; use docs/source-of-truth verification in implementation branch CI/dev env.
- **Unused defensive path (expected):** `build_discovery_run_config()` is currently unreferenced in code; changing it is still in-scope as future-proofing per phase doc.
