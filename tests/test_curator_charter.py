"""Garde d'agnosticité : la charte du curateur ne câble aucun domaine métier."""

from intreepid.agent.curator.profile import CHARTER

# Vocabulaire du dataset de démonstration + sentinelles vues en fixture, et termes
# techniques trop spécifiques d'un référentiel. Leur présence signerait un scénario
# câblé (invariant projet no-hard-coded-scenarios) : la connaissance per-dataset vit
# dans la fiche, jamais dans la charte.
_INTERDITS = (
    "999",
    "2056",
    "srid",
    "epsg",
    "lv95",
    "accident",
    "vitesse",
    "canton",
    "commune",
    "ofrou",
)


def test_charte_sans_vocabulaire_metier() -> None:
    minuscules = CHARTER.lower()
    presents = [terme for terme in _INTERDITS if terme in minuscules]
    assert presents == [], f"vocabulaire métier câblé dans la charte : {presents}"


def test_charte_prescrit_la_forme_de_tour() -> None:
    minuscules = CHARTER.lower()
    for marqueur in ("verrou", "ancrage", "enjeu", "je ne sais pas"):
        assert marqueur in minuscules, f"la charte ne prescrit plus : {marqueur}"


def test_charte_ne_demande_plus_de_memoire_en_prose() -> None:
    """« Tranché seul » versait la mémoire de l'agent dans le canal humain.

    C'est ce qui a fait échouer le gate : une vingtaine de colonnes documentées
    d'affilée dans le texte que l'humain lit. La mémoire vit dans le brouillon
    de fiche, que la surface n'affiche pas.
    """
    minuscules = CHARTER.lower()
    # Le LABEL avec ses deux-points, pas les mots seuls : « Tranche SEUL tout ce
    # que le profil permet » RESTE dans la charte (§ Méthode, point 2), et une
    # interdiction sur « tranche seul » nu ferait échouer ce test APRÈS le correctif.
    for interdit in ("tranché seul :", "tranche seul :", "ta seule mémoire"):
        assert interdit not in minuscules, f"rustine de mémoire en prose : {interdit}"


def test_charte_prescrit_une_seule_question_par_tour() -> None:
    """Le transcript de référence pose UNE question par tour (7 pour 36 colonnes)."""
    minuscules = CHARTER.lower()
    assert "une seule question" in minuscules
    assert "1 à 3 questions" not in minuscules


def test_charte_demande_le_brouillon_a_chaque_tour() -> None:
    """Le brouillon est la mémoire de l'agent : émis à chaque tour, invisible.

    Assertions sur le texte APLATI : la charte est enveloppée à 88 colonnes, donc
    une consigne peut être coupée par un retour à la ligne au milieu — chercher
    « qu'au tour » dans le texte brut ne prouve rien (il y vaut déjà False
    aujourd'hui, à cause du saut de ligne après « QU'AU »).
    """
    aplati = " ".join(CHARTER.lower().split())
    assert "`fiche_draft` **à chaque tour**" in aplati
    assert "qu'au tour où tu proposes la validation" not in aplati
    assert "il vaut `null`" not in aplati


def test_charte_prescrit_le_penchant_et_les_options() -> None:
    """Deux des cinq éléments de la question, non couverts jusqu'ici.

    SHOULD différé de la revue finale de #8 : le test de forme ne tenait que par
    le mot « ancrage ». Ces deux marqueurs sont ce qui distingue une question
    ratifiable d'une devinette.
    """
    minuscules = CHARTER.lower()
    for marqueur in ("penchant", "options"):
        assert marqueur in minuscules, f"la charte ne prescrit plus : {marqueur}"


def test_gabarit_conserve_ses_noms_factices() -> None:
    """Filet contre un retrait trop large dans le gabarit.

    Cette tâche SUPPRIME une partie de l'exemple (une question par tour) : sans
    garde, un retrait un peu large emporterait le gabarit entier, or c'est
    l'exemple — pas la consigne — qui porte le niveau de détail attendu.
    Les deux noms restants sont ceux du verrou et de la question conservée.
    """
    minuscules = CHARTER.lower()
    for factice in ("mesure_x", "code_statut"):
        assert factice in minuscules, f"le gabarit a perdu : {factice}"
