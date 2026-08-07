# Démo brique #11 — toutes les questions en un tour, une fiche pour un LLM

> Ce que la démo montre : l'agent pose toutes ses questions en un seul tour, l'application
> les sert une par une sans appel LLM, et la fiche produite est dense et structurée.

## Pré-requis

- `CLAUDE_CODE_OAUTH_TOKEN` défini, `ANTHROPIC_API_KEY` **non** définie (Q-0010).
- Le parquet OFROU brut, non fiché : mêmes 267 761 lignes et 36 colonnes qu'aux 06 et 07/08.
- Compter ~11 minutes de présence et ~1 à 2 $ d'équivalent-API (sur abonnement : du quota).
- `thinking=True` — les bases de comparaison ont toutes été mesurées ainsi. Ne pas basculer
  `thinking=False` dans la même séance : cela mélangerait deux effets (leçon des trois
  sessions qui ont optimisé un proxy).

## Lancer

    uv run python -m intreepid.demo_curator <chemin/vers/RoadTrafficAccidentLocations.parquet>

Répondre question par question. **Ligne vide** = demander l'envoi (confirmation `o/n`) ;
utile dès qu'une question n'est pas comprise — l'agent y répondra au tour suivant.

**Consigne au gate : ne donner AUCUNE consigne de style.** Les critères 2, 3 et 5 sont
précisément que le niveau et le schéma sortent tout seuls.

## Critères — arrêtés avant l'implémentation

| # | Critère | Base (06/08 soir) | Verdict |
|---|---|---|---|
| 1 | **2 appels LLM**, plus les tours provoqués explicitement par l'humain | 5 | ☐ |
| 2 | contenu de la fiche ÷ 36 colonnes **≤ 300 car.** | 804 | ☐ |
| 3 | médiane par question **≤ 800 car.** | 2 007 | ☐ |
| 4 | les **8** clés racine présentes — `dataset`, `titre`, `grain`, `perimetre`, `referentiels`, `pieges_transversaux`, `points_non_tranches`, `columns` — et **zéro** entrée de colonne absente du profil | 3 clés, 1 fantôme | ☐ |
| 5 | vocabulaire de colonne **strictement** `sens`/`type`/`pieges` | 14 clés sur 4 runs | ☐ |
| 6 | **couverture 36/36** — chaque colonne du profil est nommée par une entrée ; fiche validée | acquis | ☐ |
| 7 | écrit **hors questions** ÷ 36 colonnes **≤ 700 car. pour 2 tours d'agent, + 150 par tour supplémentaire que TU provoques** | 1 571 | ☐ |
| 8 | nombre de questions | 4 | **rapporté, non plafonné** |
| 9 | temps de génération / temps humain | 462,7 s / 495,1 s | **rapportés** |
| 10 | réponses que tu as dû **corriger** au tour suivant, et l'écho t'a-t-il servi | — (le verrou existait) | **rapporté, non bloquant** |

Le critère 7 est la **borne globale** : c'est la seule qui ne se compense pas. Il exclut les
questions parce que leur registre est déjà borné par le critère 3 — borner leur nombre serait
un plafond déguisé déplacé du prompt vers le gate.

**Pourquoi la tolérance par tour** (trouvée en passe 4, arithmétique vérifiée) : le critère 1
autorise les tours que TU provoques, et ce runbook t'invite à les provoquer. Or un tour de
clarification coûte, mesuré sur la trace du 06/08, **115 car./colonne** (prose hors questions
1 414 + raisonnement 2 728). Sans tolérance, une séance parfaitement réussie à 3 tours mesure
**728** et échoue — exactement le défaut de la brique #10, un critère qui punit le succès.
Vérifié dans les deux sens : tous les scénarios de succès passent de 2 à 5 tours, et la base du
06/08 échoue toujours (1 571 contre un seuil de 1 150 à 5 tours), donc la falsifiabilité est
conservée. **Noter en séance le nombre de tours que tu as provoqués** : il sert aux critères 1
et 7.

