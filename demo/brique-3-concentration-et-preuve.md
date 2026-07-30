# Démo — Brique #3 : concentration et preuve par modèle nul

> Runbook exhaustif pour présenter la brique #3 d'`intreepid`, en interne (technique)
> **et** au métier. C'est le premier **organe de preuve** : l'outil ne détecte pas
> seulement un excès apparent — il le **teste** contre un contrefactuel
> (redistribution multinomiale, 999 permutations, seed fixé) et rend un pseudo-p.
> Le contraste entre `most_concentrated` et `highest_raw_count` est la démonstration
> centrale : le plus gros volume n'est **pas** forcément un excès réel.
>
> Setup commun (une fois) : voir [`README.md`](README.md). Prérequis : avoir vu (ou
> pouvoir résumer) les démos briques #1 et #2. Durée : **5–7 min** + Q&A.

---

## 0. Ce que cette démo prouve — et ce qu'elle ne prouve pas

**Le pitch en une phrase :** *le modèle nul distingue « beaucoup » de « trop » — et
prouve que le canton au plus gros comptage brut n'est pas un point noir.*

**Ce que la démo établit (réel) :**
- `concentration_test` calcule, pour chaque unité, un écart standardisé de Poisson
  (observed − expected) / √expected, puis compare l'unité la plus concentrée aux
  999 redistributions aléatoires sous le modèle nul ;
- l'exposition est **déclarée dans la fiche** (`canton_exposure.parquet`) : le modèle nul
  n'est donc pas uniforme mais pondéré par l'exposition réelle (kilométrage, population,
  ou autre) — le LLM ne reçoit que des agrégats (P2) sur une connexion read-only (P3) ;
- le seed est fixé (P4) : la sortie est **reproductible** ;
- le contraste `most_concentrated` (BE) vs `highest_raw_count` (ZH) est l'argument central.

