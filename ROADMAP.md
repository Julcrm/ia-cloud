# Roadmap

Ce qui reste à faire, par ordre de priorité. Cocher une case quand c'est fait.

## Déploiement Coolify

- [x] **Identifiant GHCR** : finalement inutile — les images `ghcr.io/julcrm/ia-cloud-*`
      sont **publiques** (pull anonyme vérifié sur le VPS). Si elles repassent privées un jour,
      il faudra un jeton `read:packages` côté Coolify.
- [ ] **Migrer vers le modèle ADR-0005** (en cours). L'app Coolify `ia-cloud` actuelle
      (`lwkhf6j048rgtilywkvjevbs`) **builde depuis git** (api seule, pas de Dagster) — à remplacer
      par une ressource **Docker Compose** qui **tire** `ghcr.io/julcrm/ia-cloud-{api,orchestrator}`
      (tag figé `IMAGE_TAG=sha-<commit>`), le VPS ne build plus. Créer via **Git Based → Docker
      Compose → `/docker-compose.prod.yml`**. Le compose complet (api + dagster) exige les
      `ERP_POSTGRES_*` et `DAGSTER_POSTGRES_*` ; déployer l'**api seule** d'abord si l'ERP/retrain
      n'est pas prêt. Supprimer l'ancienne app build une fois la nouvelle en marche.
- [ ] **Déploiement auto (optionnel)** : job `deploy` dans `ci.yml` écrit (met `IMAGE_TAG=sha-…`
      via l'API Coolify puis redeploy, API joignable par Tailscale). **En sommeil** tant que
      `COOLIFY_APP_UUID` (variable) + `COOLIFY_TOKEN` + secrets Tailscale ne sont pas posés
      (voir note VPS « Déploiement CI via Tailscale »). Sinon déploiement manuel.
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
- [ ] Premier déploiement : lancer `retrain_model` à la main depuis Dagster. **Bloqué** tant que
      ia-cloud (compose complet) n'est pas déployé avec `ERP_POSTGRES_*` = `erp_reader` (le retrain
      lit l'ERP, pas de repli synthétique en prod). Tant qu'aucun `current.json` n'existe sur Garage,
      l'API reste `not_ready` ; elle le charge ensuite sans redémarrage (sonde readiness).
      `MODEL_S3_BUCKET=ia-cloud` déjà posé côté Coolify.
- [ ] ADR : réentraînement planifié par Dagster (remplace « entraînement en tâche séparée »).

## GitHub

- [ ] Protéger `dev` et `main` : « Require status checks to pass » avec les jobs
      *Lint, tests et contrat* et *Images Docker*.
- [ ] Activer le signalement privé des vulnérabilités (Settings → Code security).

## Modèle

- [x] **Artefacts du modèle sur Garage**, dossiers versionnés et `current.json` (ADR-0002) :
      `S3ModelRepository` (dossiers `models/express-delivery/<version>/`), l'API relit le modèle
      courant sans redémarrer (la sonde readiness recharge quand `current.json` change), plus de
      volume partagé dans `docker-compose.prod.yml`. Bucket `ia-cloud` réutilisé (prefix `models/`,
      à côté de `orders/` de DuckLake), `MODEL_S3_BUCKET=ia-cloud` posé côté Coolify. Reste : lancer
      `retrain_model` pour écrire le premier `current.json` (voir « Réentraînement »).
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
- [x] **Base ERP + simulateur sur le VPS** (partiel) : base `livraison_express` + rôle écriture
      `erp_writer` créés sur le Postgres partagé (`v8kok4w0oscgg0kc4csc88kw`) ; simulateur déployé
      en ressource Coolify **séparée** (`/erp-simulator`, `Dockerfile.erp-simulator`), borné
      (`LIVE_ORDER_LIMIT=11100`), a écrit **11 100 commandes**. Reste : rôle **lecture seule
      `erp_reader`** (= `ERP_POSTGRES_USER` de ia-cloud, créé au déploiement de ia-cloud), et
      mettre la **politique de restart du simulateur sur `no`** (il boucle en exit 0 une fois fini).

## Fait

- [x] Artefacts modèle sur Garage + rechargement à chaud de l'API (ADR-0002), `S3ModelRepository`.
- [x] Correctifs sécurité image de base (apt, zlib1g) dans une étape `base` commune ; Dependabot
      (uv, github-actions, docker) avec groupe `dagster*` ; `pymongo`/MongoDB retiré du simulateur.
- [x] Dossier `tp4/` renommé `erp-simulator/`.
- [x] ERP sur le VPS (partiel, voir « ERP et streaming ») : base + `erp_writer` + simulateur peuplé.
- [x] ADR-0007 : données ERP intégrées depuis PostgreSQL, MongoDB non déployé.
- [x] `PostgresOrdersSource` : entraînement sur les commandes de l'ERP.
- [x] `docker-compose.test.yml` : ERP, entraînement et API en local, de bout en bout.

## À reprendre (ordre pour finir le déploiement)

1. Rôle `erp_reader` + déployer ia-cloud (compose complet, api+dagster) avec `ERP_POSTGRES_*`,
   `DAGSTER_POSTGRES_*` (copiés du dagster-workspace), `IMAGE_TAG`, S3, `POSTGRES_*`.
2. Ajouter la code location au `workspace.yaml` du dagster-workspace.
3. Lancer `retrain_model` → `current.json` sur Garage → api `ready`.
4. Supprimer l'ancienne app Coolify qui build (`lwkhf6…`), couper le restart du simulateur.

Note : `feature/tp4` a des commits non encore mergés (job deploy CI, renommage, cette ROADMAP).
