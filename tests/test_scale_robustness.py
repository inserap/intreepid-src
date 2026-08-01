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
    spatial_scale_robustness,
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


# ---------------------------------------------------------------------------
# Golden tests — spatial_scale_robustness entrypoint
# ---------------------------------------------------------------------------


def _run(**kw):
    return spatial_scale_robustness(
        _con(), "spatial_seed", load_fiche(SPATIAL_FICHE), base_dir=CATALOG, **kw
    )


def test_pic_is_the_excess_cluster_and_significant():
    out = _run(resolutions=(8,))
    r = out["per_resolution"][0]
    # cluster E (40 points, population 20) = excès le plus fort
    assert r["pic"]["std_excess"] > 0
    assert r["significant"] is True
    assert 46.9 < r["pic"]["lat"] < 47.0  # près de Berne (sanity reprojection)


def test_unpopulated_cluster_reported_not_tested():
    r = _run(resolutions=(8,))["per_resolution"][0]
    assert r["unpopulated"]["n_points"] == 10  # cluster U
    assert r["unpopulated"]["n_cells"] >= 1


def test_verdict_robuste_across_resolutions():
    # cluster E ingénié comme excès fort → significatif à CHAQUE résolution,
    # donc l'agrégation verdict = robuste. On teste le mécanisme, pas un label observé.
    out = _run(resolutions=(7, 8))
    assert all(r["significant"] for r in out["per_resolution"])  # le POURQUOI
    assert out["verdict"] == "robuste"  # l'agrégation


def test_abstention_without_spatial_exposure():
    fiche = load_fiche(SPATIAL_FICHE)
    fiche.pop("exposures", None)
    out = spatial_scale_robustness(
        _con(), "spatial_seed", fiche, base_dir=CATALOG, resolutions=(8,)
    )
    assert out["exposure_model"] == "abstention"


def test_reproducible_and_no_raw_rows():
    a = _run(resolutions=(8,))
    b = _run(resolutions=(8,))
    assert a == b

    def _no_raw_points(o) -> bool:
        if isinstance(o, (list, tuple)):
            # seules listes émises : resolutions (int), per_resolution (dict),
            # caveats (str). Une fuite de coordonnées brutes serait une liste de
            # floats ou de paires (list/tuple) — rejetée ici.
            assert all(
                isinstance(x, (int, str, dict)) and not isinstance(x, bool) for x in o
            ), f"séquence brute dans la sortie (P2) : {o!r}"
            return all(_no_raw_points(x) for x in o)
        if isinstance(o, dict):
            return all(_no_raw_points(v) for v in o.values())
        return True

    assert _no_raw_points(a)  # aucune coordonnée brute nichée dans la sortie (P2)
