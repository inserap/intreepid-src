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


def test_charte_demande_toutes_les_questions_en_un_tour() -> None:
    """Le verrou structurel de la brique #11, retiré.

    `c37cb70` (06/08 00 h 10) avait remplacé « Pose ensuite 1 à 3 questions »
    par « une seule question » : c'est pour cela qu'il fallait 5 tours pour 4
    questions. Le transcript de référence du 04/08 — « 3 questions
    prioritaires » — tournait sur la charte d'AVANT.
    """
    aplati = " ".join(CHARTER.lower().split())
    assert "une seule question" not in aplati
    assert "une question à la fois" not in aplati
    assert "toutes les questions que tu ne peux pas trancher" in aplati


def test_charte_ne_porte_aucun_plafond_de_questions() -> None:
    """Il n'existe pas de nombre de questions correct (Q-0025).

    Cent questions sont légitimes si cent jugements exigent une autorité que le
    profil n'a pas. Le garde-fou contre le comportement robotique de v0.10.0
    reste « jamais une passe colonne par colonne » — un critère, pas un volume.
    """
    aplati = " ".join(CHARTER.lower().split())
    assert "questions structurantes suffisent" not in aplati
    assert "1 à 3 questions" not in aplati
    assert "passe colonne par colonne" in aplati


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


def test_charte_prescrit_les_options_et_plus_le_penchant_obligatoire() -> None:
    """Trois prescriptions ajoutées le 06/08, retirées ici.

    Le penchant systématique, l'indice contraire et la signalisation
    d'irréversibilité codifiaient un comportement que l'agent avait DÉJÀ
    spontanément au 04/08 — et la codification a triplé le volume d'une
    question (634 → 2 007 car. de médiane) sans rien ajouter au fond.
    """
    aplati = " ".join(CHARTER.lower().split())
    assert "options" in aplati
    assert "ton penchant" not in aplati
    assert "dans l'autre sens" not in aplati
    assert "irréversible" not in aplati


def test_charte_prescrit_le_schema_et_la_regle_dechappement() -> None:
    """Sans schéma, « fiche complète » et « trop longue » n'ont pas de sens.

    Mesuré le 07/08 sur quatre runs du MÊME prompt : 14 clés de colonne
    distinctes, 2 seulement communes aux quatre. La dérive n'est pas un
    glissement entre slices, c'est un tirage à chaque run.
    """
    aplati = " ".join(CHARTER.lower().split())
    for cle in (
        "grain",
        "perimetre",
        "referentiels",
        "pieges_transversaux",
        "points_non_tranches",
    ):
        assert cle in aplati, f"clé racine absente du schéma : {cle}"
    # `sens` et `type` figurent DÉJÀ dans la charte d'avant : les asserter seuls ne
    # discrimine rien. C'est la ligne du schéma qui doit être présente.
    assert "`sens`, `type`, `pieges`" in aplati
    # la règle d'échappement : c'est elle qui a manqué en #10, d'où la colonne
    # fantôme créée pour loger une note transversale
    assert "n'invente jamais une entrée de colonne" in aplati
    # la COUVERTURE : sans elle, la charte interdirait le regroupement des
    # libellés que le schéma prescrit, et les critères 2 et 6 s'excluraient
    assert "couverture, et non comptage" in aplati
    assert "une fiche partielle" not in aplati or "nommée dans une entrée" in aplati


def test_charte_donne_une_echelle_en_caracteres_pas_en_phrases() -> None:
    """L'unité « phrase » ne contient rien : 634 car. au 04/08, 2 007 au 06/08.

    Les deux respectaient « quatre à six phrases ». L'échelle se prescrit dans
    l'unité qu'on mesure, et qui se convertit en secondes (76 tokens/s).
    """
    aplati = " ".join(CHARTER.lower().split())
    assert "quatre à six phrases" not in aplati
    # L'échelle de la QUESTION, pas n'importe quelle mention de caractères : le
    # § Schéma en porte une autre (~150 / ~400, pour les entrées de fiche), donc
    # un simple « caractères » in … resterait vert si cette règle-ci disparaissait.
    assert "~600 caractères" in aplati


def test_gabarit_porte_plusieurs_questions() -> None:
    """Le gabarit est l'échelle réelle : un modèle imite l'exemple.

    À 918 caractères, l'ancien gabarit de question enseignait 45 % de plus que
    le gold-standard validé (634). Le nouveau en porte deux, de tailles
    différentes, pour montrer qu'une question simple est plus brève.
    """
    minuscules = CHARTER.lower()
    assert "question 1" in minuscules and "question 2" in minuscules


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
