# OverX Website

Site principal de l'écosystème **OverX** : une vitrine statique, responsive et indexable qui rassemble les applications et les futurs projets. L'accueil présente **OverLoad**, l'application Windows de téléchargement et d'organisation des médias, ainsi que **FreeGameDrop**, le bot Discord de jeux gratuits. Les pages et fonctionnalités existantes de FreeGameDrop sont conservées.

- **Ce dépôt (`TOFazer/OverX`) contient uniquement le site.**
- **`TOFazer/OverLoad` contient l'application et ses releases.** Le site y renvoie sans modifier l'application, ses workflows ou ses releases et sans héberger ses exécutables.

## Stack

- HTML statique généré par `scripts/build_site.py` (Python standard, aucune dépendance à installer)
- CSS responsive, sans framework ni ressource CDN
- JavaScript limité au menu mobile, à l'activation des liens Discord, à la recherche du catalogue, au partage et à l'affichage facultatif des statistiques mesurées
- Contenu HTML présent dans chaque page générée pour rester lisible sans JavaScript et indexable

## Prévisualiser en local

```bash
python3 scripts/build_site.py
python3 -m http.server 4173 --bind 0.0.0.0
```

Puis ouvre `http://localhost:4173`.

Pour vérifier les fichiers générés, les liens locaux, le JSON-LD et le sitemap, puis exécuter les tests de non-régression hors ligne (bibliothèque standard Python uniquement) :

```bash
python3 scripts/check_site.py
python3 -m unittest discover -s tests -v
```

## Pages

| URL du dépôt | Contenu |
| --- | --- |
| `/` | Accueil OverX, collection de projets, section OverLoad et FreeGameDrop |
| `/overload/` | Présentation OverLoad, téléchargements Windows, étapes d’installation et FAQ |
| `/discord-bots/` | Catalogue avec recherche et filtres par catégorie |
| `/discord-bots/freegamedrop/` | Fonctionnalités, commandes, FAQ et configuration du bot |
| `/discord-bots/freegamedrop/steam/` | Page d'atterrissage « jeux gratuits Steam sur Discord » |
| `/discord-bots/freegamedrop/epic-games/` | Page d'atterrissage « jeux gratuits Epic Games Store » |
| `/discord-bots/freegamedrop/gog/` | Page d'atterrissage « jeux gratuits GOG » |
| `/discord-bots/freegamedrop/ubisoft/` | Page d'atterrissage « jeux gratuits Ubisoft » |
| `/discord-bots/freegamedrop/auto-hebergement/` | Guide open source (MIT) : Python, Docker, DEV/PROD, `/api/health`, `/api/stats` |
| `/install/` | Parcours guidé d'installation Discord, permissions et dépannage |
| `/docs/` | Installation, permissions, commandes et FAQ |
| `/status/` | Panneau de santé branchable sur `/api/health`, sans faux indicateurs verts |
| `/roadmap/` | Étapes prévues, sans dates promises |
| `/changelog/` | Notes de version publiées |
| `/support/` | Documentation et issues GitHub, emplacement du serveur communautaire |
| `/privacy/`, `/terms/`, `/legal/` | Brouillons de pages légales à finaliser (`noindex`) |

## OverLoad : toujours la dernière release stable

Les boutons sont des liens HTML natifs, utilisables **sans JavaScript** et sans appel d'API GitHub au chargement. GitHub résout lui-même la dernière release stable : aucun numéro de version, tag, taille de fichier ou compteur de téléchargement n'est figé dans le site.

- Installateur Windows : <https://github.com/TOFazer/OverLoad/releases/latest/download/OverLoad-Setup.exe>
- Version portable : <https://github.com/TOFazer/OverLoad/releases/latest/download/OverLoad-Portable-win64.zip>
- Notes et fichiers de la dernière release : <https://github.com/TOFazer/OverLoad/releases/latest>

Ces URL sont centralisées dans `OVERLOAD` de `scripts/build_site.py`, puis rendues dans l'accueil et la page `/overload/`. Le lien vers les notes de version reste accessible à côté des téléchargements. Les brouillons et préversions ne sont pas ciblés par `releases/latest`.

