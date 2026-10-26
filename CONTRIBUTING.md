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
git switch dev && git merge --no-ff feature/model-card
git branch -d feature/model-card && git push origin dev
```

Une livraison fusionne `dev` dans `main` (`git merge --no-ff dev`) et peut être marquée
d'un tag, par ex. `git tag v1.1.0`. Un correctif suit le même chemin depuis `main` :

```bash
git switch main && git switch -c hotfix/cle-api
# correction, commit...
git switch main && git merge --no-ff hotfix/cle-api
git switch dev  && git merge --no-ff hotfix/cle-api
git branch -d hotfix/cle-api
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

## Avant de fusionner dans `dev`

- [ ] `uv run pytest` passe
- [ ] l'API respecte toujours le contrat (voir ci-dessous)
- [ ] le README est à jour : routes, commandes, variables d'environnement
- [ ] si le Dockerfile ou les dépendances ont changé : `docker build -t ia-cloud .` passe

## Contrat de l'API

[`openapi.yml`](openapi.yml) est fourni par le cours : **on ne le modifie pas**. Le code
s'y adapte, et `/openapi.json` généré par FastAPI doit décrire la même API. Ce qui n'est
pas dans le contrat (clé d'API, 401, 503) reste hors du schéma généré, par exemple dans
un middleware.

Vérification des opérations implémentées :

```bash
uv run python -c "
import yaml
from express_delivery.api.app import app
contrat = yaml.safe_load(open('openapi.yml'))['paths']
genere = app.openapi()['paths']
for route, operations in genere.items():
    for methode, op in operations.items():
        attendu = contrat[route][methode]
        ecarts = [k for k in ('operationId', 'tags', 'summary', 'x-session') if op.get(k) != attendu.get(k)]
        print('OK  ' if not ecarts else 'ÉCART', methode.upper(), route, ecarts or '')
"
```

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
