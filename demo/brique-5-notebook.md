# Brique #5 — le produit de session (analyste réel + notebook Quarto)

> Ce qu'elle montre : l'analyste tourne sur la **vraie donnée OFROU** (267 761 lignes), le
> greffier capture la session, et un **notebook Quarto rejouable** est généré depuis la trace.
> C'est la **validation de bout en bout de la v1 sur du réel** — le substitut contrôlé à Q-0002
> (pas encore de vrai destinataire métier).

Setup commun : voir [`README.md`](README.md) (uv, `claude setup-token`, `ANTHROPIC_API_KEY` absente).

## Pré-vol (spécifique)

Depuis la racine `intreepid/src` :

```bash
# 1) La donnée raw doit être présente (artefact fourni en amont — job ETL/FME, hors
#    périmètre de notre solution) :
ls data/raw/RoadTrafficAccidentLocations.parquet

# 2) Générer les parquet analysis-ready (prepared, gitignorés, régénérables) :
uv run python -m prepare.canton_population     # -> 26 cantons (exposition population BFS)
uv run python -m prepare.accidents_route       # -> 267761 lignes (projection + geom + date)

# 3) quarto est OPTIONNEL : s'il est absent, le .qmd est produit (l'HTML est un bonus).
quarto --version 2>/dev/null || echo "quarto absent : .qmd seul (dégrade proprement)"
```

## Déroulé

```bash
uv run python -m intreepid.demo_notebook
```

Le driver pointe le serveur MCP sur la **fiche réelle** (`INTREEPID_FICHE=catalog/accidents_route.fiche.yaml`,
héritée par le sous-processus stdio), lance une session **one-shot capturée** (analyste `opus`),
puis génère `data/prepared/session_brique5.qmd` depuis la trace.

## Sorties réelles (run du 2026-08-01, `opus`, coût **$0.19**, 6 tours)

Verdict de l'analyste (extrait — sur donnée **réelle et propre**) :

```text
- [fait] Aucune valeur sentinelle ni valeur aberrante détectable : accident_month borné
         [1;12], null_rate 0, zero_rate 0, n_outliers_3sigma 0 ; aucun code 999/-1/0.
- [fait] Série temporelle complète : series_gaps_months = 0 sur 2011→2025 (180 mois),
         volume_by_year en bande étroite — aucune rupture de collecte.
- [fait] geom saine : out_of_envelope_rate 0, invalid 0, 267761/267761 POINT SRID 2056.
- [fait] BE sur-concentré au-delà de son exposition : 37891 obs vs 32027,95 attendus
         (+5863, std_excess 32,76, pseudo-p 0,001).
- [refusé] BE serait un canton plus dangereux que la moyenne suisse.
- [fait] ZH domine les comptages bruts (49397) mais s'explique par l'exposition :
         48118 attendus, excès +1279 seulement (std_excess 5,83).
- [hypothèse] type_route très concentré (route principale 49,54% + secondaire 36,99% = 86,5%).
- [fait] severity déséquilibré (légers 77,92% / graves 20,78% / tués 1,30%).
- [fait] saisonnalité régulière : creux février (15132), pic juin (28984), rapport 1,92.
- [fait] Verdict global : 9 colonnes exploitables, aucun défaut bloquant ; les limites
         (granularité mensuelle, exposition = proxy population, pas de dénominateur trafic,
         briques spatiales fines non implémentées) sont des limites de PORTÉE, documentées.

=== notebook généré : data/prepared/session_brique5.qmd ===
HTML : (quarto absent, .qmd seul)
```

Le notebook `.qmd` rejoue la session : front-matter HTML (toc, code-fold, embed-resources),
appels d'outils en blocs `{.json}` + résultats agrégés, et chaque observation en **callout typé** :

