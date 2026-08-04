"""Contrat de sortie du curateur : prose libre + un bloc JSON de métadonnées.

Le tour que l'humain lit est la PROSE, hors blocs fencés — avant ET après le
dernier bloc. Les blocs antérieurs (quelle que soit leur langue de fence) sont
retirés du message : une fence illustrative écrite dans la prose disparaît donc
de l'affichage, cas assumé — mais elle ne déplace plus le « dernier bloc », qui
reste celui des métadonnées. Ce dernier porte `fiche_draft` (émis au seul tour de
proposition finale) et `proposes_completion`. Parsing TOLÉRANT : sans bloc, ou
bloc non-JSON, tout le texte devient le message ; si la prose est vide, repli sur
un champ `message` du bloc (ancien format). La fiche reste un dict OPAQUE (aucun
schéma figé).
"""

import json
import re
from dataclasses import dataclass
from typing import Any

_BLOCK = re.compile(r"```[A-Za-z]*[ \t\r]*\n(.*?)```", re.DOTALL)


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
    matches = list(_BLOCK.finditer(text))
    if not matches:
        return _fallback(text)
    last = matches[-1]
    try:
        payload = json.loads(last.group(1))
    except (json.JSONDecodeError, TypeError):
        return _fallback(text)  # dernier bloc non-JSON => repli tolérant
    if not isinstance(payload, dict):
        return _fallback(text)
    # La prose = tout le texte HORS blocs : avant le dernier (blocs antérieurs
    # retirés) ET après lui. Sans le suffixe, un modèle qui place son bloc en
    # tête produit un tour MUET, et toute phrase de clôture serait perdue.
    # Les deux morceaux sont substitués séparément : concaténés d'abord, deux
    # fences orphelines pourraient s'apparier et effacer du texte légitime.
    avant = _BLOCK.sub("", text[: last.start()])
    apres = text[last.end() :]
    message = f"{avant}\n{apres}".strip()
    if not message:  # aucun texte hors bloc => repli sur l'ancien champ `message`
        message = str(payload.get("message", "")).strip()
    draft = payload.get("fiche_draft")
    return CuratorTurn(
        message=message,
        fiche_draft=draft if isinstance(draft, dict) and draft else None,
        proposes_completion=bool(payload.get("proposes_completion", False)),
    )
