# Runbook — Brique #7c : Curateur conversationnel d'ingestion

> **Gate humain.** Ce runbook pilote la démo interactive : l'humain dialogue au terminal,
> relit le YAML final et valide avant le merge. La démo, pas seulement les tests verts,
> est le critère de passage.

> **Note (brique #8, `v0.12.0`)** : ce runbook décrit la démo telle qu'elle s'est
> déroulée en `v0.10.0`. Le comportement conversationnel a changé depuis (forme de
> tour prescrite, plus de passe colonne par colonne, prose hors du bloc JSON) :
> pour rejouer une curation aujourd'hui, suivre
> [`brique-8-curateur-naturel.md`](brique-8-curateur-naturel.md).

---

## Prérequis

1. **Token OAuth actif** : `CLAUDE_CODE_OAUTH_TOKEN` doit être défini dans l'environnement
   (auth abonnement, pas clé API directe).
   ```bash
   echo "${CLAUDE_CODE_OAUTH_TOKEN:0:10}..."   # doit afficher les 10 premiers caractères
   ```

2. **`ANTHROPIC_API_KEY` absente** (sinon la garde OAuth Q-0010 bloque le run) :
   ```bash
   echo "${ANTHROPIC_API_KEY:-<absente, OK>}"   # DOIT afficher "<absente, OK>"
   ```

3. **Environnement installé** (depuis `intreepid/src`) :
   ```bash
   uv sync --extra dev
   ```

4. **Dataset OFROU brut accessible** (267 761 lignes, 36 colonnes) :
   ```bash
   ls data/raw/RoadTrafficAccidentLocations.parquet   # doit exister
   ```

---

## Pré-vol (juste avant la séance)

```bash
uv run python -c "import intreepid.demo_curator"          # import propre
uv run ruff format --check . && uv run ruff check .        # lint vert
uv run pytest --ignore=tests/test_agent_eval.py -q        # tests verts
```

---

## Commande de démo

Depuis `intreepid/src` :

```bash
uv run python -m intreepid.demo_curator data/raw/RoadTrafficAccidentLocations.parquet
```

---

## Déroulé attendu

1. **Tour 0 (démarrage)** — l'agent reçoit la consigne et appelle `profile_raw` sur le
   chemin du parquet. Il obtient les agrégats mono-colonne (cardinalité, min/max, top
   valeurs, type candidat inféré) pour les 36 colonnes.

2. **Tours 1–N (dialogue maïeutique)** — le curateur parcourt les colonnes et propose des
   hypothèses, une à quelques colonnes par tour :
   - Il émet sa prose, puis un bloc JSON fencé de métadonnées
     `{"fiche_draft": …, "proposes_completion": false}` (contrat changé en
     `v0.12.0` / brique #8 : la prose n'est plus dans le JSON).
   - Son message s'affiche dans le terminal ; l'humain tape sa réponse (corrections,
     confirmations, précisions métier).
   - Exemples de questions attendues :
     - `AccidentUID` : « cardinalité = 267 761 (toutes uniques), type candidat
       `categorical` — est-ce un identifiant technique, pas une catégorie ? » → répondre
       *oui, identifiant unique*.
     - Colonnes `_de`/`_fr`/`_it`/`_en` : « libellés multilingues de la même codification
       — à regrouper comme `label_*` ou à exclure de la fiche colonnes (redondantes) ? »
     - `AccidentSeverityCategory` : « 3 niveaux (AS1/AS2/AS3) : mortel / grave / léger —
       sens métier confirmé ? »
     - Colonnes géométriques (`AccidentLocation_CHLV95_E`/`_N`) : « coordonnées LV95
       (SRID 2056), unité mètres — à confirmer. »

3. **Tour final (proposition)** — quand toutes les colonnes sont couvertes, le curateur
   propose la fiche complète avec `proposes_completion: true`. Le terminal affiche :
   ```
   [Valider ? 'o' = valider, sinon tape une correction]
   >
   ```
   Relire le draft de fiche affiché, puis taper `o` pour valider.

---

## Critères de succès

- [ ] **Fiche YAML créée** : `catalog/RoadTrafficAccidentLocations.fiche.yaml` (ou nom
  dérivé du champ `dataset` dans la fiche) est présent après validation.
- [ ] **Bloc `columns` complet** : chaque colonne de `profile_raw` (36 colonnes) est
  documentée dans la fiche (type, sens, pièges éventuels).
- [ ] **Types corrigés par l'humain** : au minimum, `AccidentUID` passe de `categorical`
  (inféré) à `identifier` ou équivalent saisi par l'humain.
- [ ] **Unités spatiales** : colonnes LV95 portent `srid: 2056` et `unite: mètres`.
- [ ] **YAML relu et cohérent** : après validation, ouvrir
  `catalog/<dataset>.fiche.yaml` et vérifier que le contenu reflète la conversation.
  ```bash
  cat catalog/RoadTrafficAccidentLocations.fiche.yaml
  ```
- [ ] **Preuve greffier affichée en fin de run** (bloc « preuve greffier ») : `statut
  session = closed`, ≥ 1 tour humain, **1 nœud `curation_validated`** avec le `dataset`
  et le `hash` de la fiche. La trace DuckDB est éphémère (tmpdir) — c'est ce résumé
  imprimé, pas le fichier, qui atteste la validation ; le livrable durable est la fiche.

---

## Plan B

| Problème | Action |
|---|---|
| Boucle qui ne termine pas | Taper `valider` ou `ok` à l'invite de correction — le mot-clé de validation est accepté même hors proposition formelle |
| Agent bloqué / timeout | `Ctrl+C` pour interrompre : la session est **abortée**, aucune fiche n'est écrite (la fiche ne l'est qu'à la validation) et la trace éphémère est supprimée — il faut relancer |
| Fichier parquet introuvable | Vérifier le chemin : `ls data/raw/RoadTrafficAccidentLocations.parquet` depuis `intreepid/src` |
| `ANTHROPIC_API_KEY` définie par erreur | `unset ANTHROPIC_API_KEY` avant de relancer |
