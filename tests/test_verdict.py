"""Vérifie le schéma du verdict et l'extraction tolérante depuis la sortie texte.

Couvre le cas nominal, l'extraction depuis du texte balisé Markdown et le
rejet d'un statut hors vocabulaire contrôlé (lève ValidationError).
"""

import pytest
from pydantic import ValidationError

from intreepid.agent.verdict import parse_verdict


def test_parse_clean_array():
    text = '[{"claim":"x","statut":"fait"},{"claim":"y","statut":"refusé"}]'
    obs = parse_verdict(text)
    assert [o.statut for o in obs] == ["fait", "refusé"]


def test_parse_json_embedded_in_prose():
    text = (
        'Voici mon verdict:\n```json\n[{"claim":"z","statut":"hypothèse"}]\n```\nFin.'
    )
    obs = parse_verdict(text)
    assert obs[0].claim == "z" and obs[0].statut == "hypothèse"


def test_reject_bad_statut():
    with pytest.raises(ValidationError):
        parse_verdict('[{"claim":"x","statut":"vrai"}]')
