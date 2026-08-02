"""Profil de rôle d'agent : configuration passée à l'orchestrateur générique.

Un profil décrit CE QUI change d'un rôle à l'autre (options SDK, parsing de la
sortie, capture du résultat) ; la mécanique d'exécution commune vit dans
``orchestrator.py``. Cf. ADR-0009 (architecture d'exécution des agents).
"""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from claude_agent_sdk import ClaudeAgentOptions

from intreepid.scribe.store import Scribe


@dataclass(frozen=True)
class Profile:
    # build_options : signature libre (l'analyste garde ``thinking`` keyword-only)
    #   → Callable[..., …]. parse reçoit la LISTE des chunks de texte (pas une
    #   string jointe) → dimensionné au besoin du curateur (Phase D). on_result :
    #   hook de capture du mode ONE-SHOT (Scribe) ; le mode multi-tours (D) aura sa
    #   propre capture via open/append/seal — on_result n'est pas re-signé.
    role: str
    build_options: Callable[..., ClaudeAgentOptions]
    parse: Callable[[list[str]], Any]
    on_result: Callable[[Scribe | None, Any], None] | None = None
