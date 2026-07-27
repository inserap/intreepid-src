from pathlib import Path
import io
import os
import sys
from claude_agent_sdk import query, ClaudeAgentOptions, AssistantMessage, TextBlock
from intreepid.agent.verdict import parse_verdict, Observation

# Sur Windows, stderr peut être cp1252 ; le SDK y écrit du debug UTF-8
# (σ, etc. dans les stats MCP). On wrappe en utf-8 avec remplacement.
_stderr_buffer = getattr(sys.stderr, "buffer", None)
_UTF8_STDERR: io.TextIOWrapper | None = (
    io.TextIOWrapper(_stderr_buffer, encoding="utf-8", errors="replace", line_buffering=True)
    if _stderr_buffer is not None
    else None
)

CHARTER = (Path(__file__).parent / "charter.md").read_text(encoding="utf-8")


async def run_analysis(question: str) -> list[Observation]:
    # Garde Q-0010 : dev sur l'abonnement (CLAUDE_CODE_OAUTH_TOKEN). ANTHROPIC_API_KEY
    # masquerait l'OAuth et facturerait l'API → on refuse de tourner si elle est présente.
    if os.environ.get("ANTHROPIC_API_KEY"):
        raise RuntimeError(
            "ANTHROPIC_API_KEY est définie : elle masque CLAUDE_CODE_OAUTH_TOKEN."
            " Unset-la (dev = abonnement)."
        )
    extra_kwargs: dict = {} if _UTF8_STDERR is None else {"debug_stderr": _UTF8_STDERR}
    options = ClaudeAgentOptions(
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
    # P2/P3 (durcissement, SHOULD advisor) : `allowed_tools` n'EXCLUT PAS les built-ins
    # (Bash/Read/Write) — il ne fait qu'auto-approuver. Désactiver les built-ins pour que
    # l'agent ne puisse pas lire le parquet hors `profile_stats`. Ajouter le champ idoine à
    # ClaudeAgentOptions ci-dessus après avoir vérifié son nom sur la version SDK installée
    # (candidats : `tools=[]` ou `disallowed_tools=[...]`). Le smoke test (Step 3) échoue
    # immédiatement si un kwarg est rejeté → garde-fou.
    chunks: list[str] = []
    async for message in query(prompt=question, options=options):
        if isinstance(message, AssistantMessage):
            for block in message.content:
                if isinstance(block, TextBlock):
                    chunks.append(block.text)
    return parse_verdict("\n".join(chunks))
