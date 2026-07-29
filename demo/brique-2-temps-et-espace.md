# Démo — Brique #2 : le profileur voit le temps et l'espace

> Runbook exhaustif pour présenter la brique #2 d'`intreepid`, en interne (technique)
> **et** au métier. Elle prolonge la brique #1 : le profileur couvre désormais les
> **4 types** de colonnes (catégoriel, numérique, **temporel**, **spatial**) et l'agent
> refuse maintenant **deux** pièges au lieu d'un. Suis-le pas à pas ; commandes, sorties
> réelles et répliques sont prêtes.
>
> Setup commun (une fois) : voir [`README.md`](README.md). Prérequis : avoir vu (ou
> pouvoir résumer) la [démo brique #1](brique-1-analyste-honnete.md) — celle-ci
> s'appuie dessus. Durée : **7–9 min** + Q&A.

---

## 0. Ce que cette démo prouve — et ce qu'elle ne prouve pas

**Le pitch en une phrase :** *le profileur lit maintenant une carte d'identité des
données dans le temps ET dans l'espace — sans jamais voir une ligne ni une coordonnée —
et l'agent refuse un piège causal plus subtil que dans la brique #1.*

**Ce que la démo établit (réel) :**
- le proxy statistique couvre les **4 types** de l'architecture §4.2 : le LLM reçoit une
  carte d'identité **temporelle** (bornes, trous de série, saisonnalité, volume/an) et
  **spatiale** (emprise, coordonnées hors zone, validité géométrique) — toujours **sans
  lire une ligne ni une coordonnée brute** (P1/P2) ;
- l'agent **repère un changement de collecte invisible** (deux années entières
  manquantes) et des **coordonnées aberrantes** (points hors de la Suisse) ;
- il **refuse un piège causal** (« la baisse de volume prouve que les routes sont plus
  sûres ») en expliquant *pourquoi* — c'est le durcissement de la brique #1 ;
- ces comportements sont **testés en continu** (oracle N=5, tolérance zéro sur les faux
  patterns) ;
- la géométrie est traitée par l'extension DuckDB `spatial`, sur une connexion **toujours
  read-only** (P3).

**Ce que la démo NE prétend PAS (à dire — c'est ce qui rend le reste crédible) :**
- pas d'interface, pas d'arbre ni de carte ;
- **aucune vraie question métier résolue** : le jeu reste un sous-ensemble de test avec
  des anomalies *plantées* (trou 2018-2019, points hors zone) — connues d'avance ;
- la densité spatiale par maille et le plus-proche-voisin sont **explicitement différés**
  (message « prévu / non implémenté ») — la version correcte est H3 multi-résolution
  anti-MAUP, une brique à part entière ;
- c'est toujours un **walking skeleton** : la donnée est mono-dataset, sans croisement.

Dire ça d'entrée **désarme** le sceptique et installe la confiance.

---

## 1. Pré-vol (juste avant la séance)

Le setup une-fois (uv, `claude setup-token`, `ANTHROPIC_API_KEY` absente) est dans
[`README.md`](README.md). Juste avant de présenter, depuis `intreepid/src` :

```bash
# a) La suite déterministe passe (rapide, sans réseau)
uv run pytest -q -m "not agent"      # attendu : 23 passed

# b) L'oracle agent passe (LENT ~6 min, 5 runs réels) — LANCE-LE AVANT la séance,
#    garde la sortie verte à l'écran ; ne le lance PAS en direct.
uv run pytest -q -m agent            # attendu : 1 passed
```

> Astuce : garde un terminal avec le `1 passed` de l'oracle déjà affiché — c'est ta
> preuve « les faits temporel/spatial ET les deux refus sont stables, pas un coup de
> chance ».

---

## 2. Le déroulé de la démo

**Lance une seule fois :**
```bash
uv run python -m intreepid.demo
```
La sortie a deux parties : la **carte d'identité statistique** (les 4 types), puis le
**verdict** de l'agent. Les extraits ci-dessous sont réels (la formulation du verdict
varie d'un run à l'autre ; les comportements-clés sont stables et testés).

### Acte 1 — « Il voit maintenant le temps et l'espace »  (~1,5 min)

Dans la partie brute, montre les **deux nouveaux blocs**. Le bloc **temporel** :

```json
"date": {
  "type": "temporal", "n": 4314, "min": "2011-01-01", "max": "2025-12-01",
  "series_gaps_months": 24,
  "seasonality_by_month": {"1":260,"2":254, ... "8":450, ... "12":301},
  "volume_by_year": {"2011":328, "2017":334, "2020":283, ... "2025":370}
}
```

Le bloc **spatial** :

```json
"geom": {
  "type": "spatial", "n": 4314, "srid_declared": 2056,
  "geometry_types": {"POINT": 4314},
  "invalid_rate": 0.0, "out_of_envelope_rate": 0.0167,
  "extent": {"min_x": 2487596, "max_x": 2831482, "min_y": 1076996, "max_y": 1290216},
  "nearest_neighbor": "prévu / non implémenté (brique ultérieure : H3 ...)"
}
```

