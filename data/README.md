# Catalogue réel des jeux gratuits

Le catalogue affiché sur `/jeux-gratuits/` est `offers.json`. Il est mis à jour par GitHub Actions avec les offres promotionnelles actives remontées par les sources publiques utilisées par FreeGameDrop.

## Mise à jour automatique

Le workflow [`.github/workflows/update-offers.yml`](../.github/workflows/update-offers.yml) se lance toutes les 30 minutes et peut aussi être démarré manuellement dans GitHub Actions. Le script [`scripts/update_offers.py`](../scripts/update_offers.py) collecte :

- **GamerPower** : jeux (`type=game`) et offres de type loot/contenu (`type=loot`), filtrés selon le statut actif et la date de fin quand elle est fournie ;
- **Epic Games Store** : offres à prix nul avec promotion active, liens produits Epic et images de la source officielle.

Le script normalise les champs pour les cartes, les pages de détails et les filtres du site. Les images acceptent `image`, `thumbnail`, `cover`, `header_image` et `image_url`. Les destinations acceptent les liens de produit/claim de la source ; une page d'accueil de boutique n'est jamais utilisée comme lien de récupération. Les couvertures Steam peuvent être générées depuis l'identifiant app ou l'URL produit.

Le rafraîchissement échoue sans écraser le dernier catalogue publié si une API ne répond pas ou renvoie une structure invalide. Après une mise à jour réussie, l'action commit le nouveau JSON sur la branche où elle a été déclenchée.

## Schéma du JSON

```json
{
  "generated_at": "2026-10-22T19:00:00Z",
  "source": "GamerPower + Epic Games Store",
  "notice": "Information sur les sources utilisées",
  "offers": [
    {
      "id": "source-123",
      "title": "Nom du jeu ou DLC",
      "description": "Description fournie par la source",
      "type": "game | dlc | pack",
      "type_label": "Jeu complet | DLC / extension | Contenu bonus",
      "platform": "steam | epic | gog | ubisoft | other",
      "platform_label": "Nom de la boutique",
      "store": "Nom de la boutique",
      "url": "https://.../fiche-produit-ou-offre",
      "image": "https://.../visuel-officiel.jpg",
      "price_original": "59,99 €",
      "expires_at": "2026-10-30T17:00:00Z",
      "availability": "temporary | unknown",
      "is_permanent": false,
      "source": "Nom de la source"
    }
  ]
}
```

Le site répartit la liste complète en pages de 24 offres, masque les offres dont la date de fin est dépassée, et crée une fiche individuelle par identifiant (`jeux-gratuits/fiche.html?id=…`). Les cartes et fiches n'activent le bouton de récupération que si la source donne une URL HTTPS spécifique à l'offre ou au produit. Les URL de boutique à la racine ne sont jamais présentées comme des liens directs.

## Portée et limites

Le catalogue montre toutes les offres récupérées par les sources configurées (GamerPower + Epic), et non tous les jeux publiés sur toutes les boutiques. Les API tierces peuvent omettre des offres, ne pas fournir de prix d'origine ou de date de fin, et parfois rediriger vers une page détaillée d'annonce plutôt que vers le produit lui-même. Le workflow ne peut pas garantir l'exhaustivité du marché ni inventer les données absentes. Les promotions sont revalidées à chaque collecte ; une offre expirée peut néanmoins rester visible quelques minutes jusqu'au prochain rafraîchissement.

Les données initiales sont volontairement vides : aucune offre d'exemple avec une fausse image ou un lien de boutique générique n'est montrée avant la première collecte réussie.
