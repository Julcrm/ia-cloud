# Sécurité

## Versions suivies

Seule la version en production, la branche `main`, reçoit des correctifs de sécurité.
Un correctif passe par une branche `hotfix/*` (voir [CONTRIBUTING.md](CONTRIBUTING.md)).

## Signaler une vulnérabilité

**Ne pas ouvrir d'issue publique.** Utiliser le signalement privé de GitHub : onglet
**Security** du dépôt, puis **Report a vulnerability**.

Indiquer la route ou le fichier concerné, les étapes pour reproduire et l'impact
supposé. Ne pas joindre de secret réel (clé d'API, mot de passe), s'il en apparaît un,
il est considéré comme compromis et changé.

Projet scolaire maintenu par une seule personne, réponse sous quelques jours ouvrés,
sans délai garanti.

## Mesures en place

Résumé de l'[ADR-0006](docs/adr/ADR-0006-securisation.pdf) : défense en profondeur, une
protection à chaque étape.

| Axe | Mesure |
|-----|--------|
| Entrées | HTTPS uniquement (Traefik, géré par Coolify) ; limite de débit par IP dans Traefik ; validation stricte par les schémas du contrat : champ manquant, en trop ou hors bornes refusé en 422 avant le code métier |
| Authentification | Clé d'API dans l'en-tête `X-API-Key` sur `/v1/*`, comparée en temps constant, refus en 401 ; sans `API_KEY` configurée, tout `/v1/*` est refusé ; les sondes `/health` restent ouvertes pour Coolify |
| Sorties | Réponses limitées aux champs du contrat ; erreurs au format `Error`, sans trace ni détail interne ; aucun secret dans les logs |
| Données | PostgreSQL et Garage joignables seulement par le réseau Docker interne ; administration par Tailscale uniquement ; clé Garage limitée au bucket `ia-cloud`, rôle PostgreSQL limité au catalogue |
| Secrets | Variables d'environnement, secrets Coolify en production ; jamais dans Git (`.env` ignoré) |
| Conteneur | Image de base figée par version et empreinte (`sha256`) ; image de l'API sans uv, pip, mlflow ni outils de build ; processus sans les droits root : utilisateur `app` (`USER 1000:1000`) ; dans `/app`, il ne peut écrire que dans `/app/data` (le code et le modèle appartiennent à root) |
| Exécution | Aucune capability Linux, pas d'élévation de privilèges (options Coolify ci-dessous) ; l'image fonctionne aussi avec un système de fichiers en lecture seule |

Les commandes ne contiennent aucune donnée personnelle directe (ni nom, ni adresse), ce
qui limite l'impact d'une fuite.

Options d'exécution, dans le champ « Custom Docker Options » de Coolify :

```text
--cap-drop ALL --security-opt no-new-privileges
```

Coolify n'applique pas `--read-only` ni `--tmpfs`. L'image a été testée en local avec :

```bash
docker run --read-only --tmpfs /tmp --tmpfs /app/data:uid=1000,gid=1000 \
  --cap-drop ALL --security-opt no-new-privileges -e API_KEY=... ia-cloud-api
```

## Suivi des vulnérabilités

L'image est analysée avec Docker Scout (`docker scout cves ia-cloud-api`) : aucune
vulnérabilité corrigible n'est tolérée. Celles sans correctif publié (paquets Debian de
l'image de base) sont suivies, et l'empreinte de l'image de base est mise à jour dès
qu'un correctif sort.

## Hors périmètre

- Le jeu de données d'entraînement est synthétique, les prédictions ne sont pas une
  décision métier.
- L'infrastructure partagée du VPS (autres projets, Coolify lui-même) n'est pas couverte
  par ce dépôt.