- **À dire (technique) :** « Même principe que la brique #1 — des agrégats, jamais de
  brut — mais étendu au temps et à l'espace. La géométrie est résumée par DuckDB
  `spatial` : emprise, taux de points hors zone, validité. Le LLM ne reçoit *aucune*
  coordonnée. Et on assume le périmètre : la densité par maille est marquée *prévu*, pas
  bricolée. »
- **À dire (métier) :** « Il lit vos données dans le temps et sur le territoire comme il
  lisait les catégories — sans que les positions individuelles quittent votre système. »

### Acte 2 — « Il voit un changement de collecte invisible à l'œil »  (~1,5 min)

```
[fait] La série `date` présente 24 mois manquants : volume_by_year saute de 2017 (334)
       à 2020 (283) — les années 2018 et 2019 sont entièrement absentes.
       → 24 mois de trou = exactement 2018 + 2019. C'est un défaut de couverture
         (extraction partielle ou changement de collecte), PAS une absence d'accidents.
```

- **À dire :** « Personne ne lui a dit que 2018-2019 manquaient. Il l'a déduit du profil
  temporel et il *qualifie* le trou : ce n'est pas "zéro accident", c'est "la donnée
  n'a pas été collectée". C'est le genre de piège qui fausse une tendance si on ne le
  voit pas. »
- Bonus (selon le run) : il repère aussi le **creux 2020** (283) et note que c'est
  *l'année COVID*, donc un point atypique — pas un début de tendance. « Il ne confond pas
  un accident de collecte, un choc externe, et une vraie tendance. »

### Acte 3 — « Il repère des coordonnées aberrantes sans voir la carte »  (~1 min)

```
[fait] geom : 1.67% des points (~72 sur 4314) tombent hors de l'emprise attendue pour
       le SRID 2056 déclaré.
       → 100% des géométries sont des POINT, aucune nulle/vide/invalide, mais 1.67%
         sortent de la Suisse — coordonnées suspectes (adresse dégradée, inversion X/Y,
         valeur par défaut). La fiche signale le piège : GPS depuis 2016, adresse avant.
```

- **À dire (métier) :** « Il vous dit "certains points ne sont pas en Suisse" **sans
  jamais afficher une position**. La confidentialité géographique est préservée, et il
  attrape quand même les erreurs de géocodage. »
- **À dire (technique) :** « L'emprise déclarée (SRID 2056, LV95) vient de la *fiche*,
  pas de la géométrie — parce que le CRS embarqué peut mentir. Le fait est ancré sur la
  connaissance métier, pas sur une étiquette technique. »

### Acte 4 — LE MOMENT CLÉ : « Il refuse un piège plus subtil qu'avant »  (~2 min)

La brique #1 refusait un croisement absent (gravité×mois). La brique #2 refuse en plus
un **piège causal** :

```
[refusé] On ne peut PAS conclure que les routes deviennent plus sûres.
         → Double refus. D'une part le volume ne baisse même pas (328 en 2011, 370 en
           2025). D'autre part, même face à une vraie baisse, en déduire une amélioration
           de la sécurité exigerait une normalisation par l'exposition (véhicules-km,
           population, parc) et un contrôle des changements de collecte — indisponibles.
           Un comptage brut ne mesure pas un risque.
```

- **À dire (le pitch) :** « On lui tend un piège en deux temps : "le volume baisse-t-il,
  et si oui, les routes sont-elles plus sûres ?". Un chatbot mordrait. Le nôtre fait
  *deux* choses : il corrige la **prémisse fausse** (le volume ne baisse pas), et il
  explique que même si elle était vraie, la conclusion causale serait **non fondée sans
  normalisation**. C'est de la rigueur, pas de l'esquive. »
- Rappelle le refus hérité (toujours là) :
```
[refusé] La relation gravité/mois ne peut pas être établie → il faudrait croiser
         `severity` et `accident_month` ; je n'ai que les distributions séparées.
```
- **Enchaîne (métier) :** « Chaque refus est motivé et *actionnable* : il vous dit
  exactement quelle donnée manquerait pour répondre. »

### Acte 5 — « C'est testé, et il ne peut pas tricher »  (~1 min)

```bash
uv run pytest -q -m "not agent"   # 23 passed  → stats exactes (golden, dont temporel/spatial)
```
Puis montre le `1 passed` de l'oracle (pré-vol) :

- **À dire (technique) :** « L'oracle ré-évalue l'agent **5 fois**. Il exige les faits
  temporel et spatial (≥4/5) **et** une tolérance zéro sur *deux* faux patterns : ni
  gravité×mois, ni volume→sûreté ne doivent jamais passer en "fait". Le double refus est
  une propriété **testée**. »
