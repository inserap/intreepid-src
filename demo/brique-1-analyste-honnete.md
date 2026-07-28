# Démo — Brique #1 : l'analyste honnête

> Runbook exhaustif pour présenter la brique #1 d'`intreepid`, en interne (technique)
> **et** au métier. Objectif : **vendre le concept** sans rien survendre. Suis-le pas à
> pas ; les commandes, sorties attendues et répliques sont prêtes.
>
> Setup commun (une fois) : voir [`README.md`](README.md). Durée : **6–8 min** + Q&A.

---

## 0. Ce que cette démo prouve — et ce qu'elle ne prouve pas

**Le pitch en une phrase :** *un client LLM générique branché sur une base de données
confirmerait n'importe quel pattern qu'on lui suggère ; le nôtre refuse ce qu'il ne
peut pas prouver — et c'est vérifié automatiquement.*

**Ce que la démo établit (réel) :**
- l'agent raisonne sur la **forme statistique** des données **sans jamais lire une
  ligne brute** (confidentialité par conception) ;
- il **repère un vrai défaut** de donnée (un code sentinelle caché) ;
- il **refuse de fabriquer** une relation qu'il ne peut pas établir (le cœur de la
  fiabilité) ;
- ce comportement est **testé en continu** (pas une démo scriptée à la main) ;
- l'agent **ne peut pas techniquement** contourner ce canal (isolation structurelle).

