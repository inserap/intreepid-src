# Brique #6 — robustesse d'échelle spatiale (H3 multi-résolution)

> Ce qu'elle montre : l'analyste teste si la **sur-concentration spatiale** des
> accidents OFROU (au-delà de l'exposition STATPOP) **survit au changement de
> maille H3** (résolutions 6, 7, 8). Verdict sur donnée réelle : **robuste** —
> la concentration est significative aux trois résolutions. Lecture honnête :
> population ≠ trafic ; les corridors de transit (peu peuplés) ressortent en
> cellules non-peuplées — indéfini, pas une preuve de danger.

Setup commun : voir [`README.md`](README.md) (uv, `claude setup-token`, `ANTHROPIC_API_KEY` absente).

## Pré-vol (spécifique)

Depuis la racine `intreepid/src` :

```bash
# 1) La donnée raw doit être présente (artefact fourni en amont — job ETL/FME) :
ls data/raw/RoadTrafficAccidentLocations.parquet

# 2) Générer les parquet analysis-ready (prepared, gitignorés, régénérables) :
uv run python -m prepare.accidents_route       # -> 267761 lignes (projection + geom + date)
uv run python -m prepare.statpop_population    # -> grille STATPOP 100 m (exposition spatiale)

# 3) quarto est OPTIONNEL : s'il est absent, le .qmd est produit (l'HTML est un bonus).
quarto --version 2>/dev/null || echo "quarto absent : .qmd seul (dégrade proprement)"
```

## Déroulé

```bash
uv run python -m intreepid.demo_scale_robustness
```

Le driver pointe le serveur MCP sur la **fiche réelle**
(`INTREEPID_FICHE=catalog/accidents_route.fiche.yaml`, héritée par le
sous-processus stdio), lance une session **one-shot capturée** (analyste
`opus`), puis génère `data/prepared/session_brique6.qmd` depuis la trace.

## Sorties réelles (smoke run du 2026-08-02, appel direct — sans agent)

Temps de calcul de l'outil : **5,3 s** (3 résolutions × 999 permutations sur
267 761 points OFROU + grille STATPOP 100 m).

```json
{
  "spatial_col": "geom",
  "exposure_model": "declared:statpop_population",
  "resolutions": [6, 7, 8],
  "seed": 42,
  "n_permutations": 999,
  "verdict": "robuste",
  "per_resolution": [
    {
      "resolution": 6,
      "n_cells_tested": 1070,
      "n_total_tested": 267333,
      "pic": { "h3": "861f9d98fffffff", "lat": 46.71920, "lng": 8.42034, "std_excess": 374.07 },
      "pseudo_p": 0.001,
      "significant": true,
      "unpopulated": { "n_cells": 47, "n_points": 428, "share": 0.0016 }
    },
    {
      "resolution": 7,
      "n_cells_tested": 4986,
      "n_total_tested": 266058,
      "pic": { "h3": "871f9d81bffffff", "lat": 46.68247, "lng": 8.60190, "std_excess": 178.65 },
      "pseudo_p": 0.001,
      "significant": true,
      "unpopulated": { "n_cells": 342, "n_points": 1703, "share": 0.0064 }
    },
    {
      "resolution": 8,
      "n_cells_tested": 17927,
      "n_total_tested": 256577,
      "pic": { "h3": "881f8edb41fffff", "lat": 47.42811, "lng": 8.49040, "std_excess": 388.34 },
      "pseudo_p": 0.001,
      "significant": true,
      "unpopulated": { "n_cells": 2741, "n_points": 11184, "share": 0.0418 }
    }
  ],
  "caveats": [
    "Le null est proportionnel à l'exposition déclarée dans la fiche : une concentration au-delà de cette exposition n'est pas une preuve de causalité (l'exposition déclarée n'est pas nécessairement le facteur explicatif du phénomène).",
    "Agrégation planaire H3 : biaisée pour un phénomène contraint à un réseau 1-D plutôt qu'étalé dans le plan (cf. Xie & Yan 2008, densité de réseau).",
    "Hiérarchie H3 non-emboîtante : l'identité d'une cellule d'une résolution à l'autre n'est pas affirmée ; le pic est décrit par résolution."
  ]
}
```

