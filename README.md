# Bonnes Affaires

Site qui rassemble les bonnes affaires du moment (high-tech, maison et bricolage, mode et beauté, voyages et loisirs). Quand on clique sur une offre, on arrive sur la page où elle a été publiée.

**Site en ligne : https://khalilbou91.github.io/bonnes-affaires/**

GitHub Pages héberge le site gratuitement et GitHub Actions lance le robot de collecte toutes les 2 heures.

## Comment ça marche

| Dossier / fichier | Rôle |
| --- | --- |
| `collector/sources.json` | La liste des flux à lire et leur catégorie. **C'est le seul fichier à modifier pour ajouter une source.** |
| `collector/collect.py` | Le robot. Python 3.9+ sans aucune dépendance. |
| `site/` | Le site web (HTML, CSS, JavaScript). |
| `site/data/deals.json` | Les offres, réécrites par le robot à chaque passage. |
| `.github/workflows/collecte-et-publication.yml` | La planification (toutes les 2 h) et la publication. |

Pour forcer une mise à jour : onglet **Actions** → **Collecte des offres et publication du site** → **Run workflow**.

## Ajouter une source

Dans `collector/sources.json`, ajoutez un bloc dans `flux` :

```json
{ "url": "https://exemple.fr/bons-plans/feed", "source": "Exemple", "categorie": "High-tech" }
```

`categorie` doit être l'une des 4 catégories listées en haut du fichier.

## Nom de domaine personnalisé

**Settings → Pages → Custom domain**, puis suivre les indications DNS de GitHub.

## Avant d'ouvrir le site au public

- Vérifier que les conditions d'utilisation de chaque source autorisent la réutilisation de leurs offres. Pour un site commercial, préférer les flux des plateformes d'affiliation (Awin, Effiliation, Amazon Partenaires…).
- Ajouter des mentions légales (éditeur, hébergeur) et signaler les éventuels liens d'affiliation.