```markdown
::: {#nte-16 .callout-note}
## fait · confiance haute
Le canton BE est sur-concentré au-delà de son exposition déclarée : 37891 observés
contre 32027,95 attendus (excès +5863, std_excess 32,76, pseudo-p 0,001 sur 999 permutations).

*… RÉSERVE D'EXPOSITION : le dénominateur est la population résidente (BFS), proxy GROSSIER
qui n'est PAS le trafic. Ce fait porte sur le rapport accidents/habitants, pas sur un excès réel.*
:::

::: {#cau-17 .callout-caution}
## refusé · confiance haute
BE serait un canton plus dangereux que la moyenne suisse.

*Refus explicite malgré le pseudo-p de 0,001. « Une concentration au-delà de la population
n'est pas une preuve de dangerosité » ; un dénominateur trafic (véhicules-km) est indispensable
et absent. Conclure exigerait de joindre et normaliser des données que je n'ai pas.*
:::

---
*tours : 6 · coût : $0.1879405 · fin : completed*
```

## Ce que ça met en évidence (fonctionnalités fortes de la v1, sur du réel)

- **`profile_stats` aux 4 types** sur 267 761 vraies lignes : qualité-donnée lue sans jamais voir une ligne (P2).
- **Honnêteté (P6) validée sur un 2ᵉ dataset réel** : la donnée réelle est **propre** → l'analyste le **dit**, sans halluciner d'anomalie (contraste avec la fixture où 999/trous/hors-emprise étaient plantés).
- **Volume ≠ excès, sur du réel** : ZH (plus gros comptage) n'est **pas** le plus concentré ; BE l'est. Sans le modèle nul, le classement par comptage brut aurait trompé.
- **Refus causal motivé** : l'analyste refuse « BE plus dangereux » et **explicite** pourquoi (proxy population ≠ trafic).
- **Le produit de session** : un notebook Quarto **rejouable, versionnable, partageable** — le différenciateur n°1 (« documentation à coût zéro »), généré déterministe depuis la trace figée.

## Objections & réponses

- *« Donc BE est plus dangereux ? »* → **Non** — c'est un excès **par rapport à la population**, un proxy grossier gravé comme réserve dans la fiche. Le dénominateur trafic (TMJA / véhicules-km) est absent ; le conclure serait malhonnête (l'analyste le refuse lui-même).
- *« pseudo-p = 0,001, c'est massif ? »* → 0,001 est le **plancher** atteignable avec 999 permutations ; c'est le `std_excess` (BE 32,76 vs ZH 5,83) qui **discrimine** l'intensité, pas le pseudo-p seul.
- *« Pourquoi pas de test sur type_route ? »* → Aucune **exposition déclarée** pour cette colonne dans la fiche → pas de dénominateur → l'analyste reste en `hypothèse` (il n'invente pas le nul).

## Findings de validation (consignés)

- **Q-0004 (dette de charte)** : la charte porte l'exemple `999` — **inerte** ici (colonne inexistante dans le réel) ; le tuning « concentration→hypothèse » reste générique. Sur le réel propre, la posture tient sans dé-tuning. Matière pour l'extraction charte↔fiche (hors périmètre brique #5).
- **Bug Windows corrigé en séance** : l'impression console (cp1252) plantait sur les caractères du verdict (`≈`, `±`) → `UnicodeEncodeError`. Correctif : `sys.stdout.reconfigure(encoding="utf-8", errors="replace")`. Révélé **par ce run réel** (la fixture ne produisait pas ces caractères) — valeur de la validation.
- **Bruit `ToolSearch` dans la trace** : la découverte d'outils de l'Agent SDK (deferred tools) est capturée fidèlement par le greffier ; filtrage cosmétique = raffinement v2.

## Plan B

- **Verdict mal formé** (l'agent n'émet pas un tableau JSON) → `run_analysis` lève **avant** la génération du notebook (pas de `.qmd`). Remède : **relancer** la démo (non-déterministe). Non observé sur les runs de validation.
- **`quarto` absent** → le `.qmd` est produit, l'HTML est sauté proprement (`render_html` best-effort). Pour l'HTML : installer quarto puis `quarto render data/prepared/session_brique5.qmd`.
