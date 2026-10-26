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
| Conteneur | Image finale sans uv ni outils de build ; processus lancé sans les droits root : le `Dockerfile` crée un utilisateur `app` (uid 1000) et bascule dessus (`USER app`) avant de démarrer l'API ; dans `/app`, il ne peut écrire que dans `/app/data` (le code et le modèle appartiennent à root) |

Les commandes ne contiennent aucune donnée personnelle directe (ni nom, ni adresse), ce
qui limite l'impact d'une fuite.

## Hors périmètre

- Le jeu de données d'entraînement est synthétique, les prédictions ne sont pas une
  décision métier.
- L'infrastructure partagée du VPS (autres projets, Coolify lui-même) n'est pas couverte
  par ce dépôt.
