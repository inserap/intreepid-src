"""Schéma structuré du verdict de l'agent (pydantic) et extraction tolérante.

Valide la sortie texte de l'agent contre le modèle Observation ; lève une
ValidationError si le statut est hors du vocabulaire contrôlé.
"""

import json
import re
from typing import Literal

from pydantic import BaseModel, TypeAdapter


class Observation(BaseModel):
    claim: str
    statut: Literal["fait", "hypothèse", "refusé"]
    note: str | None = None
    confiance: str | None = None
    nature: str | None = None


_ADAPTER = TypeAdapter(list[Observation])


def parse_verdict(text: str) -> list[Observation]:
    """Extrait le premier tableau JSON du texte et le valide contre le schéma."""
    match = re.search(r"\[\s*\{.*?\}\s*\]", text, re.DOTALL)
    if not match:
        raise ValueError("aucun tableau JSON trouvé dans la sortie de l'agent")
    return _ADAPTER.validate_python(json.loads(match.group(0)))
