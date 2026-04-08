# Plan Review: timeout-and-reliability

Date: 2026-04-08  
Reviewer: Subagent

## Scope Reviewed

- `plans/timeout-and-reliability/plan.md`
- `plans/timeout-and-reliability/phases/phase-1.md` .. `phase-5.md`
- `docs/reviews/timeout-and-reliability-review.md`
- Source validation:
  - `crawler/__init__.py`
  - `crawler/site.py`
  - `crawler/config.py`
  - `crawler/mcp_server.py`

## Overall Assessment

The plan is well-structured (5 phases are sensible) and mostly actionable, but it has one significant correctness gap and a couple of actionability gaps that should be fixed before implementation.

## Coverage of F-1..F-7

| Finding | Planned? | Notes |
|---|---|---|
| F-1 (core crawl awaits unbounded) | Yes | Phase 1 adds `asyncio.wait_for()` to crawl paths. |
| F-2 (`networkidle` unbounded) | **Partially / Incorrectly targeted** | Phase 3 updates `build_discovery_run_config()`, but that config is currently unused by crawl execution paths. |
| F-3 (`wait_for` predicate unbounded) | Yes | Phase 3 adds `page_timeout` to markdown config. |
| F-4 (MCP timeout params missing) | Yes | Phase 2 adds `timeout` to `crawl` and `crawl_site`. |
| F-5 (search retry/backoff) | Yes | Phase 4 adds retry on `httpx.RequestError`. |
| F-6 (per-URL timeout in batch crawl) | Yes | Phase 1 addresses per-URL timeout behavior. |
| F-7 (elapsed-time logging missing) | Yes | Phase 4 covers crawl/search elapsed logging. |

## Findings

### Major-1: F-2 fix is aimed at an unused config path

**Issue**  
Phase 3 proposes changing `build_discovery_run_config(wait_until="networkidle")`, but current crawl execution does not call `build_discovery_run_config()` anywhere. `crawl_page_async()` and `crawl_site_async()` both use `build_markdown_run_config()`.

**Why this matters**  
The planned change may not reduce real hanging behavior in production paths, so F-2 may remain effectively unaddressed.

**Evidence**
- `crawler/site.py` uses `config = build_markdown_run_config()` (not discovery config).
- Repo search shows only one reference to `build_discovery_run_config()` (its definition).

**Recommendation**  
Retarget F-2 mitigation to active run configs (`build_markdown_run_config()` or the specific config actually used by crawl paths), or explicitly wire discovery config into the site-crawl path if that was intended.

---

### Major-2: Timeout outcome contract for `crawl_site` is underspecified and may violate graceful-failure requirement

**Issue**  
Plan says `crawl_site_async()` should raise `TimeoutError` (Phase 1), while plan-level non-functional requirements say timed-out operations should return graceful error documents rather than unhandled exceptions.

**Why this matters**  
`mcp_server.crawl_site()` currently does not wrap `crawl_site_async()` in try/except. If `TimeoutError` is raised, tool behavior may become MCP-level failure instead of structured crawl output.

**Recommendation**  
Define and test explicit behavior for site timeout:
- Either convert timeout to structured failed output in `crawl_site` tool, or
- Keep raising but make that an explicit, accepted contract (and adjust requirement wording).

---

### Minor-1: Phase 3 acceptance criteria assume Crawl4AI behavior that may not hold

**Issue**  
Criterion states: page without `<main>` should hit `page_timeout` then “proceed with available content.” In practice, Crawl4AI/Playwright may instead return a failed result or exception depending on internal handling.

**Recommendation**  
Relax acceptance wording to: operation is bounded by timeout and returns deterministic non-hanging outcome (success with partial content **or** structured failure), then assert that outcome explicitly.

---

### Minor-2: Cancellation-safety validation is not part of test plan

**Issue**  
Plan acknowledges `asyncio.wait_for()` cancellation risk with Playwright/Crawl4AI, but tests do not verify cleanup behavior on timeout.

**Recommendation**  
Add at least one unit test with a dummy `AsyncWebCrawler` context manager to assert `__aexit__` runs on timeout/cancellation path (or equivalent cleanup assertion).

---

### Note-1: Timeout input validation is mentioned but not concretely specified

**Issue**  
Phase 2 notes minimum timeout validation (e.g., `>=5`) but lacks acceptance criteria/tests for invalid values.

**Recommendation**  
Define exact validation rules (`timeout > 0` vs `>=5`) and add one test for invalid input handling.

## Phase Boundary / Dependency Check

- 5-phase structure is sensible and mostly well-ordered.
- Phase 1 -> Phase 2 dependency is correct.
- Phase 5 as validation gate after functional phases is appropriate.
- Main dependency correction needed: Phase 3 should depend on/target the config path actually used at runtime.

## Specific Check Requested: `crawl_site_async()` timeout wrapping viability

Confirmed: `crawler/site.py:crawl_site_async()` currently issues a **single** `await crawler.arun(url=seed_url, config=config)` call for BFS crawl execution (with `config.stream = False`). Wrapping that await in `asyncio.wait_for()` would bound the entire BFS crawl duration from the caller perspective.

## Final Verdict

Plan is close to implementable, but should be revised for the two Major findings above before execution (especially retargeting the F-2 fix to active code paths).
