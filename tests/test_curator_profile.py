"""Vérifie le profil curateur : isolation P2/P3, terminaison, validation."""

from typing import Any

import pytest
import yaml

from intreepid.agent.curator.profile import (
    _DISALLOWED,
    _MCP_TOOLS,
    build_options,
    curator_profile,
)
from intreepid.agent.curator.surface import Surface
from intreepid.agent.curator.turn import CuratorTurn


def test_allowlist_is_profile_raw_only():
    assert _MCP_TOOLS == ["mcp__intreepid__profile_raw"]


def test_isolation_disallows_builtins():
    opts = build_options()
    for tool in ("Bash", "Read", "Write", "WebFetch", "Skill"):
        assert tool in _DISALLOWED
    assert opts.allowed_tools == _MCP_TOOLS
    assert opts.disallowed_tools == _DISALLOWED
    assert opts.permission_mode == "bypassPermissions"
    assert opts.setting_sources == []
    assert opts.strict_mcp_config is True


def test_next_input_returns_none_on_validation(tmp_path):
    prof = curator_profile(
        "d.parquet",
        tmp_path,
        surface=Surface(writer=lambda _t: None, reader=lambda _p: "o"),
    )
    turn = CuratorTurn(
        message="prête ?",
        fiche_delta={"dataset": "d", "columns": {"a": {}}},
        proposes_completion=True,
    )
    next_input = prof.next_input
    assert next_input is not None
    assert next_input(turn) is None  # 'o' => validé


def test_next_input_returns_reply_when_not_complete(tmp_path):
    prof = curator_profile(
        "d.parquet",
        tmp_path,
        surface=Surface(
            writer=lambda _t: None, reader=lambda _p: "corrige la colonne X"
        ),
    )
    turn = CuratorTurn(message="voici", fiche_delta=None, proposes_completion=False)
    next_input = prof.next_input
    assert next_input is not None
    assert next_input(turn) == "corrige la colonne X"


def test_build_prompt_serializes_transcript(tmp_path):
    prof = curator_profile("d.parquet", tmp_path)
    build_prompt = prof.build_prompt
    assert build_prompt is not None
    out = build_prompt([{"user": "start"}, {"assistant": "salut"}, {"user": "ok"}])
    assert "start" in out and "salut" in out and "ok" in out


def test_next_input_affiche_substitut_si_message_vide(tmp_path):
    vus: list[str] = []
    prof = curator_profile(
        "d.parquet",
        tmp_path,
        surface=Surface(writer=vus.append, reader=lambda _p: "reformule"),
    )
    turn = CuratorTurn(message="", fiche_delta=None, proposes_completion=False)
    next_input = prof.next_input
    assert next_input is not None
    result = next_input(turn)
    assert result == "reformule"
    assert any("[tour vide" in t for t in vus)


def test_on_result_writes_fiche_and_records_validation(tmp_path):
    class _Scribe:
        def __init__(self):
            self.specs = None

        def record_nodes(self, specs):
            self.specs = specs

    sc = _Scribe()
    prof = curator_profile(
        "d.parquet",
        tmp_path,
        surface=Surface(writer=lambda _t: None, reader=lambda _p: ""),
    )
    draft = {"dataset": "mon_dataset", "columns": {"a": {"type": "numeric"}}}
    result = CuratorTurn(message="fini", fiche_delta=draft, proposes_completion=True)
    next_input = prof.next_input
    on_result = prof.on_result
    assert next_input is not None and on_result is not None
    next_input(result)  # alimente l'accumulateur, que `on_result` écrira
    on_result(sc, result)  # type: ignore[arg-type]

    written = tmp_path / "mon_dataset.fiche.yaml"
    assert written.is_file()
    assert sc.specs is not None
    kind, content, meta = sc.specs[0]
    assert kind == "curation_validated"
    assert content["dataset"] == "mon_dataset"
    assert len(meta["hash"]) == 64  # sha256 hex


