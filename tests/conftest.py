"""Chemins partagés des fixtures pour la suite de tests.

Centralise les références aux fichiers de données (Parquet, YAML) générés
par build_fixture.py afin d'éviter toute duplication dans les tests.
"""

from pathlib import Path
from typing import Any

import duckdb

FIXTURES = Path(__file__).parent.parent / "fixtures"
CATALOG = Path(__file__).parent.parent / "catalog"
SEED_PARQUET = FIXTURES / "accidents_seed.parquet"
GROUND_TRUTH = FIXTURES / "ground_truth.yaml"
FICHE = CATALOG / "accidents_seed.fiche.yaml"


def scalar(con: duckdb.DuckDBPyConnection, sql: str) -> Any:
    """Retourne la 1re colonne de l'unique ligne d'une requête agrégat."""
    row = con.execute(sql).fetchone()
    assert row is not None
    return row[0]