**Ce que la démo NE prétend PAS :**
- pas de carte, pas d'arbre ;
- le jeu reste un banc de test (anomalies plantées, fixture synthétique) ;
- l'outil détecte la concentration statique par rapport à l'exposition déclarée — il ne
  modélise pas la saisonnalité ni la tendance (brique #2) ni le croisement de variables.

---

## 1. Pré-vol (juste avant la séance)

```bash
# a) Suite déterministe verte (rapide, sans réseau)
uv run pytest -q -m "not agent"      # attendu : 36 passed

# b) Oracle agent (LENT ~6 min, 5 runs réels) — LANCE-LE AVANT la séance
uv run pytest -q -m agent            # attendu : 1 passed
```

---

## 2. La question posée

```
"Certaines valeurs de la colonne `canton` concentrent-elles anormalement les
événements ? Une valeur au plus gros comptage est-elle forcément un excès réel ?
Utilise le modèle nul et rends ton verdict."
```

---

## 3. La sortie réelle de `concentration_test`

Partie déterministe — capturée sur `fixtures/accidents_seed.parquet`, seed 42,
999 permutations, exposition `canton_exposure.parquet` :

```json
{
  "unit_col": "canton",
  "exposure_model": "declared:canton_exposure.parquet",
  "n_permutations": 999,
  "seed": 42,
  "n_total": 4314,
  "n_units": 26,
  "most_concentrated": {
    "unit": "BE",
    "observed": 636,
    "expected": 178.77,
    "std_excess": 34.2,
    "pseudo_p": 0.001
  },
  "highest_raw_count": {
    "unit": "ZH",
    "observed": 781,
    "expected": 878.09,
    "std_excess": -3.28,
    "pseudo_p": 1.0
  }
}
```

---

## 4. Le déroulé de la démo

**Lance une seule fois :**
```bash
uv run python -m intreepid.demo
```
La sortie a trois parties : le profil statistique (brique #2), le résultat de
`concentration_test` (ci-dessus), puis le verdict de l'agent. Les extraits ci-dessous
sont réels pour la partie déterministe.

### Acte 1 — « BE : vrai point noir, prouvé »  (~2 min)

```json
"most_concentrated": {
  "unit": "BE",
  "observed": 636,
  "expected": 178.77,
  "std_excess": 34.2,
  "pseudo_p": 0.001
}
```

- **À dire :** « BE a 636 accidents observés, alors que l'exposition prédit 178. L'écart
  standardisé est de 34.2 — autrement dit, plus de 34 écarts-types au-dessus de ce qu'on
  attendrait sous le modèle nul. Sur 999 redistributions aléatoires, *aucune* n'atteint
  ce niveau : pseudo-p = 0.001 (minimum atteignable à 999 permutations). C'est une preuve
  statistique d'excès réel, pas une impression. »
- **À dire (technique) :** « Le modèle nul n'est pas uniforme : il redistribue les 4 314
  événements proportionnellement à l'exposition déclarée dans la fiche. Un canton grand ne
  devrait pas dominer par sa taille — il est *attendu* d'en avoir plus. BE dépasse cette
  attente de façon non explicable par le hasard. »

### Acte 2 — LE MOMENT CLÉ : « ZH : plus gros volume, mais PAS un point noir »  (~2 min)

```json
"highest_raw_count": {
  "unit": "ZH",
  "observed": 781,
  "expected": 878.09,
  "std_excess": -3.28,
  "pseudo_p": 1.0
}
```

- **À dire (le pitch) :** « ZH a le plus grand nombre brut d'accidents : 781. Un analyste
  non averti en ferait son premier point d'attention. Mais ZH est aussi le canton le plus
  peuplé, avec le réseau routier le plus chargé. Une fois l'exposition prise en compte,
  ZH *attendait* 878 accidents — il en a 3,28 écarts-types de *moins* que prévu. Son
  pseudo-p est 1.0 : aucun excès. C'est exactement le piège "volume ≠ excès". »
- **À dire (métier) :** « Si vous priorisez vos interventions sur le plus gros comptage,
  vous allez à Zurich. Si vous priorisez sur l'excès réel par rapport à l'exposition,
  vous allez à Berne. Ce sont deux politiques de priorisation opposées — et l'une d'elles
  est statistiquement non fondée. »
- **Insister :** std_excess de ZH = **−3.28** (négatif, pas "environ zéro") : ZH est en
  réalité *sous la valeur attendue* pour son niveau d'exposition. Ce n'est pas de la
  prudence, c'est un signal inverse.

### Acte 3 — « Le verdict de l'agent »  (~1,5 min)

Sortie réelle capturée (`uv run python -m intreepid.demo`, un run) :

```
- [fait] La valeur au plus gros comptage brut de `canton` (ZH, 781 événements) n'est
  PAS un excès réel : le modèle nul par permutation conditionné sur l'exposition
  déclarée donne attendu = 878,09, std_excess = -3,28 et pseudo-p = 1.
  (Réponse directe à la question : non, un plus gros comptage n'implique pas une
  sur-concentration. ZH est même EN DESSOUS de son attendu — son comptage élevé ne
  reflète que le volume d'exposition sous-jacent. Fait établi sur la sortie de
  concentration_test — agrégats + pseudo-p —, pas sur des lignes brutes.)
```

- **À dire :** « L'agent ne s'est pas fait piéger : interrogé sur le plus gros comptage,
  il répond *non, ce n'est pas un excès* — et il **cite la preuve** (attendu 878, écart
  −3,28, pseudo-p = 1). Il classe cela en `fait` parce que c'est un fait *établi par le
  modèle nul*, pas une impression. Et il précise qu'il ne l'a établi que sur des agrégats,
  jamais sur des lignes brutes (P2). »
- **Note (honnêteté) :** la formulation varie d'un run à l'autre. Ce run a mis en avant la
  réfutation de ZH (le point le plus tranchant) ; l'oracle N=5 (`-m agent`) vérifie que sur
  ≥ 4 runs sur 5 l'agent affirme aussi **BE** comme excès réel (pseudo-p bas) en `fait`, et
  que **jamais** il n'affirme ZH comme un excès. Le contraste `most_concentrated` vs
  `highest_raw_count` de l'Acte 3 (déterministe) porte, lui, l'histoire complète à chaque run.

### Acte 4 — « C'est testé, et reproductible »  (~30 s)

```bash
uv run pytest -q -m "not agent"   # 36 passed → stats exactes, dont concentration golden
```

- **À dire :** « La sortie est déterministe (seed 42, 999 permutations fixées). Les
  golden tests verrouillent les valeurs exactes de std_excess et pseudo_p pour BE et ZH.
  Si quelqu'un change l'exposition ou la fixture, les tests cassent immédiatement. »

---

## 5. Message générique

> **L'outil fonctionne sur n'importe quelle unité et n'importe quelle exposition.**
> Ici : canton / kilométrage de réseau routier. Même logique avec : magasin / surface de
> vente, commune / population, produit / part de marché, équipe / nombre d'employés.
> Le dataset accidents est un **banc de test à vérité connue** — il prouve la mécanique
> de façon reproductible. La vraie valeur, c'est votre question sur vos données.

---

## 6. Argumentaires par audience (antisèche)

**Interne technique** — insister sur :
- modèle nul multinomial pondéré (exposition déclarée dans la fiche, pas uniforme) ;
- pseudo-p exact sur 999 permutations, seed fixé (P4), connexion read-only (P3) ;
- `_std_excess` de Poisson : (observed − expected) / √expected, zéro si E ≤ 0 ;
- golden tests verrouillent les valeurs numériques exactes (anti-régression) ;
- l'outil est **agnostique au domaine** : aucune valeur de fixture en dur dans le code.

**Métier (non-expert)** — insister sur :
- « le plus gros volume n'est pas le plus grand risque — Zurich en est la preuve » ;
- « Berne est un vrai point noir : l'excès est statistiquement prouvé, pas ressenti » ;
- « l'outil tourne sur n'importe quelle colonne catégorielle avec une exposition connue » ;
- honnêteté : « c'est toujours un banc de test ; la prochaine étape c'est votre question
  sur vos données ».

---

## 7. Objections probables & réponses

| Objection | Réponse |
|---|---|
| « BE et ZH sont des fixtures plantées. » | Oui, assumé : vérité connue d'avance = mécanique prouvable de façon reproductible. Sur vos données, l'outil tourne sans modification — l'exposition vient de la fiche. |
| « Pourquoi 999 permutations et pas plus ? » | Précision ≈ 1/1000 sur le pseudo-p, moins d'une seconde. Le cap défensif est à 9 999. Suffisant pour trancher BE (pseudo-p = 0.001 = minimum atteignable) et ZH (pseudo-p = 1.0). |
| « L'exposition "déclarée dans la fiche" — qui la fournit ? » | La personne métier, au moment de configurer la fiche. C'est exactement le point : l'outil explicite l'hypothèse, il ne l'invente pas. Si l'exposition est discutable, on la change dans la fiche. |
| « Le pseudo-p 0.001 pour BE, c'est le minimum — est-ce vraiment significatif ? » | C'est le minimum atteignable à 999 permutations : sur aucun des 999 tirages aléatoires BE n'a atteint un excès pareil. Avec un std_excess de 34.2, augmenter le nombre de permutations ne changerait pas le verdict. |
| « ZH est à −3.28 — c'est étrange, pas juste "pas d'excès". » | Oui : ZH est *sous* son exposition attendue. Pas de sur-représentation, légère sous-représentation. C'est réel — et ça renforce encore le contraste avec BE. |

---

## 8. Ce que ça implique — maintenant et pour la suite

**Maintenant :** le premier organe de preuve est livré. L'outil distingue « beaucoup »
de « trop », de façon reproductible, sur n'importe quelle unité avec exposition. La démo
brique #3 est la première où l'agent peut dire « c'est prouvé » et pas seulement
« c'est plausible ».

**Prochaine étape de plus fort rendement (inchangée) :** brancher une vraie question
métier sur un vrai jeu, avec une vraie personne métier. Dataset pilote pressenti :
accidents OFROU.

**Ensuite (roadmap) :** le croisé à la demande ; la densité spatiale H3 multi-résolution
(anti-MAUP) ; le greffier/trace ; puis l'arbre, la carte, la couche connaissance.

---

## 9. Plan B (si la démo live échoue)

- Auth/réseau capricieux → montre la sortie `concentration_test` capturée (§3, JSON
  complet) + le `36 passed` des tests déterministes : BE vs ZH se démontre **sans
  réseau**, les valeurs sont verrouillées en CI.
- La formulation du verdict agent varie d'un run à l'autre ; les comportements-clés
  sont testables séparément (oracle N=5 en pre-flight).
