# Catalogue commun FreeGameDrop — JSON partagé

Ce dossier héberge le fichier lu par **OverX** pour afficher le catalogue des jeux gratuits. Il est conçu pour être mis à jour automatiquement par le bot **FreeGameDrop**, sans dupliquer la logique de collecte des offres.

## Fichier

- `data/offers.json` — généré / écrasé par le bot (ou à la main pour tester).

## Schéma

```json
{
  "generated_at": "2026-10-22T19:00:00Z",
  "source": "FreeGameDrop",
  "source_url": "https://github.com/TOFazer/FreeGameDropDev",
  "notice": "facultatif",
  "offers": [
    {
      "id": "steam_123456",
      "title": "Nom du jeu",
      "description": "Courte description",
      "type": "game | dlc | pack",
      "type_label": "Jeu complet | DLC | Contenu bonus",
      "platform": "steam | epic | gog | ubisoft",
      "platform_label": "Steam | Epic Games Store | GOG | Ubisoft",
      "store": "Steam",
      "url": "https://store.steampowered.com/app/...",
      "image": "https://... (facultatif)",
      "price_original": "59,99 €",
      "expires_at": "2026-10-30T17:00:00Z | null",
      "availability": "temporary | permanent",
      "is_permanent": false
    }
  ]
}
```

Champs obligatoires côté site : `id`, `title`, `type`, `platform`, `url`. Le reste est affiché s'il existe.

- `type` : `game` = jeu complet, `dlc` = extension / DLC, `pack` = pack cosmétique / objet / bande-son.
- `availability` + `is_permanent` : `permanent` = gratuit sans limite (affiché « Toujours gratuit »), `temporary` = expire à `expires_at` (compte à rebours). Le site masque automatiquement les offres expirées quand `expires_at` est passé.
- `expires_at` en ISO 8601 UTC, ou `null` pour les offres permanentes.
- Le site ne vérifie pas lui-même la validité : il affiche la date et le statut fournis par le catalogue commun.

## Mise à jour depuis le bot

Sur GitHub Pages, le site est statique : il lit simplement ce JSON. Le bot publie le fichier par l'une de ces méthodes :

1. **Workflow GitHub Action côté OverX** (recommandé pour commencer) — le bot pousse un `data/offers.json` à jour via l'API GitHub, ou expose un endpoint `/api/offers` et un workflow OverX le transforme en JSON commité.
2. **API hébergée séparément** — renseigner `offersApiUrl` dans `assets/site-config.js` fait pointer la page vers l'endpoint distant (CORS requis). La version JSON locale reste le fallback.

Dans les deux cas, le catalogue reste unique : les mêmes offres normalisées alimentent Discord et OverX.

## Exemple actuel

Le fichier commité contient 6 offres illustratives (pas de vraies offres vérifiées). Le bandeau du site indique clairement que ce sont des exemples jusqu'à ce que le premier export automatique le remplace.

## Intégration côté bot

Côté FreeGameDrop, normaliser les offres avant export :

- dédupliquer par `(platform, id_source)` ;
- remplir `platform` parmi `steam, epic, gog, ubisoft` ;
- renseigner `type` et `availability` (distinguer DLC temporaire vs permanent) ;
- fournir `url` vers la page officielle de récupération (pas un lien affilié) ;
- trier par `expires_at` croissant (offres urgentes en premier), puis `title`.

Le site se charge ensuite du rendu, des filtres (plateforme, type, recherche, échéance) et du badge d'urgence.
