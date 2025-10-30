#!/usr/bin/env python3
"""
Check Alpaca Positions via MCP Services
Uses the running MCP services to fetch account and position data
"""

import asyncio
import json
import os
import sys
from typing import Any, Dict

from dotenv import load_dotenv
from langchain_mcp_adapters.client import MultiServerMCPClient

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


# Load environment variables
load_dotenv()


def _normalize_tool_output(result: Any) -> Any:
    if result is None:
        return None
    if hasattr(result, "model_dump"):
        result = result.model_dump()
    elif hasattr(result, "dict"):
        result = result.dict()
    if isinstance(result, str):
        text = result.strip()
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return text
    return result


def _format_json_block(data: Any) -> str:
    if data is None:
        return "No data available."
    if isinstance(data, str):
        return data
    try:
        return json.dumps(data, indent=2)
    except TypeError:
        return str(data)


async def check_positions_via_mcp() -> None:
    print("=" * 80)
    print("📊 CHECKING ALPACA POSITIONS VIA MCP SERVICES")
    print("=" * 80)

    mcp_config = {
        "jina_search": {
            "transport": "streamable_http",
            "url": f"http://localhost:{os.getenv('SEARCH_HTTP_PORT', '8001')}/mcp",
        },
        "alpaca_data": {
            "transport": "streamable_http",
            "url": f"http://localhost:{os.getenv('ALPACA_DATA_HTTP_PORT', '8004')}/mcp",
        },
        "alpaca_trade": {
            "transport": "streamable_http",
            "url": f"http://localhost:{os.getenv('ALPACA_TRADE_HTTP_PORT', '8005')}/mcp",
        },
    }

    try:
        print("\n🔌 Connecting to MCP services...")
        client = MultiServerMCPClient(mcp_config)
        tools = await client.get_tools()
        tool_lookup: Dict[str, Any] = {tool.name: tool for tool in tools}
        print(f"✅ Connected! {len(tools)} tools available")

        async def invoke_tool(name: str, arguments: Dict[str, Any] | None = None) -> Any:
            tool = tool_lookup.get(name)
            if tool is None:
                print(f"⚠️ Tool '{name}' not available")
                return None
            try:
                raw = await tool.ainvoke(arguments or {})
            except TypeError as err:
                if "not callable" in str(err) and hasattr(tool, "arun"):
                    try:
                        raw = await tool.arun(**(arguments or {}))
                    except Exception as inner_exc:
                        print(f"❌ Error calling tool '{name}': {inner_exc}")
                        return None
                else:
                    print(f"❌ Error calling tool '{name}': {err}")
                    return None
            except Exception as exc:  # noqa: PERF203 small scope
                print(f"❌ Error calling tool '{name}': {exc}")
                return None
            return _normalize_tool_output(raw)

        account_info = await invoke_tool("get_account_info")
        if account_info:
            print("\n" + "=" * 80)
            print("ACCOUNT INFORMATION")
            print("=" * 80)
            print(_format_json_block(account_info))
        else:
            print("\n❌ Unable to fetch account information")

        positions_payload = await invoke_tool("get_positions")
        positions_map: Dict[str, Dict[str, Any]] = {}
        if isinstance(positions_payload, dict):
            raw_positions = positions_payload.get("positions")
            if isinstance(raw_positions, dict):
                positions_map = raw_positions

        if positions_map:
            print("\n" + "=" * 80)
            print("CURRENT POSITIONS")
            print("=" * 80)
            header = f"{'Symbol':<8}{'Qty':>6}{'Cost':>14}{'Price':>12}{'P/L':>12}{'P/L%':>9}"
            print(header)
            print("-" * len(header))
            for symbol, details in positions_map.items():
                qty = details.get("qty", 0)
                cost_basis = details.get("cost_basis", 0)
                price = details.get("current_price", 0)
                pl = details.get("unrealized_pl", 0)
                plpc = details.get("unrealized_plpc", 0)
                print(f"{symbol:<8}{qty:>6.0f}{cost_basis:>14,.2f}{price:>12,.2f}{pl:>12,.2f}{plpc:>9.2%}")
        else:
            print("\n❌ Unable to fetch positions or no open positions")

        portfolio_summary = await invoke_tool("get_portfolio_summary")
        if portfolio_summary:
            print("\n" + "=" * 80)
            print("PORTFOLIO SUMMARY")
            print("=" * 80)
            print(_format_json_block(portfolio_summary))
        else:
            print("\n⚠️ Portfolio summary not available")

        if positions_map and "search_news" in tool_lookup:
            print("\n" + "=" * 80)
            print("COMPANY NEWS (first 5 positions)")
            print("=" * 80)
            for symbol in list(positions_map.keys())[:5]:
                args = {"query": f"{symbol} stock news", "max_results": 3}
                news_payload = await invoke_tool("search_news", args)
                print(f"\n[{symbol}]\n{_format_json_block(news_payload)}")
        elif positions_map:
            print("\n⚠️ News tools unavailable; review company catalysts manually")

        print("\n" + "=" * 80)
        print("✅ Position check complete!")
        print("=" * 80)

    except Exception as exc:  # noqa: PERF203
        print(f"\n❌ Error: {exc}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(check_positions_via_mcp())
