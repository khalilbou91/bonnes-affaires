# Bonnes Affaires

Site qui rassemble les bonnes affaires du moment (high-tech, maison et bricolage, mode et beauté, voyages et loisirs). Quand on clique sur une offre, on arrive sur la page où elle a été publiée.

**Site en ligne : https://mesbonnesaffaires.fr** (version de test)

## Comment ça marche

Toutes les 2 heures, GitHub Actions lance le robot de collecte, enregistre les offres dans `site/data/deals.json`, puis envoie le dossier `site/` sur l'hébergement OVHcloud (SFTP, dossier `www`). Le mot de passe SFTP est rangé dans le secret `OVH_SFTP_PASSWORD` du dépôt.

| Dossier / fichier | Rôle |
| --- | --- |
| `collector/sources.json` | La liste des flux à lire et leur catégorie. **C'est le seul fichier à modifier pour ajouter une source.** |
| `collector/collect.py` | Le robot. Python 3.9+ sans aucune dépendance. |
| `site/` | Le site web (HTML, CSS, JavaScript). |
| `site/data/deals.json` | Les offres, réécrites par le robot à chaque passage. |
| `.github/workflows/collecte-et-publication.yml` | La planification (toutes les 2 h) et l'envoi sur OVHcloud. |

Pour forcer une mise à jour : onglet **Actions** → **Collecte des offres et publication du site** → **Run workflow**.

## Ajouter une source

Dans `collector/sources.json`, ajoutez un bloc dans `flux` :

```json
{ "url": "https://exemple.fr/bons-plans/feed", "source": "Exemple", "categorie": "High-tech" }
```

`categorie` doit être l'une des 4 catégories listées en haut du fichier.

## Avant d'ouvrir le site au public

- Remplacer les sources Dealabs par des flux d'affiliation (Amazon Partenaires, Awin…) pour pouvoir générer des revenus.
- Ajouter des mentions légales (éditeur, hébergeur) et signaler les liens d'affiliation.
- Retirer le bandeau « Version de test » et la balise `noindex` de `site/index.html`.
