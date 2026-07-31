"""Rendu ASCII d'un arbre de session pour la démo et l'inspection humaine."""

import json

from intreepid.scribe.trace import SessionTrace, TraceNode


def _short(text: str, limit: int = 100) -> str:
    text = " ".join(str(text).split())
    return text if len(text) <= limit else text[: limit - 1] + "…"


def render(trace: SessionTrace) -> str:
    """Rend l'arbre avec thinking/appels/observations ; résultats sous appel."""
    lines = [
        f"session {trace.session_id} [{trace.status}] — {trace.question!r} "
        f"(model={trace.model})"
    ]
    results: dict[str, list[TraceNode]] = {}
    for n in trace.nodes:
        if n.kind == "tool_result":
            results.setdefault(n.parent_id or "", []).append(n)
    for n in trace.nodes:
        if n.kind in ("session_root", "tool_result"):
            continue
        if n.kind == "thinking":
            lines.append(f"  ├─ 💭 {_short(n.content.get('text', ''))}")
        elif n.kind == "tool_call":
            args = json.dumps(n.content.get("input", {}), ensure_ascii=False)
            lines.append(f"  ├─ 🔧 {n.content.get('name', '?')}({_short(args, 60)})")
            for r in results.get(n.id, []):
                lines.append(f"  │    └─ → {_short(r.content.get('content', ''))}")
        elif n.kind == "observation":
            lines.append(
                f"  ├─ [{n.meta.get('statut')}] {_short(n.content.get('claim', ''))}"
            )
    return "\n".join(lines)
