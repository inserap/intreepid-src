"""Vérifie les outils MCP via un client in-memory (FastMCP Client).

Teste profile_stats (présence de la sentinelle dans le top-k) et describe
(retour du nom de dataset attendu) sans lancer de processus externe.
"""

import pytest
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


def test_spatial_scale_robustness_tool_smoke():
    import duckdb

    from intreepid.mcp_server.catalog import load_fiche
    from intreepid.mcp_server.scale_robustness import spatial_scale_robustness
    from tests.conftest import CATALOG, FIXTURES

    con = duckdb.connect(":memory:")
    con.execute("INSTALL spatial")
    con.execute("LOAD spatial")
    con.execute(
        "CREATE VIEW spatial_seed AS SELECT * FROM read_parquet("
        f"'{(FIXTURES / 'spatial_seed.parquet').as_posix()}')"
    )
    out = spatial_scale_robustness(
        con,
        "spatial_seed",
        load_fiche(CATALOG / "spatial_seed.fiche.yaml"),
        base_dir=CATALOG,
        resolutions=(8,),
    )
    assert out["verdict"] in {"robuste", "fragile", "absente"}


async def test_profile_raw_tool_on_unfiched_parquet(tmp_path, monkeypatch):
    """profile_raw via MCP sur un parquet sous DATA_DIR : types inférés, untrusted."""
    import duckdb
    from fastmcp import Client

    from intreepid.mcp_server import server

    data_dir = tmp_path / "data"
    data_dir.mkdir()
    p = data_dir / "ingest_sample.parquet"
    con = duckdb.connect()
    con.execute(
        f"""COPY (SELECT i::INTEGER AS id, (i % 3)::INTEGER AS code FROM range(30) t(i))
            TO '{p.as_posix()}' (FORMAT parquet)"""
    )
    con.close()
    monkeypatch.setattr(server, "DATA_DIR", data_dir.resolve())

    async with Client(server.mcp) as client:
        res = await client.call_tool("profile_raw", {"dataset_path": str(p)})
    payload = res.data
    assert payload["untrusted_data"] is True
    assert payload["profile"]["id"]["type"] == "numeric"
    assert payload["profile"]["code"]["type"] == "categorical"


async def test_profile_raw_tool_rejects_path_traversal(tmp_path, monkeypatch):
    from fastmcp import Client

    from intreepid.mcp_server import server

    data_dir = tmp_path / "data"
    data_dir.mkdir()
    monkeypatch.setattr(server, "DATA_DIR", data_dir.resolve())
    outside = tmp_path / "secret.parquet"  # hors DATA_DIR

    async with Client(server.mcp) as client:
        with pytest.raises(
            Exception, match="dataset_path"
        ):  # FastMCP encapsule le ValueError
            await client.call_tool("profile_raw", {"dataset_path": str(outside)})
