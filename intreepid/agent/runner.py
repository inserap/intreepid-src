from pathlib import Path
import io
import os
import sys
from typing import Any
from claude_agent_sdk import query, ClaudeAgentOptions, AssistantMessage, TextBlock
from intreepid.agent.verdict import parse_verdict, Observation

CHARTER = (Path(__file__).parent / "charter.md").read_text(encoding="utf-8")


async def run_analysis(question: str) -> list[Observation]:
    # Garde Q-0010 : dev sur l'abonnement (CLAUDE_CODE_OAUTH_TOKEN). ANTHROPIC_API_KEY
    # masquerait l'OAuth et facturerait l'API → on refuse de tourner si elle est présente.
    if os.environ.get("ANTHROPIC_API_KEY"):
        raise RuntimeError(
            "ANTHROPIC_API_KEY est définie : elle masque CLAUDE_CODE_OAUTH_TOKEN."
            " Unset-la (dev = abonnement)."
        )
    # Sur Windows, stderr peut être cp1252 ; le SDK y écrit du debug UTF-8
    # (σ, etc. dans les stats MCP). On wrappe localement pour ne pas muter sys.stderr
    # globalement à l'import.
    # Sur Windows, stderr peut être cp1252 ; le SDK y écrit du debug UTF-8.
    # On ouvre fd=2 séparément (closefd=False) pour éviter de détacher le buffer
    # de sys.stderr (ce qui crasherait sous pytest).
    _utf8_stderr: io.TextIOWrapper | None = None
    try:
        _fd = sys.stderr.fileno()
        _utf8_stderr = open(_fd, "w", encoding="utf-8", errors="replace",
                            closefd=False, buffering=1)
    except (AttributeError, io.UnsupportedOperation, OSError):
        _utf8_stderr = None
    extra_kwargs: dict[str, Any] = {} if _utf8_stderr is None else {"debug_stderr": _utf8_stderr}
    options = ClaudeAgentOptions(
        # P2/P3 (invariant central) : disallowed_tools bloque les built-ins fichier/shell.
        # tools=[] supprimerait aussi les outils MCP → on utilise disallowed_tools à la place.
        # permission_mode="bypassPermissions" est sûr : seuls les 3 outils MCP sont dispo.
        disallowed_tools=[
            "Bash", "Read", "Write", "Edit", "MultiEdit",
            "Glob", "Grep", "LS",
            "WebSearch", "WebFetch",
            "NotebookRead", "NotebookEdit",
        ],
        system_prompt=CHARTER,
        # lancer le serveur MCP dans l'env uv (pas un python nu du PATH)
        mcp_servers={
            "intreepid": {
                "type": "stdio",
                "command": "uv",
                "args": ["run", "python", "-m", "intreepid.mcp_server.server"],
            }
        },
        allowed_tools=[
            "mcp__intreepid__list_datasets",
            "mcp__intreepid__describe",
            "mcp__intreepid__profile_stats",
        ],
        permission_mode="bypassPermissions",
        **extra_kwargs,
    )
    chunks: list[str] = []
    async for message in query(prompt=question, options=options):
        if isinstance(message, AssistantMessage):
            for block in message.content:
                if isinstance(block, TextBlock):
                    chunks.append(block.text)
    return parse_verdict("\n".join(chunks))
