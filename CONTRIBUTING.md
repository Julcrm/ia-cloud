# Contribuer

Règles de travail du projet. L'installation et les commandes sont dans le
[README](README.md#démarrage-rapide).

## Branches

Gitflow simplifié : deux branches permanentes, des branches courtes pour le travail.

| Branche | Rôle | Part de | Fusionne dans |
|---------|------|---------|---------------|
| `main` | Ce qui est déployé en production ; on n'y commite jamais directement | — | — |
| `dev` | Intégration : la prochaine version, toujours fonctionnelle | `main` | `main` (fin de séance / livraison) |
| `feature/<sujet>` | Une fonctionnalité, par ex. `feature/model-card` | `dev` | `dev` |
| `hotfix/<sujet>` | Correction urgente de la production | `main` | `main` **et** `dev` |

```bash
git switch dev && git pull
git switch -c feature/model-card          # travail, commits...
git push -u origin feature/model-card     # puis pull request vers dev sur GitHub
```

La fusion se fait par pull request, une fois le pipeline au vert (voir ci-dessous).

Une livraison est une pull request de `dev` vers `main`, qui peut être marquée d'un tag,
par ex. `git tag v1.1.0`. Un correctif suit le même chemin depuis `main` :

```bash
git switch main && git pull
git switch -c hotfix/cle-api              # correction, commit...
git push -u origin hotfix/cle-api         # pull request vers main, puis vers dev
```

## Commits

En français, une première ligne courte qui dit ce que le commit apporte, puis le détail
en liste si besoin :

```text
Séance 3 : GET /v1/model, model card du modèle en service

- model card construite à l'entraînement, sauvegardée dans artifacts/model_card.json
- GET /v1/model conforme à openapi.yml
```

Un commit = un changement cohérent. Jamais de secret, de `.env` ni d'artefact
(`artifacts/`, `mlruns/`, `data/` sont ignorés par Git).

## Fusion : pipeline au vert

Chaque pull request vers `dev` ou `main`, et chaque push sur ces deux branches, lance
le pipeline GitHub Actions ([`.github/workflows/ci.yml`](.github/workflows/ci.yml)) :
lint et formatage (ruff), tests et conformité au contrat `openapi.yml`, build des
images `api` et `train`, démarrage de l'API, analyse de vulnérabilités.
**Une pull request n'est fusionnée que si le pipeline passe entièrement au vert.** Sinon, on corrige sur la même branche et on pousse à nouveau.

## Décisions d'architecture (ADR)

Un choix structurant (stockage, déploiement, sécurité...) fait l'objet d'un ADR dans
`docs/adr/`, numéroté à la suite (`ADR-0007-<sujet>`). Format : Statut, Date, Contexte,
Options (tableau Option / Avantage / Inconvénient, option retenue en gras), Décision,
Conséquences. Le brouillon est rédigé en Markdown et relu, puis seul le PDF est versionné.
Ajouter la ligne correspondante dans le tableau du README.

## Code

- Les contrats sont des classes abstraites dans `abstractions/`, les implémentations
  dans `infrastructure/` ; `main.py` et `create_app` sont les seuls endroits qui
  choisissent les implémentations concrètes.
- La logique métier (`domain/`) ne dépend ni de FastAPI ni du stockage.
- La configuration passe par des variables d'environnement lues dans `config.py`,
  avec une valeur par défaut qui marche en local.
