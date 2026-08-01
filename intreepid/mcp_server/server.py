"""Serveur MCP (FastMCP) exposant les outils read-only du workspace.

Point d'entrée unique de l'agent vers la donnée ; garantit que seuls des
agrégats et métadonnées sont transmis (invariants P2 et P3).
"""

import atexit
import os
from contextlib import ExitStack
from pathlib import Path

from fastmcp import FastMCP

from intreepid.mcp_server.bounds import open_readonly
from intreepid.mcp_server.catalog import (
    describe as _describe,
)
from intreepid.mcp_server.catalog import (
    list_datasets as _list,
)
from intreepid.mcp_server.catalog import (
    load_fiche,
)
from intreepid.mcp_server.concentration import concentration_test as _concentration
from intreepid.mcp_server.profile_stats import profile_stats as _profile
from intreepid.mcp_server.scale_robustness import spatial_scale_robustness as _scale

CATALOG = Path(__file__).parent.parent.parent / "catalog"
FICHE = Path(os.environ.get("INTREEPID_FICHE", CATALOG / "accidents_seed.fiche.yaml"))

_fiche = load_fiche(FICHE)
TABLE = _fiche["dataset"]
_data = (FICHE.parent / _fiche["data"]).resolve()
_stack = ExitStack()
_con = _stack.enter_context(open_readonly(_data, TABLE))
atexit.register(_stack.close)

mcp = FastMCP("intreepid")


@mcp.tool
def list_datasets() -> list[str]:
    """Liste les datasets disponibles."""
    return _list(_fiche)


@mcp.tool
def describe() -> dict:
    """Fiche de connaissance du dataset (sens, pièges, typage des colonnes)."""
    return _describe(_fiche)


@mcp.tool
def profile_stats(columns: list[str] | None = None) -> dict:
    """Carte d'identité statistique (agrégats only, read-only).

    Jamais de lignes brutes transmises au LLM.
    """
    return _profile(_con, TABLE, _fiche, columns)


@mcp.tool
def concentration_test(
    unit_col: str, n_permutations: int = 999, seed: int = 42
) -> dict:
    """Teste si une unité catégorielle est sur-concentrée vs son exposition.

    Modèle nul par permutation. Read-only : agrégats et pseudo-p, jamais de lignes.
    """
    return _concentration(
        _con,
        TABLE,
        _fiche,
        unit_col,
        base_dir=FICHE.parent,
        n_permutations=n_permutations,
        seed=seed,
    )


@mcp.tool
def spatial_scale_robustness(
    resolutions: list[int] | None = None, n_permutations: int = 999, seed: int = 42
) -> dict:
    """Robustesse d'une concentration spatiale au changement de maille (H3).

    Agrège les points en cellules H3 à plusieurs résolutions, teste vs une
    exposition déclarée dans la fiche. Read-only, agrégats only.
    """
    return _scale(
        _con,
        TABLE,
        _fiche,
        base_dir=FICHE.parent,
        resolutions=tuple(resolutions) if resolutions else (6, 7, 8),
        n_permutations=n_permutations,
        seed=seed,
    )


if __name__ == "__main__":
    mcp.run()
