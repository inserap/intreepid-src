"""Écriture de la fiche validée (YAML) + hash de validation durable (D5).

La fiche est un dict OPAQUE (aucun schéma figé). Dump YAML canonique
(`sort_keys=True`) pour un hash stable ; écriture idempotente (contenu identique
=> no-op) comme garde anti-double-validation. Un second artefact, le dialogue de
ratification (`write_questions`), vit à côté d'elle et n'entre jamais dans son
hash (I-G).
"""

import hashlib
from pathlib import Path
from typing import Any

import yaml


def _dump(data: Any) -> str:
    return yaml.safe_dump(data, sort_keys=True, allow_unicode=True)


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


def write_questions(questions: list[dict[str, Any]], path: str | Path) -> str:
    """Écrit le dialogue de ratification, à côté de la fiche.

    Second artefact de la brique #11 : les questions, leurs options et les
    réponses humaines. Il n'est JAMAIS relu par un LLM — la fiche, elle, l'est
    verbatim à chaque analyse, et un dialogue l'alourdirait pour un lecteur qui
    n'en a que faire. Sa valeur est la provenance (P4) et, plus tard,
    l'observation des redites d'une couche à l'autre chez un même producteur
    (Q-0025).
    """
    path = Path(path)
    content = _dump(questions)
    digest = hashlib.sha256(content.encode("utf-8")).hexdigest()
    if path.is_file() and path.read_text(encoding="utf-8") == content:
        return digest  # idempotent
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return digest