- Isolation (inchangée depuis brique #1) : l'agent n'a que les 3 outils MCP ; fichier et
  shell désactivés (`tests/test_runner_options.py`). L'extension `spatial` tourne sur une
  connexion **read-only** — lecture géométrique, zéro écriture.

### Bonus — « Il flaire que le jeu est truqué »  (~30 s, si le temps le permet)

```
[hypothèse] vitesse_limite_kmh a une distribution quasi uniforme suspecte (~20% chacun) :
            peu plausible en accidentologie réelle (le 50 urbain devrait dominer). De
            plus 19,6% de limites à 120 km/h pour seulement 9% d'autoroute est
            incohérent → signal fort d'un sous-ensemble échantillonné/synthétique.
```

- **À dire :** « On lui a donné un jeu de test partiellement synthétique — et il l'a
  **repéré tout seul**, en croisant deux distributions dans sa tête. C'est exactement la
  vigilance qu'on veut avant de tirer une conclusion sur des vraies données. »

---

## 3. Argumentaires par audience (antisèche)

**Interne technique** — insister sur :
- les 4 types couverts en SQL DuckDB pushdown (temporel + spatial), **zéro dépendance
  embarquée** (pas de pysal/h3/popmon) ;
- `spatial` sur connexion **read-only** (P3) via un context manager qui nettoie son
  dossier temporaire (dette brique #1 soldée) ; SRID lu de la fiche (piège CRS) ;
- l'oracle N=5 à **deux** faux patterns en tolérance zéro comme définition exécutable de
  la rigueur ; charte généralisée **sans valeur de fixture en dur** (anti-surajustement) ;
- le périmètre assumé : NN/densité **différés** (message explicite), pas de bricolage
  mono-résolution qui modéliserait l'anti-pattern MAUP.

**Métier (non-expert)** — insister sur :
- « il lit le temps et le territoire de vos données sans que les positions sortent » ;
- « il voit un trou de collecte de 2 ans que personne ne lui a signalé » ;
- « il refuse une conclusion séduisante mais fausse ("moins d'accidents = plus sûr") et
  vous dit ce qui manquerait pour la valider » ;
- honnêteté : « c'est toujours une preuve de mécanique ; la vraie valeur, c'est **votre**
  question sur **vos** données — la prochaine étape ».

---

## 4. Objections probables & réponses

| Objection | Réponse |
|---|---|
| « Le trou 2018-2019 est planté, c'est arrangé. » | Oui, assumé : banc de test à vérité connue, pour prouver la mécanique de façon reproductible. Le point est qu'il le *qualifie* (collecte, pas absence) sans qu'on l'ait prévenu. |
| « Il voit quand même la géométrie ? » | Non : il ne reçoit que des agrégats spatiaux (emprise, taux hors-zone, validité). Aucune coordonnée n'entre dans le contexte du LLM (P1/P2). |
| « Pourquoi pas de carte de densité / hotspots ? » | Volontairement différé : bien fait, c'est H3 multi-résolution (anti-MAUP), une brique dédiée. Un quadrillage naïf induirait l'artefact statistique qu'on veut éviter. Le code le dit : « prévu / non implémenté ». |
| « Le double refus, c'est de l'esquive. » | Non : chaque refus nomme la donnée manquante (croisement, ou normalisation par l'exposition). C'est actionnable, et c'est testé (tolérance zéro). |
| « Ça passe à l'échelle ? » | DuckDB `spatial` profile des millions de points ; l'agent ne lit que le résumé → le contexte ne grossit pas avec les données. |

---

## 5. Ce que ça implique — maintenant et pour la suite

**Maintenant :** le profileur est **complet** sur les 4 types de l'architecture v0.2, et
la posture d'honnêteté tient sur des pièges temporel/spatial/causal. Deux dettes de la
brique #1 sont soldées (skewness ; fuite de dossier temporaire).

**Prochaine étape de plus fort rendement (le vrai verrou, inchangé) :** brancher **une
vraie question métier sur un vrai jeu**, avec **une vraie personne métier** — c'est ce
qui transforme « la mécanique marche » en « ça m'apporte quelque chose ». Dataset pilote
pressenti : accidents OFROU.

**Ensuite (roadmap, ordre de valeur) :** le croisé à la demande + le modèle nul (réfuter,
pas seulement s'abstenir) ; la densité spatiale H3 multi-résolution (anti-MAUP) ; le
greffier/trace ; puis l'arbre, la carte, la couche connaissance.

---

## 6. Plan B (si la démo live échoue)

- Auth/réseau capricieux → montre la sortie **déjà capturée** (ce fichier §2) + le
  `1 passed` de l'oracle pré-vol : les comportements sont **testés**, donc démontrables
  même sans live.
- La formulation du verdict varie d'un run à l'autre ; les comportements-clés sont
  **stables et testés** : `999 = fait`, trou temporel = `fait`, hors-emprise = `fait`,
  gravité×mois = `refusé`, volume→sûreté = `refusé`.
