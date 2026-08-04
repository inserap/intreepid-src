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
    # Multi-tours (ADR-0009 / #7c). Défaut None => profil ONE-SHOT (non-régression).
    # Un profil multi-tours DOIT fournir next_input ET build_prompt ensemble.
    #   next_input : affiche le tour agent + lit la réponse humaine ; retourne la
    #     réponse, ou None pour signaler la validation (terminaison).
    #   build_prompt : sérialise l'historique en tour utilisateur
    #     (charte = system_prompt, byte-stable). Appelé aux tours >= 2.
    next_input: Callable[[Any], str | None] | None = None
    build_prompt: Callable[[list[dict[str, str]]], str] | None = None
