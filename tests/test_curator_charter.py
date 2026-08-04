"""Garde d'agnosticité : la charte du curateur ne câble aucun domaine métier."""

from intreepid.agent.curator.profile import CHARTER

# Vocabulaire du dataset de démonstration + sentinelles vues en fixture, et termes
# techniques trop spécifiques d'un référentiel. Leur présence signerait un scénario
# câblé (invariant projet no-hard-coded-scenarios) : la connaissance per-dataset vit
# dans la fiche, jamais dans la charte.
_INTERDITS = (
    "999",
    "2056",
    "srid",
    "epsg",
    "lv95",
    "accident",
    "vitesse",
    "canton",
    "commune",
    "ofrou",
)


def test_charte_sans_vocabulaire_metier() -> None:
    minuscules = CHARTER.lower()
    presents = [terme for terme in _INTERDITS if terme in minuscules]
    assert presents == [], f"vocabulaire métier câblé dans la charte : {presents}"


def test_charte_prescrit_la_forme_de_tour() -> None:
    minuscules = CHARTER.lower()
    for marqueur in ("verrou", "ancrage", "enjeu", "je ne sais pas"):
        assert marqueur in minuscules, f"la charte ne prescrit plus : {marqueur}"
