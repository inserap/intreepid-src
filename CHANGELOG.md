# Changelog

Toutes les évolutions notables de intreepid sont documentées dans ce fichier.

Le format suit [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), et le versioning suit [SemVer 2.0](https://semver.org/spec/v2.0.0.html).

## [Non publié]

(rien pour l'instant)

## [0.10.0] — 2026-08-04

### Ajouté
- **Curateur conversationnel d'ingestion (couches B+D d'ADR-0009 / brique #7c)** : le **2ᵉ profil d'agent**, qui transforme un dataset **non fiché** en une **fiche `columns`-complète validée** par une conversation REPL human-in-the-loop. Matérialise Q-0021 (« un agent = un profil »).
- **Orchestrateur multi-tours en-process** (`agent/orchestrator.py`, `agent/profile.py`) : `Profile` gagne 2 champs **optionnels** (`next_input`, `build_prompt`) → défaut = one-shot = **non-régression stricte** de l'analyste. `run_agent` boucle tant que non-terminal (historique **application-owned**, ré-injecté à chaque tour ; charte = `system_prompt` byte-stable) ; un **seul `Scribe`** vit toute la conversation ; `on_result` appelé à la validation **avant** scellement.
- **Package `agent/curator/`** : `turn.py` (`CuratorTurn` + `parse_curator_turn` — dernier bloc JSON fencé gagne, repli tolérant, Q-0014) ; `fiche_writer.py` (`write_fiche` YAML + hash SHA-256 **idempotent**, garde anti-traversée du nom) ; `surface.py` (REPL, I/O injectés) ; `charter.md` (charte maïeutique **agnostique** — anti-spoiler, doc humaine = `untrusted_data`, `exposures` hors-scope) ; `profile.py` (isolation P2/P3 : allowlist `profile_raw` seul + built-ins retirés ; terminaison = validation humaine ; `on_result` écrit la fiche + grave le nœud durable `curation_validated` portant le hash).
- Driver `demo_curator.py` (conversation réelle sur OFROU brut, **preuve greffier** in-process) + runbook `demo/brique-7c-curateur.md`. Tests : `test_orchestrator.py` (multi-tours), `test_curator_{turn,fiche_writer,surface,profile}.py`. **113 déterministes verts**, non-régression stricte de l'analyste one-shot.

### Notes
- MINOR : fonctionnalité additive (2ᵉ profil) ; l'analyste one-shot est **strictement préservé** (champs `Profile` optionnels à défaut one-shot). Aucune ADR mutée (I-2) ; ADR-0009 passera `Accepted` à froid.
- Walking-skeleton **en-process** assumé : la résilience crash inter-runs (couche B2 `open/append/seal`, rejeu-depuis-greffier) est **différée** (ADR-0009 §4a).
- **Gate humain (démo)** : mécanisme + **fond** validés — le curateur trouve les vrais pièges OFROU (sévérité inversée `as1`=tué, `at0`/`at00` disjoints, référentiel communal instable sur 15 ans, coordonnées EPSG:2056) et **refuse honnêtement de clore** sur les zones grises. La **naturalité conversationnelle** des questions (encore robotique) = **follow-up dédié** (recoupe Q-0020, maïeutique).
- Plan validé **SHIP** par 2 passes advisor ; revue finale whole-branch : **Ready to merge**.
- Structure : regroupement `agent/curator/` (profil+charte+helpers, préfixe supprimé) ; promotion symétrique de l'analyste en `agent/analyst/` = follow-up (session future).

## [0.9.0] — 2026-08-02

### Ajouté
- **Profil brut d'un dataset SANS fiche (couche M, ADR-0009 / brique #7b)** : profiler un dataset **non encore fiché** (ingestion) via MCP, avec un **type candidat** inféré par colonne (Q-0015a). Amorce la curation ; le curateur (brique #7c) affinera les candidats avec l'humain.
- `intreepid/mcp_server/profiling_raw.py` (**agnostique au domaine**) : `infer_type(con, table, col)` — heuristique SQL type → `categorical`/`numeric`/`temporal`/`spatial`, un numérique de **faible cardinalité** (≤ 25) = **code déguisé** (cf. sentinelle `999`) ; `profile_raw(con, table)` **réutilise** les profileurs de `profile_stats.py` (DRY, un seul `DESCRIBE`) et marque chaque profil `type_inferred: True`.
- **Outil MCP `profile_raw(dataset_path)`** : ouverture du parquet **par-appel** (`open_readonly`, CM court, read-only P3), **garde anti-traversée** (chemin résolu = `*.parquet` existant sous `DATA_DIR`), nom de table sanitisé, sortie enveloppée **`untrusted_data`** (Q-0008). Additif : bootstrap mono-fiche et 5 outils fichés **intacts**.
- Runbook `demo/brique-7b-profil-brut.md` (sortie réelle : 267 761 lignes OFROU **brutes**, 36 colonnes, types candidats — `AccidentUID` card 267 761 = signal « identifiant, pas catégorie » pour le curateur). Tests : `test_profiling_raw.py` (golden inférence + fixture réelle) + 2 tests serveur (outil MCP + rejet de traversée). **94 déterministes verts**, non-régression tenue.

### Notes
- MINOR : outil additif, aucune rupture d'API. Le type inféré est un **candidat** (jamais une vérité) — le curateur/humain le valide (frontière charte↔fiche, Q-0004/Q-0015).
- Découpage walking-skeleton (décision 2026-08-02) : #7b = couche **M seule** (seul livrable démontrable en propre) ; la couche B (trace cycle-ouvert) rejoint le curateur D en **#7c**, construite avec son consommateur. Plan validé SHIP par 2 passes advisor.
- Différés (SHOULDs advisor, non-bloquants) : docstring `infer_type` (appel répété O(n×DESCRIBE)) ; collision théorique de noms de table par sanitisation ; harmonisation d'imports de test.

## [0.8.0] — 2026-08-02

### Ajouté
- **Socle d'exécution générique des agents (ADR-0009, Phase A / brique #7a)** : un orchestrateur unique paramétré par un **profil de rôle**, qui prépare l'accueil de rôles multiples (curateur, critique…) **sans dupliquer la mécanique d'exécution**.
- `intreepid/agent/orchestrator.py` — `run_agent(profile, prompt, *, model, trace_to)` : boucle d'exécution one-shot commune à tous les rôles (garde OAuth Q-0010, capture greffier **best-effort**, parsing délégué au profil).
- `intreepid/agent/profile.py` — `Profile` (dataclass frozen) : décrit **ce qui change d'un rôle à l'autre** (options SDK, parsing de sortie, hook de capture `on_result`).
- `intreepid/agent/analyst_profile.py` — l'analyste exprimé comme `Profile` (charte, allowlist MCP, isolation P2/P3, projection du verdict).
- **`scribe` agnostique du rôle** : primitive générique `Scribe.record_nodes(specs)` / `TraceBuilder.custom(specs)` remplace `record_verdict`/`verdict` — le socle greffier ne connaît plus le schéma « observation » de l'analyste ; la **projection résultat→nœuds descend dans le profil**.
- Tests : `tests/test_orchestrator.py`, `tests/test_analyst_profile.py` (+ adaptations `test_scribe_*`). **89 déterministes verts**.

### Modifié
- `intreepid/agent/runner.py` réduit à un **wrapper mince** : `run_analysis` conserve sa signature publique (non-régression) et délègue à `run_agent(analyst_profile())`.

### Notes
- MINOR : refactor à **iso-comportement** (mêmes nœuds/ids/statuts de trace, isolation P2/P3 identique) qui **ajoute** une API publique (`run_agent`, `Profile`, `record_nodes`). Aucune rupture. Démo greffier : arbre capturé/rejoué **identique** via `run_agent`.
- Prépare les phases **B** (trace à cycle ouvert), **C** (MCP multi-dataset), **D** (profil curateur) de la brique #7.
- Différés (follow-ups) : **rendu agnostique** des renderers (`render.py`/`notebook.py` dispatchent encore sur le kind `observation`) ; `Protocol` pour `record_nodes` (retirer un `type: ignore`) ; dérive d'isolation P3 des méta-outils CLI (Q-0019).

## [0.7.0] — 2026-08-02

### Ajouté
- **Robustesse d'échelle spatiale (H3) — l'outil MCP `spatial_scale_robustness`** (Q-0009) : agrège les points d'un dataset en cellules Uber **H3** à plusieurs résolutions (`[6,7,8]`) et teste si une concentration — au-delà d'une **exposition population réelle** (STATPOP hectare) — **survit au changement de maille**. Verdict `robuste`/`fragile`/`absente` + pic descriptif par résolution + caveats d'honnêteté. Première **vraie jointure spatiale** du projet ; le différenciateur volume ≠ excès porté au grain spatial.
- `intreepid/mcp_server/scale_robustness.py` (**agnostique au domaine**) : agrégation H3 (reprojection SRID→WGS84 en SQL DuckDB, `h3-py` v4), agrégation de l'exposition en cellules H3 (mailles-hectares → points pondérés au centroïde), **null multinomial par résolution** (∝ exposition, réutilise `nullmodel.pseudo_p`), et décomposition des cellules occupées mais **non-peuplées** — exclues du test et **reportées à part** (Q-0016 : pas d'excès fabriqué ; surface les corridors de transit).
- **Exposition spatiale déclarée par référence** : la fiche du dataset porte `exposures.<colonne> = {kind: spatial_grid, fiche: <grille>, weight: <col>}` ; l'outil résout la **fiche auto-descriptive** de la grille (`catalog.load_referenced_fiche`, garde anti-traversée de chemin). Convention gravée : **clé d'exposition = colonne de jointure du dataset** (`canton` catégoriel, `geom` spatial).
- **Exposition population réelle** : `prepare/statpop_population.py` (STATPOP hectare BFS 2024, 347 736 mailles, k-anonymat déjà appliqué en amont) + fiche curée `catalog/statpop_population.fiche.yaml` (bloc `grid`, `cell_size`/`coord_ref`). Le raw parquet est un transcodage fidèle du CSV BFS (job ETL amont, hors périmètre).
- Dépendance : **`h3` (h3-py v4)** — seule dépendance nouvelle.
- Driver `intreepid/demo_scale_robustness.py` + runbook `demo/brique-6-robustesse-echelle.md` (sorties réelles). Tests `tests/test_scale_robustness.py` (golden déterministe sur fixtures synthétiques : 3 clusters proportionnel/excès/non-peuplé). **84 déterministes verts**, non-régression tenue.

### Modifié
- **`concentration_test` — abstention par défaut (Q-0016)** : sans exposition déclarée **ni** opt-in uniforme explicite (`{uniform: true}`), l'outil **s'abstient** (`exposure_model: "abstention"`) au lieu de retomber silencieusement sur un null uniforme trompeur (qui ré-introduisait la confusion volume ↔ excès pour des unités inégales).
- **`std_excess` promu dans `nullmodel.py`** (source unique de l'écart de Poisson standardisé), importé par `concentration.py` et `scale_robustness.py` — fin de la duplication.
- `intreepid/agent/runner.py` + `intreepid/agent/charter.md` : l'analyste peut appeler `spatial_scale_robustness` (ajout à l'allowlist + paragraphe de charte, honnêteté fait/hypothèse/refusé préservée).

### Notes
- MINOR : outil additif, aucune rupture d'API. Smoke réel (accidents OFROU × STATPOP) : **5,3 s, verdict `robuste`**, part `unpopulated` 4,18 % à res 8.
- Réserves gravées (caveats **génériques** dans le code + note **domaine** dans la fiche) : **population ≠ trafic** (une sur-concentration au-delà de la population n'est pas une preuve de dangerosité) ; **biais d'agrégation planaire** pour un phénomène de réseau (Xie & Yan 2008 ; méthodes réseau/NKDE = futur) ; **hiérarchie H3 non-emboîtante** (pic décrit par résolution).
- Différés (OPEN-QUESTIONS) : hotspots locaux Gi\*/LISA + correction FDR, méthodes réseau (NKDE), exposition **trafic** réelle (Q-0016) ; **plusieurs expositions par colonne de jointure** (Q-0016, `dict`→liste + sélection) ; **dérive d'isolation P3 du runner** — les méta-outils récents du CLI (`ToolSearch`, `TaskCreate`, `Cron*`…) sont hors `disallowed_tools` (nouvelle Q).

## [0.6.0] — 2026-08-01

### Ajouté
- **Le produit de session — analyste sur le réel + notebook Quarto rejouable** (item v1 #6, §10). Validation de la v1 **de bout en bout sur la vraie donnée OFROU** (267 761 lignes) : l'analyste `opus` tourne via les outils MCP existants (**zéro nouvel outil**), capturé par le greffier, et un **notebook Quarto déterministe** est généré depuis la trace.
- `intreepid/scribe/notebook.py` (**agnostique au domaine**) : `to_quarto(trace)` — fonction **pure et totale** projetant une `SessionTrace` figée en `.qmd` déterministe (front-matter HTML toc/code-fold/embed-resources ; appels d'outils en blocs `{.json}` + résultats agrégés ; observations en **callouts typés** `fait`→note / `hypothèse`→warning / `refusé`→caution ; pied `meta`). `render_html` **best-effort** (CLI `quarto` absent → `.qmd` seul, dégrade proprement).
- **Fiche auto-descriptive** + serveur pointé par `INTREEPID_FICHE` : la fiche porte `data:` + `exposures.table` en chemins **relatifs-à-elle-même**, `dataset` = nom de table ; le serveur résout depuis `FICHE.parent` (défaut = fixture ⇒ suite inchangée). Un seul point d'entrée pour basculer fixture ↔ réel.
- **Ingestion réelle** (`prepare/`, scripts trackés, Parquet gitignorés régénérables) : `accidents_route.py` (projection OFROU brut → analysis-ready, `geom` LV95 + `date`) et `canton_population.py` (exposition = population cantonale BFS, proxy **grossier assumé** ≠ trafic, réserve gravée dans la fiche). La conversion CSV→Parquet reste un job **ETL/FME amont** (hors périmètre).
- Modèle de données en **3 états** : `data/raw/` (brut fourni) → `data/prepared/` (analysis-ready), tous deux gitignorés ; `catalog/` (fiches curées, trackées) ; `fixtures/` (monde de test déterministe, tracké).
- Driver `intreepid/demo_notebook.py` + runbook `demo/brique-5-notebook.md` (sorties réelles du 2026-08-01). Tests : `test_notebook` (golden `to_quarto`), `test_prepare`, `test_catalog` (contrat fiche auto-descriptive). **70 déterministes verts**, non-régression tenue.

### Modifié
- Fiche fixture migrée `fixtures/accidents.fiche.yaml` → `catalog/accidents_seed.fiche.yaml` (dataset renommé `accidents_route` → `accidents_seed`) ; `concentration.py` : label `exposure_model` = nom de fichier.

### Notes
- **Validation v1 réussie sur du réel** : sur donnée propre, l'analyste conclut honnêtement « aucune anomalie » (posture P6 — pas d'anomalie hallucinée), démontre **volume ≠ excès** (BE sur-concentré vs sa population ; ZH plus gros comptage mais expliqué par l'exposition) et **refuse** l'abus causal (« BE plus dangereux ») faute de dénominateur trafic. Run réel : 6 tours, ~$0,19.
- Substitut **contrôlé** à Q-0002 (pas encore de vrai destinataire métier) ; ne le résout pas.
- Follow-ups (non-bloquants) : `demo.py` nom de vue `accidents_route` (cosmétique) ; bruit `ToolSearch` dans la trace (filtre v2) ; Q-0016 (exposition = proxy population, trafic réel = futur) ; Q-0016 raffiné (modèle nul par défaut = **abstention** au lieu d'uniforme, slice dédiée) ; correctif console UTF-8 (Windows cp1252) trouvé au run réel.

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
