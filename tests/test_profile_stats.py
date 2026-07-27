import duckdb, yaml
from tests.conftest import SEED_PARQUET, FICHE
from intreepid.mcp_server.profile_stats import profile_stats
from intreepid.mcp_server.catalog import load_fiche

def _con():
    con = duckdb.connect(":memory:")
    con.execute(f"CREATE VIEW accidents_route AS SELECT * FROM read_parquet('{SEED_PARQUET.as_posix()}')")
    return con

def test_sentinel_visible_in_top_k():
    fiche = load_fiche(FICHE)
    out = profile_stats(_con(), "accidents_route", fiche, ["vitesse_limite_kmh"])
    block = out["vitesse_limite_kmh"]
    assert block["type"] == "categorical"
    values = [row["value"] for row in block["top_k"]]
    assert "999" in [str(v) for v in values], "la sentinelle 999 doit apparaître dans le top-k"

def test_categorical_cardinality():
    fiche = load_fiche(FICHE)
    out = profile_stats(_con(), "accidents_route", fiche, ["severity"])
    assert out["severity"]["cardinality"] >= 2

def test_numeric_block_shape():
    fiche = load_fiche(FICHE)
    out = profile_stats(_con(), "accidents_route", fiche, ["accident_month"])
    b = out["accident_month"]
    assert b["type"] == "numeric"
    assert 1 <= b["min"] <= b["max"] <= 12
    for k in ("mean", "median", "p95", "std", "null_rate", "n_outliers_3sigma"):
        assert k in b
