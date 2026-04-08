# Timeout & Reliability Review

> **Date:** 2026-04-02  
> **Context:** Discovered during mark_down_edit PoC testing — crawl MCP tool calls hang indefinitely when target pages stall, freezing the entire agent/streaming pipeline.  
> **Severity:** High — affects all MCP consumers, not just mark_down_edit.

---

## Executive Summary

The searxNcrawl MCP server has **no timeout protection around crawl operations**. If a target page hangs (slow load, infinite network wait, `networkidle` never reached), the MCP tool call never returns. Any MCP consumer waiting for the result will freeze.

Search operations have a hardcoded 30s HTTP timeout and are not affected.

---

## Findings

### F-1: No Timeout Around Core Crawl Awaits (Critical)

**Locations:**
- `crawler/__init__.py:124,127` — `await crawler.arun(...)` in `crawl_page_async()`
- `crawler/__init__.py:227` — `await asyncio.gather(*tasks)` in `crawl_pages_async()`
- `crawler/site.py:130` — `await crawler.arun(...)` in `crawl_site_async()`

**Impact:** If `Crawl4AI.arun()` hangs (e.g., Playwright navigation stuck on a slow page), the MCP tool call blocks indefinitely. There is no `asyncio.wait_for()` wrapper, no deadline, and no fallback.

**Risk:** Any single hanging URL in a multi-URL crawl blocks the entire `asyncio.gather()` call, even if other URLs complete fast.

### F-2: `wait_until="networkidle"` Can Prevent Completion (Major)

**Location:** `crawler/config.py:193` (discovery config)

**Impact:** Pages that continuously make network requests (analytics, WebSocket pings, ad networks) may never reach "network idle" state. Playwright will wait indefinitely.

### F-3: `wait_for` JS Predicate Without Timeout (Major)

**Location:** `crawler/config.py:178` — requires `<main>` element with text length > 50

**Impact:** Pages without a `<main>` element or with lazy-loaded content will wait forever for a condition that can never be satisfied.

### F-4: MCP Tool Schemas Don't Expose Timeout Parameters (Minor)

**Location:** `crawler/mcp_server.py` — tool definitions for `crawl`, `crawl_site`, `search`

**Impact:** MCP consumers cannot pass a timeout value. The only defense is consumer-side timeout wrapping (which mark_down_edit now does), but server-side protection would be more robust.

### F-5: No Retry/Backoff for Transient Failures (Note)

**Location:** All crawl paths, search path

**Impact:** Transient network errors (DNS timeout, connection reset) fail immediately. For search in particular, a single retry with brief backoff would improve reliability significantly.

### F-6: No Per-URL Timeout in Multi-URL Crawl (Major)

**Location:** `crawler/__init__.py:183-227` — `crawl_pages_async()`

**Impact:** Individual URLs are wrapped in try/except for exceptions, but if one URL hangs (no exception raised), `asyncio.gather()` waits for all tasks including the stuck one. One bad URL blocks the entire batch.

### F-7: Missing Elapsed-Time Logging (Minor)

**Location:** All crawl/search paths

**Impact:** No per-operation timing information is logged. Diagnosing which URLs are slow or which operations take unexpectedly long requires adding temporary debug code.

---

## Recommendations

### Priority 1: Add Timeout Wrappers (Fixes F-1, F-6)

```python
# In crawl_page_async():
result = await asyncio.wait_for(
    crawler.arun(url=url, config=run_config),
    timeout=per_page_timeout  # e.g., 60s default
)

# In crawl_pages_async() — per-task timeout:
async def _crawl_with_timeout(url, config, timeout):
    try:
        return await asyncio.wait_for(
            crawl_page_async(url, config),
            timeout=timeout
        )
    except asyncio.TimeoutError:
        return CrawledDocument(url=url, success=False, error="Timeout")

# In crawl_site_async():
result = await asyncio.wait_for(
    crawler.arun(...),
    timeout=site_crawl_timeout  # e.g., 180s default
)
```

### Priority 2: Expose Timeout Parameters in MCP Tools (Fixes F-4)

Add optional parameters to tool schemas:
- `crawl`: `timeout: int = 60` (per-URL timeout in seconds)
- `crawl_site`: `timeout: int = 180` (overall site crawl timeout)

### Priority 3: Replace `networkidle` with Bounded Wait (Fixes F-2, F-3)

```python
# In config.py discovery config:
wait_until="domcontentloaded"  # instead of "networkidle"

# If content check is needed, wrap with timeout:
page_timeout=30000  # 30s max via Crawl4AI config
```

Or use `Crawl4AI`'s `page_timeout` parameter if available in the version used.

### Priority 4: Add Elapsed-Time Logging (Fixes F-7)

```python
import time

async def crawl_page_async(url, ...):
    start = time.monotonic()
    try:
        result = await asyncio.wait_for(crawler.arun(...), timeout=timeout)
        logger.info(f"Crawled {url} in {time.monotonic()-start:.1f}s")
        return result
    except asyncio.TimeoutError:
        logger.warning(f"Timeout crawling {url} after {time.monotonic()-start:.1f}s")
        raise
```

### Priority 5: Add Search Retry (Fixes F-5)

```python
# Simple retry for transient HTTP errors:
for attempt in range(max_retries):  # max_retries=2
    try:
        response = await client.get("/search", params=params)
        response.raise_for_status()
        return response.json()
    except httpx.RequestError:
        if attempt == max_retries - 1:
            raise
        await asyncio.sleep(0.5 * (attempt + 1))
```

---

## Consumer-Side Mitigations Already Applied (mark_down_edit)

As a defense-in-depth measure, `mark_down_edit` now implements:

1. **Per-event gap timeout** (120s default): `asyncio.wait_for()` around each streaming event iteration
2. **Overall stream deadline** (600s default): Hard cap on total stream duration
3. **Producer-task + async queue**: SSE emit loop decoupled from upstream stream, enabling responsive cancel even when tool call blocks
4. **Frontend stall warning**: Visual indicator when no streaming activity for 10s
5. **Tool elapsed timer**: UI shows "Tool running for Xs" during long-running MCP calls

These mitigations protect mark_down_edit users but do **not** fix the root cause in searxNcrawl. Other MCP consumers remain vulnerable.

---

## Effort Estimate

| Priority | Fix | Effort | Files |
|----------|-----|--------|-------|
| P1 | Timeout wrappers | ~1h | `__init__.py`, `site.py` |
| P2 | MCP timeout params | ~30min | `mcp_server.py` |
| P3 | Replace networkidle | ~30min | `config.py` |
| P4 | Elapsed logging | ~30min | `__init__.py`, `site.py`, `mcp_server.py` |
| P5 | Search retry | ~30min | `mcp_server.py` |
| **Total** | | **~3h** | |

---

## Testing Approach

1. **Unit test**: Mock `crawler.arun()` to hang → verify `asyncio.TimeoutError` is raised within expected time
2. **Unit test**: Multi-URL crawl with one hanging mock → verify other URLs complete and hanging URL returns timeout error
3. **Integration test**: Crawl a known slow/broken URL → verify timeout behavior end-to-end
4. **Search retry test**: Mock transient `httpx.RequestError` → verify retry succeeds on second attempt
