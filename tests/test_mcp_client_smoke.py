"""In-memory MCP client smoke test.

Unlike ``test_mcp_server.py`` (which calls the ``@mcp.tool`` coroutines
directly), this exercises the real MCP request/response round-trip through a
``fastmcp.Client`` connected in-memory to the server object. No Docker, no
network, no SearXNG required — the underlying crawl functions are monkeypatched.

This is the fast, deterministic CI counterpart to ``scripts/smoke_mcp_client.py``
(which runs the same checks against a live HTTP server).
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest
from fastmcp import Client

import crawler
from crawler.mcp_server import mcp


def _doc() -> SimpleNamespace:
    return SimpleNamespace(
        request_url="https://example.com",
        final_url="https://example.com",
        status="success",
        markdown="# Example Domain\n\nThis domain is for use in examples.",
        error_message=None,
        metadata={},
        references=[],
    )


def _result_text(result) -> str:
    blocks = getattr(result, "content", None)
    if blocks is None and isinstance(result, list):
        blocks = result
    return "\n".join(getattr(b, "text", "") or "" for b in (blocks or []))


@pytest.mark.asyncio
async def test_mcp_client_lists_expected_tools() -> None:
    async with Client(mcp) as client:
        tools = await client.list_tools()

    names = {t.name for t in tools}
    assert {"crawl", "crawl_site", "search"} <= names


@pytest.mark.asyncio
async def test_mcp_client_crawl_roundtrip(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_crawl_page_async(
        url: str, *, dedup_mode: str = "exact", auth=None, timeout=None
    ):
        return _doc()

    async def fake_crawl_pages_async(
        urls, *, concurrency=3, dedup_mode="exact", auth=None, timeout=None
    ):
        return [_doc() for _ in urls]

    monkeypatch.setattr(crawler, "crawl_page_async", fake_crawl_page_async)
    monkeypatch.setattr(crawler, "crawl_pages_async", fake_crawl_pages_async)

    async with Client(mcp) as client:
        result = await client.call_tool("crawl", {"urls": ["https://example.com"]})

    assert "Example Domain" in _result_text(result)


@pytest.mark.asyncio
async def test_mcp_client_crawl_tool_schema_has_expected_params() -> None:
    async with Client(mcp) as client:
        tools = await client.list_tools()

    crawl_tool = next(t for t in tools if t.name == "crawl")
    props = crawl_tool.inputSchema.get("properties", {})
    # Core agent-facing knobs should be advertised in the tool schema.
    for param in ("urls", "output_format", "remove_links", "dedup_mode"):
        assert param in props, f"missing '{param}' in crawl input schema"
