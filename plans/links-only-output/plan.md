---
type: planning
entity: plan
plan: "links-only-output"
status: active
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

- [ ] New `--links-only` CLI flag on the `crawl` command
- [ ] When active, output contains only extracted references in markdown reference format: `[N] label - href`
- [ ] Works with single-URL crawls
- [ ] Works with multi-URL crawls (multiple URLs as positional args)
- [ ] Works with `--site` site crawls
- [ ] Multi-document output separates link lists per page with a URL header
- [ ] `--links-only` combined with `-o` writes references to file instead of stdout
- [ ] `--links-only` combined with `--json` outputs a pure references array: `[{index, href, label}, ...]`
- [ ] `--links-only` combined with `--remove-links` raises an argparse error (mutually exclusive)
- [ ] Pages with zero references print: `No references found for <url>`

### Non-Functional

- [ ] No changes to crawl orchestration or document pipeline — formatting only
- [ ] Minimal code delta: leverage existing `CrawledDocument.references` data
- [ ] Consistent with existing CLI flag patterns (argparse, `_write_output`)

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

- [ ] `crawl <url> --links-only` outputs only references in `[N] label - href` format
- [ ] Multi-URL and `--site` crawls with `--links-only` show per-page link lists with URL headers
- [ ] `--links-only --json` outputs a pure references JSON array per document
- [ ] `-o` file output works with `--links-only`
- [ ] `--links-only` + `--remove-links` produces an argparse error
- [ ] Pages with zero references show `No references found for <url>`
- [ ] Multi-doc output follows existing CLI patterns: stdout=combined with URL headers, `-o file`=single file, `-o dir`=per-URL files
- [ ] Existing tests still pass
- [ ] New test(s) cover the `--links-only` output path including flag conflicts and edge cases
- [ ] `crawl --help` documents the new flag

## Testing Strategy

- [ ] Unit test: `--links-only` output formatting for single document
- [ ] Unit test: `--links-only` output formatting for multiple documents
- [ ] Unit test: `--links-only` + `--remove-links` conflict raises error
- [ ] Unit test: zero-reference page shows "No references found" message
- [ ] Unit test: `--links-only --json` produces pure references array
- [ ] Integration: run `crawl <url> --links-only` against a real URL and verify output format
- [ ] Regression: existing test suite passes unchanged

## Phases

| Phase | Title | Scope | Status |
|-------|-------|-------|--------|
| 1 | Add --links-only CLI flag and output formatting | [Detail](phases/phase-1.md) | pending |

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
