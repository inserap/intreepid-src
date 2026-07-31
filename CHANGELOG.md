# Changelog

Toutes les évolutions notables de intreepid sont documentées dans ce fichier.

Le format suit [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), et le versioning suit [SemVer 2.0](https://semver.org/spec/v2.0.0.html).

## [Non publié]

(rien pour l'instant)

## [0.5.0] — 2026-07-31

### Ajouté
- **Le greffier — capture épisodique de session** (première traversée de la couche mémoire, §10). Package `intreepid/scribe/`, **agnostique au domaine** : `trace.py` (contrat de données Q-0004 — arbre de session `sessions`+`nodes`, mapping **pur** du flux Agent SDK : `thinking`/`tool_call`/`tool_result` apparié via `tool_use_id`/`observation`) ; `store.py` (`Scribe` context manager DuckDB : **écriture incrémentale** — chaque nœud durable dès sa capture —, scellement `closed`/`aborted`+raison à la sortie, **append-only** — une session scellée ou crashée-ouverte ne peut jamais être rouverte ; `load()` réhydrate en read-only, P4) ; `render.py` (arbre ASCII lisible : 💭 raisonnement, 🔧 appels+agrégats, observations avec statuts — les `refusé`/`hypothèse` sont des branches mortes documentées).
- `run_analysis(question, model, trace_to=None)` : capture **opt-in**. Avec `trace_to`, le flux est dupliqué vers le `Scribe` et le **thinking summarized** est activé (le « pourquoi » entre les appels) ; sans lui, comportement **strictement inchangé** (oracle intact, thinking off). **Non-intrusion** : toute panne du greffier (ouverture, capture, scellement) est loggée et avalée — l'analyste rend toujours son verdict ; son exception à lui est enregistrée comme raison d'`aborted` puis re-propagée.
- Tests : 59 déterministes (dont non-intrusion/abort à travers le runner, immuabilité sur les 3 états de session, non-régression `trace_to=None`) + 1 test agent bout-en-bout (session réelle capturée, scellée, rejouée — 78 s).
- Démo : runbook `demo/brique-4-greffier.md` (sorties réelles du 2026-07-31) + driver `demo_greffier.py` (session enregistrée → verdict → arbre rejoué depuis le store).

### Notes
- Store épisodique = fichier DuckDB **write dédié**, distinct des fixtures sources read-only (P3) ; la trace ne contient que ce que l'agent voit — agrégats, jamais de lignes brutes (P2).
- Capture au **grain événement**, sans tri à chaud (Q-0003) ; la projection « Action sémantique » est une lecture future. Session = **épisode** de capture ≠ analyse (fil multi-sessions) : la reprise d'une analyse se fera par **référence** (vocabulaire PROV-DM allégé, `wasInformedBy`), jamais par réouverture — extensions Q-0004 (DAG, distillation, rappel MCP) hors périmètre de cette brique.

## [0.4.0] — 2026-07-30

### Ajouté
- **`concentration_test` — premier organe de preuve** (outil MCP read-only, **agnostique au domaine**). Teste si une variable catégorielle (l'« unité ») est sur-concentrée par rapport à une **exposition déclarée dans la fiche** (section `exposures`), via un **modèle nul par permutation multinomiale** (999 tirages, seed fixé) : écart de Poisson standardisé `(O−E)/√E`, pseudo-p `(M+1)/(R+1)`. Deux volets — `most_concentrated` (concentration la plus forte, pseudo-p du max → gère la multiplicité) et `highest_raw_count` (plus gros comptage brut, pseudo-p marginal) — dont le contraste démontre « volume ≠ excès ». Le LLM ne reçoit que des agrégats et un pseudo-p (P2), sur connexion read-only (P3), sortie reproductible (P4). Gardes : exposition `> 0`, cap défensif du nombre de permutations, colonne dans l'allowlist de la fiche.
- `mcp_server/nullmodel.py` : formule de pseudo-p par permutation isolée et générique (réutilisable par les futurs tests de rigueur).
- Convention de fiche **`exposures`** (`{unit_col: {table, key, weight}}`) : déclare, par colonne d'unité, la table d'exposition ; absente → modèle nul **uniforme** (signalé dans la sortie via `exposure_model`).
- Fixture étendue : table `canton_exposure.parquet` + deux concentrations plantées (une vraie = excès réel après exposition ; une fausse = plus gros volume mais exposition proportionnelle) ; `ground_truth.hotspot` régénéré depuis le Parquet relu.
- Charte de l'agent : paragraphe **générique** « preuve de concentration » (invoquer le modèle nul avant tout `fait`, interpréter le pseudo-p, ne jamais conclure sur le comptage brut seul).
- Oracle agent (`tests/test_agent_eval.py`, N=5) : l'agent retient le vrai point noir comme `fait` avec preuve (≥4/5) et n'affirme jamais le faux (plus gros volume) comme excès (0 tolérance) ; matcher négation-aware (distingue l'affirmation d'un excès de sa réfutation).
- Démo : runbook `demo/brique-3-concentration-et-preuve.md` (sorties réelles) + driver `demo.py` étendu.

### Notes
- Dépendance `numpy` ajoutée (permutation multinomiale). `esda` volontairement **non** ajouté : le test de concentration-vs-exposition n'est pas de l'autocorrélation ; `esda` (Gi\*/LISA) arrivera à la brique qui l'utilise réellement.
- Exposition **synthétique** (banc de test) ; la vraie couche (trafic / km de réseau) est une brique ultérieure. Roadmap rigueur (Gi\*/LISA, MAUP multi-résolution H3, FDR, E-value, Empirical Bayes, dowhy) tracée en Q-0009 (spec).

## [0.3.0] — 2026-07-30

### Ajouté
- **`profile_stats` complété aux 4 types de colonnes** (overview §4.2). Profil **temporel** (`_temporal` : bornes, trous de série, saisonnalité grossière, volume par année/ruptures) et profil **spatial** (`_spatial` : distribution des types de géométrie, SRID déclaré, emprise, taux de coordonnées hors emprise suisse, taux d'invalides/vides/nulls, dimension Z, longueur/aire max) via l'extension DuckDB `spatial`, en SQL pushdown — le LLM ne reçoit que des agrégats (P1/P2). Distance au plus proche voisin et densité par maille explicitement **différées** (« prévu / non implémenté », cible H3 multi-résolution anti-MAUP).
- Fixture OFROU étendue : colonnes `date`, `geom` (GeoParquet WKB, LV95/EPSG:2056) et `canton`, avec anomalies plantées (trou de série + rupture de volume ; coordonnées null-island `(0,0)` et hors emprise suisse) ; fiche et `ground_truth` régénérés (ground_truth recalculé depuis le Parquet relu).
- Oracle agent étendu (`tests/test_agent_eval.py`, N=5) : l'agent remonte des faits qualité-donnée temporels et spatiaux authentiques (≥4/5) et refuse deux faux patterns causaux (gravité×mois ; « baisse de volume ⇒ routes plus sûres »), sans lire de lignes brutes.

### Modifié
- `skewness` ajouté au profil numérique (`_numeric`) — complète §4.2 (dette brique #1 soldée).
- `mcp_server/bounds.py` : `open_readonly` devient un context manager (`TemporaryDirectory` auto-nettoyé, extension `spatial` chargée, connexion fermée avant nettoyage — garde Windows) ; `server.py` maintient la connexion long-lived via `ExitStack`+`atexit`. Solde la fuite de dossier temporaire de la brique #1.
- Charte de l'agent : guide générique de commentaire des blocs temporel/spatial (fait qualité-donnée vs extrapolation causale interdite), sans valeur de fixture en dur.
- Message explicite « prévu / non implémenté » pour les types de colonnes non couverts (remplace « non supporté dans la brique #1 »).

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
