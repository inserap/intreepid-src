"""Pilote l'agent analyste (Claude Agent SDK), isolé aux seuls outils MCP.

L'accès à la donnée passe exclusivement par profile_stats (invariant P2/P3) :
l'agent ne peut ni lire de fichiers bruts, ni exécuter de commandes système.
"""

import contextlib
import logging
import os
import uuid
from pathlib import Path

from claude_agent_sdk import AssistantMessage, ClaudeAgentOptions, TextBlock, query

from intreepid.agent.verdict import Observation, parse_verdict
from intreepid.scribe.store import Scribe

logger = logging.getLogger(__name__)

CHARTER = (Path(__file__).parent / "charter.md").read_text(encoding="utf-8")

_MCP_TOOLS = [
    "mcp__intreepid__list_datasets",
    "mcp__intreepid__describe",
    "mcp__intreepid__profile_stats",
    "mcp__intreepid__concentration_test",
    "mcp__intreepid__spatial_scale_robustness",
]


def _build_options(
    model: str | None = None, *, thinking: bool = False
) -> ClaudeAgentOptions:
    """Construit les options de l'agent avec isolation maximale (invariant P2/P3).

    Config retenue (VÉRIFIÉE EMPIRIQUEMENT par smoke, pas par lecture de source) :
    - disallowed_tools  → retire les built-ins fichier/shell/web + Skill du contexte
                          (barrière PRINCIPALE ; smoke : Bash/Read bloqués, MCP OK)
    - allowed_tools     → auto-approuve UNIQUEMENT les outils MCP intreepid
    - strict_mcp_config → ignore les serveurs MCP ambiants (~/.claude, .mcp.json…)
    - setting_sources=[] → ignore les settings utilisateur/projet (pas de skills tiers)
    - skills=[]         → aucune skill injectée
    NB : `tools=[]` a été essayé puis RETIRÉ — il vide AUSSI les outils MCP (smoke :
    l'agent se retrouve sans aucun outil et ne peut plus profiler). C'est
    `disallowed_tools` qui porte l'isolation des built-ins.
    """
    return ClaudeAgentOptions(
        model=model,  # None → défaut CLI (hérite la session) ; sinon "sonnet"/"haiku"
        allowed_tools=_MCP_TOOLS,  # auto-approuve uniquement les outils MCP intreepid
        disallowed_tools=[  # barrière principale : retire les built-ins du contexte
            "Bash",
            "Read",
            "Write",
            "Edit",
            "MultiEdit",
            "Glob",
            "Grep",
            "LS",
            "WebSearch",
            "WebFetch",
            "NotebookRead",
            "NotebookEdit",
            "Skill",
        ],
        system_prompt=CHARTER,
        mcp_servers={
            "intreepid": {
                "type": "stdio",
                "command": "uv",
                "args": ["run", "python", "-m", "intreepid.mcp_server.server"],
            }
        },
        permission_mode="bypassPermissions",
        strict_mcp_config=True,
        setting_sources=[],
        skills=[],
        thinking={"type": "adaptive", "display": "summarized"} if thinking else None,
    )


def _safe(scribe: Scribe | None, method: str, *args: object) -> None:
    """Appelle une méthode du scribe en best-effort.

    Une panne n'interrompt jamais l'analyste.
    """
    if scribe is None:
        return
    try:
        getattr(scribe, method)(*args)
    except Exception:
        logger.exception("greffier : %s a échoué (capture partielle)", method)


async def run_analysis(
    question: str, model: str | None = "opus", trace_to: str | Path | None = None
) -> list[Observation]:
    """Lance l'agent analyste et renvoie son verdict structuré.

    Défaut `model="opus"` : l'analyste est le producteur de valeur, on prend le
    modèle le plus capable — l'oracle ne teste que le plancher (mensonge, évidences),
    pas la finesse d'analyse (banc brique #1 : Sonnet passe, Haiku échoue). Passer
    None pour hériter du CLI, "sonnet"/"haiku" pour override. Modèle par rôle : Q-0013.

    Si ``trace_to`` est fourni, le greffier capture la session (arbre immuable
    DuckDB) et le thinking est activé. Sans lui, comportement strictement inchangé.
    """
    # Garde Q-0010 : dev sur l'abonnement (CLAUDE_CODE_OAUTH_TOKEN).
    # ANTHROPIC_API_KEY masquerait l'OAuth → on refuse si elle est présente.
    if os.environ.get("ANTHROPIC_API_KEY"):
        raise RuntimeError(
            "ANTHROPIC_API_KEY est définie : elle masque CLAUDE_CODE_OAUTH_TOKEN."
            " Unset-la (dev = abonnement)."
        )
    options = _build_options(model, thinking=trace_to is not None)
    chunks: list[str] = []
    with contextlib.ExitStack() as stack:
        scribe: Scribe | None = None
        if trace_to is not None:
            try:
                scribe = stack.enter_context(
                    Scribe(trace_to, uuid.uuid4().hex, question, model)
                )
            except Exception:
                logger.exception("greffier : capture désactivée (échec ouverture)")
                scribe = None
        async for message in query(prompt=question, options=options):
            _safe(scribe, "record", message)
            if isinstance(message, AssistantMessage):
                for block in message.content:
                    if isinstance(block, TextBlock):
                        chunks.append(block.text)
        verdict = parse_verdict("\n".join(chunks))
        _safe(scribe, "record_verdict", verdict)
        return verdict
