# Démo brique #4 — le greffier (capture épisodique)

**But** : montrer la *documentation fidèle à coût zéro* — la trace complète d'une
session de l'analyste (raisonnement, appels MCP, agrégats, verdict avec refus
motivés), persistée en arbre immuable DuckDB et **rejouée** (P4).

## Lancer

```bash
uv run python -m intreepid.demo_greffier
```

## Ce que ça montre

1. L'analyste tourne une session **enregistrée** (thinking activé).
2. Le verdict s'affiche (faits / hypothèses / refus).
3. L'arbre capturé est **rechargé depuis DuckDB** puis rendu : racine → 💭 raisonnement
   → 🔧 appels MCP + agrégats → observations (les `refusé`/`hypothèse` = branches
   mortes documentées).

## Sortie réelle capturée

> À remplir en lançant la démo au gate humain (avant merge), sorties réelles collées ici.

## Robustesse (optionnel)

Interrompre le run (Ctrl-C) puis recharger : la session est scellée `aborted` avec la
raison, et les nœuds capturés avant l'interruption sont conservés (double filet).
