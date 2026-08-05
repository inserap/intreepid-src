"""Projection d'une trace de session en mesures de temps et de coût.

Logique PURE (aucun I/O) : la mesure n'est pas un organe de télémétrie, c'est une
LECTURE de ce que le greffier capture déjà — nœuds horodatés et paires
``tool_call``/``tool_result``. Agnostique du rôle : ne dispatche que sur les kinds
du socle (``turn_result``, ``tool_call``, ``tool_result``), jamais sur un
vocabulaire métier. Le coût est donné PAR TOUR : le SDK ne le ventile pas par
outil, et l'inventer serait faux.

Une limite à connaître : plusieurs ``ToolUseBlock`` d'un même message ont des
horodatages VOISINS — le store date nœud par nœud, jamais par lot — donc leurs
durées recouvrent le même intervalle réel. ``total_tool_measured_ms`` en donne
l'UNION, pas la somme.

Interprétation du temps hors API (``non_api_ms``) : c'est la soustraction
``duration_ms − duration_api_ms``. L'orchestrateur relance un processus CLI et
amorce un serveur MCP en sous-processus à CHAQUE tour : ce démarrage de processus
et cet amorçage tombent entièrement dans ce chiffre. Il N'EST PAS assimilable au
coût des outils — ``total_tool_measured_ms`` mesure ceux-ci séparément via
l'appariement des horodatages call/result.

L'attribution de la sortie (``prose_chars``/``thinking_chars``) est donnée en
CARACTÈRES, pas en tokens : le SDK ne ventile pas ``output_tokens``, et inventer
une conversion serait faux. Elle répond à « prose ou thinking ? », pas à
« combien de tokens exactement ? ».
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
    cache_read_tokens: int | None
    cache_creation_tokens: int | None


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
    prose_chars: int | None
    thinking_chars: int | None
    degraded: bool = False


def _int_or_none(value: Any) -> int | None:
    """Coerce en int une valeur numérique ; None sinon. bool exclu à dessein."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return int(value)


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
        cache_read_tokens=_int_or_none(usage.get("cache_read_input_tokens")),
        cache_creation_tokens=_int_or_none(usage.get("cache_creation_input_tokens")),
    )


def _sum_optional(values: list[float | int | None]) -> float | None:
    """Somme les valeurs connues ; None si aucune ne l'est (inconnu ≠ zéro)."""
    known = [v for v in values if v is not None]
    return sum(known) if known else None


def _duree_union(intervalles: list[tuple[float, float]]) -> float | None:
    """Durée couverte par l'union d'intervalles (secondes epoch) en ms.

    Des appels concurrents se recouvrent : leur coût réel en temps est l'union,
    non la somme. Aucun intervalle connu => None (inconnu, pas zéro).
    """
    if not intervalles:
        return None
    total = 0.0
    fin_courante: float | None = None
    debut_courant = 0.0
    for debut, fin in sorted(intervalles):
        if fin_courante is None:
            debut_courant, fin_courante = debut, fin
        elif debut <= fin_courante:
            fin_courante = max(fin_courante, fin)
        else:
            total += fin_courante - debut_courant
            debut_courant, fin_courante = debut, fin
    if fin_courante is not None:
        total += fin_courante - debut_courant
    return total * 1000


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
                cache_read_tokens=None,
                cache_creation_tokens=None,
            )
        ]
    # Appariement par PARENTÉ : le builder parente chaque tool_result à son
    # tool_call (repli sur la racine si l'appel est inconnu). Une seule
    # mécanique d'appariement dans le code, celle de render.py.
    resultats: dict[str, TraceNode] = {}
    ids_appels = {n.id for n in trace.nodes if n.kind == "tool_call"}
    for n in trace.nodes:
        # `pid` extrait avant le test : `parent_id` est `str | None`, et compter sur
        # le narrowing par appartenance à un `set[str]` serait un pari sur pyright.
        pid = n.parent_id
        if n.kind == "tool_result" and pid is not None and pid in ids_appels:
            resultats[pid] = n
    tools: list[ToolMetrics] = []
    calls_by_tool: dict[str, int] = {}
    intervalles: list[tuple[float, float]] = []
    for node in trace.nodes:
        if node.kind != "tool_call":
            continue
        nom = str(node.content.get("name", "?"))
        calls_by_tool[nom] = calls_by_tool.get(nom, 0) + 1
        res = resultats.get(node.id)
        duree: float | None = None
        erreur: bool | None = None
        if res is not None:
            erreur = res.content.get("is_error")
            if node.ts is not None and res.ts is not None:
                debut = node.ts.timestamp()
                fin = res.ts.timestamp()
                duree = (fin - debut) * 1000
                intervalles.append((debut, fin))
        tools.append(ToolMetrics(name=nom, duration_ms=duree, is_error=erreur))

    # Totaux : None quand aucun composant n'est connu (inconnu ≠ zéro)
    total_cost = _sum_optional([t.cost_usd for t in turns])
    total_api = _sum_optional([t.duration_api_ms for t in turns])
    total_non_api = _sum_optional([t.non_api_ms for t in turns])

    # UNION des intervalles, pas somme : plusieurs appels d'un même message ont
    # des horodatages VOISINS (le store date nœud par nœud, jamais par lot),
    # donc leurs durées recouvrent le même intervalle réel. Les sommer
    # multipliait ce temps par le nombre d'appels parallèles.
    total_tool_measured: float | None = _duree_union(intervalles)

    # Attribution de la SORTIE, en totaux de session : agent_turn est enregistré
    # APRÈS son turn_result, donc un découpage par tour supposerait un ordre.
    # None (et non 0) quand le kind est absent : une trace d'analyste one-shot
    # n'a pas de agent_turn, sa prose n'est pas inconnue à zéro.
    prose = [
        len(str(n.content.get("text", "")))
        for n in trace.nodes
        if n.kind == "agent_turn"
    ]
    pensee = [
        len(str(n.content.get("text", ""))) for n in trace.nodes if n.kind == "thinking"
    ]

    horodates = [n.ts for n in trace.nodes if n.ts is not None]
    return SessionMetrics(
        session_id=trace.session_id,
        status=trace.status,
        turns=turns,
        tools=tools,
        wall_ms=(
            (max(horodates) - min(horodates)).total_seconds() * 1000
            # deux instants minimum : un seul ne fait pas une durée de zéro
            if len(horodates) >= 2
            else None
        ),
        total_cost_usd=total_cost,
        total_api_ms=int(total_api) if total_api is not None else None,
        total_non_api_ms=int(total_non_api) if total_non_api is not None else None,
        total_tool_measured_ms=total_tool_measured,
        calls_by_tool=calls_by_tool,
        prose_chars=sum(prose) if prose else None,
        thinking_chars=sum(pensee) if pensee else None,
        degraded=degraded,
    )


