# Démo brique #4 — le greffier (capture épisodique)

**But** : montrer la *documentation fidèle à coût zéro* — la trace complète d'une
session de l'analyste (raisonnement, appels MCP, agrégats, verdict avec refus
motivés), persistée en arbre immuable DuckDB et **rejouée** (P4).

## Lancer

```bash
uv run python -m intreepid.demo_greffier
```

> **Windows** : si vous redirigez la sortie vers un fichier, définissez d'abord
> `PYTHONIOENCODING=utf-8` — le rendu de l'arbre utilise des emoji (💭 🔧).

## Ce que ça montre

1. L'analyste tourne une session **enregistrée** (thinking activé).
2. Le verdict s'affiche (faits / hypothèses / refus).
3. L'arbre capturé est **rechargé depuis DuckDB** puis rendu : racine → 💭 raisonnement
   → 🔧 appels MCP + agrégats → observations (les `refusé`/`hypothèse` = branches
   mortes documentées).

## Sortie réelle capturée

Run du 2026-07-31 (fixture OFROU synthétique, `model=opus`, thinking summarized activé) :

```text
=== run analyste (enregistré) ===
- [fait] vitesse_limite_kmh contient la valeur 999 (0,23 % des 4314 lignes), non documentée dans la fiche du dataset alors que la colonne est censée porter une vitesse limite en km/h
- [fait] La colonne date présente un trou de série de 24 mois : volume_by_year ne contient aucune ligne pour 2018 ni 2019, alors que la plage va de 2011-01-01 à 2025-12-01
- [refusé] L'absence de 2018-2019 et les variations de volume annuel (283 en 2020 vs 370 en 2025) ne permettent PAS de conclure que les accidents ont diminué ou que la route est devenue plus sûre
- [fait] geom : 1,67 % des points sont hors de l'emprise attendue pour le SRID 2056 (LV95) déclaré par la fiche
- [fait] Le canton BE est sur-concentré au-delà du hasard : 636 accidents observés contre 178,8 attendus sous le modèle nul conditionné sur l'exposition déclarée (std_excess 34,2 ; pseudo-p = 0,001 sur 999 permutations)
- [fait] ZH domine le comptage brut (781 accidents, 18,1 % du dataset) mais n'est PAS sur-concentré : 878,1 attendus, std_excess -3,28, pseudo-p = 1
- [hypothèse] severity est fortement concentrée sur 'accident avec blessés légers' (76,8 %), contre 22,0 % de blessés graves et 1,2 % de tués
- [hypothèse] type_route est concentrée sur 'route principale' (50,2 %) et 'route secondaire' (36,3 %), les autoroutes ne pesant que 9,0 %
- [hypothèse] La distribution de vitesse_limite_kmh est anormalement plate : 60 (20,7 %), 30 (20,4 %), 50 (20,0 %), 120 (19,6 %), 80 (19,1 %) — cinq modalités quasi équiprobables
- [fait] accident_month ne présente aucune anomalie : 4314 valeurs dans [1, 12], aucun null, aucun outlier à 3 sigma, saisonnalité cohérente (creux 254-260 en janvier-février, pic 450 en août)

=== arbre de session rejoué (load → render) ===
session 6f57788f142a4de4ae4a9fd6f06f2448 [closed] — 'Profile les colonnes du dataset et rends ton verdict : y a-t-il des valeurs suspectes ? peut-on conclure une tendance du monde réel depuis un volume ?' (model=opus)
  ├─ 🔧 ToolSearch({"query": "select:describe,profile_stats,concentration_test…)
  │    └─ → No matching deferred tools found
  ├─ 🔧 ToolSearch({"query": "dataset describe profile statistics concentratio…)
  │    └─ → [{'type': 'tool_reference', 'tool_name': 'mcp__intreepid__describe'}, {'type': 'tool_reference', 't…
  ├─ 🔧 mcp__intreepid__describe({})
  │    └─ → {"columns":{"accident_month":{"sens":"mois de l'accident (1-12)","type":"numeric"},"canton":{"sens"…
  ├─ 🔧 mcp__intreepid__list_datasets({})
  │    └─ → {"result":["accidents_route"]}
  ├─ 💭 I need to profile all the columns in the dataset.
  ├─ 🔧 mcp__intreepid__profile_stats({})
  │    └─ → {"accident_month":{"type":"numeric","n":4314,"min":1,"max":12,"mean":6.771,"median":7,"p5":1,"p25":…
  ├─ 💭 I'm reviewing the data quality issues across the dataset: the speed limit field has a sentinel valu…
  ├─ 🔧 mcp__intreepid__concentration_test({"unit_col": "canton"})
  │    └─ → {"unit_col":"canton","exposure_model":"declared:canton_exposure.parquet","n_permutations":999,"seed…
  ├─ [fait] vitesse_limite_kmh contient la valeur 999 (0,23 % des 4314 lignes), non documentée dans la fiche du…
  ├─ [fait] La colonne date présente un trou de série de 24 mois : volume_by_year ne contient aucune ligne pour…
  ├─ [refusé] L'absence de 2018-2019 et les variations de volume annuel (283 en 2020 vs 370 en 2025) ne permetten…
  ├─ [fait] geom : 1,67 % des points sont hors de l'emprise attendue pour le SRID 2056 (LV95) déclaré par la fi…
  ├─ [fait] Le canton BE est sur-concentré au-delà du hasard : 636 accidents observés contre 178,8 attendus sou…
  ├─ [fait] ZH domine le comptage brut (781 accidents, 18,1 % du dataset) mais n'est PAS sur-concentré : 878,1 …
  ├─ [hypothèse] severity est fortement concentrée sur 'accident avec blessés légers' (76,8 %), contre 22,0 % de ble…
  ├─ [hypothèse] type_route est concentrée sur 'route principale' (50,2 %) et 'route secondaire' (36,3 %), les autor…
  ├─ [hypothèse] La distribution de vitesse_limite_kmh est anormalement plate : 60 (20,7 %), 30 (20,4 %), 50 (20,0 %…
  ├─ [fait] accident_month ne présente aucune anomalie : 4314 valeurs dans [1, 12], aucun null, aucun outlier à…
```

**À noter** : les deux nœuds 💭 montrent le raisonnement capturé (résumé) ; le nœud
`[refusé]` est une branche morte documentée — le refus causal motivé fait partie de la
trace, pas seulement des conclusions. Les deux premiers appels `ToolSearch` sont la
mécanique du harnais agent, capturés fidèlement (grain événement, pas de tri à chaud).

## Robustesse (optionnel)

Interrompre le run (Ctrl-C) puis recharger : la session est scellée `aborted` avec la
raison, et les nœuds capturés avant l'interruption sont conservés (double filet).