def test_on_result_ecrit_laccumulateur_et_non_le_dernier_delta(tmp_path):
    """Le test discriminant de la brique #10.

    Trois tours de deltas DISJOINTS : la fiche écrite doit porter les trois
    colonnes. Avec le code d'avant, qui écrivait `result.fiche_delta`, elle n'en
    porterait qu'une.
    """
    prof = curator_profile(
        "d.parquet",
        tmp_path,
        surface=Surface(writer=lambda _t: None, reader=lambda _p: "o"),
    )
    next_input = prof.next_input
    on_result = prof.on_result
    assert next_input is not None and on_result is not None

    next_input(
        CuratorTurn(
            message="t1",
            fiche_delta={"dataset": "mon_dataset", "columns": {"a": {"type": "num"}}},
            proposes_completion=False,
        )
    )
    next_input(
        CuratorTurn(
            message="t2",
            fiche_delta={"columns": {"b": {"type": "cat"}}},
            proposes_completion=False,
        )
    )
    final = CuratorTurn(
        message="prête ?",
        fiche_delta={"columns": {"c": {"type": "temporal"}}},
        proposes_completion=True,
    )
    assert next_input(final) is None  # 'o' => validé
    on_result(None, final)

    ecrite = yaml.safe_load((tmp_path / "mon_dataset.fiche.yaml").read_text("utf-8"))
    assert set(ecrite["columns"]) == {"a", "b", "c"}
    assert ecrite["dataset"] == "mon_dataset"


def test_validation_acceptee_quand_le_dernier_delta_est_vide(tmp_path):
    """Un dernier tour sans nouvelle colonne est désormais le cas NORMAL.

    L'ancienne garde, qui portait sur `fiche_delta is None`, l'aurait refusé.
    """
    prof = curator_profile(
        "d.parquet",
        tmp_path,
        surface=Surface(writer=lambda _t: None, reader=lambda _p: "o"),
    )
    next_input = prof.next_input
    assert next_input is not None
    next_input(
        CuratorTurn(
            message="t1",
            fiche_delta={"columns": {"a": {}}},
            proposes_completion=False,
        )
    )
    final = CuratorTurn(message="prête ?", fiche_delta=None, proposes_completion=True)
    assert next_input(final) is None


def test_validation_refusee_quand_rien_na_jamais_ete_transmis(tmp_path):
    """La garde survit, déplacée sur l'accumulateur.

    Accumulateur vide => valider ne produirait aucune fiche et perdrait la session.
    """
    vus: list[str] = []
    prof = curator_profile(
        "d.parquet",
        tmp_path,
        surface=Surface(writer=vus.append, reader=lambda _p: "renvoie la fiche"),
    )
    next_input = prof.next_input
    assert next_input is not None
    turn = CuratorTurn(message="prête ?", fiche_delta=None, proposes_completion=True)
    assert next_input(turn) == "renvoie la fiche"
    assert any("Aucune colonne" in t for t in vus)


def test_build_prompt_porte_linventaire(tmp_path):
    # Surface INJECTÉE : `Surface()` par défaut lit sur `input()`, et ce test
    # appelle `next_input`, qui se termine par `surface.ask()`. Sans injection,
    # pytest lève « reading from stdin while output is captured ».
    prof = curator_profile(
        "d.parquet",
        tmp_path,
        surface=Surface(writer=lambda _t: None, reader=lambda _p: "ok"),
    )
    next_input, build_prompt = prof.next_input, prof.build_prompt
    assert next_input is not None and build_prompt is not None
    next_input(
        CuratorTurn(
            message="t1",
            fiche_delta={"columns": {"alpha": {}, "beta": {}}},
            proposes_completion=False,
        )
    )
    out = build_prompt([{"user": "start"}, {"assistant": "t1"}])
    assert "Brouillon conservé par l'application" in out
    assert "alpha" in out and "beta" in out
    assert "2 entrée" in out


