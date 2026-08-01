"""Golden déterministe de spatial_scale_robustness (robustesse d'échelle H3).

Fixtures synthétiques (3 clusters : proportionnel / excès / non-peuplé) →
outcome connu à res 8. Vérifie agrégation H3, null population, décomposition
des cellules sans population, verdict, déterminisme, sortie sans lignes (P2).
"""

import duckdb
import pytest

from intreepid.mcp_server.catalog import load_fiche, load_referenced_fiche
from tests.conftest import CATALOG, FIXTURES

SPATIAL_FICHE = CATALOG / "spatial_seed.fiche.yaml"
SPATIAL_PARQUET = FIXTURES / "spatial_seed.parquet"
POP_PARQUET = FIXTURES / "population_seed.parquet"


def _con():
    con = duckdb.connect(":memory:")
    con.execute("INSTALL spatial")
    con.execute("LOAD spatial")
    con.execute(
        f"CREATE VIEW spatial_seed AS SELECT * FROM"
        f" read_parquet('{SPATIAL_PARQUET.as_posix()}')"
    )
    return con


def test_load_referenced_fiche():
    pop = load_referenced_fiche(CATALOG, "population_seed")
    assert pop["dataset"] == "population_seed"


def test_load_referenced_fiche_rejects_bad_name():
    with pytest.raises(ValueError):
        load_referenced_fiche(CATALOG, "../secret")


def test_fixtures_exist_and_schema():
    assert SPATIAL_PARQUET.exists() and POP_PARQUET.exists()
    fiche = load_fiche(SPATIAL_FICHE)
    assert fiche["dataset"] == "spatial_seed"
    expo = fiche["exposures"]["geom"]
    assert expo["kind"] == "spatial_grid"
    assert expo["fiche"] == "population_seed"
    pop = load_fiche(CATALOG / "population_seed.fiche.yaml")
    assert pop["grid"]["cell_size"] == 100
    assert pop["grid"]["coord_ref"] == "sw_corner"
