# ADR-0008 — Déviation qualité : pyright `standard` (au lieu de `strict`), ratchet vers `strict`

- **Status:** Accepted
- **Date:** 2026-07-28 (proposed), 2026-07-31 (accepted)
- **Decision-makers:** Alexandre Pillonel, Claude (co-conception)

> Promue `Accepted` le 2026-07-31 (avec ADR-0001, premières ADR du projet
> promues vers l'impl). La déviation est **active dans `src` depuis la brique #1**
> (v0.2.0) ; son acceptation grave une décision déjà éprouvée par le code.

## Context

`standards@0.7.0` introduit le gate qualité obligatoire pour tout impl repo
(convention `code-quality.md` de la méthodologie) : `ruff format` + `ruff check`
(dont `D100`) + `pyright` + `pytest`, avec `typeCheckingMode="strict"` par défaut.
On l'adopte sur `src` (brique #1).

`ruff` et `pytest` passent au vert sans difficulté. Mais `pyright strict` remonte
**148 erreurs**, dont **~126 sont du bruit de frontière** *strict-only*
(`reportUnknownMemberType`/`ArgumentType`/`VariableType`) : toute la surface
d'entrée/sortie du projet repose sur des libs **sans stubs de types** — `duckdb`,
`fastmcp`, `claude-agent-sdk`, `pyyaml`. Sous `strict`, chaque usage d'une valeur
`Unknown` issue de ces libs est une erreur qui cascade partout.

Point décisif (constat empirique) : en mode **`standard`** — le mode intermédiaire
et défaut de pyright (`off < basic < standard < strict`) — il ne reste que
**17 erreurs, toutes réelles** (`reportOptionalSubscript` sur des `.fetchone()`
non gardés, un `dict[str, any]` utilisant le builtin `any` au lieu de `Any`). Ces
17 ont été **corrigées** (gardes de `None`, annotations). `standard` garde donc
tous les checks *réels* ; il ne coupe que la propagation d'`Unknown` aux
frontières tierces. `basic` aurait, lui, raté ces 17 vrais défauts.

## Decision

1. **`src` dévie à `typeCheckingMode="standard"`** (et non `strict`) dans son
   `pyproject.toml`, déclaré via le mécanisme de la convention `README.md` de la
   méthodologie § override. `ruff` (E,F,I,UP,B + D restreint à l'en-tête de module) et `pytest`
   restent à pleine force ; `pyright standard` est **vert (0 erreur)**.
2. **La déviation est minime et volontairement plus stricte que le repli `basic`** :
   `standard` conserve les vérifications de type réelles (il a d'ailleurs attrapé
   17 vrais défauts, corrigés), et ne renonce qu'aux checks *strict-only* de
   propagation d'`Unknown`, sans valeur tant que la frontière tierce n'est pas typée.
3. **Plan de montée en gamme (ratchet vers `strict`)** :
   - annoter progressivement nos fonctions de frontière (fait : params de
     `profile_stats`, helper `_scalar`, helper de test `scalar`) ;
   - introduire de **fines couches typées** autour de `duckdb` / `fastmcp` /
     `claude-agent-sdk` isolant l'`Unknown` derrière une API typée, ou adopter des
     stubs si les libs en publient ;
   - quand la frontière est typée, **repasser à `strict`** et **révoquer cette
     déviation par un ADR qui la `Supersedes`**.

## Consequences

### Positive

- Gate qualité **adoptable et vert maintenant** — cohérent avec la règle du montrable.
- `standard` attrape les **vraies** erreurs de type (il en a trouvé 17) ; on ne perd
  que le bruit de frontière `Unknown`.
- Déviation **d'un seul cran** (pas jusqu'à `basic`) → plus petit écart à combler
  au ratchet, et le gate reste substantiel entre-temps.

### Negative / costs accepted

- Perte du contrôle de propagation d'`Unknown` aux frontières tierces jusqu'à ce
  que le ratchet progresse (mésusage d'une API `duckdb`/SDK possible sans alerte du
  typeur ; reste couvert par les tests).
- Une déviation locale de plus à porter jusqu'à révocation.

## Alternatives considered

- **`basic`** — Rejeté : trop permissif, il aurait **raté les 17 vrais défauts**
  (`.fetchone()` non gardés, `any` vs `Any`) que `standard` a exposés.
- **`strict` maintenu + `# pyright: basic` par-module partout** — Rejeté : le
  relâchement atterrit de fait sur la majorité des fichiers, éparpillé et opaque.
- **`strict` + `reportUnknown*` désactivés globalement** — Rejeté : vide `strict`
  de sa substance en le déguisant en strict.
- **Retirer `pyright` du gate** — Rejeté : la doctrine veut les quatre checks.

## Supersedes

None. (Sera `Supersedes` par l'ADR qui rétablira `strict` en fin de ratchet.)

## References

- Doctrine (méthodologie, hors de ce repo) : convention `code-quality.md`
  § « Reference config » et § « Per-project deviation » ; convention `README.md`
  § « How to override per project ».
- Config appliquée : [`../../pyproject.toml`](../../pyproject.toml)
  (`[tool.pyright] typeCheckingMode="standard"`).
- Constat qui a nourri la décision : candidat de promotion bottom-up — « la stack
  maison (DuckDB/FastMCP/Agent SDK/PyYAML) est systématiquement sans stubs » — à
  porter en session `methods/spec` (enrichir la doctrine d'une recette frontière-tierce).
