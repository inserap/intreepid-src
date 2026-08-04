"""Projection d'une trace de session en document Quarto (.qmd) rejouable.

Fonction PURE (aucune I/O, aucun LLM, aucune horloge murale) : sérialise une
SessionTrace déjà capturée en markdown Quarto déterministe — résultats FIGÉS
(pas de ré-exécution). Miroir de render.py (ASCII), cible Quarto. render_html
shell le CLI `quarto` en best-effort (dégrade proprement s'il est absent).
Agnostique au domaine : ne connaît que la forme des nœuds, jamais leur sujet.
"""

import json
import logging
import subprocess
from pathlib import Path

from intreepid.scribe.trace import SessionTrace, TraceNode

logger = logging.getLogger(__name__)

_CALLOUT = {"fait": "note", "hypothèse": "warning", "refusé": "caution"}
_IDPFX = {"fait": "nte", "hypothèse": "wrn", "refusé": "cau"}


def _fence(lang: str, body: str) -> str:
    return f"```{{.{lang}}}\n{body}\n```"


def _frontmatter(trace: SessionTrace) -> str:
    title = " ".join(str(trace.question).split())
    lines = ["---", f'title: "{title}"']
    started = trace.meta.get("started_at")  # omis par défaut (déterminisme)
    if started:
        lines.append(f'date: "{started}"')
    lines += [
        "format:",
        "  html:",
        "    toc: true",
        "    code-fold: true",
        "    embed-resources: true",
        "    theme: cosmo",
        "---",
    ]
    return "\n".join(lines)


def _result_json(content: object) -> str:
    if isinstance(content, str):
        try:
            return json.dumps(json.loads(content), ensure_ascii=False, indent=2)
        except (ValueError, TypeError):
            return content
    return json.dumps(content, ensure_ascii=False, indent=2, default=str)


def _results_by_call(trace: SessionTrace) -> dict[str, list[TraceNode]]:
    out: dict[str, list[TraceNode]] = {}
    for n in trace.nodes:
        if n.kind == "tool_result":
            out.setdefault(n.parent_id or "", []).append(n)
    return out


def to_quarto(trace: SessionTrace) -> str:
    """Rend une SessionTrace en document Quarto (.qmd) déterministe."""
    results = _results_by_call(trace)
    parts = [_frontmatter(trace)]
    parts.append(
        f"Session `{trace.session_id}` — modèle **{trace.model}** — "
        f"statut **{trace.status}**."
    )
    for n in trace.nodes:
        if n.kind in ("session_root", "tool_result", "turn_result"):
            continue
        if n.kind == "thinking":
            text = " ".join(str(n.content.get("text", "")).split())
            parts.append(
                f'::: {{.callout-note collapse="true"}}\n## Raisonnement\n{text}\n:::'
            )
        elif n.kind == "tool_call":
            name = n.content.get("name", "?")
            inp = json.dumps(n.content.get("input", {}), ensure_ascii=False, indent=2)
            body = [f"### 🔧 `{name}`", _fence("json", inp)]
            for r in results.get(n.id, []):
                body.append("**Résultat :**")
                body.append(_fence("json", _result_json(r.content.get("content"))))
            parts.append("\n\n".join(body))
        elif n.kind == "observation":
            statut = str(n.meta.get("statut", ""))
            kind = _CALLOUT.get(statut, "note")
            pfx = _IDPFX.get(statut, "nte")
            conf = n.meta.get("confiance")
            title = statut + (f" · confiance {conf}" if conf else "")
            block = [
                f"::: {{#{pfx}-{n.seq} .callout-{kind}}}",
                f"## {title}",
                str(n.content.get("claim", "")),
            ]
            note = n.content.get("note")
            if note:
                block.append(f"\n*{note}*")
            block.append(":::")
            parts.append("\n".join(block))
        else:
            parts.append(f"<!-- nœud non rendu : kind={n.kind} -->")
    m = trace.meta
    foot: list[str] = []
    if m.get("num_turns") is not None:
        foot.append(f"tours : {m['num_turns']}")
    if m.get("total_cost_usd") is not None:
        foot.append(f"coût : ${m['total_cost_usd']}")
    if m.get("terminal_reason"):
        foot.append(f"fin : {m['terminal_reason']}")
    if m.get("aborted_reason"):
        foot.append(f"interruption : {m['aborted_reason']}")
    if foot:
        parts.append("---\n\n*" + " · ".join(foot) + "*")
    return "\n\n".join(parts) + "\n"


def render_html(qmd_path: str | Path) -> Path | None:
    """Rend le .qmd en HTML via le CLI quarto (best-effort ; None si indisponible)."""
    qmd = Path(qmd_path)
    try:
        subprocess.run(
            ["quarto", "render", str(qmd), "--to", "html"],
            check=True,
            capture_output=True,
        )
    except FileNotFoundError:
        logger.warning("quarto introuvable : .qmd produit, HTML non rendu (%s)", qmd)
        return None
    except subprocess.CalledProcessError as e:
        logger.warning("quarto render a échoué : %s", e.stderr.decode(errors="replace"))
        return None
    return qmd.with_suffix(".html")
