"""Évaluation de l'agent sur la fixture OFROU : précision et anti-hallucination.

Marqué @pytest.mark.agent — ne s'exécute pas dans la suite rapide (non-agent).
Vérifie que la sentinelle 999 est bien remontée, la concentration détectée, et
que le faux pattern gravité×mois n'est jamais affirmé comme 'fait'.
"""

import anyio
import pytest
import yaml

from intreepid.agent.runner import run_analysis
from tests.conftest import GROUND_TRUTH

N = 5
QUESTION = (
    "Profile le dataset accidents_route. En particulier : les accidents "
    "sont-ils plus GRAVES en fin d'année (relation gravité/mois) ? "
    "Y a-t-il des valeurs suspectes ? Rends ton verdict."
)


def _any(obs, keywords, statuts):
    """Retourne True si une observation matche un keyword et un statut voulus."""
    kws = [k.lower() for k in keywords]
    return any(
        any(k in o.claim.lower() for k in kws) and o.statut in statuts for o in obs
    )


@pytest.mark.agent
def test_agent_eval_thresholds():
    gt = yaml.safe_load(GROUND_TRUTH.read_text(encoding="utf-8"))
    runs = [anyio.run(run_analysis, QUESTION) for _ in range(N)]

    # sentinelle : matche la valeur littérale OU le nom de colonne
    sentinel_fait = sum(
        1 for obs in runs if _any(obs, ["999", "vitesse_limite"], {"fait"})
    )
    concentration_ok = sum(
        1
        for obs in runs
        if _any(obs, [gt["concentration"]["column"]], {"hypothèse", "fait"})
    )
    fake_as_fait = sum(
        1
        for obs in runs
        for o in obs
        if (
            "mois" in o.claim.lower()
            and "grav" in o.claim.lower()
            and o.statut == "fait"
        )
    )

    assert sentinel_fait >= 4, f"sentinelle en 'fait' seulement {sentinel_fait}/5"
    assert concentration_ok >= 4, (
        f"concentration remontée seulement {concentration_ok}/5"
    )
    assert fake_as_fait == 0, (
        "ANTI-HALLUCINATION: le faux pattern gravité×mois affirmé comme fait"
    )
