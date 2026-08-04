"""Projection d'une trace de session en mesures de temps et de coût.

Logique PURE (aucun I/O) : la mesure n'est pas un organe de télémétrie, c'est une
LECTURE de ce que le greffier capture déjà — nœuds horodatés et paires
``tool_call``/``tool_result``. Agnostique du rôle : ne dispatche que sur les kinds
du socle (``turn_result``, ``tool_call``, ``tool_result``), jamais sur un
vocabulaire métier. Le coût est donné PAR TOUR : le SDK ne le ventile pas par
outil, et l'inventer serait faux.

Deux limites à connaître. (1) Les ``ts`` d'une trace relue sont des datetime NAÏFS
(DuckDB), ceux construits en test sont AWARE : ne jamais comparer les deux mondes,
les écarts internes à une trace restent justes (piège DST sur une session à cheval
sur un changement d'heure). (2) Plusieurs ``ToolUseBlock`` d'un même message
partagent l'instant d'observation : leurs durées valent alors celle du lot.
"""

from dataclasses import dataclass
from typing import Any

from intreepid.scribe.trace import SessionTrace, TraceNode


@dataclass(frozen=True)
class TurnMetrics:
    """Mesures d'un tour d'agent (un aller-retour complet du SDK)."""

    index: int
    duration_ms: int | None
    duration_api_ms: int | None
    tool_ms: int | None
    cost_usd: float | None
    input_tokens: int | None
    output_tokens: int | None


@dataclass(frozen=True)
class ToolMetrics:
    """Mesures d'un appel d'outil (durée = écart des horodatages call/result)."""

    name: str
    duration_ms: float | None
    is_error: bool | None


@dataclass(frozen=True)
class SessionMetrics:
    """Agrégat mesuré d'une session."""

    session_id: str
    status: str
    turns: list[TurnMetrics]
    tools: list[ToolMetrics]
    wall_ms: float | None
    total_cost_usd: float
    total_api_ms: int
    total_tool_ms: int
    calls_by_tool: dict[str, int]
    degraded: bool = False


def _int_or_none(value: Any) -> int | None:
    return value if isinstance(value, int) else None


def _turn(index: int, node: TraceNode) -> TurnMetrics:
    duree = _int_or_none(node.content.get("duration_ms"))
    api = _int_or_none(node.content.get("duration_api_ms"))
    usage = node.content.get("usage") or {}
    cout = node.content.get("total_cost_usd")
    return TurnMetrics(
        index=index,
        duration_ms=duree,
        duration_api_ms=api,
        tool_ms=(duree - api) if (duree is not None and api is not None) else None,
        cost_usd=cout if isinstance(cout, (int, float)) else None,
        input_tokens=_int_or_none(usage.get("input_tokens")),
        output_tokens=_int_or_none(usage.get("output_tokens")),
    )


def summarize(trace: SessionTrace) -> SessionMetrics:
    """Projette une trace en mesures. Tolérant : un `ts` absent => durée inconnue."""
    turns = [
        _turn(i, n)
        for i, n in enumerate(
            (n for n in trace.nodes if n.kind == "turn_result"), start=1
        )
    ]
    degraded = False
    if not turns and trace.meta.get("total_cost_usd") is not None:
        # Trace antérieure au nœud turn_result : la méta de session scellée porte
        # encore le coût. Mesure DÉGRADÉE (aucune durée) plutôt que fausse à zéro.
        cout_meta = trace.meta.get("total_cost_usd")
        degraded = True
        turns = [
            TurnMetrics(
                index=1,
                duration_ms=None,
                duration_api_ms=None,
                tool_ms=None,
                cost_usd=cout_meta if isinstance(cout_meta, (int, float)) else None,
                input_tokens=None,
                output_tokens=None,
            )
        ]
    resultats = {
        str(n.meta["tool_use_id"]): n
        for n in trace.nodes
        if n.kind == "tool_result" and n.meta.get("tool_use_id") is not None
    }
    tools: list[ToolMetrics] = []
    calls_by_tool: dict[str, int] = {}
    for node in trace.nodes:
        if node.kind != "tool_call":
            continue
        nom = str(node.content.get("name", "?"))
        calls_by_tool[nom] = calls_by_tool.get(nom, 0) + 1
        # id absent des deux côtés => pas d'appariement (sinon "None" == "None")
        tid = node.meta.get("tool_use_id")
        res = resultats.get(str(tid)) if tid is not None else None
        duree: float | None = None
        erreur: bool | None = None
        if res is not None:
            erreur = res.content.get("is_error")
            if node.ts is not None and res.ts is not None:
                duree = (res.ts - node.ts).total_seconds() * 1000
        tools.append(ToolMetrics(name=nom, duration_ms=duree, is_error=erreur))
    horodates = [n.ts for n in trace.nodes if n.ts is not None]
    return SessionMetrics(
        session_id=trace.session_id,
        status=trace.status,
        turns=turns,
        tools=tools,
        wall_ms=(
            (max(horodates) - min(horodates)).total_seconds() * 1000
            if horodates
            else None
        ),
        total_cost_usd=sum((t.cost_usd or 0.0 for t in turns), 0.0),
        total_api_ms=sum(t.duration_api_ms or 0 for t in turns),
        total_tool_ms=sum(t.tool_ms or 0 for t in turns),
        calls_by_tool=calls_by_tool,
        degraded=degraded,
    )


def _s(ms: float | None) -> str:
    return "?" if ms is None else f"{ms / 1000:.1f}s"


def render_metrics(m: SessionMetrics) -> str:
    """Rendu texte des mesures (même esprit que ``render.py``)."""
    # En mode dégradé, les totaux de durée et le décompte de tours seraient FAUX
    # (0.0s, « 1 tour ») : on affiche « ? » plutôt qu'un chiffre inventé.
    lignes = [
        f"Session {m.session_id} [{m.status}]",
        f"  bout en bout : {_s(m.wall_ms)}"
        f" · coût total : {m.total_cost_usd:.4f} USD"
        f" · {'?' if m.degraded else len(m.turns)} tour(s)",
    ]
    if m.degraded:
        lignes.append(
            "  (mesure dégradée : trace antérieure à l'instrumentation — coût lu"
            " dans la méta de session ; durées et détail par tour indisponibles)"
        )
    else:
        lignes.append(
            f"  dont API : {_s(m.total_api_ms)} · hors LLM : {_s(m.total_tool_ms)}"
        )
        if m.turns:
            lignes.append("  Tours :")
            for t in m.turns:
                lignes.append(
                    f"    #{t.index} {_s(t.duration_ms)}"
                    f" (API {_s(t.duration_api_ms)}, hors LLM {_s(t.tool_ms)})"
                    f" · {t.cost_usd if t.cost_usd is not None else '?'} USD"
                    f" · in {t.input_tokens} / out {t.output_tokens} tokens"
                )
    if m.tools:
        lignes.append("  Appels d'outil :")
        for outil in m.tools:
            marque = " [erreur]" if outil.is_error else ""
            lignes.append(f"    {outil.name} : {_s(outil.duration_ms)}{marque}")
        lignes.append(f"  Décompte : {m.calls_by_tool}")
    return "\n".join(lignes)
