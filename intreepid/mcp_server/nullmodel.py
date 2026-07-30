"""Formule générique de p-value par permutation (modèle nul).

Isolée pour être réutilisée par tout test de rigueur fondé sur un contrefactuel
aléatoire (concentration ici ; autocorrélation, etc. plus tard). Ne connaît aucun
domaine : prend une distribution nulle et une statistique observée, rend un pseudo-p.
"""

from collections.abc import Sequence

import numpy as np


def pseudo_p(null_stats: "Sequence[float] | np.ndarray", observed: float) -> float:
    """p-value par permutation : (#{null_stats >= observed} + 1) / (N + 1).

    Le +1 au numérateur et au dénominateur compte l'observé comme un tirage
    possible sous H0 (borne inférieure 1/(N+1), jamais 0 ; borne supérieure 1).
    """
    arr = np.asarray(null_stats, dtype=float)
    if arr.size == 0:
        raise ValueError("null_stats vide : pseudo-p indéfini")
    exceed = int(np.count_nonzero(arr >= observed))
    return (exceed + 1) / (arr.size + 1)
