# Changelog

Toutes les évolutions notables de intreepid sont documentées dans ce fichier.

Le format suit [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), et le versioning suit [SemVer 2.0](https://semver.org/spec/v2.0.0.html).

## [Non publié]

(rien pour l'instant)

## [0.2.0] — 2026-07-28

### Ajouté
- Vision architecturale v0.2 (`docs/architecture/overview.md`) et glossaire métier initial (`docs/glossary.md`), issus de la session de fondation du 2026-07-26.
- **Brique #1 — walking skeleton** (première implémentation) : serveur MCP FastMCP read-only (`profile_stats` mono-colonne, `describe`, `list_datasets`) sur DuckDB/Parquet ; agent analyste (Claude Agent SDK) isolé aux seuls outils MCP, produisant un verdict structuré honnête (`fait`/`hypothèse`/`refusé`) sans lire de lignes brutes (P2/P3) ; fixture à vérités plantées (sous-ensemble OFROU) ; tests deux étages (golden déterministe + éval agent N=5) ; démo CLI (`python -m intreepid.demo`).
- **Gate qualité** (`standards@0.7.0`) : `ruff` (format + lint E,F,I,UP,B,D avec en-têtes de module) + `pyright` + `pytest` avant commit.

### Modifié
- `pyright` en `typeCheckingMode="standard"` (déviation ADR-0008 vs défaut `strict` de `standards@0.7.0` ; ratchet vers `strict` planifié — stack maison sans stubs).

## [0.1.0] — 2026-07-26

### Ajouté
- Bootstrap initial du projet `intreepid`.
