"""Serveur MCP (FastMCP) exposant les outils read-only du workspace.

Point d'entrée unique de l'agent vers la donnée ; garantit que seuls des
agrégats et métadonnées sont transmis (invariants P2 et P3).
"""

import atexit
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

FIXTURES = Path(__file__).parent.parent.parent / "fixtures"
TABLE = "accidents_route"

_fiche = load_fiche(FIXTURES / "accidents.fiche.yaml")
_stack = ExitStack()
_con = _stack.enter_context(open_readonly(FIXTURES / "accidents_seed.parquet", TABLE))
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
        base_dir=FIXTURES,
        n_permutations=n_permutations,
        seed=seed,
    )


if __name__ == "__main__":
    mcp.run()
