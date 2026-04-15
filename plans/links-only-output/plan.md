---
type: planning
entity: plan
plan: "links-only-output"
status: completed
created: "2026-03-24"
updated: "2026-03-24"
---

# Plan: links-only-output

## Objective

Add a `--links-only` flag to the `crawl` CLI command that outputs only the extracted references (links) in markdown reference format instead of the full page content.

## Motivation

The crawl pipeline already extracts and stores page references in `CrawledDocument.references`, but this data is only accessible in JSON output mode. Users need a quick way to extract just the links from a crawled page — useful for link auditing, sitemap discovery, and piping into downstream tools. A dedicated `--links-only` flag provides a clean, purpose-built interface for this use case.

## Requirements

### Functional

- [x] New `--links-only` CLI flag on the `crawl` command
- [x] When active, output contains only extracted references in markdown reference format: `[N] label - href`
- [x] Works with single-URL crawls
- [x] Works with multi-URL crawls (multiple URLs as positional args)
- [x] Works with `--site` site crawls
- [x] Multi-document output separates link lists per page with a URL header
- [x] `--links-only` combined with `-o` writes references to file instead of stdout
- [x] `--links-only` combined with `--json` outputs a pure references array: `[{index, href, label}, ...]`
- [x] `--links-only` combined with `--remove-links` raises an argparse error (mutually exclusive)
- [x] Pages with zero references print: `No references found for <url>`

### Non-Functional

- [x] No changes to crawl orchestration or document pipeline — formatting only
- [x] Minimal code delta: leverage existing `CrawledDocument.references` data
- [x] Consistent with existing CLI flag patterns (argparse, `_write_output`)

## Scope

### In Scope

- CLI `crawler/cli.py`: new `--links-only` argument, output formatting logic
- Reference formatting helper (may be a small function in `cli.py` or `document.py`)
- Interaction with existing flags: `-o`, `--json`, `--site`, `--remove-links`

### Out of Scope

- MCP server changes (user explicitly scoped to CLI only)
- Enhancements to reference extraction logic (`references.py`)
- New tests for reference parsing itself
- Changes to `CrawledDocument` data model

## Definition of Done

- [x] `crawl <url> --links-only` outputs only references in `[N] label - href` format
- [x] Multi-URL and `--site` crawls with `--links-only` show per-page link lists with URL headers
- [x] `--links-only --json` outputs a pure references JSON array per document
- [x] `-o` file output works with `--links-only`
- [x] `--links-only` + `--remove-links` produces an argparse error
- [x] Pages with zero references show `No references found for <url>`
- [x] Multi-doc output follows existing CLI patterns: stdout=combined with URL headers, `-o file`=single file, `-o dir`=per-URL files
- [x] Existing tests still pass
- [x] New test(s) cover the `--links-only` output path including flag conflicts and edge cases
- [x] `crawl --help` documents the new flag

## Testing Strategy

- [x] Unit test: `--links-only` output formatting for single document
- [x] Unit test: `--links-only` output formatting for multiple documents
- [x] Unit test: `--links-only` + `--remove-links` conflict raises error
- [x] Unit test: zero-reference page shows "No references found" message
- [x] Unit test: `--links-only --json` produces pure references array
- [x] Integration: run `crawl <url> --links-only` against a real URL and verify output format
- [x] Regression: existing test suite passes unchanged

## Phases

| Phase | Title | Scope | Status |
|-------|-------|-------|--------|
| 1 | Add --links-only CLI flag and output formatting | [Detail](phases/phase-1.md) | completed |

## Risks & Open Questions

| Risk/Question | Impact | Mitigation/Answer |
|---------------|--------|-------------------|
| Pages with zero references produce empty output | Low | **Decided**: Print `No references found for <url>` message |
| `--links-only` + `--remove-links` is contradictory | Low | **Decided**: Raise argparse error — flags are mutually exclusive |
| Reference extraction quality varies by page | Medium | Out of scope — existing extraction is used as-is |

## Changelog

### 2026-03-24

- Plan created
- Plan reviewed (delegate): 4 major findings resolved — flag conflict (argparse error), JSON output (pure references array), zero-reference behavior (message), multi-doc output (follows existing CLI patterns)
- Implementation plan authored and verified for Phase 1
- Implementation plan reviewed: 3 major findings resolved (test coverage expanded to 12 cases, smoke test added)
- Phase 1 executed: 54/54 tests pass, smoke tests verified
- Plan completed