### Lecture des chiffres clés

| Résolution | Cellules testées | Pic std_excess | pseudo-p | Unpopulated share |
|---|---|---|---|---|
| 6 (≈ 36 km²) | 1 070 | 374,07 | 0,001 | 0,16 % |
| 7 (≈ 5 km²) | 4 986 | 178,65 | 0,001 | 0,64 % |
| 8 (≈ 0,7 km²) | 17 927 | 388,34 | 0,001 | **4,18 %** |

**Verdict : robuste** — la sur-concentration survit aux trois grilles. Le
pseudo-p plancher (0,001 = 1/999) confirme la significativité mais c'est le
`std_excess` qui mesure l'intensité (pic entre 178 et 388 selon la résolution).

La **part unpopulated croît avec la résolution** (0,16 % → 4,18 % à res 8) :
les cellules fines capturent les corridors de transit à faible population STATPOP
— attendu et documenté dans la fiche (`note: axes de transit`).

## Ce que ça met en évidence

- **Robustesse d'échelle** : la conclusion ne dépend pas du choix arbitraire de
  la maille H3 — valeur épistémique directe.
- **Limites honnêtes exposées** : population ≠ trafic (caveat 1), biais planaire
  pour un phénomène de réseau routier (caveat 2 — Xie & Yan 2008), non-emboîtement
  H3 (caveat 3).
- **Cellules non-peuplées = corridors de transit** : à res 8, 4,18 % des points
  tombent hors exposition STATPOP — indéfini dans le modèle nul, **pas une preuve
  de danger**, documenté comme tel.
- **Agnostique au domaine** : l'agent compose l'outil ; aucune logique métier
  n'est codée dans le driver ou le serveur MCP.

## Objections & réponses

- *« Le verdict "robuste" prouve la dangerosité de ces zones ? »* → **Non** —
  la sur-concentration est mesurée par rapport à la population STATPOP, proxy
  grossier, pas le trafic (TMJA absent). Robuste ≠ dangereux.
- *« pseudo-p = 0,001 partout, ça ne discrimine rien ? »* → C'est le plancher
  atteignable avec 999 permutations. Ce qui discrimine l'intensité, c'est le
  `std_excess` : res 7 (178,65) < res 6 (374,07) < res 8 (388,34). La
  résolution 8 capture des pics hyperlocaux très intenses.
- *« Pourquoi les cellules non-peuplées augmentent avec la résolution ? »* →
  Les cellules fines (res 8 ≈ 0,7 km²) isolent des tronçons de route à
  population résidente quasi nulle (tunnels, échangeurs, routes de montagne)
  que la grille STATPOP 100 m ne couvre pas. C'est le biais planaire H3 documenté
  dans les caveats.
- *« Pourquoi pas NKDE ou Gi* ? »* → Hors périmètre brique #6 (Q-0016
  partiellement résolu). Documenté en OPEN-QUESTIONS pour la v2.

## Plan B

- **Outil lent (> 90 s)** → non observé (5,3 s sur 267 761 points). Si cela
  se produit sur une machine plus lente, passer `n_permutations=99` directement
  dans le smoke test (le driver utilise la valeur par défaut 999 de l'outil).
- **Verdict mal formé** (l'agent n'émet pas un tableau JSON) → `run_analysis`
  lève avant la génération du notebook. Remède : relancer (non-déterministe).
- **`quarto` absent** → le `.qmd` est produit, l'HTML est sauté proprement
  (`render_html` best-effort). Pour l'HTML : `quarto render data/prepared/session_brique6.qmd`.
