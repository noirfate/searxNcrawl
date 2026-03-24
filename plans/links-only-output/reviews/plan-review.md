---
type: review
entity: plan-review
plan: "links-only-output"
status: final
reviewer: "delegate"
created: "2026-03-24"
---

# Plan Review: links-only-output

> Reviewing [links-only-output](../plan.md)

## Overall Assessment

**Verdict**: Needs Revision

The plan is close to executable and has good baseline coverage of CLI touchpoints, required modes, and testing intent. However, there are unresolved behavioral decisions and one likely mismatch with current implementation (`--links-only --json` is not currently “references-only” via existing behavior), which creates material execution risk. Clarifying output semantics (especially multi-document behavior and conflicting flags) will make Phase 1 actionable without mid-implementation policy decisions.

## Requirement Coverage

| Requirement | Covered By | Gap? | Notes |
| ----------- | ---------- | ---- | ----- |
| New `--links-only` CLI flag on `crawl` | plan Functional + phase Includes | No | Clear owner in Phase 1. |
| Output only references in `[N] label - href` | plan Functional + phase Includes/AC | No | Formatting target is explicit. |
| Works with single-URL crawls | plan Functional + phase AC | No | Covered. |
| Works with multi-URL crawls | plan Functional + phase AC | **Yes** | Output destination/shape is ambiguous vs current multi-doc file behavior. |
| Works with `--site` crawls | plan Functional + phase AC | **Yes** | Same ambiguity for per-page output when many docs are produced. |
| Multi-document output separates lists with URL header | plan Functional + phase Includes/AC | **Yes** | Header format and when to apply (stdout vs files) are unspecified. |
| `--links-only` + `-o` writes references to file | plan Functional + DoD + phase AC | No | Covered. |
| `--links-only --json` outputs references-only JSON | plan Functional + phase Includes/AC | **Yes** | Conflicts with current `_doc_to_dict` payload; plan assumes “existing behavior” incorrectly. |
| No orchestration/pipeline changes | Non-functional + scope | No | Feasible if formatting/output layer only. |
| Minimal delta leveraging existing references | Non-functional + phase notes | No | Realistic. |
| Consistent with argparse + `_write_output` patterns | Non-functional + scope | No | Properly targeted. |

## Scope Clarity

### Findings

- **Major**: Multi-document behavior is underspecified. Current CLI writes multiple docs to files/directories; plan language implies combined per-page output with headers but does not specify whether this applies to stdout, single file, per-file content, or all cases.
- **Major**: Conflict handling for `--links-only` with `--remove-links` is unresolved (“error or precedence”). This is a policy decision and should be fixed in plan before implementation.

## Definition of Done Assessment

### Findings

- **Major**: DoD item for `--links-only --json` says references-only JSON, but no explicit acceptance of the required shape/schema (single doc object vs list, retained keys, backward compatibility expectations).
- **Minor**: Zero-reference behavior (“No references found” vs empty output) is left undecided in risks; this should be promoted to an explicit acceptance rule to avoid inconsistent implementation/tests.

## Phase Structure Assessment

| Phase | Title | Verdict | Issue |
| ----- | ----- | ------- | ----- |
| 1 | Add --links-only CLI flag and output formatting | Partial | Single phase is appropriate size, but includes unresolved behavior decisions that should be pre-decided. |

## Testing Strategy Assessment

### Test Coverage Gaps

- **Major**: No explicit tests for `--links-only --remove-links` expected behavior (error vs precedence).
- **Major**: No explicit tests locking multi-document output contract across modes (`stdout`, `-o file`, `-o dir`, default multi-doc directory behavior).
- **Minor**: No explicit test for zero-reference output behavior.

### Real-World Testing

Planned: one real URL integration check (`crawl <url> --links-only`). This is present and appropriate; consider treating it as manual/smoke due to external flakiness.

## Reference Consistency

### Findings

- **Major**: Plan states `--links-only --json` is “existing behavior via `_doc_to_dict`,” but current `_doc_to_dict` includes `markdown`, metadata, status, and URLs, so this is not references-only behavior.
- **Note**: `todo.md` references `implementation/phase-1-impl.md`, which is not part of provided artifacts yet; not blocking for plan review.

## Completeness Check

### Findings

- **Major**: Plan is not fully execution-ready because key output contracts are still deferred to implementation-time decisions.
- **Minor**: Help text wording is required but no concrete wording/constraints are provided for conflicting flags.

## Findings Summary

| # | Severity | Area | Finding | Recommendation |
| - | -------- | ---- | ------- | -------------- |
| 1 | Major | Requirement coverage | Multi-document output contract is ambiguous relative to existing CLI output semantics. | Specify exact behavior matrix by mode: single vs multi docs, stdout vs `-o file` vs `-o dir`, and header placement/format. |
| 2 | Major | Scope clarity | `--links-only` + `--remove-links` behavior unresolved. | Decide now: either reject with argparse/runtime error, or define strict precedence and document it. |
| 3 | Major | Reference consistency | `--links-only --json` marked as existing behavior, but current `_doc_to_dict` is not references-only. | Define required JSON schema and required code path changes explicitly; call out compatibility expectations. |
| 4 | Major | Testing strategy | Missing explicit tests for flag-conflict behavior and mode matrix. | Add concrete test cases for conflict handling and each output destination/mode combination. |
| 5 | Minor | DoD completeness | Zero-reference output behavior undecided. | Add acceptance criterion for empty reference lists (silent empty, header-only, or explicit message). |
| 6 | Minor | Completeness | Help text expectations are broad, not concrete. | Add exact help text intent, especially interaction notes (`--json`, `--remove-links`). |
| 7 | Note | Artifact hygiene | `todo.md` points to an implementation artifact not present yet. | Create it during implementation planning or remove link until available. |

## Recommendations

1. Resolve and document the behavioral contract before coding: multi-doc output format/destination rules, zero-reference behavior, and `--links-only` + `--remove-links` policy.
2. Correct the JSON assumption by specifying the exact `--links-only --json` schema and whether this intentionally changes existing JSON output fields.
3. Expand the test plan into a small behavior matrix covering all output destinations and conflicting flag interactions.
4. Optionally add one manual smoke-test note for a real URL to keep CI deterministic while preserving real-world validation.
