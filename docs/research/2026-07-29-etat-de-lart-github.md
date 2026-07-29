# État de l'art — projets GitHub en lien avec intreepid

> **Objet** : veille technologique — projets open source similaires ou adjacents à intreepid
> (exploration analytique agentique, données géographiques ou non).
> **Méthode** : recherche approfondie menée le 2026-07-29 sur cinq axes en parallèle
> (pages GitHub publiques + recherche web). Étoiles et activité relevées à cette date
> (ordres de grandeur).
> **Statut** : document de veille — n'engage aucune décision d'architecture ; les
> recommandations sont des pistes à instruire (ADR le cas échéant).

---

## Synthèse exécutive

**1. La niche d'intreepid est réelle.** Aucun projet identifié — sur ~80 projets examinés,
une soixantaine retenus ici — ne combine les quatre signatures du projet :
(a) le LLM ne voit que des **profils statistiques/agrégats** servis par MCP, jamais les
lignes brutes ni la géométrie ; (b) la **session comme arbre d'exploration** persistant,
couplé à la carte ; (c) une **épistémologie multi-agents** (critique, candide, greffier —
les « multi-agents » existants sont des pipelines techniques, pas des rôles de
délibération) ; (d) la **mémoire distillée** (catalogue, graphe d'insights, playbook).
Chaque pièce existe isolément quelque part ; personne ne les a soudées, et personne
n'ajoute la dimension spatiale (empreinte carto par nœud de raisonnement).

**2. Le pari architectural est dans le sens du courant (2024→2026).**
- **Bascule du code-gen vers le tool-calling** : la 1re génération géo-LLM (LLM-Geo,
  ChatGeoPT) faisait générer du code (~80 % de réussite, non reproductible) ; la
  génération actuelle (OpenAssistant/kepler.gl, gis-mcp, Mundi, Kue) expose des
  primitives déterministes — exactement P1/P2.
- **Consolidation brutale des chatbots text-to-SQL** : Vanna archivé (03.2026),
  TaskWeaver archivé (03.2026), Dataherald abandonné, DataLine sans mainteneur,
  Briefer racheté. Le « chat devant une BDD » seul n'est pas un produit durable —
  l'anti-objectif d'intreepid est confirmé par le marché.
- **Le centre de gravité est le contexte sémantique gouverné** : les projets qui
  prospèrent (WrenAI, SuperSonic, Cube, dbt-MCP) donnent au LLM un modèle sémantique,
  pas le schéma brut — validation directe du catalogue YAML.
- **MCP devient l'interface universelle** agents ↔ données (Cube, MindsDB, MotherDuck,
  Esri en bêta) et **« local-first, le LLM ne voit que les métadonnées »** est le pattern
  dominant côté géo (kepler.gl, SQLRooms, Kue), avec DuckDB(-WASM) comme moteur récurrent.

