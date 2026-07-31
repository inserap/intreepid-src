# ADR-0001 — Socle de données : DuckDB + GeoParquet

- **Status:** Accepted
- **Date:** 2026-07-26 (proposed), 2026-07-31 (accepted)
- **Decision-makers:** Alexandre Pillonel, Claude (co-conception)

## Context

Le workspace doit consommer n'importe quelles données (géographiques ou non) via un moteur de requête unique, interrogeable par des agents LLM au travers d'outils MCP, sans jamais leur exposer les données brutes (principe P2). Il faut une *lingua franca* de requête entre les pipelines d'ingestion (FME), les agents et les notebooks de sortie.

## Decision

Tout converge vers Parquet/GeoParquet (ingestion assurée par FME depuis n'importe quelle source). **DuckDB + extension spatiale** est le moteur unique : SQL complet, spatial natif, léger, exécutable en local ou serveur. Les embeddings éventuels (recherche sémantique cross-datasets, v2) utiliseront l'extension **DuckDB VSS** — pas de vector database dédié.

## Consequences

### Positive

- La couche MCP s'écrit contre une seule API de requête.
- La *lingua franca* entre FME, agents et notebooks est le SQL DuckDB.
- Stack légère, reproductible, sans serveur lourd à opérer pour la v1.

### Negative / costs accepted

- Plafond de scalabilité de DuckDB (mono-nœud) accepté pour l'échelle visée ; une montée en charge future pourrait rouvrir la question.
- Dépendance à la maturité de l'extension spatiale et de VSS.

## Alternatives considered

- **PostGIS serveur** — moteur spatial mature. Rejeté : plus lourd à opérer, inutile à l'échelle visée pour la v1.
- **Vector DB dédié (Pinecone, Weaviate, Milvus)** — pour la recherche sémantique. Rejeté : résout des problèmes de milliards de vecteurs, hors de propos ici ; DuckDB VSS suffit.

## Supersedes

None.

## References

- Provenance : session de fondation du 2026-07-26 (documentée dans le spec repo).
- Vision : [`../architecture/overview.md`](../architecture/overview.md) §1, §3, §14