**Contrat de publication côté OverLoad :** chaque nouvelle release stable doit continuer à joindre les assets avec les noms exacts `OverLoad-Setup.exe` et `OverLoad-Portable-win64.zip`. Si un fichier est absent de la dernière release stable, GitHub renverra une erreur pour son lien permanent ; les tests du site vérifient les URL mais ne publient ni ne corrigent les releases. Aucune régénération ou modification d'OverX n'est nécessaire à chaque nouvelle version respectant ces noms.

**Parcours utilisateur :** télécharger `OverLoad-Setup.exe`, puis le lancer sur son PC Windows 11 (64 bits). Pour la version portable, extraire le ZIP et lancer `OverLoad.exe`. Le site ne lance aucun exécutable, n'installe rien à distance et n'ajoute aucun système de mise à jour automatique à l'application.

La présentation des fonctionnalités suit le README officiel d'OverLoad : fichiers accessibles par liens directs HTTP(S), analyse multimédia et préparation de projets vidéo. Elle ne promet pas de téléchargement depuis toutes les plateformes ni de contournement de DRM.

## Configurer l'installation Discord

Le lien OAuth2 de production fourni par le propriétaire est configuré dans `assets/site-config.js`. Les CTA ouvrent directement Discord (même sans JavaScript) ; la page `/install/` explique les étapes, les permissions et les blocages fréquents. Si le lien change, modifie cette configuration puis régénère le site :

```js
window.OVERX_CONFIG = Object.freeze({
  siteUrl: "",               // domaine public → canonical, og:url, twitter:image, sitemap.xml
  discordApplicationId: "IDENTIFIANT_PUBLIC_DE_L_APPLICATION_PROD",
  discordInstallUrl: "",     // URL complète fournie par le propriétaire (prioritaire)
  installPermissions: "268528656",
  communityInviteUrl: "",
  statsApiUrl: "",           // GET /api/stats du dashboard du bot (JSON, CORS requis)
  healthApiUrl: "",          // GET /api/health du dashboard du bot
  // ...
});
```

Le site construit alors l'URL OAuth2 Discord avec les scopes `bot applications.commands` — et seulement ceux-là pour le lien du bot. La connexion « Se connecter avec Discord » d'un futur dashboard utilise `identify guilds` côté OAuth2 du dashboard, jamais dans le lien d'invitation du bot.

- **Application ID / Client ID** : identifiant public, utilisable dans le frontend.
- **DISCORD_TOKEN, DISCORD_CLIENT_SECRET, SECRET_KEY, DATABASE_URL** : secrets ; ne jamais les mettre dans ce dépôt ni dans un fichier servi au navigateur.
- `installPermissions` (268528656) correspond au lien de production : les 5 permissions de base du bot plus **Lire l'historique** et **Gérer les messages**, documentées comme facultatives (nettoyage d'anciens panneaux).

`communityInviteUrl` peut recevoir l'invitation publique du serveur OverX : les blocs communautaires (accueil, support, pied de page) apparaissent automatiquement dès que l'URL est renseignée et valide.

## SEO et découverte

- Chaque page indexable reçoit un titre et une description ciblés, OpenGraph, Twitter Card et un `BreadcrumbList` JSON-LD ; l'accueil ajoute `Organization`, `WebSite` et `ItemList`, les fiches FreeGameDrop et OverLoad ajoutent `SoftwareApplication` + `FAQPage`. OverLoad déclare Windows et son URL de téléchargement stable, sans version codée en dur.
- `scripts/build_og_images.py` rend les cartes de partage 1200×630 (`assets/og/*.png`, commitées) ; Pillow n'est requis que pour les régénérer : `python3 -m venv .venv && .venv/bin/pip install pillow && .venv/bin/python scripts/build_og_images.py`.
- Dès que `siteUrl` est renseigné, le build écrit `sitemap.xml` et ajoute la directive `Sitemap:` dans `robots.txt`, ainsi que `canonical`/`og:url`/`og:image` absolus. Tant que le domaine n'est pas choisi, rien n'est inventé.
- Les pages légales restent en `noindex` et hors sitemap.

## Données et affirmations publiques

