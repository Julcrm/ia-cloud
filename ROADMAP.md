# Roadmap

Ce qui reste à faire, par ordre de priorité. Cocher une case quand c'est fait.

## Déploiement Coolify

- [ ] **Récupérer un identifiant GHCR pour Coolify** : jeton personnel GitHub avec le seul
      droit `read:packages`, enregistré pour le registre `ghcr.io` côté Coolify / serveur
      (`docker login ghcr.io` avec ce jeton).
      Sans lui, Coolify ne peut pas télécharger les images, privées par défaut sur GHCR.
- [ ] Déployer `docker-compose.prod.yml` comme application **Docker Compose** : images
      `ghcr.io/julcrm/ia-cloud-{api,orchestrator}`, tag figé `IMAGE_TAG=sha-<commit>`
      (ADR-0005), variables d'environnement dans Coolify (le compose refuse de démarrer s'il
      en manque une). L'image déployée est celle testée par le pipeline, le VPS ne build plus.
- [ ] **Rollback** (ADR-0005) : documenter puis tester la procédure. Bug métier en
      production → retrouver le commit précédent (`git log main`), mettre son tag
      `sha-<commit>` dans `IMAGE_TAG`, redéployer (l'ancienne version doit passer
      `/health/ready`). Secours : Configuration → Rollback de Coolify.
- [ ] Vérifier après déploiement que Coolify applique bien `cap_drop: ALL` et
      `no-new-privileges` déclarés dans le compose (SECURITY.md).

## Réentraînement (Dagster)

- [x] Code server Dagster `ia-cloud-dagster` (gRPC :4000) : asset `express_delivery_model`,
      job `retrain_model` planifié chaque nuit à 3 h.
- [ ] Ajouter la code location au `workspace.yaml` du repo dagster-workspace
      (`host: ia-cloud-dagster`, `port: 4000`, `location_name: ia_cloud`).
- [ ] Variables `DAGSTER_POSTGRES_*` dans Coolify, les mêmes que le dagster-workspace.
- [ ] Premier déploiement : lancer `retrain_model` à la main depuis Dagster, puis redémarrer
      l'API (le volume `artifacts` est vide, l'API reste `not_ready` jusque-là).
- [ ] ADR : réentraînement planifié par Dagster (remplace « entraînement en tâche séparée »).

## GitHub

- [ ] Protéger `dev` et `main` : « Require status checks to pass » avec les jobs
      *Lint, tests et contrat* et *Images Docker*.
- [ ] Activer le signalement privé des vulnérabilités (Settings → Code security).

## Modèle

- [ ] **Artefacts du modèle sur Garage**, dossiers versionnés et `current.json` (ADR-0002) :
      l'API relit le modèle courant sans redémarrer, l'image API ne contient plus de modèle.
      Prioritaire : aujourd'hui l'API ne voit le modèle réentraîné qu'à son redémarrage
      (volume partagé, `shortcut:` dans `docker-compose.prod.yml`).
- [ ] Faire valider par le métier les hypothèses de l'ADR-0007 : vent compté comme orage,
      capacité transporteur maximale de 50.
- [ ] Obtenir une vraie cible (délai ou mode de livraison réel) : la cible actuelle est
      simulée par la règle métier, les métriques ne mesurent pas une performance réelle.
- [ ] Serveur MLflow sur le VPS pour garder l'historique des entraînements (optionnel).

## ERP et streaming

En attente de la consigne du prof sur le streaming (Kafka ou Redpanda).

- [ ] ADR : alimentation de DuckLake depuis l'ERP. Options : double écriture par l'ERP,
      Redpanda en premier avec un consumer par base, CDC (Debezium).
- [ ] Copier une fois l'historique de l'ERP dans DuckLake, puis entraîner sur DuckLake
      (`DuckLakeOrdersSource`) : PostgreSQL de l'ERP n'est plus lu qu'à cette occasion.
- [ ] Base ERP sur le VPS : base `livraison_express` dédiée sur le PostgreSQL partagé, un rôle
      d'écriture pour le simulateur, un rôle en lecture seule pour l'entraînement ; simulateur
      déployé à part (système externe), ralenti (`INTERVAL_SECONDS`) ou borné.

## Fait

- [x] ADR-0007 : données ERP intégrées depuis PostgreSQL, MongoDB non déployé.
- [x] `PostgresOrdersSource` : entraînement sur les commandes de l'ERP.
- [x] `docker-compose.test.yml` : ERP, entraînement et API en local, de bout en bout.
