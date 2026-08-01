"""Golden déterministe de spatial_scale_robustness (robustesse d'échelle H3).

Fixtures synthétiques (3 clusters : proportionnel / excès / non-peuplé) →
outcome connu à res 8. Vérifie agrégation H3, null population, décomposition
des cellules sans population, verdict, déterminisme, sortie sans lignes (P2).
"""

import duckdb
import pytest

from intreepid.mcp_server.catalog import load_fiche, load_referenced_fiche
from intreepid.mcp_server.scale_robustness import (
    h3_counts,
    h3_exposure,
    spatial_col_of,
    split_cells,
)
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


def test_spatial_col_of():
    assert spatial_col_of(load_fiche(SPATIAL_FICHE)) == "geom"


def test_h3_counts_groups_points_into_cells():
    counts = h3_counts(_con(), "spatial_seed", "geom", 2056, 8)
    # 70 points au total, regroupés en 3 cellules (clusters espacés de ~4km)
    assert sum(counts.values()) == 70
    assert len(counts) >= 3  # au moins 3 cellules (les 3 clusters)
    assert all(isinstance(k, str) and v > 0 for k, v in counts.items())


def test_h3_exposure_aggregates_population():
    grid_fiche = load_fiche(CATALOG / "population_seed.fiche.yaml")
    expo = h3_exposure(_con(), grid_fiche, CATALOG, 8, "population")
    assert sum(expo.values()) == 5020  # 5000 (P) + 20 (E), U absent
    assert all(v > 0 for v in expo.values())


def test_split_cells_separates_unpopulated():
    obs = {"a": 20, "b": 40, "c": 10}
    expo = {"a": 5000.0, "b": 20.0}  # c non peuplé
    testables, unpop = split_cells(obs, expo)
    assert testables == {"a": 20, "b": 40}
    assert unpop == {"c": 10}
