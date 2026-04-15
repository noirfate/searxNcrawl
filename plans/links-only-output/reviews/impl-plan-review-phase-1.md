---
type: review
entity: implementation-plan-review
plan: "links-only-output"
phase: 1
status: final
reviewer: "delegate"
created: "2026-03-24"
---

# Implementation Plan Review: Phase 1 - Add --links-only CLI flag and output formatting

> Reviewing [Phase 1 Implementation Plan](../implementation/phase-1-impl.md)
> Against [Phase 1 Scope](../phases/phase-1.md) and [Plan](../plan.md)

## Overall Assessment

**Verdict**: Needs Revision

The implementation plan is mostly grounded in the current codebase and the core approach (parser flag + `_write_output()` routing + focused tests) is feasible. However, the testing section does not fully cover required acceptance behaviors (notably `-o` destination variants and `--site` links-only behavior), and it omits an explicit real-world validation step. These gaps make the plan risky to execute as-is because an implementer could ship incomplete behavior while still passing the proposed verify command.

## Scope Alignment

### Findings

- The planned code changes stay within Phase 1 scope (CLI-only changes in `crawler/cli.py` and tests in `tests/test_cli.py`) with no evident scope creep.
- Scope coverage is incomplete in the testing plan: phase acceptance includes `--site` and `-o` behavior variants, but these are not explicitly represented in planned tests.

## Technical Feasibility

### Findings

- The proposed architecture is sound for this codebase: threading `args.links_only` from `_parse_crawl_args()` through `_run_crawl_async()` into `_write_output()` matches existing CLI flow.
- Reusing `CrawledDocument.references` and bypassing `_doc_to_dict()` for links-only JSON is technically appropriate and consistent with existing data model (`crawler/document.py`).
- The destination-classification concern is valid: current multi-doc behavior in `_write_output()` assumes directory semantics, so a dedicated links-only branch is a reasonable approach.

## Step Quality Assessment

| Step | Title | Concrete? | Actionable? | Issue |
| ---- | ----- | --------- | ----------- | ----- |
| 1 | Add parser flag and mutual exclusion contract | Yes | Yes | Good symbol/path specificity; directly implementable. |
| 2 | Add dedicated references formatter helper | Yes | Yes | Good output contract details including zero-reference behavior. |
| 3 | Add links-only output routing in `_write_output()` | Yes | Yes | Clear branch behavior, but should explicitly call out preserving existing return/exit semantics in `_run_crawl_async()`. |
| 4 | Implement destination-specific links-only materialization | Yes | Mostly | Destination matrix is good; classification rules could be slightly more explicit (file vs dir heuristics) to reduce implementer choice. |
| 5 | Expand CLI tests for links-only behavior | Mostly | Mostly | Missing explicit tests for `--site` and `-o` file/dir behaviors required by phase acceptance criteria. |

## Required Context Assessment

### Missing Context

- `README.md` (or equivalent CLI usage source) is not listed; this is useful for ensuring `crawl --help` style/wording consistency, though not strictly blocking.

### Unnecessary Context

- `docs/modules/crawler-cli.md` is optional for implementation (helpful orientation, not required); keeping it is acceptable.

## Testing Plan Assessment

### Test Integrity Check

The plan includes good integrity constraints (additive tests, no weakening/deletion, preserving dedup/auth assertions). This is strong. However, it does not explicitly mention updating existing `argparse.Namespace` fixtures in async tests if `_run_crawl_async()` starts accessing `args.links_only`; this is a practical integrity detail that should be stated.

### Test Gaps

- **Major**: No explicit tests for `-o` destination behavior in links-only mode (`single file`, `multi-doc combined file`, `multi-doc directory`), despite being required by scope/acceptance.
- **Major**: No explicit links-only `--site` behavior test, despite phase acceptance requiring per-page behavior for site crawl.
- **Minor**: No explicit test for help text surfacing `--links-only` (`crawl --help`), which is listed in acceptance criteria.

### Real-World Testing

Real-world testing is **not explicitly included** in the implementation plan’s testing section. Current verify command (`python -m pytest tests/test_cli.py -v`) is unit-focused and does not validate behavior against a live crawl target. This should be added as a post-verify/manual validation step (e.g., `crawl <url> --links-only` and `crawl <url> --site --links-only` smoke checks).

## Reference Consistency

### Findings

- File paths and symbols cited in the implementation plan exist and are correctly named: `crawler/cli.py`, `crawler/document.py`, `crawler/references.py`, `tests/test_cli.py`.
- Line anchors in the Reality Check are accurate against current repo state for the referenced regions (`_doc_to_dict`, `_write_output`, `_parse_crawl_args`, `_run_crawl_async` call site, data model and tests).
- Module doc reference `[crawler-cli](../../docs/modules/crawler-cli.md)` resolves correctly.

## Reality Check Validation

### Findings

- Reality Check is largely honest and useful: it correctly identifies current multi-doc output behavior mismatch with required links-only combined output semantics.
- The noted docs drift in `docs/overview.md` (tests inventory mismatch) is valid and non-blocking.
- One additional practical mismatch should be called out: existing async tests build manual `argparse.Namespace` objects without `links_only`; this must be handled via fixture updates or guarded attribute access to avoid test/runtime breakage during refactor.

## Findings Summary

| # | Severity | Area | Finding | Recommendation |
| - | -------- | ---- | ------- | -------------- |
| 1 | Major | Testing Plan | Planned tests do not explicitly cover required `-o` links-only destination variants (single file, multi-doc file, multi-doc dir). | Add concrete tests for each destination mode and expected materialization behavior. |
| 2 | Major | Testing Plan | No explicit links-only `--site` behavior test despite phase acceptance requiring per-page output semantics. | Add at least one site-crawl links-only test (stubbed crawl result is fine) asserting per-page sectioning/output format. |
| 3 | Major | Testing Plan | No explicit real-world validation step; verify command is unit-only. | Add a documented manual smoke step against a real URL for `--links-only` (and ideally `--site --links-only`). |
| 4 | Minor | Test Integrity | Plan does not explicitly account for `args.links_only` on existing `argparse.Namespace` fixtures in async tests. | State and implement fixture updates (or safe `getattr`) so existing tests remain valid after signature/arg changes. |
| 5 | Minor | Coverage Completeness | Help text requirement (`crawl --help` includes `--links-only`) is not directly tested. | Add a parser/help assertion test or equivalent CLI help snapshot check. |
| 6 | Note | Context | `docs/modules/crawler-cli.md` is helpful but not strictly required context for implementation execution. | Keep as optional context; prioritize code files and phase docs. |

## Recommendations

1. Expand Step 5 and the Testing Plan with explicit test cases for all accepted `-o` destination modes and `--site` links-only behavior.
2. Add an explicit real-world smoke-test step (post-pytest) to validate output shape on live content.
3. Amend test integrity constraints to mention updating manual `argparse.Namespace` fixtures for `links_only` access.
4. Add a small help-text assertion to cover `crawl --help` acceptance.
