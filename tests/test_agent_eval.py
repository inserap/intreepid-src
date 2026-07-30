"""Évaluation de l'agent sur la fixture OFROU : précision et anti-hallucination.

Marqué @pytest.mark.agent — ne s'exécute pas dans la suite rapide (non-agent).
Vérifie que l'agent remonte des faits qualité-donnée authentiques (sentinelle 999,
trou de série temporel, coordonnées hors emprise CH), signale la concentration, et
refuse les faux patterns (gravité×mois ; baisse de volume => routes plus sûres).
"""

import anyio
import pytest
import yaml

from intreepid.agent.runner import run_analysis
from tests.conftest import GROUND_TRUTH

N = 5
QUESTION = (
    "Profile TOUTES les colonnes du dataset accidents_route (catégorielles, "
    "numériques, temporelle `date`, spatiale `geom`). En particulier : "
    "(a) les accidents sont-ils plus GRAVES en fin d'année (relation gravité/mois) ? "
    "(b) y a-t-il des valeurs ou coordonnées suspectes ? "
    "(c) le volume d'accidents baisse-t-il dans la série — et si oui, peut-on en "
    "conclure que les routes deviennent plus sûres ? Rends ton verdict."
)


def _any(obs, keywords, statuts):
    """True si une observation matche un keyword ET un statut voulus."""
    kws = [k.lower() for k in keywords]
    return any(
        any(k in o.claim.lower() for k in kws) and o.statut in statuts for o in obs
    )


def _mentions(claim, keywords):
    """True si le claim contient au moins un des mots-clés."""
    c = claim.lower()
    return any(k in c for k in keywords)


# M2 : matcher robuste du faux pattern causal. Le pont interdit = relier une
# tendance de VOLUME/série à une conclusion de SÉCURITÉ/danger du monde réel.
# La conjonction (terme-sécurité ET terme-tendance) évite la tautologie : un
# fait qualité-donnée « le volume chute (rupture de collecte) » ne contient PAS
# de terme-sécurité et n'est donc pas capté ici (il compte comme fait temporel).
_SAFETY = ["sûr", "sûre", "sécur", "danger", "risque"]
_TREND = ["volume", "baisse", "diminu", "recul", "moins", "tendance"]


@pytest.mark.agent
def test_agent_eval_thresholds():
    gt = yaml.safe_load(GROUND_TRUTH.read_text(encoding="utf-8"))
    runs = [anyio.run(run_analysis, QUESTION) for _ in range(N)]

    # --- Faits authentiques à remonter (brique #1 conservée) ---
    sentinel_fait = sum(
        1 for obs in runs if _any(obs, ["999", "vitesse_limite"], {"fait"})
    )
    concentration_ok = sum(
        1
        for obs in runs
        if _any(obs, [gt["concentration"]["column"]], {"hypothèse", "fait"})
    )
    # --- Faits authentiques brique #2 (qualité-donnée, PAS causaux) ---
    temporal_fait = sum(
        1
        for obs in runs
        if _any(
            obs,
            ["trou", "manquant", "série", "volume", "collecte", "rupture"],
            {"fait"},
        )
    )
    spatial_fait = sum(
        1
        for obs in runs
        if _any(
            obs,
            [
                "emprise",
                "coordonn",
                "géom",
                "geom",
                "0,0",
                "null-island",
                "suisse",
            ],
            {"fait"},
        )
    )
    # --- Faux patterns : jamais 'fait' ---
    fake_gravite_as_fait = sum(
        1
        for obs in runs
        for o in obs
        if "mois" in o.claim.lower()
        and "grav" in o.claim.lower()
        and o.statut == "fait"
    )
    # pont causal volume->sécurité : terme-sécurité ET terme-tendance, en 'fait'
    fake_safer_as_fait = sum(
        1
        for obs in runs
        for o in obs
        if _mentions(o.claim, _SAFETY)
        and _mentions(o.claim, _TREND)
        and o.statut == "fait"
    )

    assert sentinel_fait >= 4, f"sentinelle en 'fait' seulement {sentinel_fait}/5"
    assert concentration_ok >= 4, (
        f"concentration remontée seulement {concentration_ok}/5"
    )
    assert temporal_fait >= 4, (
        f"fait temporel (trou/rupture) seulement {temporal_fait}/5"
    )
    assert spatial_fait >= 4, f"fait spatial (hors emprise) seulement {spatial_fait}/5"
    assert fake_gravite_as_fait == 0, (
        "ANTI-HALLUCINATION: faux pattern gravité×mois affirmé comme fait"
    )
    assert fake_safer_as_fait == 0, (
        "ANTI-HALLUCINATION: pont causal volume->sécurité affirmé comme fait"
        " (artefact de collecte, causalité non fondable en mono-colonne)"
    )


CONCENTRATION_QUESTION = (
    "Certaines valeurs de la colonne `canton` concentrent-elles anormalement les "
    "événements du dataset accidents_route ? Une valeur au plus gros comptage "
    "est-elle forcément un excès réel ? Utilise les outils à ta disposition "
    "(dont le modèle nul) et rends ton verdict."
)


@pytest.mark.agent
def test_agent_eval_concentration():
    hs = yaml.safe_load(GROUND_TRUTH.read_text(encoding="utf-8"))["hotspot"]
    a, b = hs["true_hotspot"], hs["false_hotspot"]
    runs = [anyio.run(run_analysis, CONCENTRATION_QUESTION) for _ in range(N)]

    _CONC = ["concentr", "excès", "exces", "sur-représent", "point"]

    # (a) la VRAIE concentration (a) est retenue comme fait, avec preuve
    true_as_fait = sum(
        1
        for obs in runs
        for o in obs
        if a in o.claim and _mentions(o.claim, _CONC) and o.statut == "fait"
    )
    # (b) la FAUSSE concentration (b, plus gros comptage) n'est JAMAIS un fait d'excès
    false_as_fait = sum(
        1
        for obs in runs
        for o in obs
        if b in o.claim and _mentions(o.claim, _CONC) and o.statut == "fait"
    )

    assert true_as_fait >= 4, (
        f"vraie concentration {a} retenue en 'fait' seulement {true_as_fait}/5"
    )
    assert false_as_fait == 0, (
        f"ANTI-HALLUCINATION: fausse concentration {b} (gros volume) affirmée comme"
        " excès en 'fait' — le comptage brut n'est pas une preuve"
    )
