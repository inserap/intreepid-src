"""Test de concentration par modèle nul — agnostique au domaine.

Teste si une variable catégorielle (l'« unité ») est sur-concentrée par rapport à
une exposition attendue, via redistribution multinomiale aléatoire (contrefactuel).
Le LLM ne reçoit que des agrégats et un pseudo-p (P2) ; connexion read-only (P3) ;
seed fixé (P4). Aucune connaissance de domaine : l'exposition est déclarée dans la
fiche (section `exposures`) ; à défaut, abstention (l'uniforme exige un opt-in
explicite `{uniform: true}` — Q-0016 : pas de null uniforme silencieux trompeur).
"""

from pathlib import Path
from typing import Any

import duckdb
import numpy as np

from intreepid.mcp_server.nullmodel import pseudo_p, std_excess

_MAX_PERMUTATIONS = 9999  # cap dur (borne défensive, esprit TOP_K de profile_stats)
_DEFAULT_PERMUTATIONS = 999  # défaut raisonnable : précision ~1/1000, < 1 s


def _ident(name: str) -> str:
    if not name.replace("_", "").isalnum():
        raise ValueError(f"nom de colonne invalide: {name!r}")
    return f'"{name}"'


def _unit(units, observed, expected, z, i, pseudo):
    return {
        "unit": units[i],
        "observed": int(observed[i]),
        "expected": round(float(expected[i]), 2),
        "std_excess": round(float(z[i]), 2),
        "pseudo_p": round(pseudo, 4),
    }


def concentration_test(
    con: duckdb.DuckDBPyConnection,
    table: str,
    fiche: dict[str, Any],
    unit_col: str,
    *,
    base_dir: Path,
    n_permutations: int = _DEFAULT_PERMUTATIONS,
    seed: int = 42,
) -> dict[str, Any]:
    if unit_col not in fiche["columns"]:
        raise ValueError(f"colonne hors allowlist de la fiche: {unit_col!r}")
    n_permutations = max(1, min(n_permutations, _MAX_PERMUTATIONS))  # S5 : cap défensif
    u, t = _ident(unit_col), _ident(table)

    rows = con.execute(
        f"SELECT {u} AS unit, count(*) AS o FROM {t} GROUP BY {u} ORDER BY {u}"
    ).fetchall()
    units = [str(r[0]) for r in rows]
    observed = np.array([r[1] for r in rows], dtype=float)
    n_total = int(observed.sum())
    if n_total == 0:
        raise ValueError("aucune ligne : test de concentration impossible")

    decl = fiche.get("exposures", {}).get(unit_col)
    if decl and decl.get("uniform") is True:
        weights = np.ones(len(units), dtype=float)
        exposure_model = "uniform:declared"
    elif decl:
        path = (Path(base_dir) / decl["table"]).as_posix()
        wrows = con.execute(
            f"SELECT {_ident(decl['key'])} AS k, {_ident(decl['weight'])} AS w"
            f" FROM read_parquet('{path}')"
        ).fetchall()
        wmap = {str(r[0]): float(r[1]) for r in wrows}
        absent = [x for x in units if x not in wmap]
        if absent:
            raise ValueError(f"unités sans exposition déclarée: {absent}")
        weights = np.array([wmap[x] for x in units], dtype=float)
        exposure_model = f"declared:{Path(decl['table']).name}"
    else:
        return {
            "unit_col": unit_col,
            "exposure_model": "abstention",
            "reason": "sur-concentration non évaluable sans exposition déclarée "
            "(ni table d'exposition, ni opt-in uniforme explicite)",
            "n_units": len(units),
            "n_total": n_total,
        }

    # S4 : une exposition nulle/négative rendrait E_u=0 pour une unité pourtant
    # observée -> son excès serait silencieusement masqué. Contrat : w_u > 0.
    if bool(np.any(weights <= 0)):
        raise ValueError("exposition nulle ou négative interdite (w_u > 0 requis)")
    p = weights / weights.sum()
    expected = n_total * p
    z = std_excess(observed, expected)
    i_most = int(np.argmax(z))
    i_raw = int(np.argmax(observed))
    t_obs = float(z[i_most])
    zb_obs = float(z[i_raw])

    rng = np.random.default_rng(seed)
    t_sim = np.empty(n_permutations)
    zb_sim = np.empty(n_permutations)
    for r in range(n_permutations):
        sim = rng.multinomial(n_total, p).astype(float)
        zsim = std_excess(sim, expected)
        t_sim[r] = zsim.max()
        zb_sim[r] = zsim[i_raw]

    return {
        "unit_col": unit_col,
        "exposure_model": exposure_model,
        "n_permutations": n_permutations,
        "seed": seed,
        "n_total": n_total,
        "n_units": len(units),
        "most_concentrated": _unit(
            units, observed, expected, z, i_most, pseudo_p(t_sim, t_obs)
        ),
        "highest_raw_count": _unit(
            units, observed, expected, z, i_raw, pseudo_p(zb_sim, zb_obs)
        ),
    }
