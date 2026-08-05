"""Orchestrateur générique : pilote un agent (profil de rôle) via l'Agent SDK.

Boucle d'exécution commune à tous les rôles (ADR-0009). Phase A : mode one-shot
(un tour, comme l'analyste) ; mode multi-tours (#7c) : next_input non-None.
L'accès donnée reste exclusivement via MCP (P2/P3) ;
la garde OAuth (Q-0010) refuse ANTHROPIC_API_KEY qui masquerait l'abonnement.
"""

import contextlib
import logging
import os
import uuid
from collections.abc import Callable
from pathlib import Path
from typing import Any

from claude_agent_sdk import AssistantMessage, TextBlock, query

from intreepid.agent.profile import Profile
from intreepid.scribe.store import Scribe

logger = logging.getLogger(__name__)


def _safe(fn: Callable[..., Any] | None, *args: Any) -> None:
    """Appelle un hook en best-effort : une panne n'interrompt jamais l'agent."""
    if fn is None:
        return
    try:
        fn(*args)
    except Exception:
        logger.exception("orchestrateur : hook a échoué (capture partielle)")


async def run_agent(
    profile: Profile,
    prompt: str,
    *,
    model: str | None = None,
    trace_to: str | Path | None = None,
) -> Any:
    if os.environ.get("ANTHROPIC_API_KEY"):
        raise RuntimeError(
            "ANTHROPIC_API_KEY est définie : elle masque CLAUDE_CODE_OAUTH_TOKEN."
            " Unset-la (dev = abonnement)."
        )
    options = profile.build_options(model, thinking=trace_to is not None)
    with contextlib.ExitStack() as stack:
        scribe: Scribe | None = None
        if trace_to is not None:
            try:
                scribe = stack.enter_context(
                    Scribe(trace_to, uuid.uuid4().hex, prompt, model)
                )
            except Exception:
                logger.exception("greffier : capture désactivée (échec ouverture)")
                scribe = None
        multi_turn = profile.next_input is not None
        transcript: list[dict[str, str]] = [{"user": prompt}]
        current_prompt = prompt
        while True:
            chunks: list[str] = []
            async for message in query(prompt=current_prompt, options=options):
                if scribe is not None:
                    _safe(scribe.record, message)  # capture best-effort (jamais fatale)
                if isinstance(message, AssistantMessage):
                    for block in message.content:
                        if isinstance(block, TextBlock):
                            chunks.append(block.text)
            result = profile.parse(chunks)
            if not multi_turn:
                if profile.on_result is not None:
                    _safe(profile.on_result, scribe, result)
                return result
            tour_agent = "\n".join(chunks)
            transcript.append({"assistant": tour_agent})
            if scribe is not None:
                # Miroir de human_turn : la trace d'une conversation doit porter
                # ses DEUX voix. Enregistré AVANT next_input, qui bloque sur
                # l'humain — sinon un Ctrl+C perdrait le tour de l'agent.
                _safe(
                    scribe.record_nodes,
                    [("agent_turn", {"text": tour_agent}, {"actor": "agent"})],
                )
            assert profile.next_input is not None
            human_reply = profile.next_input(result)
            if scribe is not None and human_reply is not None:
                _safe(
                    scribe.record_nodes,
                    [("human_turn", {"text": human_reply}, {"actor": "human"})],
                )
            if human_reply is None:  # validation humaine => terminal
                if profile.on_result is not None:
                    _safe(profile.on_result, scribe, result)
                return result
            transcript.append({"user": human_reply})
            assert profile.build_prompt is not None
            current_prompt = profile.build_prompt(transcript)
