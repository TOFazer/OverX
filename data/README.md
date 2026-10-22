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
      "url": "https://store.steampowered.com/app/ID/...",
      "image": "https://... (image officielle, recommandée)",
      "price_original": "59,99 €",
      "expires_at": "2026-10-30T17:00:00Z | null",
      "availability": "temporary | permanent",
      "is_permanent": false
    }
  ]
}
```

Champs obligatoires côté site : `id`, `title`, `type`, `platform`, `url`. Le champ `url` doit être un lien HTTPS vers la fiche précise du jeu ou du DLC (pas la page d'accueil de la boutique) ; sans lien direct valide, le bouton de récupération est désactivé. Le champ `image` accepte une URL HTTPS vers le visuel officiel du produit. Pour Steam, le site peut retrouver automatiquement l'en-tête de jeu/DLC depuis l'identifiant de la fiche si `image` est absent. Le reste est affiché s'il existe.

- `type` : `game` = jeu complet, `dlc` = extension / DLC, `pack` = pack cosmétique / objet / bande-son.
- `availability` + `is_permanent` : `permanent` = gratuit sans limite (affiché « Toujours gratuit »), `temporary` = expire à `expires_at` (compte à rebours). Le site masque automatiquement les offres expirées quand `expires_at` est passé.
- `expires_at` en ISO 8601 UTC, ou `null` pour les offres permanentes.
- Le site masque automatiquement les offres expirées et répartit les résultats filtrés en pages de 24 cartes ; aucune limite de nombre d'offres n'est imposée par l'interface.
- Chaque carte ouvre aussi une fiche OverX dédiée au jeu/DLC (identifiant d'offre dans l'URL), avec image, description, statut et bouton de récupération vers la boutique officielle.
- Le site ne vérifie pas lui-même la validité du prix ni l'exhaustivité du collecteur : il affiche les offres publiées dans ce fichier et les dates/statuts fournis par le catalogue commun. « Tout » signifie donc toutes les offres trouvées et exportées par les sources configurées côté bot, pas l'ensemble de tous les jeux jamais publiés sur toutes les boutiques.

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
