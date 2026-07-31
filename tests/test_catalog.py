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