def test_linventaire_ne_contamine_pas_la_reponse_humaine(tmp_path):
    """Contrainte dure : la réponse humaine ne porte QUE des mots de l'humain.

    L'orchestrateur grave la valeur retournée par `next_input` en nœud
    `human_turn` / `actor: "human"`. Y glisser l'inventaire inscrirait dans une
    trace probante des mots que l'humain n'a pas dits — c'est le défaut que la
    passe 2 d'advisor de la brique #8 avait attrapé.
    """
    prof = curator_profile(
        "d.parquet",
        tmp_path,
        surface=Surface(writer=lambda _t: None, reader=lambda _p: "1a"),
    )
    next_input = prof.next_input
    assert next_input is not None
    reponse = next_input(
        CuratorTurn(
            message="t1",
            fiche_delta={"columns": {"alpha": {}}},
            proposes_completion=False,
        )
    )
    assert reponse == "1a"
    assert "Brouillon" not in str(reponse)


@pytest.mark.parametrize(
    ("cas", "delta", "propose"),
    [
        ("tour ordinaire", {"columns": {"alpha": {}}}, False),
        ("proposition corrigée, non validée", {"columns": {"alpha": {}}}, True),
        ("garde : accumulateur vide", None, True),
    ],
)
def test_les_trois_retours_de_next_input_ne_portent_que_lhumain(
    tmp_path: Any, cas: str, delta: dict[str, Any] | None, propose: bool
) -> None:
    """Aucun des trois chemins de retour n'ajoute un mot de l'application.

    L'orchestrateur grave la valeur retournée par `next_input` en nœud
    `human_turn` / `actor: "human"` : tout ce qui n'est pas dit par l'humain y
    serait une falsification de trace probante. Le test existant ne couvrait
    qu'un chemin sur trois ; celui de la garde affiche justement un message de
    l'application juste avant de relire, et rien n'empêcherait quelqu'un d'y
    joindre un jour l'inventaire du brouillon.
    """
    dit = "ce que l'humain a tapé, et rien d'autre"
    vus: list[str] = []
    prof = curator_profile(
        "d.parquet",
        tmp_path,
        surface=Surface(writer=vus.append, reader=lambda _p: dit),
    )
    next_input = prof.next_input
    assert next_input is not None
    retour = next_input(
        CuratorTurn(message="t", fiche_delta=delta, proposes_completion=propose)
    )
    assert retour == dit, f"chemin « {cas} » : retour contaminé"


def _reader_scripte(reponses: list[str]):
    """Rend un reader qui débite `reponses` puis lève si on lui en demande plus."""
    file = list(reponses)

    def _lire(_prompt: str = "> ") -> str:
        if not file:
            raise AssertionError("le profil a demandé plus de réponses que prévu")
        return file.pop(0)

    return _lire


def _tour_avec_questions(nb: int, propose: bool = False) -> CuratorTurn:
    return CuratorTurn(
        message="m",
        fiche_delta={"columns": {"a": {}}},
        proposes_completion=propose,
        questions=[
            {"n": i, "colonne": f"c{i}", "options": {"a": "oui", "b": "non"}}
            for i in range(1, nb + 1)
        ],
    )


def test_les_questions_sont_servies_une_par_une(tmp_path):
    vus: list[str] = []
    prof = curator_profile(
        "d.parquet",
        tmp_path,
        surface=Surface(writer=vus.append, reader=_reader_scripte(["1a", "2b", "3a"])),
    )
    next_input = prof.next_input
    assert next_input is not None
    retour = next_input(_tour_avec_questions(3))
    affiche = "\n".join(vus)
    assert "Question 1/3" in affiche
    assert "Question 2/3" in affiche
    assert "Question 3/3" in affiche
    assert retour == "1a\n2b\n3a"


