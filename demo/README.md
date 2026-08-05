# Démos — intreepid

Ce dossier regroupe les **runbooks de présentation**, **un fichier par démo**. Chaque
runbook est autonome (déroulé, commandes, sorties attendues, répliques, objections,
plan B). Le **setup commun** (identique à toutes les démos) vit ici, pour ne pas le
répéter.

## Setup commun (une fois)

Depuis la racine `intreepid/src` :

```bash
uv sync --extra dev        # environnement Python (uv, jamais pip)
claude setup-token         # auth agent = abonnement (ouvre le navigateur, stocke le token)
echo "${ANTHROPIC_API_KEY:-<absente, OK>}"   # DOIT être absente (sinon elle masque l'abonnement)
```

Le pré-vol spécifique (les vérifications juste avant une séance) est **dans chaque
runbook**.

## Démos disponibles

| Démo | Runbook | Ce qu'elle montre | Statut |
|---|---|---|---|
| Brique #1 — l'analyste honnête | [`brique-1-analyste-honnete.md`](brique-1-analyste-honnete.md) | proxy statistique (jamais de lignes brutes), refus du faux pattern, isolation P2/P3, preuve en CI | à jour (`v0.2.0`) |
| Brique #2 — le temps et l'espace | [`brique-2-temps-et-espace.md`](brique-2-temps-et-espace.md) | profil aux 4 types (temporel + spatial), trou de collecte + points hors zone, **double** refus causal, densité différée (H3), preuve en CI | à jour (`v0.3.0`) |
| Brique #3 — concentration et preuve | [`brique-3-concentration-et-preuve.md`](brique-3-concentration-et-preuve.md) | modèle nul multinomial pondéré, contraste most_concentrated (BE) vs highest_raw_count (ZH), pseudo-p, piège « volume ≠ excès », agnostique au domaine | à jour (`v0.4.0`) |
| Brique #4 — le greffier | [`brique-4-greffier.md`](brique-4-greffier.md) | capture épisodique (trace complète, arbre immuable DuckDB), rejeu, robustesse (interruption + filet) | à jour (`v0.5.0`) |
| Brique #5 — le produit de session | [`brique-5-notebook.md`](brique-5-notebook.md) | analyste sur donnée **réelle** (267K OFROU), notebook Quarto rejouable depuis la trace, volume ≠ excès sur du réel (BE/ZH), refus causal, honnêteté validée sur donnée propre | à jour (`v0.6.0`) |
| Brique #6 — robustesse d'échelle spatiale | [`brique-6-robustesse-echelle.md`](brique-6-robustesse-echelle.md) | test H3 multi-résolution (6/7/8), verdict **robuste** sur 267K points OFROU + STATPOP, part unpopulated (corridors transit), caveats planaire/réseau, agnostique au domaine | à venir (`v0.7.0`) |
| Brique #7b — le profil brut | [`brique-7b-profil-brut.md`](brique-7b-profil-brut.md) | profiler un dataset **sans fiche** (ingestion) via MCP, inférence de type candidat (Q-0015a), code déguisé par faible cardinalité, garde anti-traversée, sans LLM | à venir (`v0.9.0`) |
| Brique #7c — le curateur conversationnel | [`brique-7c-curateur.md`](brique-7c-curateur.md) | curation maïeutique d'un dataset non-fiché (OFROU 267K lignes, 36 colonnes), dialogue colonne par colonne, types corrigés par l'humain, fiche YAML validée, nœud `curation_validated` dans le greffier | à venir (`v0.10.0`) |
| Brique #8 — le curateur naturel | [`brique-8-curateur-naturel.md`](brique-8-curateur-naturel.md) | qualité conversationnelle par défaut : forme de tour prescrite (verrou / ancrage chiffré / enjeu / options / « je ne sais pas »), une seule question par tour, brouillon de fiche émis à chaque tour (invisible pour l'humain) | à venir (`v0.11.0`) |

## Ajouter une démo

Un fichier par brique ou par jalon : `demo/brique-N-<slug>.md` (ou
`demo/<jalon>-<slug>.md` pour un jalon transverse, p. ex. une future v2). Réutiliser le
setup commun ci-dessus ; garder le runbook autonome pour le reste ; ajouter une ligne
au tableau ci-dessus.

## Principe (anti-cathédrale)

On **n'anticipe pas** une taxonomie de démos pour des briques qui n'existent pas
encore, ni pour une v2 lointaine. Le découpage « un fichier par démo » suffit et
absorbe naturellement les futures briques et la v2 le jour venu. Un runbook se crée
**quand la brique qu'il démontre existe**, pas avant.
