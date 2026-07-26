# Sécurité — intreepid

## Signalement des failles

Pour signaler une vulnérabilité : <contact email | issue privée | ...>.
Ne pas créer d'issue publique avant qu'un correctif soit en place.

## Versions supportées

Voir [CHANGELOG.md](CHANGELOG.md). Les correctifs de sécurité sont rétroportés uniquement sur la version mineure courante.

## Bonnes pratiques (synthèse)

- Aucun secret en clair dans le repo.
- `.gitignore` couvre `.env`, `*.key`, `*.pem`, `secrets/`, `credentials.json`.
- Permissions Claude Code par défaut : read-only safe (`.claude/settings.json`).
- Données client / PII : ne jamais coller dans des prompts LLM ou des logs.

Pour la doctrine de sécurité partagée (règle de vigilance Claude sur les informations sensibles, conventions transverses), voir `standards/conventions/security.md` côté méthodologie INSER AI (le path exact est documenté dans le spec repo associé).
