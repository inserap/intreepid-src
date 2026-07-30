"""Golden de la formule de pseudo-p par permutation (nullmodel).

Vérifie les bornes (aucun/tous les tirages dépassent), un cas intermédiaire et
le rejet d'une entrée vide. Aucune connaissance de domaine.
"""

import numpy as np
import pytest

from intreepid.mcp_server.nullmodel import pseudo_p


def test_pseudo_p_none_exceeds():
    null = np.zeros(999)
    assert pseudo_p(null, 5.0) == pytest.approx(1 / 1000)


def test_pseudo_p_all_exceed():
    null = np.full(999, 10.0)
    assert pseudo_p(null, 5.0) == pytest.approx(1.0)


def test_pseudo_p_half():
    null = np.array([0.0] * 500 + [10.0] * 499)  # 499 valeurs >= 5.0
    assert pseudo_p(null, 5.0) == pytest.approx(500 / 1000)


def test_pseudo_p_empty_raises():
    with pytest.raises(ValueError, match="vide"):
        pseudo_p(np.array([]), 1.0)
