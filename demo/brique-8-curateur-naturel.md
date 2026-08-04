# Runbook — Brique #8 : qualité conversationnelle du curateur

> **Gate humain.** Ce runbook pilote la démo interactive. Le critère de passage
> n'est pas la fiche produite (#7c l'avait déjà) mais la **forme des questions** :
> le curateur doit être compréhensible **dès le premier tour**, sans qu'on lui
> demande quoi que ce soit.
>
> **Règle absolue de la séance : ne donner AUCUNE consigne de style.** Pas de
> « pose les questions une à la fois », pas de « sois moins succinct ». Si le
> besoin s'en fait sentir, le gate a échoué — c'est l'information qu'on cherche.

---

## Prérequis

1. **Token OAuth actif** :
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
4. **Dataset brut accessible** :
   ```bash
   ls data/raw/RoadTrafficAccidentLocations.parquet   # doit exister
   ```
5. **État de `catalog/` avant le run** — la fiche produite est nommée d'après le
   champ `dataset` choisi par l'agent : elle peut écraser un fixture tracké.
   ```bash
   git status --short catalog/    # AUCUNE ligne affichée = OK, on peut lancer
   ```

## Pré-vol

```bash
uv run ruff format --check . && uv run ruff check .
uv run pyright
uv run pytest --ignore=tests/test_agent_eval.py -q
```

## Commande

Depuis `intreepid/src`, noter l'heure de démarrage :

```bash
date +%H:%M:%S
uv run python -m intreepid.demo_curator data/raw/RoadTrafficAccidentLocations.parquet
```

## Pendant la séance

- Répondre **au fond** (par numéro et lettre, ou en texte libre), jamais sur la forme.
- « je ne sais pas » est une réponse légitime : elle doit produire un **piège
  documenté**, avec sa procédure de vérification et un repli praticable.
- **Chronométrer 2 ou 3 tours** : délai entre l'envoi de la réponse et l'affichage
  du tour suivant (référence #7c : ≈ 2 min).
- Compter le **nombre de tours** jusqu'à la proposition de validation
  (référence #7c : 8 tours humains).
- Noter si des **préambules d'outil** (« je vais d'abord profiler… ») apparaissent
  avant le verrou : la prose hors JSON les rend désormais visibles.
- Noter si l'on a **contredit le penchant** du curateur au moins une fois. Le gold
  montre 7 réponses « a » sur 8, et (a) y est systématiquement l'option privilégiée
  par l'agent : sans ce relevé, on ne peut pas distinguer « le curateur a raison »
  de « l'humain ratifie sans réfléchir » — le mode d'échec propre à la puce PENCHANT.
- Noter l'heure de fin (`date +%H:%M:%S`).

## Critères de succès

> Les commandes des critères **c** à **g** se lancent dans le **même terminal** :
> la variable `$FICHE` est posée au critère c et réutilisée ensuite.

- [ ] **a. Premier tour déjà au niveau** : chaque question du **premier** tour porte
  son objet, un ancrage chiffré tiré du profil, l'enjeu du mauvais choix rendu
  tangible par un mécanisme concret, des options fermées, « je ne sais pas »
  déclaré valide, et le **penchant** de l'agent avec l'indice qui l'y pousse.
- [ ] **b. Zéro consigne de style** : la séance s'est déroulée sans qu'on ait eu
  besoin de corriger la forme.
- [ ] **c. Fiche complète** : la fiche écrite couvre les **36 colonnes** — test de
  non-régression du draft tardif (il n'est émis qu'au dernier tour). Le chemin
  exact est celui imprimé par le run (« ✓ fiche écrite : <chemin> ») :
  ```bash
  FICHE=$(ls -t catalog/*.fiche.yaml | head -1) && echo "$FICHE"
  uv run python -c "import yaml,sys; d=yaml.safe_load(open(sys.argv[1],encoding='utf-8')); print(len(d.get('columns',{})),'colonnes')" "$FICHE"
  ```
  **Avant d'aller plus loin, vérifier que le chemin affiché par `echo "$FICHE"`
  est bien celui imprimé par le run.** `ls -t` prend le fichier le plus récent de
  `catalog/` : si un fixture y a été touché entre-temps, on compterait les colonnes
  du mauvais fichier et on croirait la fiche complète.
- [ ] **d. Latence et volume notés** : temps par tour et nombre de tours consignés,
  en regard des ≈ 2 min × 8 tours de #7c.
- [ ] **e. Preuve greffier** : bloc « preuve greffier » en fin de run — `statut
  session = closed`, ≥ 1 tour humain, **1 nœud `curation_validated`** avec dataset
  et hash.
- [ ] **f. Aucune fuite du gabarit** : la fiche produite ne contient aucun des noms
  factices de l'exemple de la charte (`mesure_x`, `mesure_y`, `code_statut`,
  `code_type`, `ref_source`, `libelle_a`).
  ```bash
  grep -nE "mesure_x|mesure_y|code_statut|code_type|ref_source|libelle_a" "$FICHE" || echo "aucune fuite, OK"
  ```
  Le `grep` n'attrape que la copie littérale : **relire la fiche** pour repérer une
  imitation structurelle (un « `-1` = valeur manquante » absent de la donnée réelle).
- [ ] **g. Aucun fixture écrasé** :
  ```bash
  git status --short catalog/    # ne doit lister QUE la fiche nouvellement créée
  ```

## Comparaison au gold-standard

Relire le transcript de référence
(`<SPEC>/research/2026-08-04-curateur-gate-humain-materiel.md` §3) et juger, sur les
tours produits : le niveau de détail y est-il, sans la précision live ?

## Garde-fou : une seule itération

Si le niveau n'est pas atteint, **une seule** correction de charte est autorisée,
suivie d'un unique nouveau run. Si le second run échoue lui aussi : **arrêter**,
capturer le transcript comme matériel, et cadrer à froid l'approche C (contrat de
tour pleinement structuré, rendu composé par la surface). On ne tune pas une UX en
réaction au merge — leçon #7c.

## Plan B

| Problème | Action |
|---|---|
| Boucle qui ne termine pas | Taper `valider` ou `ok` à l'invite de correction |
| Agent bloqué / timeout | `Ctrl+C` : session **abortée**, aucune fiche écrite, il faut relancer |
| Fichier parquet introuvable | `ls data/raw/RoadTrafficAccidentLocations.parquet` depuis `intreepid/src` |
| `ANTHROPIC_API_KEY` définie par erreur | `unset ANTHROPIC_API_KEY` avant de relancer |
| L'agent propose la validation sans fiche | Le curateur ne peut plus terminer là-dessus : lui demander la fiche complète à l'invite, ou `Ctrl+C` |
| Fiche écrite incomplète (< 36 colonnes) | Ne pas re-tuner : c'est le risque « draft tardif » du design ; repli documenté = réintroduire l'émission du draft à chaque tour |
| La fiche écrite écrase un fixture tracké de `catalog/` | `git restore catalog/<fichier>` ; renommer à la main la fiche produite |
