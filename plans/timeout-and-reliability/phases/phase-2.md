---
type: planning
entity: phase
plan: "timeout-and-reliability"
phase: 2
status: completed  # pending | in_progress | completed | skipped
created: "2026-04-08"
updated: "2026-04-08"
---

# Phase 2: MCP Tool Timeout Parameters

> Part of [timeout-and-reliability](../plan.md)

## Objective

Expose timeout parameters in the MCP tool schemas so that consumers can configure per-URL and site crawl timeouts. Thread these parameters through to the underlying crawl functions.

Fixes finding **F-4** (Minor) from the review.

## Scope

### Includes

- `crawler/mcp_server.py`:
  - `crawl` tool: add `timeout: int = 30` parameter (per-URL timeout in seconds)
  - `crawl_site` tool: add `timeout: int = 120` parameter (overall site crawl timeout in seconds)
  - Pass timeout values through to underlying functions
- `crawler/__init__.py`:
  - `crawl_page_async()`: accept optional `timeout` parameter
  - `crawl_pages_async()`: accept optional `timeout` parameter (applied per-URL)
- `crawler/site.py`:
  - `crawl_site_async()`: accept optional `timeout` parameter

### Excludes (deferred to later phases)

- Changes to synchronous wrappers (`crawl_page`, `crawl_pages`, `crawl_site`) — not used by MCP
- CLI parameter exposure

## Prerequisites

- [ ] Phase 1 complete (timeout wrappers in place with default values)

## Deliverables

- [ ] `crawl` MCP tool accepts `timeout` parameter with default 30
- [ ] `crawl_site` MCP tool accepts `timeout` parameter with default 120
- [ ] Timeout values are threaded through to the actual crawl functions
- [ ] Tool docstrings updated to describe the new parameters

## Acceptance Criteria

- [ ] Call `crawl(urls=[...], timeout=10)` → uses 10s timeout instead of default
- [ ] Call `crawl_site(url=..., timeout=60)` → uses 60s timeout instead of default
- [ ] Existing tests continue to pass
- [ ] MCP tool schema includes the new parameters with descriptions

## Dependencies on Other Phases

| Phase | Relationship | Notes |
|-------|-------------|-------|
| Phase 1 | blocked-by | Requires timeout wrapper infrastructure |
| Phase 3 | parallel | Independent |
| Phase 4 | parallel | Independent |
| Phase 5 | blocks | Tests should verify parameter forwarding |

## Notes

- The MCP tool parameter overrides the module-level default when provided.
- Parameter type: `int` (seconds). Validation: `timeout >= 1` (allow short timeouts for testing, but reject zero/negative).
- For `crawl` with multiple URLs, the timeout applies per-URL (consistent with Phase 1 behavior).
- Invalid timeout values should raise `ValueError` with a clear message.
