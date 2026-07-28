"""Accès à la fiche de connaissance du dataset (describe / list_datasets).

Charge et expose les métadonnées structurées du dataset (sens des colonnes,
pièges, typage) depuis le fichier YAML de fiche.
"""

from pathlib import Path
from typing import Any

import yaml


def load_fiche(path: str | Path) -> dict[str, Any]:
    return yaml.safe_load(Path(path).read_text(encoding="utf-8"))


def list_datasets(fiche: dict[str, Any]) -> list[str]:
    return [fiche["dataset"]]


def describe(fiche: dict[str, Any]) -> dict[str, Any]:
    return fiche
