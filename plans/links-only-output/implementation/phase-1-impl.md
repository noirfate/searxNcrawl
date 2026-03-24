---
type: planning
entity: implementation-plan
plan: "links-only-output"
phase: 1
status: draft
created: "2026-03-24"
updated: "2026-03-24"
---

# Implementation Plan: Phase 1 - Add --links-only CLI flag and output formatting

> Implements [Phase 1](../phases/phase-1.md) of [links-only-output](../plan.md)

## Approach

Implement `--links-only` as a CLI-only output-mode switch in `crawler/cli.py`, reusing already-extracted `CrawledDocument.references` (`crawler/document.py:28`, `crawler/references.py:13-56`) and avoiding crawl pipeline/model changes. The implementation should add parser-level conflict handling (`--links-only` vs `--remove-links`), then branch output behavior early in `_write_output()` (`crawler/cli.py:164-225`) so links-only formatting/serialization is isolated from existing markdown and `_doc_to_dict()` JSON paths.

Because links-only has explicit gated behavior for single-doc, multi-doc, `--json`, zero-reference, and `-o` destinations, this plan scopes code changes to argument parsing, a dedicated references formatter helper, and targeted `_write_output()` routing, plus test expansion in `tests/test_cli.py`.

## Affected Modules

| Module | Change Type | Description |
|--------|-------------|-------------|
| [crawler-cli](../../docs/modules/crawler-cli.md) | modify | Add `--links-only` flag to `_parse_crawl_args()` and links-only branches/helper in `_write_output()` for markdown + JSON references output. |
| `tests/test_cli.py` | modify | Add parser/output tests for links-only behavior (flag parsing, mutual exclusion, single/multi-doc, JSON, zero-reference). |

## Required Context

| File | Why |
|------|-----|
| `plans/links-only-output/plan.md` | Global requirements, constraints, and gated decisions for output contract and flag interaction. |
| `plans/links-only-output/phases/phase-1.md` | Phase 1 objective, deliverables, and acceptance criteria. |
| `crawler/cli.py` | Target implementation points: `_doc_to_dict()` (`:138-151`), `_write_output()` (`:164-225`), `_parse_crawl_args()` (`:232-333`), `_run_crawl_async()` call path (`:404-409`). |
| `crawler/document.py` | Canonical `Reference`/`CrawledDocument` fields for output rendering and JSON shape (`:9-31`). |
| `crawler/references.py` | Confirms upstream reference extraction already provides `index/href/label`; no extraction changes needed (`:13-56`). |
| `tests/test_cli.py` | Existing test style for parser and async flow monkeypatching to extend with links-only cases (`:24-170`). |
| `docs/modules/crawler-cli.md` | Module inventory and symbol anchors for CLI surface updates. |

## Implementation Steps

### Step 1: Add parser flag and mutual exclusion contract

- **What**: In `_parse_crawl_args()` (`crawler/cli.py:232-333`), introduce `--links-only` and make it mutually exclusive with `--remove-links` using `argparse` mutual exclusion group.
- **Where**: `crawler/cli.py`, symbol `_parse_crawl_args`.
- **Why**: Phase requirements explicitly gate contradictory flags as parser error and require help surface for the new mode.
- **Considerations**: Preserve existing defaults and arg names (`args.json_output`, `args.remove_links`) while adding `args.links_only`; ensure help text is clear that links-only prints references only.

### Step 2: Add dedicated references formatter helper

- **What**: Add `_format_references(doc: CrawledDocument) -> str` that renders one reference per line as `[N] label - href`, and returns `No references found for <url>` when `doc.references` is empty.
- **Where**: `crawler/cli.py`, near `_doc_to_dict()`/`_write_output()` for output-related cohesion.
- **Why**: Centralizing formatting avoids duplicating logic across stdout/file/multi-doc paths and enforces the exact gated output string.
- **Considerations**: Use `doc.final_url` for `<url>` in the zero-reference message; retain `ref.index` from `Reference` (do not re-enumerate), and treat empty labels consistently (still include separator with normalized output contract).

### Step 3: Add links-only output routing in `_write_output()`

- **What**: Extend `_write_output()` signature and logic to accept a links-only mode flag and branch before existing markdown/JSON code paths. For links-only mode:
  - markdown mode uses `_format_references(doc)` output.
  - `--links-only --json` emits pure references arrays (`[{"index": ..., "href": ..., "label": ...}]`) and does not use `_doc_to_dict()`.
- **Where**: `crawler/cli.py`, symbol `_write_output` (`:164-225`) and caller `_run_crawl_async` (`:404-409`) to pass `args.links_only`.
- **Why**: Gated requirement demands links-only behavior independent of existing document serialization and `remove-links` markdown scrub logic.
- **Considerations**: Keep non-links-only behavior unchanged; for multi-doc links-only output, follow gated format: URL headers + per-doc links list when writing combined stdout/single file, and per-URL files when output destination is a directory.

### Step 4: Implement destination-specific links-only materialization

- **What**: Within the links-only branch, explicitly handle destination modes:
  - Single doc + stdout/file path.
  - Multi-doc + stdout combined output with per-URL headers.
  - Multi-doc + `-o <file>` combined output file.
  - Multi-doc + `-o <dir>` per-URL files.
