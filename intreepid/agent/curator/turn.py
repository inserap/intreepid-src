"""Contrat de sortie du curateur : un tour = message + draft de fiche + intention.

Parsing TOLÉRANT : le curateur émet un bloc JSON fencé ; on prend le DERNIER
bloc (le tour final, jamais un exemple intermédiaire — leçon Q-0014). Sans bloc,
tout le texte devient le message (repli). La fiche reste un dict OPAQUE (aucun
schéma figé).
"""

import json
import re
from dataclasses import dataclass
from typing import Any

_BLOCK = re.compile(r"```(?:json|curator)?\s*\n(.*?)```", re.DOTALL)


@dataclass(frozen=True)
class CuratorTurn:
    message: str
    fiche_draft: dict[str, Any] | None
    proposes_completion: bool


def _fallback(text: str) -> CuratorTurn:
    return CuratorTurn(
        message=text.strip(), fiche_draft=None, proposes_completion=False
    )


def parse_curator_turn(text: str) -> CuratorTurn:
    blocks = _BLOCK.findall(text)
    if not blocks:
        return _fallback(text)
    try:
        payload = json.loads(blocks[-1])
    except (json.JSONDecodeError, TypeError):
        return _fallback(text)  # dernier bloc non-JSON => repli tolérant
    if not isinstance(payload, dict):
        return _fallback(text)
    return CuratorTurn(
        message=str(payload.get("message", "")).strip(),
        fiche_draft=payload.get("fiche_draft"),
        proposes_completion=bool(payload.get("proposes_completion", False)),
    )
