from fastmcp import Client
from intreepid.mcp_server.server import mcp


async def test_profile_stats_tool_over_mcp():
    async with Client(mcp) as client:
        res = await client.call_tool("profile_stats", {"columns": ["vitesse_limite_kmh"]})
        block = res.data["vitesse_limite_kmh"]
        assert "999" in [str(r["value"]) for r in block["top_k"]]


async def test_describe_tool():
    async with Client(mcp) as client:
        res = await client.call_tool("describe", {})
        assert res.data["dataset"] == "accidents_route"
