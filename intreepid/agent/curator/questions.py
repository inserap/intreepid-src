"""Canal des questions du curateur : fusionner, rendre, attacher les réponses.

L'agent émet TOUTES ses questions en un tour, dans son bloc de métadonnées
(brique #11). L'application les sert une par une SANS aucun appel LLM : c'est là
qu'est le gain de temps, les attentes intermédiaires disparaissant.

Trois fonctions PURES — aucune I/O, aucun argument muté. La valeur d'une question
reste un objet quasi opaque : on n'en lit que `n`, `options` et les champs de
texte affichés, jamais une sémantique métier.
"""

from typing import Any

_INCONNU = object()


def merge_questions(
    acc: list[dict[str, Any]] | None, delta: list[dict[str, Any]] | None
) -> list[dict[str, Any]]:
    """Fusionne un lot de questions dans l'accumulateur, par numéro.

    Dernière écriture gagne — même sémantique que `columns` dans `merge_delta` :
    un tour supplémentaire peut créer une question NEUVE ou RÉVISER une question
    existante, et ce tour n'altère que cet artefact. Une entrée sans numéro
    n'est pas jetée : elle est ajoutée en fin, faute de clé de fusion.
    """
    out: list[dict[str, Any]] = [dict(q) for q in (acc or []) if isinstance(q, dict)]
    if not delta:
        return out
    index = {q.get("n"): i for i, q in enumerate(out) if q.get("n") is not None}
    for entree in delta:
        if not isinstance(entree, dict):
            continue  # repli tolérant, cf. turn.py : ne jamais effacer l'acquis
        numero = entree.get("n", _INCONNU)
        if numero is not _INCONNU and numero in index:
            out[index[numero]] = dict(entree)
            continue
        if numero is not _INCONNU and numero is not None:
            index[numero] = len(out)
        out.append(dict(entree))
    return out


def render_question(q: dict[str, Any], *, position: int, total: int) -> str:
    """Assemble une question structurée en texte lisible par un humain.

    « Une question qu'il ne comprend pas est une question perdue » : les champs
    sont rédigés par l'agent en phrases complètes, cette fonction ne fait que
    les ordonner. `position`/`total` sont la PROGRESSION affichée ; `n` est le
    numéro logique de l'agent, auquel ses verrous renvoient. Les deux DIFFÈRENT
    dès le second tour — l'agent numérote en continu sur toute la conversation —
    et l'écran doit donc porter les DEUX : sans le `n`, l'agent dit « répondez
    5a » quand l'écran annonce « Question 1/3 ». On ne renumérote jamais à sa
    place.
    """
    lignes = [f"\n── Question {position}/{total}" + _numero(q) + _sur(q) + " ──"]
    for champ in ("constat", "enjeu", "pourquoi"):
        valeur = q.get(champ)
        if isinstance(valeur, str) and valeur.strip():
            lignes.append(valeur.strip())
    options = q.get("options")
    if isinstance(options, dict):
        for cle, libelle in options.items():
            lignes.append(f"  ({cle}) {libelle}")
    penchant = q.get("penchant")
    if isinstance(penchant, str) and penchant.strip():
        lignes.append(f"  je penche pour ({penchant.strip()})")
    lignes.append("  ou « je ne sais pas » — réponse pleinement valide")
    return "\n".join(lignes)


def _numero(q: dict[str, Any]) -> str:
    """Rend le numéro de l'agent, ou rien. `bool` exclu à dessein.

    `isinstance(True, int)` est vrai en Python : sans cette garde, un `n: true`
    afficherait « (n° True) ». Même précaution que `scribe/metrics.py::_int_or_none`.
    """
    numero = q.get("n")
    if isinstance(numero, bool):
        return ""
    return f" (n° {numero})" if isinstance(numero, (int, float, str)) else ""


def _sur(q: dict[str, Any]) -> str:
    colonne = q.get("colonne")
    return f", sur {colonne}" if isinstance(colonne, str) and colonne else ""


def attach_answers(
    questions: list[dict[str, Any]], answers: dict[Any, str]
) -> list[dict[str, Any]]:
    """Rend une copie des questions portant la réponse humaine, ou `None`.

    `None` est un fait, pas un trou : une question restée sans réponse devient un
    point non tranché de la fiche (P6 — le doute lui-même est une connaissance
    sur la donnée).
    """
    out: list[dict[str, Any]] = []
    for q in questions:
        copie = dict(q)
        copie["reponse"] = answers.get(q.get("n"))
        out.append(copie)
    return out
