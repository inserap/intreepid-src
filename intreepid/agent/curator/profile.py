"""Profil de l'agent curateur : isolation P2/P3, conversation, écriture de fiche.

2ᵉ profil réel de l'orchestrateur générique (ADR-0009, Q-0021). Multi-tours :
`next_input` lit la réponse humaine (None => validé) et ACCUMULE le delta de fiche
du tour (Q-0023 — l'agent n'émet que ses colonnes neuves, cf. `draft.py`) ;
`build_prompt` sérialise l'historique (charte = system_prompt byte-stable) et y
ajoute l'inventaire du brouillon ; `on_result` écrit l'ACCUMULATEUR et grave le
nœud `curation_validated` (hash). La fiche reste un dict quasi opaque : Python n'en
connaît que la clé `columns`, les noms de colonnes, et `dataset` — lu par `_on_result`
pour nommer le fichier écrit, lecture ANTÉRIEURE à cette slice.
"""

import re
from pathlib import Path
from typing import Any

from claude_agent_sdk import ClaudeAgentOptions

from intreepid.agent.curator.draft import inventory_line, merge_delta
from intreepid.agent.curator.fiche_writer import write_fiche, write_questions
from intreepid.agent.curator.questions import (
    attach_answers,
    merge_questions,
    render_question,
)
from intreepid.agent.curator.surface import Surface
from intreepid.agent.curator.turn import CuratorTurn, parse_curator_turn
from intreepid.agent.profile import Profile
from intreepid.scribe.store import Scribe

CHARTER = (Path(__file__).parent / "charter.md").read_text(encoding="utf-8")

_MCP_TOOLS = ["mcp__intreepid__profile_raw"]

_DISALLOWED = [
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
]

_VALIDATE_WORDS = {"o", "oui", "ok", "valide", "valider", "valid"}

# Confirmer un ENVOI de réponses n'est pas valider une FICHE : deux vocabulaires
# distincts, pour qu'un ajout à l'un ne change pas le sens de l'autre.
_SEND_WORDS = {"o", "oui", "ok", "envoie", "envoyer"}


