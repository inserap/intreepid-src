# Glossaire — intreepid

> Vocabulaire canonique du projet. Ajouter un terme ici quand :
> - il apparaît dans ≥ 2 documents avec une signification spécifique, OU
> - deux contributeurs ont utilisé le même mot avec des sens différents, OU
> - une ADR le définit formellement.
>
> Source canonique de la plupart des concepts : [`architecture/overview.md`](architecture/overview.md).

## Termes

| Terme | Définition |
|-------|------------|
| **Arbre d'exploration** | Structure d'une session de découverte : nœuds (hypothèses, requêtes, insights, parking), branches, bifurcations, impasses estompées. Mémoire épisodique brute. |
| **Empreinte spatiale (du raisonnement)** | Emprise géographique (ou temporelle / de sous-population) portée par chaque nœud de l'arbre, capturée par le greffier. Fonde le couplage arbre-carte. Primitive candidate à généralisation. |
| **Zones blanches** | Territoire couvert par les données mais jamais visité par aucune branche de raisonnement. Générateur de questions naïves. |
| **Greffier** | Agent qui documente silencieusement la session (hypothèses, requêtes, résultats, abandons + raisons, attribution, empreintes) et distille vers le graphe et la biographie à la clôture. |
| **Curateur** | Agent qui profile les nouveaux datasets, interviewe l'humain, et propose les corrections du catalogue par merge request. |
| **Critique** | Agent dont le mandat est de démolir les découvertes (corrélations fallacieuses, Simpson, MAUP, régression vers la moyenne), avec obligation de proportionnalité. |
| **Candide** | Agent qui pose délibérément les questions naïves/décalées pour ouvrir des voies latérales. |
| **Facilitateur** | Agent des sessions à plusieurs : sérialise les contributions, relance les silencieux, transforme les désaccords en hypothèses testables. |
| **Catalogue sémantique** | Fiches de connaissance YAML par dataset (sens métier, pièges, limites, relations, questions déjà explorées). Versionné GitLab/GitHub. |
| **Biographie des données** | Savoir accumulé sur les données elles-mêmes (fiabilités, ruptures, pertes de jointure), capturé en session et fusionné dans le catalogue. |
| **Graphe de connaissances** | Insights typés avec cycle de vie (idée → hypothèse → testée → confirmée/réfutée → périmée), preuves (requêtes) et attribution. Mémoire sémantique. |
| **Playbook** | Bibliothèque de coups analytiques éprouvés. Mémoire procédurale. |
| **Parking d'idées** | Zone où garer une idée hors du fil courant sans dérailler ; revue en fin de session. |
| **Modèle nul** | Contrefactuel aléatoire (permutations spatiales) généré avant de retenir un pattern ; ce qui ne se distingue pas du bruit meurt. |
| **MAUP** | *Modifiable Areal Unit Problem* : les résultats changent selon le découpage territorial. Parade : analyse multi-résolutions H3 + small multiples. |
| **Maille H3** | Grille hexagonale hiérarchique (16 résolutions) ; voisins équidistants, identifiant texte par cellule, agrégation par simple GROUP BY. |
| **Règle du montrable** | Quelque chose de démontrable à un tiers toutes les 2–3 semaines, même imparfait. |
| **Squelette qui marche** | Version minimale traversant tout le système de bout en bout, épaissie itération après itération. |
| **Risque cathédrale** | Tendance à sur-spécifier/perfectionner sans livrer (cf. Henry : Tier 1 complet, Tier 2 jamais commencé). |
| **Session** | Unité de travail exploratoire (solo ou à plusieurs), produisant une trace brute immuable et un notebook curaté. |
| **Notebook de sortie** | Projection lisible et rejouable d'une session (Quarto pressenti) — produit de la session, pas espace de travail. |
