# intreepid

> Workspace de découverte analytique : explorer des données (géospatiales ou non) en dialogue avec des agents LLM pour découvrir des informations non triviales.
> Statut : draft — vision architecturale v0.3, aucune implémentation engagée.
> Version : voir [CHANGELOG.md](CHANGELOG.md).
> Nom de code provisoire (`intreepid`) — nom définitif non tranché (candidats pressentis : Semantree, Semantrek).

## À quoi sert ce projet

`intreepid` est un espace de travail agentique où un ou plusieurs humains explorent des données en dialogue avec des agents LLM, pour découvrir des informations **non triviales** et décider sur la base de connaissances nouvelles. Il s'adosse à la BI classique, il ne la remplace pas.

Trois capacités impossibles sans LLM en définissent la raison d'être : **documentation à coût zéro** (un agent greffier capture tout le raisonnement pendant que les humains restent concentrés sur la découverte), **capitalisation systémique** (chaque session laisse le système plus intelligent sur les données, le domaine et la méthode) et **rigueur architecturée** (agents critique et candide, modèles nuls, traçabilité complète — chaque insight doit survivre à la contradiction avant d'être retenu).

Les LLM y aident, orientent, challengent et proposent — jamais ils ne remplacent le calcul déterministe ni le jugement métier. La vision complète (couches, boucle de découverte, charte des agents, couplage arbre-carte, modèle de mémoire) est décrite dans [`docs/architecture/overview.md`](docs/architecture/overview.md).

## Architecture

Voir [`docs/architecture/`](docs/architecture/) :

- [`docs/architecture/overview.md`](docs/architecture/overview.md) — Vue d'ensemble.
- [`docs/architecture/concepts/`](docs/architecture/concepts/) — Concepts canoniques.
- [`docs/architecture/patterns/`](docs/architecture/patterns/) — Patterns transverses.

## Conventions

Ce projet suit SemVer 2.0 et Keep a Changelog 1.1.0. Pour les conventions de codage, de commits et de versioning, voir le spec repo associé qui pilote ce projet (le path est documenté dans son `repository-topology.md`).

- Commits : [Conventional Commits](https://www.conventionalcommits.org/)
- Versioning : [SemVer 2.0](https://semver.org/spec/v2.0.0.html) — cf. [`docs/VERSIONING.md`](docs/VERSIONING.md)
- Changelog : [Keep a Changelog 1.1.0](https://keepachangelog.com/en/1.1.0/)
- Langue documentation : français

## Sécurité

Voir [`SECURITY.md`](SECURITY.md).

## Licence

à définir

## Note

Ce repo est un livrable autonome. Il est piloté par un **spec repo** dédié (séparé) qui n'est pas nécessaire pour utiliser ou contribuer au code ici. Un mainteneur futur peut reprendre ce projet sans aucune dépendance externe au-delà de sa stack technique.
