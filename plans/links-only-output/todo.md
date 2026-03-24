---
type: planning
entity: todo
plan: "links-only-output"
updated: "2026-03-24"
---

# Todo: links-only-output

> Tracking [links-only-output](plan.md)

## Active Phase: 1 - Add --links-only CLI flag and output formatting

### Phase Context

- **Scope**: [Phase 1](phases/phase-1.md)
- **Implementation**: [Phase 1 Plan](implementation/phase-1-impl.md)
- **Latest Handover**: — (none yet)
- **Relevant Docs**: `docs/modules/crawler-cli.md`, `docs/modules/crawler-document-pipeline.md`

### Pending

- [ ] Add `--links-only` argument to `_parse_crawl_args()` with mutual exclusion vs `--remove-links` <!-- added: 2026-03-24 -->
- [ ] Implement reference formatting function (`[N] label - href`) <!-- added: 2026-03-24 -->
- [ ] Update `_write_output()` to handle `--links-only` mode (single + multi-doc) <!-- added: 2026-03-24 -->
- [ ] Handle `--links-only` + `--json`: pure references array output <!-- added: 2026-03-24 -->
- [ ] Handle zero-reference pages: `No references found for <url>` <!-- added: 2026-03-24 -->
- [ ] Add unit tests: formatting, flag conflict, zero-refs, JSON output <!-- added: 2026-03-24 -->
- [ ] Verify existing tests still pass <!-- added: 2026-03-24 -->
- [ ] Integration test: real URL with `--links-only` <!-- added: 2026-03-24 -->

### In Progress

### Completed

### Blocked

## Changelog

### 2026-03-24

- Plan created, initial todo items populated from Phase 1 scope
- Plan reviewed: resolved 4 major findings (flag conflict → argparse error, JSON → pure refs array, zero-refs → message, multi-doc → existing patterns)