def build_options(
    model: str | None = None, *, thinking: bool = False
) -> ClaudeAgentOptions:
    """Options du curateur avec isolation maximale (P2/P3), calquées sur l'analyste."""
    return ClaudeAgentOptions(
        model=model,
        allowed_tools=_MCP_TOOLS,
        disallowed_tools=_DISALLOWED,
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


def curator_profile(
    dataset_path: str,
    catalog_dir: str | Path,
    surface: Surface | None = None,
) -> Profile:
    surface = surface or Surface()
    catalog_dir = Path(catalog_dir)

    # Brouillon tenu par l'APPLICATION (Q-0023) : l'agent n'émet que ses deltas,
    # et c'est ce dict-ci qui porte la fiche complète d'un tour à l'autre.
    brouillon: dict[str, Any] = {}
    # Les questions, et les réponses humaines associées par numéro. Elles ne vont
    # PAS dans la fiche : celle-ci est relue verbatim par un LLM à chaque analyse.
    questions: list[dict[str, Any]] = []
    reponses: dict[Any, str] = {}

    def _echo(q: dict[str, Any], reponse: str) -> None:
        """Rappelle le libellé de l'option choisie, sans deviner.

        Le verrou intermédiaire disparaît en phase 2 (aucun appel LLM entre deux
        questions) : cet écho est la garde minimale contre la faute de frappe.
        Il n'affiche QUE si la réponse dépouillée est exactement une clé
        d'option — aucune heuristique, aucune interprétation.
        """
        options = q.get("options")
        if not isinstance(options, dict):
            return
        cle = re.sub(r"[^a-z]", "", reponse.lower())
        libelle = options.get(cle)
        if isinstance(libelle, str):
            surface.show(f"  → ({cle}) {libelle}")

    def _collecter(posees: list[dict[str, Any]]) -> str:
        """Sert les questions une par une et rend les réponses BRUTES.

        Aucun appel LLM ici : c'est tout le gain de la brique #11. Le retour est
        gravé en nœud `human_turn` / `actor: "human"`, donc il ne porte que des
        mots de l'humain — l'association se fait par l'ORDRE de service, jamais
        par un préfixe ajouté par l'application (I-E).
        """
        collectees: list[str] = []
        total = len(posees)
        i = 0
        while i < total:
            surface.show(render_question(posees[i], position=i + 1, total=total))
            reponse = surface.ask()
            if reponse.strip():
                collectees.append(reponse)
                numero = posees[i].get("n")
                if numero is not None:
                    # SANS cette garde, deux questions sans `n` partagent la clé
                    # None : la seconde réponse écraserait la première, et
                    # l'artefact de provenance attribuerait à la question 1 une
                    # réponse que l'humain a donnée pour une autre. Un artefact
                    # dont la valeur déclarée est la provenance ne mentira pas :
                    # sans numéro, `reponse: null` — la parole humaine reste dans
                    # la trace, nœud `human_turn`.
                    reponses[numero] = reponse
                _echo(posees[i], reponse)
                i += 1
                continue
            if not collectees:
                surface.show("\n[Aucune réponse collectée : rien à envoyer.]")
                continue
            surface.show(
                f"\n[Envoyer maintenant ? {len(collectees)} réponse(s) collectée(s),"
                f" questions {i + 1} à {total} sans réponse."
                " 'o' = envoyer ; toute autre saisie repose la question.]"
            )
            # Vocabulaire DÉDIÉ, pas `_VALIDATE_WORDS` : celui-là valide une
            # FICHE. « valide », « ok » y signifieraient « envoie », et un jour
            # quelqu'un ajouterait un mot à l'un en cassant l'autre.
            if surface.ask().strip().lower() in _SEND_WORDS:
                break
        return "\n".join(collectees)

    def _next_input(result: CuratorTurn) -> str | None:
        nonlocal brouillon, questions
        brouillon = merge_delta(brouillon, result.fiche_delta)
        questions = merge_questions(questions, result.questions)
        surface.show(result.message or "[tour vide — demande-lui de reformuler]")
        if result.proposes_completion:
            if not brouillon.get("columns"):
                # La garde porte sur l'ACCUMULATEUR, plus sur le delta du tour :
                # un dernier tour sans nouvelle colonne est désormais le cas
                # normal. Valider avec un accumulateur vide perdrait la session.
                # On ne relance PAS tout seul : une relance automatique boucle
                # sans borne et s'inscrirait dans la trace comme un tour humain.
                surface.show(
                    "\n[Aucune colonne transmise — rien ne serait écrit en l'état."
                    " Demande-lui de transmettre la fiche, ou Ctrl+C.]"
                )
                return surface.ask()
            surface.show("\n[Valider ? 'o' = valider, sinon tape une correction]")
            reply = surface.ask()
            if reply.strip().lower() in _VALIDATE_WORDS:
                return None  # validé => terminal
            return reply
        # Filtre AVANT de servir, mêmes règles que `merge_questions` : une liste
        # dont les entrées ne sont pas des dicts (l'agent écrivant ses questions en
        # clair dans le tableau) ferait lever `AttributeError` dans `_collecter` et
        # perdrait la séance ENTIÈRE — `on_result` ne serait jamais atteint, aucune
        # fiche ne serait écrite. Le design § 9 promet la tolérance sur ce chemin.
        posees = [q for q in (result.questions or []) if isinstance(q, dict)]
        if posees:
            return _collecter(posees)
        return surface.ask()

    def _on_result(scribe: Scribe | None, result: CuratorTurn) -> None:
        # MÊME condition que la garde de `_next_input` : deux formulations
        # différentes ("brouillon vide" vs "pas de colonnes") laisseraient un
        # accumulateur du genre {"dataset": "d"} refusé à la validation mais
        # écrit ici. Inatteignable aujourd'hui, ambigu à la lecture.
        if not brouillon.get("columns"):
            surface.show("Aucune fiche à écrire (aucune colonne transmise).")
            return
        raw = str(brouillon.get("dataset") or Path(dataset_path).stem)
        # garde : nom de fichier sûr (pas de slash/point)
        # => pas d'écriture hors catalog_dir
        dataset = re.sub(r"[^0-9A-Za-z_]", "_", Path(raw).stem)
        path = catalog_dir / f"{dataset}.fiche.yaml"
        try:
            h = write_fiche(brouillon, path)
        except Exception as e:  # feedback humain garanti (on_result est best-effort)
            surface.show(f"✗ échec écriture fiche : {e!r}")
            raise
        surface.show(f"✓ fiche écrite : {path} (sha256 {h[:12]}…)")
        if questions:
            chemin_q = catalog_dir / f"{dataset}.questions.yaml"
            try:
                write_questions(attach_answers(questions, reponses), chemin_q)
            except Exception as e:  # feedback garanti (on_result est best-effort)
                surface.show(f"✗ échec écriture des questions : {e!r}")
                raise
            surface.show(f"✓ questions écrites : {chemin_q}")
        if scribe is not None:
            scribe.record_nodes(
                [
                    (
                        "curation_validated",
                        {"path": str(path), "dataset": dataset},
                        {"hash": h, "actor": "human"},
                    )
                ]
            )

    def _serialize(transcript: list[dict[str, str]]) -> str:
        lines = ["Historique de la curation :"]
        for turn in transcript:
            for role, text in turn.items():
                who = "HUMAIN" if role == "user" else "TOI"
                lines.append(f"[{who}] {text}")
        # Canal APPLICATION-OWNED (ADR-0009) : l'inventaire passe par le prompt,
        # jamais par la réponse humaine, qui est gravée en `human_turn`.
        lines.append(f"\n{inventory_line(brouillon)}")
        lines.append("\nContinue la curation en respectant ton format de sortie.")
        return "\n".join(lines)

    return Profile(
        role="curator",
        build_options=build_options,
        parse=lambda chunks: parse_curator_turn("\n".join(chunks)),
        on_result=_on_result,
        next_input=_next_input,
        build_prompt=_serialize,
    )
