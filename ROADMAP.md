# Roadmap

Ce qui reste à faire, par ordre de priorité. Cocher une case quand c'est fait.

## Déploiement Coolify

- [ ] **Récupérer un identifiant GHCR pour Coolify** : jeton personnel GitHub avec le seul
      droit `read:packages`, enregistré pour le registre `ghcr.io` côté Coolify / serveur
      (`docker login ghcr.io` avec ce jeton).
      Sans lui, Coolify ne peut pas télécharger les images, privées par défaut sur GHCR.
- [ ] Passer l'application API en type **Docker Image** :
      `ghcr.io/julcrm/ia-cloud-api:latest`, healthcheck `/health/ready` (rolling update,
      ADR-0005). L'image déployée est celle testée par le pipeline, le VPS ne build plus.
- [ ] Options Docker de l'API dans Coolify : `--cap-drop ALL --security-opt no-new-privileges`
      (SECURITY.md).
- [ ] Créer l'application d'entraînement : `ghcr.io/julcrm/ia-cloud-train:latest`, lancée
      à la demande ou en tâche planifiée.

## GitHub

- [ ] Protéger `dev` et `main` : « Require status checks to pass » avec les jobs
      *Lint, tests et contrat* et *Images Docker*.
- [ ] Activer le signalement privé des vulnérabilités (Settings → Code security).

## Entraînement sur le VPS

- [ ] Artefacts du modèle sur Garage, dossiers versionnés et `current.json` (ADR-0002) :
      l'API lit le modèle courant, l'image API ne contient plus de modèle.
- [ ] ADR : entraînement en tâche séparée sur le VPS.
- [ ] Serveur MLflow sur le VPS pour garder l'historique des entraînements (optionnel).
- [ ] Entraîner sur les commandes collectées dans DuckLake plutôt que sur des données
      synthétiques.
- [ ] Docker Compose local (API, entraînement, PostgreSQL, Garage) pour tester la
      configuration de production (optionnel).