**Ce que la démo NE prétend PAS (à dire — c'est ce qui rend le reste crédible) :**
- pas d'interface, pas d'arbre ni de carte ;
- **aucune vraie question métier résolue** : le jeu est un sous-ensemble de test avec
  des anomalies *plantées* (connues d'avance), pas des découvertes dans la nature ;
- la **valeur métier n'est pas encore validée** — elle le sera face à une vraie
  personne métier sur une vraie question (c'est la prochaine étape) ;
- c'est un **walking skeleton** : la plus petite traversée complète du système, pas
  un produit.

Dire ça d'entrée **désarme** le sceptique et installe la confiance.

---

## 1. Pré-vol (juste avant la séance)

Le setup une-fois (uv, `claude setup-token`, `ANTHROPIC_API_KEY` absente) est dans
[`README.md`](README.md). Juste avant de présenter, depuis `intreepid/src` :

```bash
# a) La suite déterministe passe (rapide, sans réseau)
uv run pytest -q -m "not agent"      # attendu : 18 passed

# b) L'oracle agent passe (LENT ~4 min, 5 runs réels) — LANCE-LE AVANT la séance,
#    garde la sortie verte à l'écran ; ne le lance PAS en direct (4 min de silence).
uv run pytest -q -m agent            # attendu : 1 passed
```

> Astuce : garde un terminal avec le `1 passed` de l'oracle déjà affiché — c'est ta
> preuve « ce n'est pas un coup de chance ».

---

## 2. Le déroulé de la démo

### Acte 1 — « Le LLM ne voit jamais tes données »  (~1 min)

**Lance :**
```bash
uv run python -m intreepid.demo
```

La première partie affiche la **carte d'identité statistique** que l'agent reçoit —
*à la place* des lignes brutes. Montre par exemple la colonne `vitesse_limite_kmh` :

```json
"vitesse_limite_kmh": {
  "type": "categorical", "n": 5000, "cardinality": 6, "entropy": 2.34,
  "top_k": [
    {"value": 60, "freq": 0.2066}, {"value": 30, "freq": 0.2024},
    {"value": 50, "freq": 0.2014}, {"value": 120, "freq": 0.1982},
    {"value": 80, "freq": 0.189},  {"value": 999, "freq": 0.0024}
  ]
}
```

- **À dire (technique) :** « L'agent ne reçoit que ces agrégats, calculés par DuckDB.
  Il ne peut pas lire une ligne individuelle — c'est structurel, on le montrera. »
- **À dire (métier) :** « Vos données sensibles ne partent jamais vers le modèle. Il
  travaille sur des résumés, comme un statisticien qui lit un tableau de bord, pas le
  fichier des personnes. »

### Acte 2 — « Il trouve ce qui cloche »  (~1,5 min)

La seconde partie affiche le **verdict** de l'agent. Le premier constat :

```
[fait] vitesse_limite_kmh contient la valeur 999 (0,24 % des 5000 lignes, ~12 lignes)
       → valeur hors de tout régime de vitesse suisse plausible ; la fiche ne
         documente aucun code sentinelle : très probablement un marqueur
         'inconnu/non renseigné'.
```

- **À dire :** « Personne ne lui a parlé du 999. Il l'a repéré seul dans la
  distribution, et a *raisonné* que c'est un code sentinelle — le genre de piège qui
  fausse une moyenne si on ne le voit pas. »

Puis un constat plus fin (selon le run, la formulation varie) :

```
[hypothèse] vitesse_limite_kmh a une distribution anormalement plate (~20 % chacun) →
            suggère un échantillon stratifié par vitesse, non extrapolable à la
            population réelle. À vérifier auprès du producteur.
```

- **À dire (métier) :** « Ça, c'est précieux : il vous prévient que le jeu n'est
  peut-être pas représentatif — *avant* que vous tiriez une conclusion fausse. »

### Acte 3 — LE MOMENT CLÉ : « Il refuse de deviner »  (~1,5 min)

```
[refusé] Les accidents ne sont pas plus graves en fin d'année — je ne peux pas
         répondre à cette question.
         → il faudrait croiser le mois et la gravité ; je n'ai que les distributions
           séparées, jamais leur relation. Aucun élément ne soutient ni n'infirme.
```

- **À dire (le pitch) :** « On lui a *tendu un piège* dans la question : "les accidents
  sont-ils plus graves en fin d'année ?". Un chatbot générique aurait sorti une réponse
  confiante et fausse. Le nôtre dit : *je n'ai pas la donnée pour ça, je refuse.* »
- **Enchaîne (métier) :** « C'est **exactement** ce qui fait qu'on peut lui faire
  confiance. Un outil qui invente une fois a perdu sa crédibilité pour toujours. »
- Bonus (il pousse la rigueur) : il note que même *avec* le croisement, ~60 accidents
  mortels donneraient ~5 cas/mois — trop peu pour conclure. « Il connaît les limites
  statistiques, pas seulement les données. »

### Acte 4 — « Ce n'est pas une démo scriptée : c'est testé »  (~1 min)

```bash
uv run pytest -q -m "not agent"   # 18 passed  → les stats sont exactes (golden)
```

Puis explique l'oracle (montre le `1 passed` déjà obtenu) :

- **À dire (technique) :** « L'agent est ré-évalué **5 fois** à chaque run de test, avec
  une règle à **tolérance zéro** : s'il affirme *une seule fois* le faux pattern comme
  un fait, le test échoue. Le refus n'est pas un hasard, c'est une propriété testée. »
- Fichier à ouvrir si on te le demande : `tests/test_agent_eval.py`.

### Acte 5 — « Il ne peut pas tricher »  (~1 min)

```bash
uv run pytest tests/test_runner_options.py -q   # 7 passed
```

- **À dire (technique) :** « Ce test *garde* l'invariant : l'agent n'a accès qu'à trois
  outils de lecture statistique. Les outils fichier/shell (lire un fichier, lancer une
  commande) sont **désactivés**. Même si son prompt le lui demandait, il ne pourrait pas
  ouvrir le Parquet. La confidentialité n'est pas une promesse, c'est une contrainte. »
- **À dire (métier) :** « L'isolation est *dans la mécanique*, pas dans la bonne volonté
  du modèle. »

---

## 3. Argumentaires par audience (antisèche)

**Interne technique** — insister sur :
- le proxy statistique (P2 : jamais de lignes brutes) et l'isolation MCP-only (P3) ;
- l'oracle à seuils N=5 + tolérance zéro comme *définition exécutable* de la fiabilité ;
- le gate qualité (ruff / pyright / pytest) et la dette de typage assumée (mode
  `standard`, déviation tracée par ADR-0008, ratchet planifié) ;
- le coût : un serveur MCP + un runner d'agent, ~zéro infra (DuckDB embarqué).

**Métier (non-expert)** — insister sur :
- « il documente son incertitude et refuse de deviner » = fiabilité ;
- « vos données ne partent pas au modèle » = confidentialité ;
- « il repère les pièges de la donnée que même un expert pourrait rater » = valeur ;
- honnêteté : « aujourd'hui c'est une preuve de mécanique ; la vraie démo de valeur,
  c'est avec **votre** question sur **vos** données — c'est ce qu'on veut faire avec
  vous ».

---

## 4. Objections probables & réponses

| Objection | Réponse |
|---|---|
| « C'est juste un chatbot sur une base. » | Non : un chatbot confirmerait le faux pattern. La différence testée, c'est le **refus**. C'est le point 3. |
| « Les anomalies sont plantées, c'est arrangé. » | Oui, assumé : c'est un *banc de test* à vérité connue, pour prouver la mécanique de façon reproductible. L'étape suivante est un vrai jeu. |
| « Il n'y a pas d'interface. » | Volontaire (anti-cathédrale) : on traverse d'abord tout le système en minuscule. L'UI (chat + arbre + carte) est la suite, une fois la valeur validée. |
| « Est-ce que ça passe à l'échelle ? » | DuckDB lit des milliards de lignes ; l'agent ne lit que des résumés → le contexte du LLM ne grossit pas avec les données. |
| « Et si le modèle hallucine quand même ? » | C'est justement ce que l'oracle traque (tolérance zéro). Et la couche critique/modèles-nuls viendra durcir encore (roadmap). |

---

## 5. Ce que ça implique — maintenant et pour la suite

**Maintenant :** la brique valide **la mécanique et la posture** (proxy statistique +
refus honnête + isolation + preuve en CI). C'est le socle sur lequel tout le reste se
branche.

**Prochaine étape de plus fort rendement (le vrai verrou) :** brancher **une vraie
question métier sur un vrai jeu**, avec **une vraie personne métier** dans la boucle —
c'est ce qui transformera « la mécanique marche » en « ça m'apporte quelque chose ».
Concrètement : confirmer le dataset pilote (accidents OFROU pressenti) et un
destinataire qui a une question aiguë.

**Ensuite (roadmap, dans l'ordre de valeur) :** le croisé à la demande + le modèle nul
(pour *réfuter* et pas seulement *s'abstenir*) ; le greffier/trace (capitaliser le
raisonnement) ; puis l'arbre, la carte, la couche connaissance.

---

## 6. Plan B (si la démo live échoue)

- Auth/réseau capricieux → montre la sortie **déjà capturée** (ce fichier §2) + le
  `1 passed` de l'oracle pré-vol : le comportement est **testé**, donc démontrable même
  sans live.
- Le verdict de l'agent varie d'un run à l'autre dans sa formulation ; les **deux
  comportements clés sont stables et testés** : `999 = fait`, `gravité×mois = refusé`.
