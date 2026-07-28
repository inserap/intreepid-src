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