- **Where**: `crawler/cli.py`, symbol `_write_output`.
- **Why**: Phase acceptance and plan decisions define exact behavior for multi-doc and `-o` in links-only mode.
- **Considerations**: Do not rely on current implicit directory fallback for multi-doc; use explicit destination classification for links-only branch to avoid ambiguous `output.endswith("/")` heuristics.

### Step 5: Expand CLI tests for links-only behavior

- **What**: Add tests in `tests/test_cli.py` for:
  1. parser accepts `--links-only`;
  2. parser rejects `--links-only --remove-links`;
  3. single-doc markdown links-only output;
  4. single-doc JSON links-only output (pure array);
  5. multi-doc links-only output with per-URL sectioning;
  6. zero-reference fallback message.
- **Where**: `tests/test_cli.py` (`:24-170` existing baseline).
- **Why**: These are explicit phase deliverables and guard against regression in output routing.
- **Considerations**: Reuse existing test style with lightweight document doubles (`SimpleNamespace`), `capsys` for stdout assertions, and `tmp_path` for `-o` path assertions; do not weaken or remove existing dedup/auth tests.

## Testing Plan

Primary verify command:

`python -m pytest tests/test_cli.py -v`

| Test Type | What to Test | Expected Outcome |
|-----------|-------------|-----------------|
| Parser unit | `--links-only` is parsed and exposed as `args.links_only`; `--links-only --remove-links` exits with argparse error | Parser succeeds for valid flag and rejects invalid combination with `SystemExit` error path |
| Output unit (markdown) | `_write_output()` links-only single + multi-doc markdown rendering, including zero-reference message | Output contains only reference lines (`[N] label - href`) and `No references found for <url>` when references are empty |
| Output unit (JSON) | `_write_output()` with links-only + json mode serialization | JSON payload is pure references array shape (`index/href/label`) without `markdown`, `status`, or other `_doc_to_dict()` fields |
| Regression unit | Existing tests in `tests/test_cli.py` (dedup forwarding/auth propagation) | Existing tests continue to pass unchanged |

### Test Integrity Constraints

- `tests/test_cli.py:24-39` parser default/storage-state tests should remain unchanged; new links-only parser tests are additive.
- `tests/test_cli.py:41-170` async dedup/auth forwarding tests must remain valid; if `_run_crawl_async()` call signature to `_write_output()` changes (extra `links_only` argument), monkeypatched lambdas should be updated only to accept new kwargs, not to alter behavioral assertions.
- No existing tests should be deleted, skipped, or weakened to accommodate links-only behavior.

## Rollback Strategy

If links-only output behavior causes regressions, revert the Phase 1 delta in `crawler/cli.py` and `tests/test_cli.py` as one unit. This returns the CLI to pre-feature behavior because no data-model or crawl-pipeline changes are planned. Validate rollback with `python -m pytest tests/test_cli.py -v` and a manual `crawl <url>` sanity run.

## Open Decisions

| Decision | Options | Chosen | Rationale |
|----------|---------|--------|-----------|
| `--links-only` conflict behavior with `--remove-links` | allow both / runtime warning / argparse mutual exclusion | argparse mutual exclusion | Already gated in plan and phase acceptance; fail-fast at parse time prevents contradictory output semantics. |
| Links-only JSON payload shape | full `_doc_to_dict` w/ filtered markdown / pure references array | pure references array | Already gated in plan (`[{index, href, label}, ...]`), simplifies downstream consumption. |
| Zero-reference behavior | empty output / empty JSON & empty markdown / explicit message | explicit markdown message `No references found for <url>` (JSON remains empty array) | Gated requirement prioritizes user clarity for markdown path while preserving machine-friendly JSON arrays. |

## Reality Check

### Code Anchors Used

| File | Symbol/Area | Why it matters |
|------|-------------|----------------|
| `crawler/cli.py` | `_doc_to_dict` (`:138-151`) | Confirms current JSON path includes full document fields; links-only JSON must bypass this serializer. |
| `crawler/cli.py` | `_write_output` (`:164-225`) | Primary implementation target for output routing (stdout/file/dir) and existing remove-links behavior. |
| `crawler/cli.py` | `_parse_crawl_args` (`:232-333`) | Parser surface where new flag/help text and mutual exclusivity must be implemented. |
| `crawler/cli.py` | `_run_crawl_async` call to `_write_output` (`:404-409`) | Confirms where links-only mode must be threaded from args into output layer. |
| `crawler/document.py` | `Reference`, `CrawledDocument.references` (`:9-31`) | Defines canonical fields used by links-only markdown and JSON serialization. |
| `crawler/references.py` | `parse_references`, `_build_from_links` (`:13-56`) | Verifies references are already normalized/populated upstream; phase should not alter extraction. |
| `tests/test_cli.py` | parser + async tests (`:24-170`) | Establishes current testing style and regression surface that Phase 1 tests must extend. |

### Mismatches / Notes

- Current `_write_output()` behavior for `len(docs) > 1` and `output is None` writes per-URL files into `.` (`crawler/cli.py:203-225`), which conflicts with the gated Phase 1 requirement that links-only multi-doc stdout is combined with URL headers.
- Current `_write_output()` does not support explicit multi-doc `-o <file>` combined output; multi-doc with `output` is treated as directory (`crawler/cli.py:203-225`). Phase 1 links-only branch therefore needs destination classification logic beyond current baseline behavior.
- `docs/overview.md:101-102` states `tests/` only contains `__pycache__`, but `tests/test_cli.py` exists and is active. This is documentation drift, not a Phase 1 scope blocker.