Aucun endpoint de statistiques n'est connecté par défaut : les compteurs de l'accueil affichent « — » et la page Statut indique « non mesuré ». Si `statsApiUrl` / `healthApiUrl` pointent vers le tableau de bord du bot (`/api/stats`, `/api/health`, JSON sans secret), l'accueil et le statut affichent les valeurs réellement mesurées ; en cas d'API injoignable ou de CORS refusé, les compteurs restent à « — » et un message l'explique. Le dashboard du bot doit autoriser CORS depuis l'origine du site, ou être servi derrière le même domaine.

La fiche FreeGameDrop s'appuie sur le README du dépôt `TOFazer/FreeGameDropDev` : plateformes documentées (Steam, Epic via API officielle + GamerPower, GOG, Ubisoft), commandes, permissions, licence MIT, surveillance et confidentialité. Les chiffres et l'état en ligne ne sont jamais déduits du seul code source.

## Ajouter un projet, un bot ou une plateforme

- **Une application ou un projet** : ajouter sa présentation à l’accueil, sa page dans `PAGES` de `scripts/build_site.py` et son entrée dans l’`ItemList` de l’accueil, puis régénérer. Ajouter sa page à `EXPECTED_PAGES` dans `scripts/check_site.py` et couvrir ses liens par des tests. La navigation et le pied de page partagés gardent OverX comme point d’entrée.
- **Un bot** : une entrée dans `BOTS` de `scripts/build_site.py` (nom, catégorie, fiche) ; l’`ItemList` de l’accueil et le bloc « écosystème » sont générés à partir de ce registre. Ajouter aussi le contenu de sa fiche et de sa carte au catalogue et à l’accueil.
- **Une plateforme** : une entrée dans `FGD_PLATFORMS` ; sa page d'atterrissage indexable, sa tuile sur la fiche bot, et son lien de pied de page sont générés automatiquement.

## Publication

Le site est déployable comme site statique depuis la racine de ce dépôt (par exemple GitHub Pages). Aucun backend, OAuth, base de données, analytics ou cookie non essentiel n'est ajouté dans cette V1.

Une fois le domaine et l'hébergeur choisis :

1. renseigner `siteUrl` puis régénérer (sitemap, canonical, cartes de partage absolues) ;
2. renseigner l'hébergeur dans les mentions légales et la politique de confidentialité ;
3. compléter l'identité et le contact de l'éditeur dans `legal/`, `privacy/` et `terms/` ;
4. faire vérifier les textes légaux avant publication ;
5. ajouter `communityInviteUrl` si le serveur communautaire existe, et vérifier que le lien de production correspond à la bonne application ;
6. brancher `statsApiUrl` / `healthApiUrl` uniquement vers des endpoints publics mesurés ;
7. viser l'App Directory Discord : application vérifiée, description, tags, serveur de support public et URL d'installation (prérequis listés dans la roadmap).

Les pages légales portent un avertissement visible et doivent être complétées avant d'être présentées comme définitives.

## Identité OverX — Forest Minimal (2026)

- Direction visuelle : studio de logiciels indépendant, sobre et éditorial — fond ivoire, charbon pour le texte, vert sapin pour les actions et quelques sections sombres. Pas de néons ni d’effets lumineux ; le doré reste un accent discret pour FreeGameDrop.
- Palette : vert sapin `#203D2D`, vert forêt `#345641`, sauge `#A5B5A0`, ivoire `#F3F1E8`, charbon `#20231F` et doré doux `#C6A566`.
- Le système visuel est défini dans `assets/css/forest-minimal.css`, chargé après les styles structurels de `assets/css/site.css`. Le symbole géométrique partagé entre navigation, pied de page et favicon est `assets/brand-mark.svg`.
- Le hero de l’accueil présente une vraie capture locale d’OverLoad (`assets/overload/accueil.png`) ; les téléchargements et les fiches de projet gardent leurs liens officiels.
- Le bloc « Notre approche » reste accessible via `#overx`. Les deux actions du hero fonctionnent sans JavaScript.
- Les animations de révélation restent discrètes et respectent `prefers-reduced-motion`. Le menu mobile conserve son fonctionnement clavier.
- L’aperçu Discord est une **démonstration fictive**, pas une annonce de promotion réelle. Les compteurs non connectés ne figurent plus sur l’accueil ; la page Statut reste disponible.

Après toute modification de contenu, modifier `scripts/build_site.py`, puis régénérer les pages (ne pas modifier uniquement le HTML généré).