def test_le_retour_ne_porte_aucun_mot_de_lapplication(tmp_path):
    """I-E : `next_input` est gravé en `human_turn` / actor human.

    Aucun numéro ajouté, aucun libellé d'option : l'association se fait par
    l'ORDRE de service, et l'agent a ses propres numéros dans son historique.
    """
    prof = curator_profile(
        "d.parquet",
        tmp_path,
        surface=Surface(writer=lambda _t: None, reader=_reader_scripte(["1a", "2b"])),
    )
    next_input = prof.next_input
    assert next_input is not None
    retour = next_input(_tour_avec_questions(2))
    assert retour == "1a\n2b"
    for parasite in ("Question", "Brouillon", "oui", "non", "→"):
        assert parasite not in retour


def test_lecho_rappelle_le_libelle_de_loption_choisie(tmp_path):
    vus: list[str] = []
    prof = curator_profile(
        "d.parquet",
        tmp_path,
        surface=Surface(writer=vus.append, reader=_reader_scripte(["1a"])),
    )
    next_input = prof.next_input
    assert next_input is not None
    next_input(_tour_avec_questions(1))
    assert any("(a) oui" in t for t in vus)


def test_ligne_vide_puis_o_envoie_ce_qui_est_collecte(tmp_path):
    vus: list[str] = []
    prof = curator_profile(
        "d.parquet",
        tmp_path,
        surface=Surface(writer=vus.append, reader=_reader_scripte(["1a", "", "o"])),
    )
    next_input = prof.next_input
    assert next_input is not None
    retour = next_input(_tour_avec_questions(5))
    assert retour == "1a"
    affiche = "\n".join(vus)
    assert "Envoyer maintenant" in affiche
    assert "questions 2 à 5 sans réponse" in affiche


def test_ligne_vide_puis_n_reprend_la_question_courante(tmp_path):
    vus: list[str] = []
    prof = curator_profile(
        "d.parquet",
        tmp_path,
        surface=Surface(
            writer=vus.append, reader=_reader_scripte(["1a", "", "n", "2b"])
        ),
    )
    next_input = prof.next_input
    assert next_input is not None
    retour = next_input(_tour_avec_questions(2))
    assert retour == "1a\n2b"
    assert sum(1 for t in vus if "Question 2/2" in t) == 2  # reposée


def test_envoi_refuse_sans_aucune_reponse_collectee(tmp_path):
    vus: list[str] = []
    prof = curator_profile(
        "d.parquet",
        tmp_path,
        surface=Surface(writer=vus.append, reader=_reader_scripte(["", "1a"])),
    )
    next_input = prof.next_input
    assert next_input is not None
    retour = next_input(_tour_avec_questions(1))
    assert retour == "1a"
    assert any("rien à envoyer" in t for t in vus)


def test_sans_questions_le_comportement_actuel_est_preserve(tmp_path):
    """Repli STRUCTUREL : un bloc sans `questions` retombe sur une saisie unique."""
    prof = curator_profile(
        "d.parquet",
        tmp_path,
        surface=Surface(writer=lambda _t: None, reader=_reader_scripte(["ma reponse"])),
    )
    next_input = prof.next_input
    assert next_input is not None
    turn = CuratorTurn(message="m", fiche_delta=None, proposes_completion=False)
    assert next_input(turn) == "ma reponse"


def test_questions_non_dict_ne_perdent_pas_la_seance(tmp_path):
    """Mode de panne qui coûterait la séance ENTIÈRE, pas seulement un tour.

    Si l'agent écrit ses questions en clair dans le tableau, servir ces entrées
    lèverait `AttributeError` dans la boucle de collecte : `on_result` ne serait
    jamais atteint et aucune fiche ne serait écrite. Le repli est structurel —
    on retombe sur la saisie unique, comme si le bloc n'avait pas de questions.
    """
    prof = curator_profile(
        "d.parquet",
        tmp_path,
        surface=Surface(writer=lambda _t: None, reader=_reader_scripte(["libre"])),
    )
    next_input = prof.next_input
    assert next_input is not None
    turn = CuratorTurn(
        message="m",
        fiche_delta=None,
        proposes_completion=False,
        questions=["Question 1 : ...", "Question 2 : ..."],  # type: ignore[list-item]
    )
    assert next_input(turn) == "libre"


