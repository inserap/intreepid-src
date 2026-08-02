# Démo brique #7b — le profil brut (dataset SANS fiche)

**But** : montrer l'**amorce de la curation** — profiler un dataset **jamais fiché** (le cas
d'ingestion) via le canal MCP, avec un **type candidat** inféré par colonne (Q-0015a). Pas de LLM,
déterministe. C'est la couche M d'ADR-0009 ; le curateur (brique #7c) consommera `profile_raw` puis
affinera les types candidats avec l'humain.

## Pré-vol

- Pas d'agent, pas d'abonnement requis (aucun LLM). Seul `uv sync --extra dev` (setup commun).
- Un parquet **brut** sous `data/` (ici la donnée OFROU brute `data/raw/RoadTrafficAccidentLocations.parquet`, gitignorée mais présente en dev).

## Lancer

```bash
PYTHONIOENCODING=utf-8 uv run python - <<'PY'
from intreepid.mcp_server.bounds import open_readonly
from intreepid.mcp_server.profiling_raw import profile_raw

p = "data/raw/RoadTrafficAccidentLocations.parquet"
with open_readonly(p, "accidents_raw") as con:
    n = con.execute("SELECT count(*) FROM accidents_raw").fetchone()[0]
    prof = profile_raw(con, "accidents_raw")

print(f"{n} lignes, {len(prof)} colonnes, jamais fichees")
for col, d in prof.items():
    print(f"  - {col:44s} -> {d['type']}")
PY
```

> L'outil est aussi exposé côté **MCP** : `profile_raw(dataset_path)` (garde anti-traversée — le
> chemin doit être un `*.parquet` existant sous `DATA_DIR = data/` ; sortie enveloppée
> `untrusted_data`). Le smoke ci-dessus appelle la fonction directement pour la lisibilité.

## Ce que ça montre (sortie réelle, 2026-08-02, OFROU brut 267 761 lignes, 36 colonnes)

- **Codes/catégories** repérés par faible cardinalité : `AccidentType` (card 11),
  `AccidentSeverityCategory` (3), booléens `AccidentInvolving*` (2), `RoadType` (6), `CantonCode`
  (26), `AccidentWeekDay` (7), `AccidentHour` (24) → `categorical`.
- **Coordonnées** `AccidentLocation_CHLV95_E` / `_N` → `numeric` (min/max cohérents avec l'emprise
  LV95 : E∈[2 486 335 ; 2 832 028], N∈[1 075 625 ; 1 294 423]). La donnée **brute** a des coordonnées
  en **colonnes séparées** (pas de `geom` — la géométrie naît à l'étape `prepared`), et `profile_raw`
  le voit tel quel : aucune inférence `spatial` ici.
- **Signal de curation** : `AccidentUID` → `categorical` avec **card = 267 761** (chaque ligne
  unique). L'inférence le classe catégoriel par défaut (VARCHAR), mais l'uniqueness ≈ 1 crie
  « **identifiant**, pas catégorie » — exactement le candidat que le curateur corrigera.
- **Colonnes multilingues** (`*_de/_fr/_it/_en`) toutes profilées identiquement — le curateur
  décidera lesquelles garder.

Toutes les colonnes portent `type_inferred: True` : ce sont des **candidats**, jamais une vérité —
le curateur/humain valide (frontière charte↔fiche, Q-0004/Q-0015).

## Robustesse

- Chemin hors `data/` → **rejeté** (`ValueError`, garde anti-traversée) — testé en CI
  (`test_profile_raw_tool_rejects_path_traversal`).
- Table vide supposée non rencontrée (l'outil garde `is_file` en amont ; profiler une table vide
  est hors périmètre #7b).
