"""Robustesse d'échelle spatiale — agnostique au domaine.

Agrège les points d'un dataset en cellules Uber H3 à plusieurs résolutions et
teste si une concentration (vs exposition déclarée) survit au changement de
maille. Reprojection SRID→WGS84 en SQL DuckDB ; null par redistribution
multinomiale ∝ exposition (réutilise nullmodel.pseudo_p). Le LLM ne reçoit que
des agrégats et des identifiants de cellule (P2) ; connexion read-only (P3).
Caveat assumé : agrégation planaire — biaisée pour un phénomène de réseau.
"""

from pathlib import Path
from typing import Any

import duckdb
import h3
import numpy as np

from intreepid.mcp_server.catalog import load_referenced_fiche
from intreepid.mcp_server.nullmodel import pseudo_p, std_excess

_CAVEATS = [
    "Le null est proportionnel à l'exposition déclarée dans la fiche : une "
    "concentration au-delà de cette exposition n'est pas une preuve de "
    "causalité (l'exposition déclarée n'est pas nécessairement le facteur "
    "explicatif du phénomène).",
    "Agrégation planaire H3 : biaisée pour un phénomène contraint à un réseau "
    "1-D plutôt qu'étalé dans le plan (cf. Xie & Yan 2008, densité de réseau).",
    "Hiérarchie H3 non-emboîtante : l'identité d'une cellule d'une résolution "
    "à l'autre n'est pas affirmée ; le pic est décrit par résolution.",
]


def spatial_col_of(fiche: dict[str, Any]) -> str:
    """Nom de la colonne spatiale ponctuelle déclarée dans la fiche."""
    for name, meta in fiche["columns"].items():
        if (
            meta.get("type") == "spatial"
            and meta.get("geometry_type_attendu") == "point"
        ):
            return name
    raise ValueError("aucune colonne spatiale ponctuelle dans la fiche")


def _ident(name: str) -> str:
    if not name.replace("_", "").isalnum():
        raise ValueError(f"nom de colonne invalide: {name!r}")
    return f'"{name}"'


def h3_counts(
    con: duckdb.DuckDBPyConnection,
    table: str,
    geom_col: str,
    srid: int,
    resolution: int,
) -> dict[str, int]:
    """Reprojette les points en WGS84 et compte-les par cellule H3."""
    g, t = _ident(geom_col), _ident(table)
    # ST_Transform → WGS84 ; always_xy garantit (lng,lat) ; ST_X=lng, ST_Y=lat.
    src_srid = f"EPSG:{int(srid)}"
    sql = (
        f"SELECT ST_X(p) AS lng, ST_Y(p) AS lat FROM ("
        f"  SELECT ST_Transform({g}, '{src_srid}', 'EPSG:4326', always_xy := true)"
        f" AS p FROM {t} WHERE {g} IS NOT NULL) q"
    )
    rows = con.execute(sql).fetchall()
    counts: dict[str, int] = {}
    for lng, lat in rows:
        cell = h3.latlng_to_cell(float(lat), float(lng), resolution)
        counts[cell] = counts.get(cell, 0) + 1
    return counts


def h3_exposure(
    con: duckdb.DuckDBPyConnection,
    grid_fiche: dict[str, Any],
    base_dir: "str | Path",
    resolution: int,
    weight_col: str,
) -> dict[str, float]:
    """Agrège une grille d'exposition (points-mailles pondérés) en cellules H3.

    `weight_col` est fourni par le lien d'exposition (`exposures.<col>.weight`),
    jamais inféré : le consommateur choisit la colonne de poids.
    """
    grid = grid_fiche["grid"]
    data = (Path(base_dir) / grid_fiche["data"]).as_posix()
    e_col, n_col = grid["east"], grid["north"]
    srid = int(grid_fiche["columns"][e_col]["srid"])
    half = float(grid["cell_size"]) / 2 if grid.get("coord_ref") == "sw_corner" else 0.0
    pt = f"ST_Point({_ident(e_col)} + {half}, {_ident(n_col)} + {half})"
    rows = con.execute(
        f"SELECT ST_X(p) AS lng, ST_Y(p) AS lat, w FROM ("
        f"  SELECT ST_Transform({pt},"
        f"    'EPSG:{srid}', 'EPSG:4326', always_xy := true) AS p,"
        f"    {_ident(weight_col)}::DOUBLE AS w"
        f"  FROM read_parquet('{data}')) q"
    ).fetchall()
    expo: dict[str, float] = {}
    for lng, lat, w in rows:
        cell = h3.latlng_to_cell(float(lat), float(lng), resolution)
        expo[cell] = expo.get(cell, 0.0) + float(w)
    return expo


