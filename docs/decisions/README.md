# ADRs — Architectural Decision Records de intreepid

Ce dossier contient les ADRs **Accepted** (immutables) du projet `intreepid`. Les ADRs en cours de rédaction (`Proposed`) vivent dans le spec repo associé, dans son propre dossier `decisions/`. Elles sont promues ici une fois acceptées (procédure côté spec — voir la doctrine du spec repo).

Format : Nygard + Alternatives considered + Supersedes.

Template : [`TEMPLATE.md`](TEMPLATE.md).

## Index

| ID | Titre | Statut |
|---|---|---|
| [ADR-0001](0001-socle-duckdb-geoparquet.md) | Socle de données : DuckDB + GeoParquet | Accepted (2026-07-31) |
| [ADR-0008](0008-code-quality-deviation-pyright-standard.md) | Déviation qualité : pyright `standard` (ratchet vers `strict`) | Accepted (2026-07-31) |

> Trous de numérotation (0002–0007) attendus : ces ADR restent `Proposed` dans le
> spec repo tant qu'elles ne sont pas acceptées. Les numéros sont immuables et suivent
> l'ADR sur tout son cycle de vie.

## Numérotation

- Format : `NNNN-<title>.md` (NNNN à 4 chiffres, démarrage `0001`).
- Numéros immuables et jamais réutilisés.

## Lifecycle (impl-side view)

```
draft (in spec/decisions/) → Proposed (in spec/decisions/) → Accepted (promoted here)
                                                          ↘ Rejected (stays in spec/decisions/)
                                                          ↘ Superseded (replaced by newer ADR here)
```

Les ADRs `Accepted` dans ce dossier sont **immuables**.
