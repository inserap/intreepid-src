"""Écriture de la fiche validée (YAML) + hash de validation durable (D5).

La fiche est un dict OPAQUE (aucun schéma figé). Dump YAML canonique
(`sort_keys=True`) pour un hash stable ; écriture idempotente (contenu identique
=> no-op) comme garde anti-double-validation.
"""

import hashlib
from pathlib import Path

import yaml


def _dump(draft: dict) -> str:
    return yaml.safe_dump(draft, sort_keys=True, allow_unicode=True)


def fiche_sha256(draft: dict) -> str:
    return hashlib.sha256(_dump(draft).encode("utf-8")).hexdigest()


def write_fiche(draft: dict, path: str | Path) -> str:
    path = Path(path)
    content = _dump(draft)
    if path.is_file() and path.read_text(encoding="utf-8") == content:
        return hashlib.sha256(content.encode("utf-8")).hexdigest()  # idempotent
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return hashlib.sha256(content.encode("utf-8")).hexdigest()
