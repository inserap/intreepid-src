# Architecture — intreepid

Description du système : concepts canoniques, patterns transverses, topologie, anatomie.

## Structure

| Fichier / Dossier | Rôle |
|---|---|
| [`overview.md`](overview.md) | Vue d'ensemble — principe suprême, concepts-clé, principes |
| [`concepts/`](concepts/) | Un fichier par concept canonique (Resource, Capability, Plan, etc., selon le domaine) |
| [`patterns/`](patterns/) | Cross-cutting patterns (disambiguation, dispatch, error handling, etc.) |

## Quand étoffer cette structure

- Démarrer par `overview.md` dès qu'on a 1 paragraphe de doctrine architecturale.
- Ajouter un fichier dans `concepts/` dès qu'un terme apparaît dans ≥ 2 ADRs ou ≥ 2 slices.
- Ajouter un fichier dans `patterns/` dès qu'un pattern est utilisé dans ≥ 2 composants.

## Quand laisser vide

- Pas de pression pour remplir d'avance. Le contenu émerge avec le projet.
