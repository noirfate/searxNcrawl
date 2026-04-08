---
type: planning
entity: phase
plan: "timeout-and-reliability"
phase: 3
status: completed  # pending | in_progress | completed | skipped
created: "2026-04-08"
updated: "2026-04-08"
---

# Phase 3: Replace networkidle + Bound wait_for

> Part of [timeout-and-reliability](../plan.md)

## Objective

Bound all crawl configs with `page_timeout` so that neither navigation waits (`wait_until`) nor `wait_for` JS predicates can cause indefinite hangs. Also fix the unused `networkidle` setting in discovery config for future-proofing.

Fixes findings **F-2** (Major) and **F-3** (Major) from the review.

## Scope

### Includes

- `crawler/config.py`:
  - `build_markdown_run_config()`: add `page_timeout=30000` (30s) — this bounds both the default navigation wait and the `wait_for` JS predicate. This is the **active config** used by `crawl_page_async()` and `crawl_site_async()`.
  - `build_discovery_run_config()`: change `wait_until="networkidle"` to `wait_until="domcontentloaded"` AND add `page_timeout=30000` — defensive fix for future use (currently unused but should not hang if wired in later).
  - The existing `wait_for` predicate (`js:() => document.querySelector('main') && ...`) is kept but now bounded by `page_timeout`

### Excludes (deferred to later phases)

- No changes to timeout wrapping (Phase 1) or MCP parameters (Phase 2)

## Prerequisites

- [ ] None — independent of other phases

## Deliverables

- [ ] Discovery config uses `domcontentloaded` instead of `networkidle`
- [ ] Markdown config includes `page_timeout=30000`
- [ ] Existing tests continue to pass

## Acceptance Criteria

- [ ] Crawl a page with continuous network activity (e.g., WebSocket pings) → completes within `page_timeout` instead of hanging
- [ ] Crawl a page without `<main>` element → operation is bounded by `page_timeout` (30s) and returns a deterministic non-hanging outcome (success with partial content or structured failure)
- [ ] `build_discovery_run_config()` no longer uses `networkidle` and has `page_timeout` set
- [ ] Existing tests continue to pass

## Dependencies on Other Phases

| Phase | Relationship | Notes |
|-------|-------------|-------|
| Phase 1 | parallel | Independent |
| Phase 2 | parallel | Independent |
| Phase 4 | parallel | Independent |
| Phase 5 | blocks | Tests should verify bounded wait behavior |

## Notes

- `domcontentloaded` fires when the initial HTML document has been completely loaded and parsed, without waiting for stylesheets, images, and subframes to finish loading.
- `page_timeout` in Crawl4AI controls the maximum time Playwright waits for page operations. Set to 30000ms (30s).
- The `wait_for` predicate may fail on pages without `<main>`, but `page_timeout` ensures it won't hang forever. The crawl will proceed with whatever content is available after the timeout expires.
- This is a behavioral change — pages that previously waited for full network idle will now proceed faster. This is the desired trade-off for reliability.
