"""Accumulation du brouillon de fiche du curateur, hors de l'agent (Q-0023).

L'agent est sans état entre les tours. Plutôt que de lui faire ré-émettre la fiche
entière à chaque tour (79 % de sa sortie au gate du 06/08), il n'émet que ce qu'il
vient de trancher ou de corriger ; l'application accumule et lui rend l'inventaire.

Deux garde-fous : la fusion est GÉNÉRIQUE — dernière écriture gagne, par clé, aucune
sémantique métier, la valeur d'une colonne reste un objet opaque jamais inspecté ; et
les deux fonctions sont PURES — aucune I/O, aucun argument muté.
"""

from typing import Any


def merge_delta(
    acc: dict[str, Any] | None, delta: dict[str, Any] | None
) -> dict[str, Any]:
    """Fusionne un delta dans l'accumulateur et retourne un NOUVEAU dict.

    Les clés de haut niveau sont écrasées ; `columns` est fusionné entrée par
    entrée et jamais remplacé en bloc — sinon une colonne tranchée au tour 2
    disparaîtrait au tour 3.
    """
    out: dict[str, Any] = dict(acc or {})
    if not delta:
        return out
    colonnes: dict[str, Any] = dict(out.get("columns") or {})
    for cle, valeur in delta.items():
        if cle == "columns":
            # non-dict => ignoré (repli tolérant, cf. `turn.py`) : un modèle qui
            # envoie une liste ne doit pas effacer ce qui est déjà acquis.
            if isinstance(valeur, dict):
                colonnes.update(valeur)
            continue
        out[cle] = valeur
    if colonnes or "columns" in out:
        out["columns"] = colonnes
    return out


def inventory_line(acc: dict[str, Any] | None) -> str:
    """Rend la ligne d'état de ce que l'application détient pour l'agent.

    Elle passe par `build_prompt` (canal application-owned), JAMAIS par la valeur
    retournée par `next_input` — l'orchestrateur grave celle-ci en nœud
    `human_turn` / `actor: "human"`, et on inscrirait dans une trace probante des
    mots que l'humain n'a pas dits.
    """
    colonnes = sorted((acc or {}).get("columns") or {})
    if not colonnes:
        return "Brouillon conservé par l'application : aucune colonne documentée."
    return (
        f"Brouillon conservé par l'application : {len(colonnes)} colonne(s)"
        f" documentée(s) — {', '.join(colonnes)}."
    )