def test_bloc_illisible_le_dit_a_lhumain(tmp_path):
    """Le runbook promet que l'application parle ; sans ceci elle se taisait.

    Un bloc non-JSON fait replier `parse_curator_turn` : ni colonnes ni
    questions n'arrivent, et la prose porte encore sa fence. L'humain voyait
    « Voici mes questions. » suivi du JSON cassé, puis un prompt nu — aucune
    question servie et rien pour le lui dire, en pleine séance payée.
    """
    vus: list[str] = []
    prof = curator_profile(
        "d.parquet",
        tmp_path,
        surface=Surface(writer=vus.append, reader=_reader_scripte(["reemets"])),
    )
    next_input = prof.next_input
    assert next_input is not None
    casse = CuratorTurn(
        message='Voici mes questions.\n```json\n{"questions": [{"n": 1}\n```',
        fiche_delta=None,
        proposes_completion=False,
    )
    assert next_input(casse) == "reemets"
    assert any("Bloc de métadonnées illisible" in t for t in vus)
    assert any("tour est perdu" in t for t in vus)


def test_un_tour_normal_ne_crie_pas_au_bloc_illisible(tmp_path):
    """Discriminance : la garde ne doit pas se déclencher sur un tour sain."""
    vus: list[str] = []
    prof = curator_profile(
        "d.parquet",
        tmp_path,
        surface=Surface(writer=vus.append, reader=_reader_scripte(["1a"])),
    )
    next_input = prof.next_input
    assert next_input is not None
    next_input(_tour_avec_questions(1))
    assert not any("illisible" in t for t in vus)


def test_on_result_ecrit_les_deux_artefacts_avec_les_reponses(tmp_path):
    prof = curator_profile(
        "d.parquet",
        tmp_path,
        surface=Surface(
            writer=lambda _t: None, reader=_reader_scripte(["1a", "2b", "o"])
        ),
    )
    next_input, on_result = prof.next_input, prof.on_result
    assert next_input is not None and on_result is not None
    tour = CuratorTurn(
        message="m",
        fiche_delta={"dataset": "mon_dataset", "columns": {"a": {}}},
        proposes_completion=False,
        questions=[
            {"n": 1, "colonne": "c1", "options": {"a": "oui"}},
            {"n": 2, "colonne": "c2", "options": {"b": "non"}},
        ],
    )
    next_input(tour)
    final = CuratorTurn(message="prête ?", fiche_delta=None, proposes_completion=True)
    assert next_input(final) is None  # 'o' => validé
    on_result(None, final)

    fiche = yaml.safe_load(
        (tmp_path / "mon_dataset.fiche.yaml").read_text(encoding="utf-8")
    )
    assert "questions" not in fiche  # la fiche est écrite POUR un LLM
    posees = yaml.safe_load(
        (tmp_path / "mon_dataset.questions.yaml").read_text(encoding="utf-8")
    )
    assert [q["reponse"] for q in posees] == ["1a", "2b"]


def test_aucun_fichier_de_questions_si_aucune_question(tmp_path):
    prof = curator_profile(
        "d.parquet",
        tmp_path,
        surface=Surface(writer=lambda _t: None, reader=_reader_scripte(["o"])),
    )
    next_input, on_result = prof.next_input, prof.on_result
    assert next_input is not None and on_result is not None
    final = CuratorTurn(
        message="prête ?",
        fiche_delta={"dataset": "mon_dataset", "columns": {"a": {}}},
        proposes_completion=True,
    )
    assert next_input(final) is None
    on_result(None, final)
    assert (tmp_path / "mon_dataset.fiche.yaml").is_file()
    assert not (tmp_path / "mon_dataset.questions.yaml").exists()
