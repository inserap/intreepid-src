"""Golden déterministe de concentration_test (modèle nul de concentration).

Vérifie : vraie concentration significative (pseudo-p bas), fausse non
significative (pseudo-p haut), bascule uniforme sans exposition déclarée,
reproductibilité (seed), sortie sans lignes (P2), garde table vide, cap permutations.
"""

import duckdb
import pytest
import yaml

from intreepid.mcp_server.catalog import load_fiche
from intreepid.mcp_server.concentration import concentration_test
from tests.conftest import CATALOG, FICHE, GROUND_TRUTH, SEED_PARQUET


def _con():
    con = duckdb.connect(":memory:")
    con.execute("INSTALL spatial")
    con.execute("LOAD spatial")
    con.execute(
        f"CREATE VIEW accidents_route AS SELECT * FROM"
        f" read_parquet('{SEED_PARQUET.as_posix()}')"
    )
    return con


def _gt():
    return yaml.safe_load(GROUND_TRUTH.read_text(encoding="utf-8"))["hotspot"]


def test_true_hotspot_is_significant():
    out = concentration_test(
        _con(), "accidents_route", load_fiche(FICHE), "canton", base_dir=CATALOG
    )
    assert out["exposure_model"] == "declared:canton_exposure.parquet"
    assert out["most_concentrated"]["unit"] == _gt()["true_hotspot"]
    assert out["most_concentrated"]["pseudo_p"] < 0.05


def test_false_hotspot_not_significant():
    out = concentration_test(
        _con(), "accidents_route", load_fiche(FICHE), "canton", base_dir=CATALOG
    )
    assert out["highest_raw_count"]["unit"] == _gt()["false_hotspot"]
    assert out["highest_raw_count"]["pseudo_p"] >= 0.05


def test_uniform_when_no_exposure_declared():
    fiche = load_fiche(FICHE)
    fiche.pop("exposures", None)
    out = concentration_test(
        _con(), "accidents_route", fiche, "canton", base_dir=CATALOG
    )
    assert out["exposure_model"] == "uniform"


def test_reproducible_with_seed():
    a = concentration_test(
        _con(), "accidents_route", load_fiche(FICHE), "canton", base_dir=CATALOG
    )
    b = concentration_test(
        _con(), "accidents_route", load_fiche(FICHE), "canton", base_dir=CATALOG
    )
    assert a == b


def test_output_has_no_raw_rows():
    out = concentration_test(
        _con(), "accidents_route", load_fiche(FICHE), "canton", base_dir=CATALOG
    )
    assert set(out) == {
        "unit_col",
        "exposure_model",
        "n_permutations",
        "seed",
        "n_total",
        "n_units",
        "most_concentrated",
        "highest_raw_count",
    }

    # P2 : aucune liste/tuple NULLE PART dans la sortie (récursif) — pas de lignes
    # ni de coordonnées transmises, même nichées dans un sous-dict.
    def _no_sequences(obj) -> bool:
        if isinstance(obj, (list, tuple)):
            return False
        if isinstance(obj, dict):
            return all(_no_sequences(v) for v in obj.values())
        return True

    assert _no_sequences(out)


def test_unit_col_must_be_in_fiche():
    with pytest.raises(ValueError, match="allowlist"):
        concentration_test(
            _con(),
            "accidents_route",
            load_fiche(FICHE),
            "pas_une_colonne",
            base_dir=CATALOG,
        )


def test_permutations_capped():
    # S5 : cap défensif — une valeur énorme (agent/prompt injection) est bornée.
    out = concentration_test(
        _con(),
        "accidents_route",
        load_fiche(FICHE),
        "canton",
        base_dir=CATALOG,
        n_permutations=10**9,
    )
    assert out["n_permutations"] <= 9999
