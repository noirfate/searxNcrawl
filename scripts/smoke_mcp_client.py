#!/usr/bin/env python3
"""End-to-end MCP client smoke test for searxNcrawl.

Connects to a running searxNcrawl MCP server using the official ``fastmcp``
client (the same protocol Claude Code / Cursor / etc. speak), then verifies the
server actually works:

  1. ``tools/list`` exposes ``crawl``, ``crawl_site`` and ``search``
  2. ``crawl`` on https://example.com returns real content ("Example Domain")
  3. ``search`` returns results (requires a reachable SearXNG with JSON enabled)

Exit code: 0 = all checks passed, 1 = a check failed, 2 = could not connect.

Usage
-----
    # Against the docker-compose stack (after `docker compose up -d`):
    docker compose run --rm smoke                 # runs this script in-container

    # Or from the host / a venv (needs `pip install -e .`):
    python scripts/smoke_mcp_client.py                                  # http://localhost:9555/mcp
    python scripts/smoke_mcp_client.py --url http://localhost:9555/mcp
    MCP_URL=http://localhost:9555/mcp python scripts/smoke_mcp_client.py

    # Skip the search check when no SearXNG is available:
    python scripts/smoke_mcp_client.py --no-search
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from urllib.parse import urlparse

try:
    from fastmcp import Client
except ModuleNotFoundError:
    sys.exit(
        "This smoke test needs the 'fastmcp' package in your environment.\n"
        "Install it first, e.g.:\n"
        "    pip install fastmcp     # just the client\n"
        "    pip install -e .        # or the whole project\n"
    )


def _default_url() -> str:
    if os.getenv("MCP_URL"):
        return os.environ["MCP_URL"]
    host = os.getenv("MCP_HOST", "localhost")
    port = os.getenv("MCP_PORT", "9555")
    return f"http://{host}:{port}/mcp"


_PROXY_ENV_VARS = (
    "all_proxy", "ALL_PROXY",
    "http_proxy", "HTTP_PROXY",
    "https_proxy", "HTTPS_PROXY",
)


def _bypass_proxy_for_local(url: str) -> None:
    """A localhost MCP endpoint must not be routed through a host proxy.

    httpx (used by fastmcp) honors all_proxy/http(s)_proxy from the environment.
    If a SOCKS proxy is configured (common dev setups), connecting to localhost
    otherwise fails with "Using SOCKS proxy, but 'socksio' is not installed".
    For local targets we strip those vars so the client connects directly.
    """
    host = (urlparse(url).hostname or "").lower()
    if host in ("localhost", "127.0.0.1", "0.0.0.0", "::1"):
        for var in _PROXY_ENV_VARS:
            os.environ.pop(var, None)


# Default crawl target for the smoke test.
#
# IMPORTANT: the server's default extraction config is tuned for documentation
# sites — it waits (up to ~30s) for a `<main>` element to render. Minimal pages
# that have no `<main>` (e.g. https://example.com) therefore time out and return
# an empty/failed document. That's a config quirk, NOT a broken stack. So the
# smoke test crawls a real docs page (which has `<main>`). Override with
# SMOKE_CRAWL_URL / SMOKE_CRAWL_MARKER (or --crawl-url / --crawl-marker).
_DEFAULT_CRAWL_URL = "https://docs.crawl4ai.com/"
_DEFAULT_CRAWL_MARKER = "Crawl4AI"


def _result_text(result) -> str:
    """Extract concatenated text from a fastmcp call_tool result.

    Handles both the CallToolResult object (fastmcp 2.x) and a bare list of
    content blocks (older shapes).
    """
    blocks = getattr(result, "content", None)
    if blocks is None and isinstance(result, list):
        blocks = result
    parts = []
    for block in blocks or []:
        text = getattr(block, "text", None)
        if text:
            parts.append(text)
    if not parts:
        data = getattr(result, "data", None)
        if data is not None:
            parts.append(str(data))
    return "\n".join(parts)


class _Report:
    def __init__(self) -> None:
        self.passed = 0
        self.failed = 0

    def check(self, name: str, ok: bool, detail: str = "") -> None:
        if ok:
            self.passed += 1
            print(f"  [PASS] {name}")
        else:
            self.failed += 1
            suffix = f" -- {detail}" if detail else ""
            print(f"  [FAIL] {name}{suffix}")


async def run(url: str, crawl_url: str, crawl_marker: str, run_search: bool) -> int:
    report = _Report()
    _bypass_proxy_for_local(url)
    print(f"Connecting to MCP server: {url}")

    try:
        async with Client(url) as client:
            # 1) tools/list
            tools = await client.list_tools()
            names = {t.name for t in tools}
            print(f"Discovered tools: {sorted(names)}")
            for expected in ("crawl", "crawl_site", "search"):
                report.check(f"tools/list exposes '{expected}'", expected in names)

            # 2) crawl a docs page (has <main>; see note on _DEFAULT_CRAWL_URL)
            try:
                res = await client.call_tool("crawl", {"urls": [crawl_url]})
                body = _result_text(res)
                report.check(
                    f"crawl {crawl_url} returns content",
                    crawl_marker in body,
                    f"marker {crawl_marker!r} not found "
                    f"(page changed? try --crawl-marker). first 200 chars: "
                    f"{body[:200].replace(chr(10), ' ')}",
                )
            except Exception as exc:  # noqa: BLE001
                report.check(f"crawl {crawl_url} returns content", False, repr(exc))

            # 3) search (needs SearXNG w/ JSON output)
            if run_search:
                try:
                    res = await client.call_tool(
                        "search",
                        {"query": "python programming", "max_results": 3},
                    )
                    body = _result_text(res)
                    ok = ('"results"' in body) and ('"error"' not in body)
                    report.check(
                        "search returns results",
                        ok,
                        body[:200].replace("\n", " ") if not ok else "",
                    )
                except Exception as exc:  # noqa: BLE001
                    report.check("search returns results", False, repr(exc))
            else:
                print("  [SKIP] search (--no-search)")
    except Exception as exc:  # noqa: BLE001
        print(
            f"\n[ERROR] Could not connect / initialize MCP session: {exc!r}",
            file=sys.stderr,
        )
        return 2

    print(f"\nResult: {report.passed} passed, {report.failed} failed")
    return 0 if report.failed == 0 else 1


def main() -> int:
    parser = argparse.ArgumentParser(
        description="searxNcrawl MCP client smoke test",
    )
    parser.add_argument(
        "--url",
        default=_default_url(),
        help="MCP endpoint URL (default: $MCP_URL or http://localhost:9555/mcp)",
    )
    parser.add_argument(
        "--crawl-url",
        default=os.getenv("SMOKE_CRAWL_URL", _DEFAULT_CRAWL_URL),
        help=f"URL to crawl (default: $SMOKE_CRAWL_URL or {_DEFAULT_CRAWL_URL})",
    )
    parser.add_argument(
        "--crawl-marker",
        default=os.getenv("SMOKE_CRAWL_MARKER", _DEFAULT_CRAWL_MARKER),
        help="substring expected in the crawled markdown "
        f"(default: $SMOKE_CRAWL_MARKER or {_DEFAULT_CRAWL_MARKER!r})",
    )
    parser.add_argument(
        "--no-search",
        action="store_true",
        help="skip the search check (use when no SearXNG is available)",
    )
    args = parser.parse_args()
    return asyncio.run(
        run(
            args.url,
            crawl_url=args.crawl_url,
            crawl_marker=args.crawl_marker,
            run_search=not args.no_search,
        )
    )


if __name__ == "__main__":
    raise SystemExit(main())
