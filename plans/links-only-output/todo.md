---
type: planning
entity: todo
plan: "links-only-output"
updated: "2026-03-24"
---

# Todo: links-only-output

> Tracking [links-only-output](plan.md)

## Plan Completed ✓

All phases complete. Plan status: **completed**.

### Completed

- [x] Add `--links-only` argument to `_parse_crawl_args()` with mutual exclusion vs `--remove-links` <!-- completed: 2026-03-24 -->
- [x] Implement reference formatting function (`[N] label - href`) <!-- completed: 2026-03-24 -->
- [x] Update `_write_output()` to handle `--links-only` mode (single + multi-doc) <!-- completed: 2026-03-24 -->
- [x] Handle `--links-only` + `--json`: pure references array output <!-- completed: 2026-03-24 -->
- [x] Handle zero-reference pages: `No references found for <url>` <!-- completed: 2026-03-24 -->
- [x] Add unit tests: formatting, flag conflict, zero-refs, JSON output, `-o` destinations, `--site` <!-- completed: 2026-03-24 -->
- [x] Verify existing tests still pass (54/54) <!-- completed: 2026-03-24 -->
- [x] Smoke test: `crawl --links-only https://example.com` against real URL <!-- completed: 2026-03-24 -->

## Changelog

### 2026-03-24

- Plan created, initial todo items populated from Phase 1 scope
- Plan reviewed: resolved 4 major findings (flag conflict → argparse error, JSON → pure refs array, zero-refs → message, multi-doc → existing patterns)
- Implementation plan authored, reviewed (3 major findings → test plan expanded), and revised
- Phase 1 executed: all items completed, 54/54 tests pass, smoke tests verified
- Plan completed