def _s(ms: float | None) -> str:
    return "?" if ms is None else f"{ms / 1000:.1f}s"


def _cout(v: float | None, n_inconnus: int = 0) -> str:
    if v is None:
        return "?"
    if n_inconnus:
        return f"≥ {v:.4f} USD ({n_inconnus} tour(s) sans coût)"
    return f"{v:.4f} USD"


def render_metrics(m: SessionMetrics) -> str:
    """Rendu texte des mesures (même esprit que ``render.py``)."""
    # Calcul du nombre de tours sans coût (pour le minorant)
    tours_sans_cout = sum(1 for t in m.turns if t.cost_usd is None) if m.turns else 0

    lignes = [
        f"Session {m.session_id} [{m.status}]",
        f"  bout en bout : {_s(m.wall_ms)}"
        f" · coût total : {_cout(m.total_cost_usd, tours_sans_cout)}"
        f" · {'?' if m.degraded else len(m.turns)} tour(s)",
    ]
    if m.degraded:
        lignes.append(
            "  (mesure dégradée : trace antérieure à l'instrumentation —"
            " coût du dernier tour connu (minorant) ;"
            " durées et détail par tour indisponibles)"
        )
    else:
        if m.total_api_ms is not None or m.total_non_api_ms is not None:
            lignes.append(
                f"  dont API : {_s(m.total_api_ms)}"
                f" · hors API (horloge SDK) : {_s(m.total_non_api_ms)}"
            )
        if m.total_tool_measured_ms is not None:
            # PAS soustractible du hors-API : autre horloge (horodatages du
            # greffier, posés à l'observation du message). Les deux chiffres
            # cohabitent, ils ne s'expliquent pas l'un par l'autre.
            lignes.append(
                f"    outils mesurés (horodatages greffier) :"
                f" {_s(m.total_tool_measured_ms)}"
            )
        if m.turns:
            lignes.append("  Tours :")
            for t in m.turns:
                in_tok = t.input_tokens if t.input_tokens is not None else "?"
                out_tok = t.output_tokens if t.output_tokens is not None else "?"
                cache_r = t.cache_read_tokens
                cache_c = t.cache_creation_tokens
                cache = (
                    "cache ?"
                    if cache_r is None and cache_c is None
                    else f"cache {cache_r if cache_r is not None else '?'} lus"
                    f" / {cache_c if cache_c is not None else '?'} créés"
                )
                lignes.append(
                    f"    #{t.index} {_s(t.duration_ms)}"
                    f" (API {_s(t.duration_api_ms)}, hors API {_s(t.non_api_ms)})"
                    f" · {_cout(t.cost_usd)}"
                    f" · in {in_tok} ({cache}) / out {out_tok} tokens"
                )
    if m.prose_chars is not None or m.thinking_chars is not None:
        prose = "?" if m.prose_chars is None else str(m.prose_chars)
        pensee = "?" if m.thinking_chars is None else str(m.thinking_chars)
        lignes.append(
            f"  Sortie écrite : prose {prose} car. · thinking {pensee} car."
            " (caractères, pas tokens)"
        )
    if m.tools:
        lignes.append("  Appels d'outil :")
        for outil in m.tools:
            if outil.is_error is None:
                marque = " [sans résultat]"  # non apparié ≠ réussi
            elif outil.is_error:
                marque = " [erreur]"
            else:
                marque = ""
            lignes.append(f"    {outil.name} : {_s(outil.duration_ms)}{marque}")
        decompte = ", ".join(f"{nom} × {n}" for nom, n in m.calls_by_tool.items())
        lignes.append(f"  Décompte : {decompte}")
    return "\n".join(lignes)
