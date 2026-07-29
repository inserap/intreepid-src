"""Golden déterministe des statistiques mono-colonne (profile_stats).

Vérifie la visibilité de la sentinelle dans le top-k, la cardinalité des
catégories et la forme du bloc numérique pour accident_month.
"""

import duckdb
import pytest

from intreepid.mcp_server.catalog import load_fiche
from intreepid.mcp_server.profile_stats import profile_stats
from tests.conftest import FICHE, SEED_PARQUET


def _con():
    con = duckdb.connect(":memory:")
    con.execute("INSTALL spatial")
    con.execute("LOAD spatial")
    con.execute(
        f"CREATE VIEW accidents_route AS SELECT * FROM"
        f" read_parquet('{SEED_PARQUET.as_posix()}')"
    )
    return con


def test_sentinel_visible_in_top_k():
    fiche = load_fiche(FICHE)
    out = profile_stats(_con(), "accidents_route", fiche, ["vitesse_limite_kmh"])
    block = out["vitesse_limite_kmh"]
    assert block["type"] == "categorical"
    values = [row["value"] for row in block["top_k"]]
    assert "999" in [str(v) for v in values], (
        "la sentinelle 999 doit apparaître dans le top-k"
    )


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
    for k in (
        "type",
        "min",
        "max",
        "mean",
        "median",
        "p5",
        "p25",
        "p75",
        "p95",
        "std",
        "skewness",
        "null_rate",
        "zero_rate",
        "n_outliers_3sigma",
    ):
        assert k in b


def test_temporal_block_shape():
    fiche = load_fiche(FICHE)
    out = profile_stats(_con(), "accidents_route", fiche, ["date"])
    b = out["date"]
    assert b["type"] == "temporal"
    assert b["min"] <= b["max"]
    assert b["series_gaps_months"] > 0  # trou de série planté
    assert set(b["seasonality_by_month"]) <= {str(mo) for mo in range(1, 13)}
    assert (
        len(b["volume_by_year"]) >= 2
    )  # rupture de volume visible sur plusieurs années


def test_unknown_type_message():
    fiche = {"dataset": "x", "columns": {"c": {"type": "code"}}}
    con = _con()
    con.execute("CREATE VIEW x AS SELECT 1 AS c")
    with pytest.raises(ValueError, match="prévu / non implémenté"):
        profile_stats(con, "x", fiche, ["c"])
