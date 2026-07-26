# ADRs — Architectural Decision Records de intreepid

Ce dossier contient les ADRs **Accepted** (immutables) du projet `intreepid`. Les ADRs en cours de rédaction (`Proposed`) vivent dans le spec repo associé, dans son propre dossier `decisions/`. Elles sont promues ici une fois acceptées (procédure côté spec — voir la doctrine du spec repo).

Format : Nygard + Alternatives considered + Supersedes.

Template : [`TEMPLATE.md`](TEMPLATE.md).

## Index

| ID | Titre | Statut |
|---|---|---|
| _aucune pour l'instant_ | | |

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
