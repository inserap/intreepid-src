from pathlib import Path
from fastmcp import FastMCP
from intreepid.mcp_server.bounds import open_readonly
from intreepid.mcp_server.catalog import load_fiche, describe as _describe, list_datasets as _list
from intreepid.mcp_server.profile_stats import profile_stats as _profile

FIXTURES = Path(__file__).parent.parent.parent / "fixtures"
TABLE = "accidents_route"

_fiche = load_fiche(FIXTURES / "accidents.fiche.yaml")
_con = open_readonly(FIXTURES / "accidents_seed.parquet", TABLE)

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
    """Carte d'identité statistique (agrégats only, read-only). Jamais de lignes brutes."""
    return _profile(_con, TABLE, _fiche, columns)


if __name__ == "__main__":
    mcp.run()
