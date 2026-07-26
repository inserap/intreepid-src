# Politique de versioning — intreepid

intreepid suit [Semantic Versioning 2.0](https://semver.org/spec/v2.0.0.html) et [Keep a Changelog 1.1.0](https://keepachangelog.com/en/1.1.0/).

> Pour la doctrine partagée (modèle SemVer par entité, processus de release commun), voir le spec repo associé. La doctrine canonique vit dans `standards/conventions/versioning.md` côté méthodologie INSER AI.

## Ce qui déclenche chaque bump

### MAJOR (X.0.0)
- Une ADR antérieurement `Accepted` est `Superseded` par une nouvelle ADR avec sémantique breaking.
- Un invariant non-négociable est changé ou supprimé.
- Un contrat public (API, format de fichier, signature) change de manière incompatible.

### MINOR (X.Y.0)
- Une nouvelle ADR est `Accepted`.
- Un nouveau concept / pattern / capacité est ajouté.
- Un raffinement non-breaking.
- Une nouvelle feature shipped.

### PATCH (X.Y.Z)
- Correction de typo, clarification, reformulation sans changement de fond.
- Termes ajoutés au glossaire.
- Amélioration de doc.

## Processus de release

1. Déplacer les entrées de `[Non publié]` du `CHANGELOG.md` vers une nouvelle section versionnée datée.
2. Bumper la version dans `<metadata file>` si applicable (`pyproject.toml`, `package.json`, …).
3. Commit : `chore: release v<X.Y.Z>`.
4. **Tagger** — uniquement à la demande explicite de l'utilisateur. Claude n'exécute jamais `git tag` de manière autonome. Claude suggère la commande (`git tag v<X.Y.Z>`) dans le récap ; l'utilisateur l'exécute lui-même.

## Pre-1.0.0

Tant que intreepid est en `0.Y.Z`, l'API est instable.

## Version initiale

intreepid démarre à `0.1.0`.