def split_cells(
    obs: dict[str, int], expo: dict[str, float]
) -> "tuple[dict[str, int], dict[str, int]]":
    """Sépare cellules testables (exposition>0) et non-peuplées (exposition==0)."""
    testables = {c: o for c, o in obs.items() if expo.get(c, 0.0) > 0.0}
    unpop = {c: o for c, o in obs.items() if expo.get(c, 0.0) <= 0.0}
    return testables, unpop


def spatial_scale_robustness(
    con: duckdb.DuckDBPyConnection,
    table: str,
    fiche: dict[str, Any],
    *,
    base_dir: "str | Path",
    resolutions: "tuple[int, ...]" = (6, 7, 8),
    n_permutations: int = 999,
    seed: int = 42,
) -> dict[str, Any]:
    """Teste la robustesse d'échelle d'une concentration spatiale sur grille H3."""
    spatial_col = spatial_col_of(fiche)
    srid = int(fiche["columns"][spatial_col]["srid"])
    decl = fiche.get("exposures", {}).get(spatial_col)
    if not decl or decl.get("kind") != "spatial_grid":
        return {
            "spatial_col": spatial_col,
            "exposure_model": "abstention",
            "reason": "robustesse non évaluable sans exposition spatiale déclarée",
            "resolutions": list(resolutions),
        }
    grid_fiche = load_referenced_fiche(base_dir, decl["fiche"])
    weight_col = decl["weight"]

    per: list[dict[str, Any]] = []
    rng = np.random.default_rng(seed)
    for res in resolutions:
        obs = h3_counts(con, table, spatial_col, srid, res)
        expo = h3_exposure(con, grid_fiche, base_dir, res, weight_col)
        testables, unpop = split_cells(obs, expo)
        cells = sorted(testables)
        unpop_block: dict[str, Any] = {
            "n_cells": len(unpop),
            "n_points": int(sum(unpop.values())),
            "share": round(sum(unpop.values()) / max(1, sum(obs.values())), 4),
        }
        if not cells:
            per.append(
                {
                    "resolution": res,
                    "n_cells_tested": 0,
                    "n_total_tested": 0,
                    "pic": None,
                    "pseudo_p": None,
                    "significant": False,
                    "unpopulated": unpop_block,
                }
            )
            continue
        o = np.array([testables[c] for c in cells], dtype=float)
        w = np.array([expo[c] for c in cells], dtype=float)
        n_total = int(o.sum())
        p = w / w.sum()
        expected = n_total * p
        z = std_excess(o, expected)
        i_pic = int(np.argmax(z))
        t_obs = float(z[i_pic])
        t_sim = np.empty(n_permutations)
        for r in range(n_permutations):
            sim = rng.multinomial(n_total, p).astype(float)
            t_sim[r] = std_excess(sim, expected).max()
        pp = pseudo_p(t_sim, t_obs)
        lat, lng = h3.cell_to_latlng(cells[i_pic])
        per.append(
            {
                "resolution": res,
                "n_cells_tested": len(cells),
                "n_total_tested": n_total,
                "pic": {
                    "h3": cells[i_pic],
                    "lat": round(float(lat), 5),
                    "lng": round(float(lng), 5),
                    "std_excess": round(t_obs, 2),
                },
                "pseudo_p": round(pp, 4),
                "significant": pp <= 0.05,
                "unpopulated": unpop_block,
            }
        )

    sig = [r["significant"] for r in per]
    verdict = "robuste" if all(sig) else ("absente" if not any(sig) else "fragile")
    return {
        "spatial_col": spatial_col,
        "exposure_model": f"declared:{decl['fiche']}",
        "resolutions": list(resolutions),
        "seed": seed,
        "n_permutations": n_permutations,
        "verdict": verdict,
        "per_resolution": per,
        "caveats": _CAVEATS,
    }
