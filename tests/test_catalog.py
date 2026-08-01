"""Vérifie que les fiches du catalogue sont auto-descriptives et résolvent.

La fiche porte le chemin relatif vers SA donnée (data) et vers ses tables
d'exposition, ancrés sur le dossier de la fiche. Testé sur le monde fixture
(tracké, déterministe) ; la fiche réelle est validée en structure seulement.
"""

from intreepid.mcp_server.catalog import load_fiche
from tests.conftest import CATALOG, FICHE


def test_fixture_fiche_self_describes():
    fiche = load_fiche(FICHE)
    assert fiche["dataset"] == "accidents_seed"
    data = (FICHE.parent / fiche["data"]).resolve()
    assert data.exists(), f"parquet introuvable via la fiche : {data}"
    expo = (FICHE.parent / fiche["exposures"]["canton"]["table"]).resolve()
    assert expo.exists(), f"exposition introuvable via la fiche : {expo}"


def test_catalog_dir_holds_fiche():
    assert (CATALOG / "accidents_seed.fiche.yaml").exists()


def test_real_fiche_wellformed():
    from tests.conftest import CATALOG  # noqa: PLC0415

    fiche = load_fiche(CATALOG / "accidents_route.fiche.yaml")
    assert fiche["dataset"] == "accidents_route"
    assert fiche["data"] == "../data/prepared/accidents_route.parquet"
    expected = {
        "type_route",
        "severity",
        "accident_month",
        "canton",
        "implique_pieton",
        "implique_velo",
        "implique_moto",
        "date",
        "geom",
    }
    assert set(fiche["columns"]) == expected
    assert fiche["exposures"]["canton"]["weight"] == "population"