**Et rapporter aussi le TOTAL des questions** (`total : … · questions N · …` du bloc
d'attribution) — base **7 906** au 06/08, attendu ~4 400. Le critère 3 est une médiane : ajouter
des questions bon marché la fait **baisser**, et le critère 7 les exclut. Le total est donc le
seul chiffre qui empêche la compensation de se cacher dans le seul canal non borné. Une médiane
basse avec un total élevé n'est pas un succès.

## Comment mesurer chaque critère

**Critère 1 — appels LLM.** Le bloc `--- mesures ---` imprimé en fin de séance donne
`… · N tour(s)`. Chaque tour est un appel. Attendu : 2, plus un par tour que vous avez
provoqué (contestation, précision, demande d'éclaircissement).

> **Divergence connue, à OBSERVER et non à corriger en séance.** Le design fait inscrire les
> questions restées sans réponse en `points_non_tranches` au tour de validation ; la charte, elle,
> dit à l'agent de **les reposer au tour suivant** si elles comptent encore. Si tu utilises la
> ligne vide pour sauter des questions, un tour de plus peut donc apparaître — et ce n'est ni un
> tour que TU as provoqué, ni un échec du mécanisme. **Noter le cas s'il se produit** : c'est
> l'arbitrage charte/design qui se tranchera après, sur une observation réelle plutôt que sur le
> papier.
>
> **Comment le compter, pour ne pas hésiter en séance** : il apparaît au critère 1, qui est
> l'endroit où l'anomalie doit se voir — et il compte dans la tolérance du critère 7, au même
> titre qu'un tour que tu aurais provoqué. Raison : le critère 7 borne ce qui est écrit **par
> tour**, pas le nombre de tours ; l'y ignorer punirait deux fois le même événement, dont une
> fois sur un poste que tu n'as pas causé.

**Critères 2, 4, 5, 6 — la fiche.** Le driver affiche à la validation
`✓ fiche écrite : … (sha256 …)`. Sur ce chemin :

**`PYTHONIOENCODING=utf-8` n'est pas optionnel.** Les caractères fautifs sont le **tiret
cadratin** de la ligne de couverture elle-même et les accents des libellés : sous un codec
étroit (`cp850`, `ascii`) `print` lève `UnicodeEncodeError` et **la ligne de couverture est
perdue** — le critère 6 ne serait pas mesuré. *(Vérifié en passe 4 ; la justification initiale
invoquait un signe `≤` qui ne figure pas dans le script — un lecteur qui l'aurait cherché aurait
conclu que la précaution était inutile.)*

```bash
PYTHONIOENCODING=utf-8 uv run python -c "
import yaml,sys,re
d=yaml.safe_load(open(sys.argv[1],encoding='utf-8'))
cols=d.get('columns') or {}
voc=sorted({k for v in cols.values() if isinstance(v,dict) for k in v})
dump=yaml.safe_dump(d,allow_unicode=True)
noms=[l.strip() for l in open(sys.argv[2],encoding='utf-8') if l.strip()]
ATTENDUES={'dataset','titre','grain','perimetre','referentiels','pieges_transversaux','points_non_tranches','columns'}
print('clés racine  :', sorted(d))
print('manquantes   :', sorted(ATTENDUES - set(d)) or 'aucune', '| en trop :', sorted(set(d) - ATTENDUES) or 'aucune')
print('entrées      :', len(cols), '(< 36 est NORMAL si des colonnes sont groupées)')
print('hors profil  :', [k for k in cols if k not in noms] or 'aucune')
print('vocabulaire  :', voc)
print('entrées non-dict :', [k for k, v in cols.items() if not isinstance(v, dict)] or 'aucune')
print('contenu      :', len(dump), 'car.')
print('par colonne  :', round(len(dump)/len(noms)), 'car. (base 804, cible 300 max)')
# CRITÈRE 6 — couverture, pas comptage. Frontières de mot OBLIGATOIRES : six des
# 36 colonnes sont sous-chaînes d'une autre (AccidentType dans AccidentType_de,
# AccidentHour dans AccidentHour_text...). Un test 'n in dump' déclare 36/36 sur
# une fiche où ces six ne sont nommées NULLE PART : le critère ne pourrait pas
# échouer, et précisément sur les colonnes les plus exposées au regroupement.
# VÉRIFIÉ sur le parquet : 6 des 36 le sont (AccidentType, RoadType,
# AccidentMonth, AccidentWeekDay, AccidentHour, AccidentSeverityCategory), et
# sur une fiche ne nommant qu'elles le naïf dit 36/36 quand celui-ci dit 30/36.
# Classe ASCII à dessein : les 36 noms le sont ; un jeu aux noms accentués
# exigerait \\b (Unicode) — à changer le jour où un tel jeu se présente.
absents=[n for n in noms
         if not re.search(r'(?<![0-9A-Za-z_])'+re.escape(n)+r'(?![0-9A-Za-z_])', dump)]
print('couverture   :', len(noms)-len(absents), '/', len(noms), '— manquantes :', absents or 'aucune')
" catalog/<nom>.fiche.yaml /tmp/noms-colonnes.txt
```

La liste des 36 noms s'obtient une fois pour toutes, avant la séance :

```bash
uv run python -c "
import duckdb,sys
for c in duckdb.connect().execute('DESCRIBE SELECT * FROM read_parquet(?)',[sys.argv[1]]).fetchall():
    print(c[0])
" <chemin/vers/RoadTrafficAccidentLocations.parquet> > /tmp/noms-colonnes.txt
```

Critère 4 : `manquantes` doit valoir `aucune` et `hors profil` aussi. **Une rubrique sans
contenu s'écrit vide (`[]`), elle ne s'omet pas** : sans cette règle, une séance où tu tranches
TOUT laisse `points_non_tranches` sans matière, l'agent l'omet, et le gate échoue sur la
meilleure séance possible (trouvé en passe 4). La charte le prescrit désormais explicitement. **La clé d'une
entrée groupée est l'UNE des colonnes qu'elle couvre**, jamais un nom fabriqué — sinon ce critère
échoue sur une séance réussie (trouvé en passe 3).
Critère 5 : `vocabulaire` doit valoir exactement `['pieges', 'sens', 'type']`.
Critère 6 : `couverture` doit valoir `36 / 36`. **Ce critère mesure une couverture, pas un compte
d'entrées** : avec le regroupement, `entrées` vaudra ~16-18 et ce sera un succès.
**Nécessaire, non suffisant** : un nom cité en passant compte comme couvert. Relire les entrées
groupées à l'œil avant de cocher.

**Critère 8 et qualité des questions — le second artefact.** Le driver l'annonce par
`✓ questions écrites : …`. C'est le SEUL endroit où se vérifie le risque n° 2 du design (le
groupement dégrade-t-il la qualité des questions ?), et c'est exactement ce qui a fait échouer la
brique #8 :

```bash
PYTHONIOENCODING=utf-8 uv run python -c "
import yaml,sys
qs=yaml.safe_load(open(sys.argv[1],encoding='utf-8'))
print('questions :', len(qs))
for q in qs:
    manque=[c for c in ('constat','enjeu','options') if not q.get(c)]
    etat='complet' if not manque else f'INCOMPLET {manque}'
    print(f\"  n{q.get('n')} : {etat} | réponse : {q.get('reponse') or 'AUCUNE'}\")
" catalog/<nom>.questions.yaml
```

Chaque question doit porter son objet, son ancrage chiffré et ses options fermées. Une question
`INCOMPLET` n'est pas un échec chiffré du gate, mais elle se consigne : c'est le signal que le
plafond de taille du critère 3 a mordu sur le fond.

**Critère 3 — médiane par question.** Le bloc d'attribution la donne directement :
`médiane par question : N car.`, comptée sur les **caractères rédigés** (champs de texte et
libellés d'options, sans la syntaxe JSON) — même unité que la base de 2 007.

**Critère 7 — la borne globale.** Deux blocs à combiner :

    écrit hors questions = (« tour d'agent » + « thinking » du bloc `--- mesures ---`)
                           − « questions » du bloc d'attribution
    puis ÷ 36

*Vérification de la base, reproduite sur la trace réelle du 06/08 soir : 50 814 + 13 638 = 64 452 ;
(64 452 − 7 906) ÷ 36 = **1 571**, au caractère près.*

Les deux blocs s'affichent en fin de séance, mais **ne dépendre d'aucun défilement de
terminal** : la trace est conservée et le calcul se rejoue offline, autant de fois qu'on veut.

```bash
PYTHONIOENCODING=utf-8 uv run python -c "
import duckdb, re, sys
from pathlib import Path
from intreepid.demo_curator import _attribution
from intreepid.scribe.metrics import summarize
from intreepid.scribe.store import load
db = Path(sys.argv[1]); n_cols = int(sys.argv[2]); provoques = int(sys.argv[3])
con = duckdb.connect(str(db), read_only=True)
sid = con.execute('SELECT session_id FROM sessions').fetchone()[0]; con.close()
tr = load(db, sid); attr = _attribution(tr); m = summarize(tr)
q = int(re.search(r'total : .*questions (\d+)', attr).group(1))
ecrit = (m.prose_chars or 0) + (m.thinking_chars or 0)
print('ecrit (tour agent + thinking) :', ecrit)
print('questions                     :', q)
print('hors questions / colonne      :', round((ecrit - q) / n_cols))
print('seuil (2 tours + N provoques) :', 700 + 150 * provoques)
" traces/<fichier>.duckdb 36 1
```

*Le troisième argument est le nombre de tours que TU as provoqués.* Commande **exécutée**
sur `traces/curator-785a2ccd.duckdb` (la séance du 06/08) : elle rend `ecrit 64452`, soit les
50 814 + 13 638 annoncés, et `1790` par colonne — la valeur de la note de lecture ci-dessous.

> **Note de lecture indispensable.** Appliquée telle quelle à une trace **antérieure** à cette
> slice, la formule donne **1 790**, non 1 571 : sur ces traces les questions étaient en **prose**,
> donc le poste `questions` de l'attribution vaut `0` et rien n'est soustrait. Les 7 906 caractères
> ont été mesurés **à la main dans le transcript**. À partir de cette slice, les questions vivent
> dans le bloc et l'instrument les isole tout seul — les deux chiffres deviennent comparables.
> Vérifié en exécutant l'instrument sur `traces/curator-785a2ccd.duckdb` : il rend
> `prose 14977 · questions 0 · delta 35837`, exactement les valeurs du recap de la brique #10.

**Critère 9 — les deux temps, séparément.** `bout en bout`, `dont API` et `hors API` sont dans
le bloc `--- mesures ---`. Le **temps humain** est `bout en bout − API − hors API` : 495,1 s au
06/08, et il n'est pas censé baisser.

**Critère 10 — le seul risque du design qu'aucun chiffre n'attrape.** Cette slice **supprime**
le verrou entre deux questions : jusqu'ici, l'agent reformulait ta réponse au tour suivant et tu
pouvais le reprendre. Désormais sept questions défilent sans qu'aucun modèle ne tourne, et la
seule garde est l'écho du libellé de l'option choisie. Le design le pose en risque n° 3 et nomme
l'observable — *« l'humain a-t-il eu besoin de corriger après coup ? »* — mais aucun des neuf
critères ne le demande, et le critère 1 ne peut pas y répondre : un tour d'éclaircissement et un
tour de rattrapage donnent le **même** chiffre et des verdicts opposés.

Donc, à la main, en fin de séance, deux notes :

- combien de réponses tu as dû **corriger** au tour suivant (0 = le mécanisme tient) ;
- si l'**écho** `→ (a) libellé` t'a effectivement servi, ou si tu ne l'as pas regardé.

Rapporté au recap, jamais compté comme un échec : c'est une observation de première séance, pas
un seuil. Sans elle, la question du design reste sans réponse quel que soit le résultat du gate
— et c'est exactement ce qui a fait échouer la brique #8, dont le gate ne regardait pas
l'artefact où son risque principal se manifestait.

## Ce que ce gate ne prouvera PAS

- **Rien sur le temps à ±34 % près.** Mesuré le 07/08 sur quatre runs à configuration
  identique : la variance de TEMPS run-à-run atteint 34 % sur une branche et 28 % sur l'autre.
  *(Le +39 % de la même recherche porte sur les caractères par colonne — une variance
  d'écriture, que la consigne de densité est précisément censée supprimer. Ne pas confondre
  les deux.)* Le verdict porte sur les **caractères** ;
  les secondes sont rapportées, et un écart de temps inférieur à 30 % ne vaut pas conclusion.
- **Le bout-en-bout peut ne pas baisser du tout.** 495 s des 961 s du 06/08 sont du temps
  humain, soit **124 s par question** (4 questions). Cette slice fait passer les questions de 4
  à ~7 : l'attente humaine peut monter vers **~865 s**, et le bout-en-bout stagner autour de
  1 000 s alors que la génération aura chuté de 65 %. **Le verdict porte sur les caractères, pas
  sur les secondes** — et c'est précisément pour cela. Le temps humain est rapporté, jamais
  compté comme un échec du curateur : il relève de Q-0025.

## Pièges de lecture

- Un `questions 0 car.` avec une prose longue n'est pas un tour vertueux : c'est un bloc
  malformé, dont le parseur a tout compté en prose. Vérifier la prose avant de se réjouir.
- Le critère 2 est un **ratio par colonne du profil**, pas un total : le regroupement des
  libellés change le nombre d'entrées, et une médiane par entrée **monterait** sur un succès.
- Le critère 2 borne une **moyenne**, et son dénominateur est le nombre de colonnes du
  **profil** (36) — jamais le nombre d'entrées. Mesuré sur une fiche simulée à 17 entrées
  groupées, 8 rubriques racine remplies : 150 car./entrée → **129** ; 250 → **162** ;
  300 → **178** ; 400 → **210**. Toute la fourchette de densité que la charte prescrit passe
  donc largement : ce critère mord sur la verbosité d'ensemble (base 804), pas sur le calibre
  choisi par entrée. **Ne pas le relire par entrée** — les mêmes fiches donnent alors 272 à
  444, et on conclurait à un échec sur une séance réussie.
- Le poste « questions » est mesuré sur `json.dumps`, pas sur les octets émis par le modèle :
  s'il indente son JSON, l'indentation retombe côté delta et le critère 7 est **surestimé** ;
  s'il l'écrit compact, `json.dumps` est plus long et le critère 7 est **flatté**. La direction
  dépend du modèle — regarder le JSON du tour avant de conclure sur un écart serré.

## Si ça tourne mal

- **Ctrl+C en cours de séance.** Le bloc de fin de séance est appelé dans un `finally` et ne se
  tait jamais : preuve du greffier, mesures et attribution s'affichent, la trace est conservée.
- **Le runner refuse de démarrer** en signalant `ANTHROPIC_API_KEY` : c'est la garde
  d'authentification (elle masquerait l'abonnement). Retirer la variable, ne pas contourner.
- **La séance s'achève sans fiche écrite** : c'est un échec du gate, pas un incident à
  rattraper. On arrête et on recadre en session fraîche.
- **Le bloc de métadonnées est illisible** : ni colonnes ni questions reçues. L'application le
  dit. Relancer — ~2 min et ~0,5 $ — plutôt que de tenter de rattraper à la main.

## Garde-fou D5 — une seule itération

Si le gate échoue, on **arrête** et on recadre en session fraîche. On ne re-tune pas la charte
en séance jusqu'à ce que ça passe : un gate qu'on ajuste pour qu'il s'ouvre a cessé d'être un
gate.
