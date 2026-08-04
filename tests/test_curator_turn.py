"""Vérifie le parsing d'un tour curateur : prose hors blocs, métadonnées dedans."""

from intreepid.agent.curator.turn import CuratorTurn, parse_curator_turn


def test_prose_hors_bloc_devient_le_message() -> None:
    text = (
        "Point 1 verrouillé : la colonne est un code, pas une mesure.\n\n"
        "Question 2, sur code_statut : six valeurs distinctes sur 40 000 lignes.\n\n"
        "```json\n"
        '{"fiche_draft": null, "proposes_completion": false}\n'
        "```\n"
    )
    turn: CuratorTurn = parse_curator_turn(text)
    assert turn.message.startswith("Point 1 verrouillé")
    assert "Question 2" in turn.message
    assert "```" not in turn.message
    assert turn.fiche_draft is None
    assert turn.proposes_completion is False


def test_fiche_draft_et_completion_lus_dans_le_bloc() -> None:
    text = (
        "Voici la fiche finale.\n"
        "```json\n"
        '{"fiche_draft": {"dataset": "d", "columns": {"v": {"type": "categorical"}}},'
        ' "proposes_completion": true}\n'
        "```\n"
    )
    turn = parse_curator_turn(text)
    assert turn.message == "Voici la fiche finale."
    assert turn.fiche_draft is not None
    assert turn.fiche_draft["dataset"] == "d"
    assert turn.proposes_completion is True


def test_bloc_en_tete_la_prose_qui_suit_reste_le_message() -> None:
    text = (
        "```json\n"
        '{"fiche_draft": null, "proposes_completion": false}\n'
        "```\n"
        "Question 1, sur code_statut : six valeurs distinctes.\n"
    )
    turn = parse_curator_turn(text)
    assert turn.message == "Question 1, sur code_statut : six valeurs distinctes."


def test_texte_apres_le_bloc_final_nest_pas_perdu() -> None:
    text = (
        "Voici la fiche.\n"
        "```json\n"
        '{"fiche_draft": null, "proposes_completion": true}\n'
        "```\n"
        "Validez-vous ?\n"
    )
    turn = parse_curator_turn(text)
    assert "Voici la fiche." in turn.message
    assert "Validez-vous ?" in turn.message
    assert turn.proposes_completion is True


def test_bloc_seul_repli_sur_champ_message_legacy() -> None:
    text = '```json\n{"message": "ancien format", "proposes_completion": false}\n```\n'
    turn = parse_curator_turn(text)
    assert turn.message == "ancien format"
    assert turn.proposes_completion is False


def test_dernier_bloc_gagne_et_blocs_anterieurs_sont_retires() -> None:
    text = (
        "```json\n"
        '{"fiche_draft": null, "proposes_completion": false}\n'
        "```\n"
        "puis le vrai tour :\n"
        "```json\n"
        '{"fiche_draft": null, "proposes_completion": true}\n'
        "```\n"
    )
    turn = parse_curator_turn(text)
    assert turn.message == "puis le vrai tour :"
    assert turn.proposes_completion is True


def test_sans_bloc_tout_le_texte_est_le_message() -> None:
    turn = parse_curator_turn("juste du texte libre")
    assert turn.message == "juste du texte libre"
    assert turn.fiche_draft is None
    assert turn.proposes_completion is False


def test_bloc_non_json_repli_sur_texte_brut() -> None:
    text = "colonnes :\n```\na: numeric  # pas du JSON\n```\n"
    turn = parse_curator_turn(text)
    assert turn.fiche_draft is None
    assert turn.proposes_completion is False
    assert "colonnes" in turn.message  # repli sur le texte brut


def test_champs_absents_valeurs_par_defaut() -> None:
    text = "message en prose\n```json\n{}\n```\n"
    turn = parse_curator_turn(text)
    assert turn.message == "message en prose"
    assert turn.fiche_draft is None
    assert turn.proposes_completion is False


def test_fiche_draft_non_dict_ou_vide_vaut_none() -> None:
    for brut in ("{}", '"voir ci-dessus"', "[]"):
        payload = f'{{"fiche_draft": {brut}, "proposes_completion": true}}'
        text = f"P.\n```json\n{payload}\n```\n"
        assert parse_curator_turn(text).fiche_draft is None


def test_crlf_line_endings_parsed() -> None:
    text = (
        'P.\r\n```json\r\n{"fiche_draft": null, "proposes_completion": true}\r\n```\r\n'
    )
    result = parse_curator_turn(text)
    assert result.proposes_completion is True


def test_fence_non_json_dans_la_prose_ne_casse_pas_le_parsing() -> None:
    # Le curateur écrit désormais du markdown libre : une fence illustrative
    # (```yaml, ```sql…) ne doit ni casser le parsing ni polluer le message.
    text = (
        "Un exemple de ce que je vais écrire :\n"
        "```yaml\n"
        "colonnes:\n  a: code\n"
        "```\n"
        "Question 4, sur ref_source : quatre valeurs distinctes.\n"
        "```json\n"
        '{"fiche_draft": null, "proposes_completion": false}\n'
        "```\n"
    )
    turn = parse_curator_turn(text)
    assert turn.proposes_completion is False
    assert "Question 4" in turn.message
    assert "```" not in turn.message
    assert "colonnes:" not in turn.message  # la fence illustrative est retirée
