---
type: planning
entity: phase
plan: "links-only-output"
phase: 1
status: pending
created: "2026-03-24"
updated: "2026-03-24"
---

# Phase 1: Add --links-only CLI flag and output formatting

> Part of [links-only-output](../plan.md)

## Objective

Implement the `--links-only` flag in the CLI crawl command so that users can output only extracted references in markdown reference format instead of the full crawled content.

## Scope

### Includes

- Add `--links-only` argument to `_parse_crawl_args()` in `crawler/cli.py`
- Implement reference formatting function that renders `CrawledDocument.references` as `[N] label - href` lines
- Modify `_write_output()` to use the new formatting when `--links-only` is active
- Handle single-document and multi-document cases (URL headers for multi-doc)
- Handle interaction with `--json` flag: output pure references array `[{index, href, label}, ...]` (NOT full `_doc_to_dict`)
- Handle interaction with `-o` flag (file output follows existing multi-doc patterns: `-o file`=single file, `-o dir`=per-URL files)
- Handle `--links-only` + `--remove-links` as mutually exclusive (argparse error)
- Handle zero-reference pages: print `No references found for <url>`
- Add/update tests for the new output path
- Update help text for the new flag

### Excludes (deferred to later phases)

- MCP server changes
- Reference extraction improvements
- CrawledDocument model changes

## Prerequisites

- [ ] Feature branch `feature/links-only-output` created (done)
- [ ] Understanding of `_write_output()` flow in `crawler/cli.py` (documented in docs/)

## Deliverables

- [ ] `--links-only` flag added to CLI argument parser
- [ ] Reference formatting function producing `[N] label - href` output
- [ ] `_write_output()` updated to handle `--links-only` mode
- [ ] Tests covering the new flag and output formatting
- [ ] Help text updated

## Acceptance Criteria

- [ ] `crawl https://example.com --links-only` prints only references, one per line, in `[N] label - href` format
- [ ] `crawl https://a.com https://b.com --links-only` prints per-URL headers followed by references
- [ ] `crawl https://example.com --site --links-only` prints per-page headers followed by references
- [ ] `crawl https://example.com --links-only --json` outputs pure references JSON array
- [ ] `crawl https://example.com --links-only -o out.txt` writes references to file
- [ ] `crawl https://example.com --links-only --remove-links` produces argparse error
- [ ] Page with no references shows `No references found for <url>`
- [ ] All existing tests pass
- [ ] `crawl --help` shows `--links-only` with a clear description

## Dependencies on Other Phases

| Phase | Relationship | Notes |
|-------|-------------|-------|
| — | — | Single-phase plan, no dependencies |

## Notes

- `CrawledDocument.references` is a `List[Reference]` where `Reference` has `index: int`, `href: str`, `label: str`
- References are already populated by the crawl pipeline via `references.py`
- Key functions in `cli.py`: `_parse_crawl_args()`, `_run_crawl_async()`, `_write_output()`, `_doc_to_dict()`
- Relevant docs: `docs/modules/crawler-cli.md`, `docs/modules/crawler-document-pipeline.md`
