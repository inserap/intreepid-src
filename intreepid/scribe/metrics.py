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

Interprétation du temps hors API (``non_api_ms``) : c'est la soustraction
``duration_ms − duration_api_ms``. L'orchestrateur relance un processus CLI et
amorce un serveur MCP en sous-processus à CHAQUE tour : ce démarrage de processus
et cet amorçage tombent entièrement dans ce chiffre. Il N'EST PAS assimilable au
coût des outils — ``total_tool_measured_ms`` mesure ceux-ci séparément via
l'appariement des horodatages call/result.
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
    non_api_ms: int | None
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
    total_cost_usd: float | None
    total_api_ms: int | None
    total_non_api_ms: int | None
    total_tool_measured_ms: float | None
    calls_by_tool: dict[str, int]
    degraded: bool = False
    totals_partial: bool = False


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
        non_api_ms=(duree - api) if (duree is not None and api is not None) else None,
        cost_usd=cout if isinstance(cout, (int, float)) else None,
        input_tokens=_int_or_none(usage.get("input_tokens")),
        output_tokens=_int_or_none(usage.get("output_tokens")),
    )


def _sum_optional(values: list[float | int | None]) -> tuple[float | None, bool]:
    """Somme les valeurs connues ; renvoie (None, False) si aucune, (somme, partiel)."""
    known = [v for v in values if v is not None]
    if not known:
        return None, False
    partial = len(known) < len(values)
    return sum(known), partial


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
        # encore le coût du dernier tour connu. Mesure DÉGRADÉE (aucune durée)
        # plutôt que fausse à zéro.
        cout_meta = trace.meta.get("total_cost_usd")
        degraded = True
        turns = [
            TurnMetrics(
                index=1,
                duration_ms=None,
                duration_api_ms=None,
                non_api_ms=None,
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

    # Totaux : None quand aucun composant n'est connu ; partiel si mélangé
    total_cost, cost_partial = _sum_optional([t.cost_usd for t in turns])
    total_api, api_partial = _sum_optional([t.duration_api_ms for t in turns])
    total_non_api, non_api_partial = _sum_optional([t.non_api_ms for t in turns])
    totals_partial = cost_partial or api_partial or non_api_partial

    # Outils mesurés : somme des durées d'appel effectivement appariées
    tool_durees = [t.duration_ms for t in tools if t.duration_ms is not None]
    total_tool_measured: float | None = sum(tool_durees) if tool_durees else None

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
        total_cost_usd=total_cost,
        total_api_ms=int(total_api) if total_api is not None else None,
        total_non_api_ms=int(total_non_api) if total_non_api is not None else None,
        total_tool_measured_ms=total_tool_measured,
        calls_by_tool=calls_by_tool,
        degraded=degraded,
        totals_partial=totals_partial,
    )


def _s(ms: float | None) -> str:
    return "?" if ms is None else f"{ms / 1000:.1f}s"


def _cout(v: float | None, partial: bool = False, n_inconnus: int = 0) -> str:
    if v is None:
        return "?"
    if partial and n_inconnus:
        return f"≥ {v:.4f} USD ({n_inconnus} tour(s) sans coût)"
    return f"{v:.4f} USD"


def render_metrics(m: SessionMetrics) -> str:
    """Rendu texte des mesures (même esprit que ``render.py``)."""
    # Calcul du nombre de tours sans coût (pour le minorant)
    tours_sans_cout = sum(1 for t in m.turns if t.cost_usd is None) if m.turns else 0

    lignes = [
        f"Session {m.session_id} [{m.status}]",
        f"  bout en bout : {_s(m.wall_ms)}"
        f" · coût total : {_cout(m.total_cost_usd, m.totals_partial, tours_sans_cout)}"
        f" · {'?' if m.degraded else len(m.turns)} tour(s)",
    ]
    if m.degraded:
        lignes.append(
            "  (mesure dégradée : trace antérieure à l'instrumentation —"
            " coût du dernier tour connu (minorant) ;"
            " durées et détail par tour indisponibles)"
        )
    else:
        # Ligne de durées : uniquement si au moins un total est connu
        api_s = _s(m.total_api_ms)
        non_api_s = _s(m.total_non_api_ms)
        if m.total_api_ms is not None or m.total_non_api_ms is not None:
            ligne_durees = (
                f"  dont API : {api_s} · hors API (sur tours mesurés) : {non_api_s}"
            )
            if m.total_non_api_ms is not None and m.total_tool_measured_ms is not None:
                reste_ms = m.total_non_api_ms - m.total_tool_measured_ms
                ligne_durees += (
                    f"\n    dont outils mesurés : {_s(m.total_tool_measured_ms)}"
                    f" · démarrage processus/amorçage : {_s(reste_ms)}"
                )
            elif m.total_tool_measured_ms is not None:
                ligne_durees += (
                    f"\n    dont outils mesurés : {_s(m.total_tool_measured_ms)}"
                )
            lignes.append(ligne_durees)
        if m.turns:
            lignes.append("  Tours :")
            for t in m.turns:
                in_tok = t.input_tokens if t.input_tokens is not None else "?"
                out_tok = t.output_tokens if t.output_tokens is not None else "?"
                lignes.append(
                    f"    #{t.index} {_s(t.duration_ms)}"
                    f" (API {_s(t.duration_api_ms)}, hors API {_s(t.non_api_ms)})"
                    f" · {t.cost_usd if t.cost_usd is not None else '?'} USD"
                    f" · in {in_tok} / out {out_tok} tokens"
                )
    if m.tools:
        lignes.append("  Appels d'outil :")
        for outil in m.tools:
            marque = " [erreur]" if outil.is_error else ""
            lignes.append(f"    {outil.name} : {_s(outil.duration_ms)}{marque}")
        lignes.append(f"  Décompte : {m.calls_by_tool}")
    return "\n".join(lignes)
