import json
import re
from typing import Literal, Optional
from pydantic import BaseModel, TypeAdapter

class Observation(BaseModel):
    claim: str
    statut: Literal["fait", "hypothèse", "refusé"]
    note: Optional[str] = None
    confiance: Optional[str] = None
    nature: Optional[str] = None

_ADAPTER = TypeAdapter(list[Observation])

def parse_verdict(text: str) -> list[Observation]:
    """Extrait le premier tableau JSON du texte et le valide contre le schéma du verdict."""
    match = re.search(r"\[\s*\{.*?\}\s*\]", text, re.DOTALL)
    if not match:
        raise ValueError("aucun tableau JSON trouvé dans la sortie de l'agent")
    return _ADAPTER.validate_python(json.loads(match.group(0)))
