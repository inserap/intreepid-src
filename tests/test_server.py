"""Vérifie les outils MCP via un client in-memory (FastMCP Client).

Teste profile_stats (présence de la sentinelle dans le top-k) et describe
(retour du nom de dataset attendu) sans lancer de processus externe.
"""

from fastmcp import Client

from intreepid.mcp_server.server import mcp


async def test_profile_stats_tool_over_mcp():
    async with Client(mcp) as client:
        res = await client.call_tool(
            "profile_stats", {"columns": ["vitesse_limite_kmh"]}
        )
        block = res.data["vitesse_limite_kmh"]
        assert "999" in [str(r["value"]) for r in block["top_k"]]


async def test_describe_tool():
    async with Client(mcp) as client:
        res = await client.call_tool("describe", {})
        assert res.data["dataset"] == "accidents_seed"


async def test_concentration_tool_over_mcp():
    async with Client(mcp) as client:
        res = await client.call_tool("concentration_test", {"unit_col": "canton"})
        assert res.data["exposure_model"] == "declared:canton_exposure.parquet"
        assert "unit" in res.data["most_concentrated"]
        assert "pseudo_p" in res.data["highest_raw_count"]