**3. Ce qui n'existe nulle part — la valeur propre à construire** : `profile_stats`
comme proxy exclusif des données ; catalogue sémantique YAML sur GeoParquet ;
H3 exposé en MCP (aucun serveur H3 n'existe) ; combinaison DuckDB spatial + GeoParquet
+ MCP ; pont ML `train_model`/`predict`/`explain` ; mémoire de sessions analytiques.

**4. Briques réutilisables prioritaires** (licences permissives sauf mention) :

| Besoin intreepid | Brique candidate | Usage |
|---|---|---|
| Serveur MCP | **FastMCP v2** (déjà choisi) | middleware pour garde-fous transverses, composition `mount` |
| Read-only DuckDB | **mcp-server-motherduck**, **ktanaka101/mcp-server-duckdb** | patrons : `read_only=True` natif + limites de ressources (cf. postgres-mcp Pro) |
| Primitives spatiales MCP | **mahdin75/gis-mcp** (92 outils, PySAL inclus) | signatures d'outils à emprunter ; ajouter H3/DuckDB spatial soi-même |
| Feature engineering H3 | **kraina-ai/srai** | H3Regionalizer + jointures région-features = pipeline pilote accidents |
| Modèles nuls spatiaux | **pysal/esda** (LISA, Moran, permutations) | le garde-fou anti-pattern-fantôme du critique |
| Réfutation causale | **py-why/dowhy** (refuters) | outil `refute_insight` |
| Profil statistique | inspiration **ydata-profiling** (alertes), **whylogs** (profils fusionnables → dérive), **Sweetviz** (associations unifiées) | `profile_stats` reste à écrire en SQL DuckDB pushdown |
| Arbre / provenance | **Trrack** (modèle de données), **tldraw branching-chat-template** (canvas), **LangGraph** (checkpoint+fork = replay) | signature arbre-carte |
| Mémoire sémantique | **getzep/graphiti** (épisodes → faits temporels invalidables → entités) | mapping quasi 1:1 avec la mémoire à trois étages |
| Contexte suisse | **malkreide/swisstopo-mcp** (FastMCP, MIT) | montable côte à côte ; à vendorer (facteur bus = 1) |
| Restitution | **Quarto** + **Evidence** (confirmés) ; challengers : **marimo** (`.py` réactif, sûr en génération LLM), **Rill** (BI-as-code « agent-first », DuckDB+MCP) | notebooks et BI persistante |
| Front data workspace | **sqlrooms** (Foursquare, MIT, DuckDB + agents) | brique ou référence de design |

**5. Points de vigilance licences** : Rath (AGPL, gelé), Mundi.ai (AGPL+CLA),
Pingouin (GPL), D-Tale (LGPL), Chat2DB (source-available), AI-Scientist (RAIL),
Kue/LLM-Geo (GPL), LLM-Find (AGPL) → inspiration seulement, pas d'embarquement.

**6. Projets à suivre en veille continue** : Mundi.ai (trajectoire produit la plus
proche), Data Formulator (étalon UX d'exploration branchée), OpenAssistant/kepler.gl,
opengeos/geoai (branche agents/MCP), Rill, graphiti, workshop GeoGenAgent (SIGSPATIAL)
et les listes awesome-mcp-servers / awesome-agentic-AI-for-ST.

---

## Axe 1 — Agents LLM d'analyse de données / text-to-SQL / exploration conversationnelle

### Projets majeurs

**Vanna** — <https://github.com/vanna-ai/vanna> — ~23,8k★ — **archivé 03.2026** — MIT.
Text-to-SQL par RAG « entraîné » sur DDL + doc + paires question/SQL « golden ».
*Pertinence* : double leçon. (a) Les paires question→SQL validées sont une mémoire
capitalisable — à intégrer au playbook. (b) Contre-exemple stratégique : le
chatbot-devant-BDD pur finit archivé ou en pivot commercial ; la valeur durable est
dans le contexte accumulé, pas dans la génération SQL.

**WrenAI** — <https://github.com/Canner/WrenAI> — ~16,7k★ — actif — Apache-2.0.
« GenBI » : le LLM raisonne sur un modèle sémantique MDL (schéma + définitions métier),
pas sur les tables brutes ; 20+ sources dont DuckDB.
*Pertinence* : le plus proche philosophiquement sur le point clé du catalogue ; le MDL
est le meilleur benchmark pour concevoir le schéma YAML (relations, métriques,
synonymes). Diffère : orienté réponse/dashboard mono-agent, sans mémoire de découverte
ni critique ni rejouabilité.

**DB-GPT** — <https://github.com/eosphoros-ai/DB-GPT> — ~19,6k★ — très actif — MIT.
Plateforme data agentique auto-hébergeable : multi-agents, workflows AWEL, text-to-SQL
fine-tuné, sandbox.
*Pertinence* : référence multi-agents en environnement privé, mais plateforme
« tout-en-un » très lourde — contre-modèle du P7 (simplicité) ; ses agents sont des
pipelines techniques, pas des rôles épistémiques.

**PandasAI** — <https://github.com/sinaptik-ai/pandas-ai> — ~23,7k★ — actif — MIT (+/ee).
Analyse conversationnelle de dataframes : le LLM génère du Python exécuté en sandbox
Docker ; couche sémantique YAML.
*Pertinence* : sa couche YAML est à disséquer ; architecture opposée sur la sécurité
(code arbitraire généré, historique de CVE d'injection) — intreepid évite le problème
par construction (SQL visible + outils MCP read-only), argument à documenter.

**Microsoft LIDA** — <https://github.com/microsoft/lida> — ~3,3k★ — activité modérée — MIT.
Génération auto de visualisations : pipeline summarizer → goal explorer → visgenerator.
*Pertinence* : deux idées à reprendre telles quelles : le **summarizer** (profil compact
du dataset donné au LLM à la place des données = P2 avant l'heure) et le
**goal explorer** (génération d'hypothèses/questions — socle pour le candide).

**Microsoft Data Formulator** — <https://github.com/microsoft/data-formulator> —
~16k★ — très actif — MIT.
Exploration/visualisation pilotée par agents : canvas de dérivation de « concepts » de
données, **threads d'analyse branchables**.
*Pertinence* : le meilleur exemple UX existant de « workspace de découverte » vs chat
linéaire — à étudier pour l'arbre (matérialisation des pistes, reprise d'une branche).
Ne couvre ni SQL gouverné, ni mémoire, ni rigueur statistique — l'étalon à dépasser.

**Microsoft TaskWeaver** — <https://github.com/microsoft/TaskWeaver> — ~6,2k★ —
**archivé 03.2026** — MIT.
Agents « code-first » avec état analytique conservé entre tours.
*Pertinence* : l'idée d'état persistant nommé et réutilisable entre tours est précieuse ;
son archivage conforte le choix de bâtir sur MCP standard plutôt qu'un framework
propriétaire.

**SuperSonic** — <https://github.com/tencentmusic/supersonic> — ~5k★ — actif — Apache-2.0.
Chat BI + headless BI sur modèle sémantique gouverné.
*Pertinence* : son pipeline de **correction sémantique** (le SQL généré est validé/corrigé
contre le modèle avant exécution) est une idée forte pour fiabiliser le `query_sql`
d'intreepid.

**Dataherald** — <https://github.com/Dataherald/dataherald> — ~3,6k★ — abandonné (2024)
— Apache-2.0.
NL-to-SQL « enterprise » en API.
*Pertinence* : deux concepts à récupérer malgré l'abandon : le registre de **golden SQL**
(cousin du playbook) et le **score de confiance** attaché à chaque SQL généré,
affichable à côté du SQL visible (P6, incertitude chiffrée).

**Cube** — <https://github.com/cube-js/cube> — ~20,5k★ — très actif — Apache-2.0/MIT.
Le semantic layer open source de référence, désormais avec endpoint MCP.
*Pertinence* : validation d'architecture ; leur benchmark (DDL brut vs DDL + 4 Ko de
sémantique) chiffre le gain de l'approche catalogue. Surveiller l'Open Semantic
Interchange et MetricFlow (open-sourcé 10.2025) pour une éventuelle compatibilité.

### Signaux secondaires

- **Briefer** (~4,3k★, AGPL, racheté) : format « document d'analyse vivant » proche du
  rôle du greffier ; avertissement sur la viabilité des workspaces généralistes.
- **SQLCoder** (defog-ai, ~4k★) : LLM text-to-SQL locaux — option souveraineté ; rappel :
  le levier est le contexte, pas le modèle.
- **DataLine** (~1,6k★, GPL, décline) : positionnement local-first validé ; plafond du
  chatbot sans mémoire illustré.
- **Chat2DB** (~27,5k★, source-available) : persona développeur/DBA — délimite ce
  qu'intreepid n'est pas.
- **SQLBot** (~6,5k★, base GPLv3) : chat BI exposé **en tant que serveur MCP** — piste :
  intreepid pourrait aussi *exposer* ses capacités en MCP, pas seulement en consommer.
- **DeepBI**, **MindsDB**, **tablegpt-agent**, **SQL Chat** : périphériques.
- **InsightPilot** (Microsoft Research, EMNLP 2023, pas de code —
  <https://aclanthology.org/2023.emnlp-demo.31/>) : le LLM choisit des **actions
  d'analyse prédéfinies** au lieu d'écrire du code — ancêtre académique direct des
  outils MCP d'intreepid ; lecture recommandée.

---

## Axe 2 — LLM × géospatial / SIG

### Plateformes « GIS conversationnel »

**Mundi.ai** — <https://github.com/BuntingLabs/mundi.ai> — ~314★ — très actif —
**AGPL-3.0 + CLA**.
Web GIS « AI-native » : le LLM appelle géotraitements (QGIS headless en option),
symbologie, SQL PostGIS ; LLM locaux supportés.
*Pertinence* : le parent conceptuel le plus proche — à disséquer pour le découpage des
outils exposés et la création de **couches temporaires par opération** (non-destructif,
traçable). Diffère : pas de feature engineering H3 amont ni de socle DuckDB/GeoParquet.
Licence : inspiration seulement.

**SQLRooms** — <https://github.com/sqlrooms/sqlrooms> — ~456★ — très actif — **MIT**.
Framework React (Foursquare) pour applis analytiques local-first sur DuckDB
(WASM/natif) : « Rooms » = workspaces autonomes avec agents IA qui écrivent du SQL,
données restant locales.
*Pertinence* : alignement quasi parfait avec le socle — candidat sérieux comme brique
frontend ou référence de design « agent SQL sur DuckDB dans un workspace persistant ».

**Chat2Geo** — <https://github.com/GeoRetina/chat2geo> — ~510★ — MIT —
**archivé 06.2026** (devenu produit commercial).
Chat type ChatGPT + **MapLibre GL** + Earth Engine.
*Pertinence* : même triptyque UI qu'intreepid ; le code MIT archivé reste une mine pour
l'orchestration chat ↔ carte. Trajectoire instructive (open source vitrine → SaaS).

### Primitives spatiales exposées à l'agent

**OpenAssistant / kepler.gl AI Assistant** — <https://github.com/geodaai/openassistant>
— ~57★ (adossé à kepler.gl 11k+) — actif — **MIT**.
50+ outils géospatiaux JS exposés au LLM : stats spatiales GeoDa (**LISA, Moran**),
SQL DuckDB-WASM, **indexation H3**, classification, jointures spatiales — « les données
restent dans le navigateur, le LLM ne reçoit que les métadonnées ».
*Pertinence* : la validation la plus directe de P1/P2 ; le catalogue d'outils est un
gabarit pour la palette MCP d'intreepid ; `@kepler.gl/ai-assistant` montre le câblage
outils ↔ carte WebGL.

**gis-mcp** — <https://github.com/mahdin75/gis-mcp> — ~173★ — actif — **MIT**.
Serveur MCP, **92 fonctions** : Shapely, PyProj, GeoPandas, Rasterio, **PySAL**
(autocorrélation, clustering, régression spatiale).
*Pertinence* : la référence pour la granularité/nommage des outils spatiaux MCP ;
fork-able ou pillable. Manque H3, DuckDB spatial, GeoParquet — à ajouter soi-même.

**gdal-mcp** — <https://github.com/JordanGunn/gdal-mcp> — jeune — actif.
Workflows GDAL en MCP avec **middleware de « réflexion »** forçant l'agent à justifier
ses choix méthodologiques.
*Pertinence* : ce middleware de justification est transposable au greffier/critique
(choix de normalisation/agrégation défendables — cas accidents).

**opengeos/geoai** — <https://github.com/opengeos/geoai> — ~3,2k★ — très actif — MIT.
IA géospatiale haut niveau (écosystème geemap/leafmap), avec serveur MCP et
agent-harness cartographique récents.
*Pertinence* : standard de fait émergent côté communauté géo-Python — point
d'intégration et veille.

### Génération de code : l'approche alternative (et ses limites)

**LLM-Geo** — <https://github.com/gladcolor/LLM-Geo> — ~452★ — actif — GPL-3.0.
Pionnier « Autonomous GIS » : le LLM construit un graphe de solution et génère le code
de chaque nœud (~80 % de réussite).
*Pertinence* : contre-exemple du choix inverse (20 % d'échec, non reproductible = la
justification chiffrée de P1/P2) ; mais le **graphe de solution explicite** (plan
d'analyse inspectable) est réutilisable comme représentation du raisonnement.

**LLM-Find** — <https://github.com/gladcolor/LLM-Find> — ~61★ — AGPL.
Découverte/récupération autonome de données géo, avec un « handbook » par source.
*Pertinence* : le pattern « handbook par source » est transposable aux sources suisses
(STAC geo.admin.ch, OFROU) sous forme d'outil MCP `find_dataset` documenté.

**MapGPT** — <https://github.com/AGI-GIS/MapGPT> — académique (CaGIS 2024).
Cartographie autonome par invocation séquentielle d'outils carto.
*Pertinence* : référence pour l'ajustement itératif de symbologie MapLibre par dialogue
(palette/seuils de la carte de risque) via outils de style déterministes.

### Plugins QGIS conversationnels (écosystème des utilisateurs cibles)

**IntelliGeo** — <https://github.com/MahdiFarnaghi/intelli_geo> — ~63★ — actif —
Apache-2.0. Chat QGIS produisant du PyQGIS **ou des modèles graphiques Processing**.
*Pertinence* : la sortie « workflow inspectable plutôt que code opaque » est une idée
forte pour la confiance — analogue au plan d'analyse visible.

**Kue** — <https://github.com/BuntingLabs/kue-qgis-plugin> — ~17★ — GPL (SaaS).
Copilote QGIS ; n'envoie au cloud que **noms de couches, attributs et une ligne
d'échantillon par couche** ; SQL montré avant exécution.
*Pertinence* : contrat de confidentialité concret et communicable — même famille que
`profile_stats` ; « montrer le SQL avant exécution » = bonne pratique UX (P4/P6).

### Feature engineering spatial et benchmarks

**srai** — <https://github.com/kraina-ai/srai> — ~383★ — actif — Apache-2.0.
« Spatial Representations for AI » : régionalisation (**H3**, S2, Voronoï), chargeurs
OSM/Overture/GTFS, jointures région-features, embedders (Hex2Vec…).
*Pertinence* : brique idéale de la couche feature engineering — H3Regionalizer +
IntersectionJoiner = le pipeline maille H3 × accidents × contexte routier ; Hex2Vec
pour « trouve-moi des mailles au profil similaire ». API en évolution rapide.

**GeoLLM (Stanford)** — <https://github.com/rohinmanvi/GeoLLM> — académique (ICLR 2024).
Sérialisation textuelle du contexte spatial (lieux voisins, distances) dans le prompt.
*Pertinence* : formalise « comment décrire un lieu à un LLM sans géométrie » — utile
pour le format des profils de mailles H3 ; le papier jumeau sur les **biais
géographiques des LLM** est un garde-fou à documenter (les priors du LLM sur les
« zones dangereuses » sont biaisés — d'où les agrégats déterministes).

**GeoBenchX** — <https://github.com/Solirinai/GeoBenchX> — ~31★ — MIT.
Benchmark de tâches géo multi-étapes pour agents tool-calling (23 outils,
LLM-as-judge), mesurant aussi la **reconnaissance des tâches insolubles**.
*Pertinence* : méthode d'évaluation à adapter au cas OFROU — dont « détecter les
questions auxquelles les données ne peuvent pas répondre » (P6). Voir aussi
GeoAnalystBench (<https://github.com/GeoDS/GeoAnalystBench>) et GABench.

Mentions : **ChatGeoPT** (PoC 2023, pédagogique), **GeoGPT** (LLM de domaine
géosciences, orthogonal), **TorchGeo** (~3,5k★, ML observation de la Terre, sans LLM),
liste **awesome-agentic-AI-for-ST**
(<https://github.com/mohammadhashemii/awesome-agentic-AI-for-ST>).

---

## Axe 3 — Serveurs MCP données & géospatial

### Socle

**FastMCP** — <https://github.com/jlowin/fastmcp> — ~26,9k★ — très actif — Apache-2.0.
*Pertinence* : choix déjà acté, confirmé. La v2 apporte ce que le SDK officiel n'a pas :
**middleware** (garde-fous read-only/volumétrie transverses), **composition `mount`**
(séparer modules data/spatial/ML/mémoire), tests in-process.

**modelcontextprotocol/servers** — <https://github.com/modelcontextprotocol/servers> —
~89k★. Les serveurs de référence Postgres/SQLite sont **archivés** — l'écosystème data
MCP est porté par éditeurs et communauté. Le serveur *memory* (knowledge graph) est une
référence de design pour `search_knowledge`/`search_sessions`.

**awesome-mcp-servers** — <https://github.com/punkpeye/awesome-mcp-servers> — ~91,5k★ —
outil de veille continue.

### DuckDB / SQL

**mcp-server-motherduck** — <https://github.com/motherduckdb/mcp-server-motherduck> —
~504★ — actif — MIT. Officiel : DuckDB local/S3/MotherDuck, **read-only par défaut**.
*Pertinence* : le concurrent direct de `query_sql` — à étudier pour le read-only et
l'accès Parquet/S3. Mais il renvoie les **lignes brutes** au LLM (incompatible P2), sans
catalogue sémantique ni spatial. Verdict : emprunt de code, pas une base à forker.

**mcp-server-duckdb** — <https://github.com/ktanaka101/mcp-server-duckdb> — ~177★ — MIT.
*Pertinence* : une technique à retenir : déléguer le read-only au moteur
(`duckdb.connect(read_only=True)`) plutôt qu'à un filtre regex sur le SQL. Son design
« un outil unique » est l'anti-modèle (intreepid veut des outils sémantiques
différenciés).

**mcp-server-data-exploration** —
<https://github.com/reading-plus-ai/mcp-server-data-exploration> — ~544★ — MIT.
`load-csv` + `run-script` (Python arbitraire). *Pertinence* : philosophie opposée
(code arbitraire vs outils contraints) — contre-exemple ; son prompt `explore-data`
guidé est la seule chose à lire.

### PostgreSQL / PostGIS

**postgres-mcp « Pro »** — <https://github.com/crystaldba/postgres-mcp> — ~3,1k★ — MIT.
*Pertinence* : la meilleure référence de design d'un MCP data « sérieux » : son **mode
restricted** (transactions read-only + **limites de ressources/temps**) est exactement
le patron des garde-fous prévus ; bonne séparation schéma/exécution/diagnostic.

**pg-mcp-server** — <https://github.com/stuzero/pg-mcp-server> — modeste.
*Pertinence* : son **YAML de connaissance sur les extensions** (PostGIS, pgvector)
injecté comme contexte est le plus proche existant du catalogue sémantique YAML — à
lire pour le format.

**postgis-mcp** (receptopalak, ISC) et « PostGIS Yukon MCP » (~32 outils spatiaux,
validation SQL systématique) : petits, mais bonne granularité « une opération = un
outil » pour les primitives spatiales.

### Géo suisse et services

**swisstopo-mcp** — <https://github.com/malkreide/swisstopo-mcp> — 4★ mais très soigné
(138 commits, audit 07.2026) — **MIT** — Python 3.11 + FastMCP.
~20 outils sans auth : API geo.admin.ch (500+ couches), géocodage, altitudes/profils,
**WGS84↔LV95**, STAC, WMTS, cadastre RDPPF. Vérifié : **il n'existe pas de MCP officiel
geoadmin/swisstopo** à ce jour.
*Pertinence* : réutilisable quasi tel quel comme serveur compagnon (même stack,
read-only par nature) — à **vendorer** vu le facteur bus (1 contributeur). Alternatives :
vikramgorla/mcp-swiss (76 outils, TS), swiss-apis-mcp (REFRAME).

**mapbox/mcp-server** — <https://github.com/mapbox/mcp-server> — ~351★ — MIT.
*Pertinence* : le serveur géo le mieux industrialisé — structuration des outils,
primitives géométriques offline, et **MCP-UI** (rendu carto interactif dans la
conversation — la piste la plus crédible pour un rendu MapLibre/kepler via MCP,
niche aujourd'hui vide). Dépend d'un token Mapbox.

**open-streetmap-mcp** — <https://github.com/jagan-shanmugam/open-streetmap-mcp> —
~212★ — MIT. *Pertinence* : nommage d'outils « orienté tâche analytique »
(`analyze_neighborhood`) plutôt qu'« orienté API » — cohérent avec la philosophie
describe/profile.

**ArcGIS MCP (Esri)** — bêta propriétaire (06.2026, Location Services).
*Pertinence* : signal de marché (Esri valide MCP comme interface SIG), rien de
réutilisable.

**QGIS MCP** (jjsantos01, ~1k★) : pilote un desktop, code arbitraire — hors
architecture.

### Couche sémantique et notebooks

**dbt-mcp** — <https://github.com/dbt-labs/dbt-mcp> — ~596★ — très actif — Apache-2.0.
*Pertinence* : LA référence « exposer une couche sémantique à un LLM » — le triptyque
*list_metrics → get_dimensions → query* est le patron à imiter pour
`list_datasets`/`describe`. Trop couplé à dbt pour réutilisation directe.

**Cube MCP** : le serveur local est déprécié (SaaS) ; retenir le benchmark semantic
layer et la gouvernance de db-mcp (limites, blocage PII).

**jupyter-mcp-server** — <https://github.com/datalayer/jupyter-mcp-server> — ~1,2k★ —
BSD-3. *Pertinence* : hors cœur (code arbitraire), mais utile pour matérialiser une
session en notebook et pour la gestion des sorties multimodales (graphiques retournés
par outils).

### Bilan de l'axe : existe vs à construire

Existe et pillable : read-only DuckDB robuste, garde-fous ressources, primitives
spatiales génériques (gis-mcp), contexte suisse (swisstopo-mcp), patrons de couche
sémantique (dbt-mcp, pg-mcp-server).
N'existe nulle part : `profile_stats` comme proxy (tous renvoient les lignes brutes),
catalogue YAML sur GeoParquet, **H3 en MCP**, DuckDB spatial + GeoParquet + MCP,
pont ML, mémoire de sessions analytiques, viz MapLibre/kepler via MCP (piste MCP-UI).

---

## Axe 4 — Profiling, découverte d'insights, BI-as-code, rigueur statistique

### Profiling (candidats pour `profile_stats`)

**ydata-profiling** — <https://github.com/ydataai/ydata-profiling> — ~13,7k★ — actif —
MIT. *Pertinence* : la référence ; sortie **JSON** exploitable comme carte d'identité,
et surtout sa **taxonomie d'alertes** (skewness, cardinalité, uniformité, duplicats) à
transposer dans la partie « signaux » de `profile_stats`. Limites : pandas-centrique,
lourd, pas de spatial.

**whylogs** — <https://github.com/whylabs/whylogs> — ~2,8k★ — actif — Apache-2.0.
Profils par **sketches** streaming, **fusionnables** et versionnables ; dérive = diff
de deux profils.
*Pertinence* : la conception la plus proche de l'esprit `profile_stats` (profil =
artefact léger, sérialisable, comparable dans le temps) — la bonne architecture si on
profile des partitions, et la dérive devient gratuite (découverte proactive FME Flow).

**Sweetviz** (~3,1k★, MIT) : la **matrice d'associations unifiée** num/cat (Pearson +
coefficient d'incertitude + rapport de corrélation) est directement transposable — le
LLM a besoin d'un seul tableau d'associations, pas de trois métriques disjointes.
**D-Tale** (~5,2k★, LGPL) : catalogue de « ce qu'un humain regarde en premier ».
**dataprep** (~2,2k★, maintenance incertaine) : plan B seulement.

Conclusion profiling : **`profile_stats` reste à écrire en interne, en SQL DuckDB
pushdown** (`approx_quantile`, `approx_count_distinct`, entropie, window functions pour
les trous temporels, `ST_Extent` pour l'emprise) — aucune lib ne couvre le cahier des
charges (stats + temporel + spatial, en JSON compact pour LLM) ; les trois emprunts
ci-dessus donnent la sortie.

### Découverte d'insights / auto-EDA

**Rath** — <https://github.com/Kanaries/Rath> — ~4,7k★ — **AGPL, gelé** (pivot
PyGWalker). Le projet historiquement le plus proche de la vision (AutoPilot, Copilot,
causalité) — inspiration UX/algorithmique uniquement ; étudier son « mega-auto
explainer » pour la boucle d'hypothèses.

**PyGWalker** — <https://github.com/Kanaries/pygwalker> — ~15,9k★ — très actif —
Apache-2.0. Exploration type Tableau, **calcul délégué à DuckDB**, specs de charts
sérialisables. *Pertinence* : valide l'architecture compute ; les specs JSON de
graphiques sont un bon format pivot LLM → visualisation.

**Data Formulator** (cf. axe 1) : l'étalon UX agentique du domaine.

**Lux** (~5,4k★, quasi arrêté) : sa grammaire d'**intents** (Enhance/Filter/Generalize)
inspire les « prochaines questions » que l'agent propose après un profil.

**MetaInsight / QuickInsights** (Microsoft Research, SIGMOD 2019/2021) — **pas de code
publié** (productisé dans Power BI). *Pertinence* : la meilleure base algorithmique
pour le **scoring d'insights** (types d'insights, significance, priorisation par
impact) — à réimplémenter sur DuckDB à partir des papiers :
<https://www.microsoft.com/en-us/research/wp-content/uploads/2021/03/metainsight-extended.pdf>,
<https://www.microsoft.com/en-us/research/uploads/prod/2019/05/QuickInsights-camera-ready-final.pdf>.

**Evidently** — <https://github.com/evidentlyai/evidently> — ~7,8k★ — très actif —
Apache-2.0. 100+ métriques dérive/qualité, Test Suites pass/fail, JSON.
*Pertinence* : brique prête pour le volet dérive/anomalies de la découverte proactive ;
bon modèle d'API « Report = liste de métriques déclaratives ».

### BI-as-code et restitution

**Evidence** (~6,8k★, MIT) : markdown + SQL → site statique — **idéal en génération
LLM** (texte pur, diffable) ; cible de matérialisation confirmée.
**Quarto** (~5,9k★, MIT) : notebook de restitution confirmé (le dépôt contient même de
la documentation destinée aux LLM) ; complémentaire d'Evidence (document figé rigoureux
vs BI vivante).
**marimo** — <https://github.com/marimo-team/marimo> — ~22,1k★ — très actif —
Apache-2.0. Notebook **réactif** en `.py` pur, sans état caché, SQL/DuckDB natif.
*Pertinence* : alternative sérieuse comme format d'atelier — le graphe réactif élimine
l'état caché, critique quand c'est un LLM qui écrit les cellules ; `.py` plus sûr à
générer/diffuser que du JSON ipynb. POC recommandé.
**Rill** — <https://github.com/rilldata/rill> — ~2,8k★ — très actif — Apache-2.0.
BI-as-code « **agent-first** » : YAML+SQL, moteur DuckDB, semantic layer, **serveur
MCP**. *Pertinence* : le challenger direct d'Evidence, idéologiquement le plus aligné ;
son « metrics view YAML » inspire le catalogue.
**Superset** (~70k★, Apache-2.0) : persistance BI « entreprise » via API import/export ;
assets moins LLM-friendly qu'Evidence — à réserver aux déploiements où il existe déjà.

### Rigueur statistique outillée

**DoWhy** — <https://github.com/py-why/dowhy> — ~8,2k★ — actif — MIT.
Inférence causale model → identify → estimate → **refute**.
*Pertinence* : brique clé — les **refuters** (placebo treatment, random common cause,
data subset) sont exactement les garde-fous anti-corrélations-fallacieuses, exposables
comme outil MCP `refute_insight` au service du critique ; le module GCM d'attribution
d'anomalies alimente les insights explicatifs.

**esda / PySAL** — <https://github.com/pysal/esda> — ~255★ — actif (NSF) — BSD-3.
Moran's I, **LISA**, Getis-Ord, avec **inférence par permutation** intégrée.
*Pertinence* : quasi sans alternative pour les **modèles nuls spatiaux** — « ce cluster
est-il significatif sous permutation spatiale ? » est précisément le garde-fou avant de
promouvoir un insight géographique. Standard académique malgré peu d'étoiles.

**Pingouin** (~1,9k★, **GPL**) : sorties riches (taille d'effet + IC + puissance +
corrections multi-tests — indispensables quand un agent teste des dizaines
d'hypothèses, garden of forking paths). Licence à surveiller ; alternative BSD :
`scipy.stats.permutation_test`/`bootstrap`.

**pointblank** — <https://github.com/posit-dev/pointblank> — ~460★ — actif (Posit) —
MIT. Validation chaînable multi-backend (**DuckDB natif** via Narwhals/Ibis), et
`DraftValidation` qui **génère des règles par IA à partir du dataset** — exactement le
pont profil → contraintes que `profile_stats` peut alimenter. Meilleur fit que
Great Expectations (~11,7k★, lourd, orienté pipelines — inspiration de vocabulaire).

---

## Axe 5 — Provenance, arbres d'exploration, agents adverses, mémoire

### Provenance et traçabilité d'analyse

**Trrack** — <https://github.com/visdesignlab/trrack> (successeur
<https://github.com/Trrack/trrackjs>) — BSD-3 — TypeScript.
Provenance d'interactions en **graphe arborescent** : nœud par action, annotations,
métadonnées, partage d'état par URL, composant de visualisation (trrack-vis).
*Pertinence* : **très haute — quasiment le modèle de données de l'arbre d'intreepid.**
Schéma nœud/action/état, sérialisation JSON et mini-arbre navigable (minimap)
réutilisables ou imitables. À étudier : leur gestion de la granularité et le merge
d'actions rapprochées (anti-hairball).

**VisTrails** — <https://github.com/VisTrails/VisTrails> — ~105★ — dormant — BSD-3.
Pionnier de la provenance de workflows scientifiques (le « version tree »).
*Pertinence* : l'ancêtre académique exact de l'arbre d'exploration — 15 ans de leçons
publiées sur le replay et l'élagage visuel des branches abandonnées.

**Verdant** — <https://github.com/mkery/Verdant> — ~152★ — MIT.
Historique automatique complet de notebooks Jupyter, indexé par artefact.
*Pertinence* : leçons de design pour le greffier — capturer tout automatiquement mais
**indexer par artefact, pas par chronologie**, sinon l'historique est inutilisable.

**OpenLineage** — <https://github.com/OpenLineage/OpenLineage> — ~2,6k★ — Apache-2.0 —
LF AI & Data. Standard de lineage Jobs/Runs/Datasets + **facets** extensibles.
*Pertinence* : si le greffier émet ses traces (SQL, transformations) au format
OpenLineage, intégration gratuite à l'écosystème data client ; le pattern « facets »
est un bon modèle d'extensibilité pour annoter les nœuds.

**Kedro-Viz** — <https://github.com/kedro-org/kedro-viz> — ~753★ — Apache-2.0.
*Pertinence* : un des rares projets ayant industrialisé la lisibilité de grands graphes
(**collapse hiérarchique, focus mode**) — les techniques anti-hairball à reprendre ;
composant React réutilisable.

### Arbres de conversation / raisonnement (UI)

**Loom** — <https://github.com/socketteer/loom> — ~1,4k★ — dormant mais culte.
« Multiversal tree writing interface » : arbre de génération multi-branches.
*Pertinence* : inspiration UX directe — navigation clavier, vue linéaire d'une branche
vs vue topologique ; ses « zones non explorées du multivers » sont le parent des
**zones blanches du raisonnement**.

**tldraw branching-chat-template** —
<https://github.com/tldraw/branching-chat-template> — récent — MIT.
Arbre de chat sur canvas infini (tldraw SDK), contexte reconstruit en remontant la
branche. *Pertinence* : **base front candidate** — tldraw apporte gratuitement
pan/zoom/minimap/multi-utilisateur ; prouve la faisabilité en ~40 commits.

**Forky** — <https://github.com/ishandhanani/forky> — ~36★ — récent.
Chats LLM façon git : DAG, fork, et **merge sémantique à 3 voies** (LCA + résumé d'état
par branche). *Pertinence* : le patron pour fusionner des insights de branches
divergentes (distillation par le greffier). Voir aussi Prompt-Tree
(<https://github.com/yxp934/Prompt-Tree>, curation manuelle du contexte par nœuds).

**LangGraph** — <https://github.com/langchain-ai/langgraph> — ~38,4k★ — MIT — très
actif. **Checkpointing durable + time-travel (rejouer/forker depuis tout checkpoint)**
+ human-in-the-loop.
*Pertinence* : backend d'exécution candidat — chaque nœud de l'arbre peut être un
checkpoint forkable : le **mode replay** presque clé en main. (À arbitrer vs Claude
Agent SDK déjà choisi — l'emprunt peut se limiter au patron de checkpointing.)

### Agents adverses / débat

**MAD (Multi-Agents-Debate)** — <https://github.com/Skytliang/Multi-Agents-Debate> —
~599★ — GPL-3.0. Débat affirmatif/négatif + juge contre la « degeneration of thought ».
*Pertinence* : la justification empirique de l'architecture critique/candide (un agent
seul ne se corrige pas) ; prompts de rôles et mécanisme d'arrêt transposables.

**llm_multiagent_debate** (Du et al., ICML 2024) —
<https://github.com/composable-models/llm_multiagent_debate> — ~544★.
*Pertinence* : les chiffres pour **calibrer le coût du critique** — le gain plafonne
vite (2-3 agents, 2-3 rounds) → le critique doit être déclenché sélectivement (sur les
découvertes candidates), pas en continu. Converge avec le principe de proportionnalité
de la charte.

**ChatEval** — <https://github.com/chanchimin/ChatEval> — ~340★ — Apache-2.0.
Panel d'arbitres multi-personas avec délibération transparente.
*Pertinence* : le pattern « personas configurables » pour critique/candide ; la
délibération elle-même doit être capturée dans l'arbre (greffier).

**AutoGen** — <https://github.com/microsoft/autogen> — ~60k★ — MIT — **mode
maintenance**. *Pertinence* : bibliothèque de patterns (writer/critic, group chat) à
piller, pas un socle.

### Mémoire d'agents

**Graphiti (Zep)** — <https://github.com/getzep/graphiti> — ~29,3k★ — Apache-2.0 —
très actif. Graphe de connaissances **temporel** : épisodes (sources brutes) → faits
avec **fenêtres de validité** (invalidés, jamais supprimés) → entités ; récupération
hybride sub-seconde.
*Pertinence* : **LE candidat pour la mémoire sémantique** — mapping quasi 1:1 : arbres
de session immuables = épisodes, insights = faits avec provenance native vers l'épisode
source, et l'invalidation temporelle gère « réfuté par le critique » sans perte
d'historique. (Backend Neo4j/FalkorDB à peser face au P7.)

**Letta (ex-MemGPT)** — <https://github.com/letta-ai/letta> — ~24k★ — Apache-2.0.
*Pertinence* : incarne P9 (apprendre par le contexte, pas les poids) ; self-editing
memory et sleep-time compute = modèle pour la distillation asynchrone du playbook.

**Mem0** — <https://github.com/mem0ai/mem0> — ~62k★ — Apache-2.0.
*Pertinence* : l'état de l'art de l'**extraction** (que garder, à quelle granularité, à
quel coût) et ses benchmarks — la question centrale du greffier.

**Cognee** — <https://github.com/topoteretes/cognee> — ~29,5k★ — Apache-2.0.
*Pertinence* : alternative à Graphiti tournant sur simple **PostgreSQL+pgvector**
(P7-friendly), avec génération d'ontologies (structuration auto du catalogue) et
opération « Improve » (boucle greffier→critique→mémoire).

### Agents de découverte scientifique

**AI Scientist (Sakana)** — <https://github.com/SakanaAI/AI-Scientist> — ~14,3k★ —
licence RAIL (non permissive). *Pertinence* : son module de **peer review automatisé**
(few-shot sur critères, score agrégé) est un patron mûr pour le critique — s'en
inspirer, ne pas en dépendre.

**data-to-paper** — <https://github.com/Technion-Kishony-lab/data-to-paper> — ~814★ —
**MIT** — mature. Agents guidés le long du chemin scientifique, mode Copilot supervisé,
et **« data-chaining » : chaque valeur du manuscrit est cliquable et remonte aux lignes
de code qui l'ont produite**.
*Pertinence* : **la plus proche parente du greffier** — la traçabilité
clic-jusqu'à-la-source est exactement la promesse insight → nœud → requête → données
(P4) ; le mode Copilot montre comment insérer la validation humaine sans casser le
flux. MIT : code étudiable et réutilisable.

---

## Enseignements transverses pour les prochaines étapes

1. **Granularité de capture du greffier** (risque n°2 identifié dans l'overview) :
   Verdant et Mem0 convergent — tout capturer automatiquement, mais **indexer par
   artefact/entité, pas par chronologie**. À intégrer dès le modèle de données de
   l'arbre.
2. **Anti-hairball** : deux mécanismes complémentaires éprouvés — collapse hiérarchique
   + focus mode (Kedro-Viz) et double vue linéaire/topologique (Loom). Prévoir
   l'agrégation de nœuds dès la conception (cohérent avec la « sémantique du zoom »).
3. **Coût du critique** : la littérature du débat multi-agents est unanime — le gain
   plafonne à 2-3 agents / 2-3 rounds ; déclenchement sélectif sur les découvertes
   candidates (conforme au principe de proportionnalité de la charte).
4. **Le différenciateur défendable face à Data Formulator & co.** n'est pas le chat ni
   la carte : c'est la **validation statistique outillée avant matérialisation**
   (esda/permutations, DoWhy/refuters, corrections multi-tests) + la **provenance
   cliquable** (à la data-to-paper) + la **mémoire distillée**. Aucun concurrent
   n'outille les trois.
5. **Positionnement** : la vague 2025-2026 des canvas de chat arborescents banalise le
   « branching chat » — intreepid doit se positionner un cran au-dessus : brancher
   *l'enquête analytique* (avec preuve, carte et mémoire), pas la conversation.
