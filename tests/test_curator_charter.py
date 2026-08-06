"""Garde d'agnosticité : la charte du curateur ne câble aucun domaine métier."""

import re

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
    aplati = " ".join(minuscules.split())
    assert "une seule question" in minuscules
    assert "1 à 3 questions" not in minuscules
    # le premier tour est celui que le gate juge : aucun pluriel ne doit y
    # laisser lire une autorisation de grouper les questions. Sur le texte
    # APLATI : un ré-enveloppement à 88 colonnes couperait la chaîne en deux
    # et ferait passer la garde en silence.
    assert "sur les questions" not in aplati


def test_charte_nomme_loutil_par_son_identifiant_complet() -> None:
    """La charte doit nommer l'outil MCP par son identifiant enregistré.

    4 appels `ToolSearch` parasites au gate du 06/08 : la charte nommait
    `profile_raw` là où l'outil est enregistré `mcp__intreepid__profile_raw`.
    `select:profile_raw` échouait, l'agent se rabattait sur une recherche par
    mots-clés, puis appelait l'outil — deux appels par usage (Q-0019).

    PIÈGE : `mcp__intreepid__profile_raw` CONTIENT `profile_raw`. Une assertion
    « `profile_raw` not in CHARTER » échouerait TOUJOURS. On compte donc les
    occurrences NON précédées du préfixe.
    """
    assert "mcp__intreepid__profile_raw" in CHARTER
    nus = re.findall(r"(?<!mcp__intreepid__)profile_raw", CHARTER)
    assert nus == [], f"{len(nus)} occurrence(s) du nom nu dans la charte"


def test_charte_prescrit_le_delta_pas_la_fiche_entiere() -> None:
    """Le contrat de sortie porte le delta, plus la fiche entière.

    Le brouillon pesait 79 % de la sortie de l'agent (55 544 car. sur 69 628),
    ré-émis entier à chaque tour.
    """
    aplati = " ".join(CHARTER.lower().split())
    assert "fiche_delta" in aplati
    assert "fiche_draft" not in aplati
    assert "ne renvoie jamais une colonne déjà transmise" in aplati


def test_charte_dit_le_principe_de_la_prose_pas_une_liste_dexceptions() -> None:
    """La prose porte conséquences et risques, jamais la documentation.

    Garde contre le mode d'échec de la brique #8 : privé de son brouillon
    structuré, l'agent déplace sa mémoire dans le seul canal que l'humain lit.
    Formulée en PRINCIPE et non en interdiction absolue, parce que deux
    prescriptions centrales de la charte — le verrou d'ouverture et le résumé
    des pièges au tour de validation — parlent légitimement de colonnes déjà
    transmises. Une interdiction absolue les supprimerait ; une liste
    d'exceptions serait un château de cartes.
    """
    aplati = " ".join(CHARTER.lower().split())
    assert "jamais la documentation d'une colonne déjà transmise" in aplati
    # remplacement, pas ajout : l'ancienne interdiction absolue est bien partie
    assert "ne redocumente jamais" not in aplati


def test_charte_distingue_information_et_autorite() -> None:
    """Un jugement de périmètre métier se ratifie, il ne se tranche pas.

    4 ratifications humaines au lieu de 7 au gate du 06/08 : l'agent avait
    tranché seul des jugements de périmètre. Le profil ne les tranchera jamais,
    si riche soit-il — c'est un manque d'autorité, pas un manque d'information.
    """
    aplati = " ".join(CHARTER.lower().split())
    assert "jugement de périmètre" in aplati
    assert "il se ratifie" in aplati


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
