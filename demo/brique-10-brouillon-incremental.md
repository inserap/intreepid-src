# Démo brique #10 — le brouillon incrémental

> Ce que la démo montre : l'agent cesse de réécrire sa fiche entière à chaque tour, et
> les jugements de périmètre métier reviennent à l'humain. Le gate est **chiffré** : il
> compare une séance réelle à la base mesurée du 06/08 (`v0.12.0`).

## Pré-requis

- `CLAUDE_CODE_OAUTH_TOKEN` défini, `ANTHROPIC_API_KEY` **non** définie (Q-0010 — le
  runner refuse de démarrer sinon).
- Le parquet OFROU brut, non fiché, sous `DATA_DIR` (mêmes 267 761 lignes et 36
  colonnes qu'au 06/08 : comparer deux séances suppose le même jeu).
- Compter ~12 minutes de présence et ~1 à 2 $ d'équivalent-API (sur abonnement, c'est
  du quota, pas un débit).

## Lancer

```bash
uv run python -m intreepid.demo_curator <chemin/vers/RoadTrafficAccidentLocations.parquet>
```

Répondre aux questions par numéro et lettre (`1a`, `2b`…), ou en texte libre, ou « je ne
sais pas ». Valider par `o` au tour de proposition.

**Consigne au gate : ne donner AUCUNE consigne de style.** Le critère 4 est précisément
que le niveau sorte tout seul.

## Ce qu'on lit à la fin

Le driver imprime la preuve greffier, les mesures, puis le bloc neuf :

```
--- attribution de la sortie écrite ---
#1  prose 2130 car. · delta 3120 car.
...
total : prose 12480 · delta 15900 (56 % de la sortie écrite ; base du 06/08 : 79 %)
fiche écrite : 16871 car. → delta ÷ fiche = 0.9 (base du 06/08 : 3,3 ; cible ≤ 1,5 ; JSON vs YAML, ±20 %)
```

*(chiffres d'illustration — pas une prédiction)*

> **Piège de lecture.** Un `delta 0` accompagné d'une prose anormalement longue n'est
> pas un tour vertueux : c'est un tour dont le bloc JSON était malformé — le parseur a
> tout compté en prose. Vérifier la prose avant de se réjouir d'un delta nul.

## Critères — arrêtés avant l'implémentation

| # | Critère | Base du 06/08 | Verdict |
|---|---|---|---|
| 1 | delta ÷ fiche écrite **≤ 1,5** | 3,3 | ☐ |
| 2 | part du delta dans la sortie écrite **≤ 50 %** | 79 % | ☐ |
| 3 | aucun tour ne dépasse **3 367 car.** de prose — le maximum du 06/08 | 2 130 → 3 367 car. | ☐ |
| 4 | premier tour aux cinq éléments (objet, ancrage chiffré, enjeu rendu tangible par un mécanisme, options fermées + « je ne sais pas » déclaré valide, penchant avec indice contraire), **zéro consigne de style** | acquis | ☐ |
| 5 | fiche finale **complète** (36 colonnes), validée | acquis | ☐ |
| 6 | **zéro** appel `ToolSearch` dans le décompte d'outils | 4 | ☐ |

Les critères 1 et 2 sont des **ratios**, pas des totaux : le changement de seuil ajoute
des tours, et un total absolu confondrait les deux effets. **Réserve d'unité sur le
critère 1** : le delta est du JSON, la fiche écrite du YAML — le ratio est indicatif à
±20 % près. L'écart 3,3 → 1,5 est très au-delà de ce bruit.

**Vérifier le critère 5.** Le driver affiche à la validation la ligne
`✓ fiche écrite : … (sha256 …)` — le chemin exact de la fiche s'y lit. Compter les
colonnes avec :

```bash
uv run python -c "import yaml,sys;d=yaml.safe_load(open(sys.argv[1],encoding='utf-8'));print(len(d['columns']),'colonnes')" catalog/<nom>.fiche.yaml
```

**Vérifier le critère 6.** Dans le bloc `--- mesures ---` que le driver imprime en fin
de séance, la section `  Appels d'outil :` contient une ligne de décompte de la forme :

```
  Décompte : mcp__intreepid__profile_raw × 2, ToolSearch × 4
```

Si `ToolSearch` n'y apparaît pas, le critère est satisfait.

## Observés, non exigés

- Le delta par tour cesse-t-il de croître ? (base : 7 764 → 19 242 car.) Une correction
  tardive peut légitimement produire un gros delta tardif.
- Nombre de questions (attendu en hausse — conséquence du seuil, jamais une cible).
- Coût total et latence par tour (base : 1,8033 $ / 734,4 s / 90-102 s par tour).
- L'agent retrouve-t-il la sévérité **ordinale à l'envers** et l'**absence de comptage de
  victimes** ? Stochastique : un manque se consigne, il ne fait pas échouer le gate.
- **Arrondi de la base** : la base « 79 % » est en réalité 79,77 % tronquée, alors que
  l'instrument arrondit — un jeu identique afficherait « 80 % » face à « 79 % ». Sans
  conséquence pour un verdict qui attend une chute vers ~10 %, mais à savoir avant de
  lire l'écart.

## Si ça tourne mal

- **Ctrl+C en cours de séance.** Le bloc de fin de séance est appelé dans un `finally`
  et ne se tait jamais : la preuve du greffier, les mesures et l'attribution s'affichent
  quand même, et la trace est conservée. Une séance interrompue reste donc lisible.
- **Le runner refuse de démarrer** en signalant que `ANTHROPIC_API_KEY` est définie :
  c'est la garde d'authentification (elle masquerait l'abonnement). Retirer la variable
  de l'environnement, ne pas contourner la garde.
- **La séance s'achève sans fiche écrite** : c'est un échec du gate, pas un incident à
  rattraper. On arrête et on recadre en session fraîche.

## Garde-fou D5 — une seule itération

Si le gate échoue, on **arrête** et on recadre en session fraîche. On ne re-tune pas la
charte en séance jusqu'à ce que ça passe : un gate qu'on ajuste pour qu'il s'ouvre a
cessé d'être un gate.
