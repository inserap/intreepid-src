"""Accès à la fiche de connaissance du dataset (describe / list_datasets).

Charge et expose les métadonnées structurées du dataset (sens des colonnes,
pièges, typage) depuis le fichier YAML de fiche.
"""

from pathlib import Path
from typing import Any

import yaml


def load_fiche(path: str | Path) -> dict[str, Any]:
    return yaml.safe_load(Path(path).read_text(encoding="utf-8"))


def load_referenced_fiche(catalog_dir: str | Path, name: str) -> dict[str, Any]:
    """Charge une fiche référencée par nom (`catalog/<name>.fiche.yaml`)."""
    if not name.replace("_", "").isalnum():
        raise ValueError(f"nom de fiche invalide: {name!r}")
    return load_fiche(Path(catalog_dir) / f"{name}.fiche.yaml")


def list_datasets(fiche: dict[str, Any]) -> list[str]:
    return [fiche["dataset"]]


def describe(fiche: dict[str, Any]) -> dict[str, Any]:
    return fiche
