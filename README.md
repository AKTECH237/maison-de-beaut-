# Maison Éclat : plateforme hybride e-commerce et boutique physique

Site de vente de **cosmétiques** (laits, savons, lotions, sérums, parfums) et d'**articles capillaires** (mèches, greffes, perruques), avec boutique en ligne, Click & Collect et caisse en magasin. Réalisé en Django, d'après le cahier des charges « Plateforme Hybride Ecommerce & Boutique Physique ».

## Fonctionnalités

| Cahier des charges | Dans le projet |
|---|---|
| Deux espaces de catalogue et filtres | Cosmétiques & Soins (type de peau, effet) ; Mèches, Greffes & Capillaire (origine, texture) ; recherche |
| Variantes (14" / 18" / 24", 250 ml / 500 ml) | Déclinaisons avec prix et stock propres |
| Livraison ou Click & Collect | Choix au checkout, frais par ville, option express, retrait gratuit |
| Modes de paiement | Choix : à la livraison, Mobile Money, carte (enregistré ; paiement en ligne non branché) |
| Stock unique et synchronisé | Site et caisse partagent la même base : une vente en boutique baisse le stock en ligne |
| Alerte de stock bas | Seuil par déclinaison, visible dans l'admin et le tableau de bord |
| Suivi des livraisons | Statuts Nouvelle → En préparation → Confirmée → Prise en charge → Livrée → Payée |
| Livreurs et bordereaux | Attribution (interne ou Yango) et bordereau imprimable |
| WhatsApp | Bouton sur chaque fiche produit (photos ou vidéos) |
| Réassurance | Badges d'authenticité, adresse et horaires sur toutes les pages |
| Comptes clients | Inscription, connexion, historique des commandes |

## Prérequis

Python 3.10 ou plus et pip. Internet n'est nécessaire que pour les photos produits et la police ; tout le reste fonctionne hors ligne.

## Lancer le site

```bash
git clone https://github.com/<votre-compte>/maison-eclat.git
cd maison-eclat
python3 -m venv .venv
source .venv/bin/activate          # Windows : .venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py seed              # catalogue de démonstration
python manage.py createsuperuser   # compte du personnel (caisse et gestion)
python manage.py runserver
```

Ouvrir http://127.0.0.1:8000. Si `makemigrations` est demandé après une mise à jour du code : `python manage.py makemigrations shop`.

## Lancer sur une autre machine

1. **Avec Git** : les commandes ci-dessus suffisent (les migrations sont dans le dépôt).
2. **Avec Docker** : `docker compose up --build`, puis `docker compose exec web python manage.py createsuperuser`.
3. **Sans internet** : sur une machine connectée, `pip download -r requirements.txt -d wheels`. Copier le dossier `wheels` avec le projet, puis `pip install --no-index --find-links wheels -r requirements.txt`.
4. **Voir le site depuis un téléphone sur le même Wi-Fi** : `python manage.py runserver 0.0.0.0:8000`, puis ouvrir `http://<IP-de-l-ordinateur>:8000` (Linux : `hostname -I`).

## Images produits en ligne

Les images sont chargées depuis internet : hors connexion, une initiale colorée s'affiche à la place.

- **Par défaut** : image automatique par mots-clés (loremflickr.com), sans clé.
- **Images précises (recommandé)** : créer une clé gratuite sur https://www.pexels.com/api/ puis
  ```bash
  export PEXELS_API_KEY="votre_cle"      # PowerShell : $env:PEXELS_API_KEY="votre_cle"
  python manage.py fetch_images
  ```
  Les adresses sont enregistrées en base. Une image se change aussi à la main (champ « image » d'un produit dans l'admin).

## Pages principales

| URL | Rôle |
|---|---|
| `/` | Accueil, recherche |
| `/boutique/soins/`, `/boutique/capillaire/` | Catalogues filtrables |
| `/panier/`, `/commande/` | Panier et commande |
| `/inscription/`, `/connexion/`, `/mon-compte/` | Comptes clients |
| `/caisse/` | Caisse boutique (personnel) |
| `/gestion/` | Stock bas, commandes, livreurs (personnel) |
| `/admin/` | Back-office complet |

## Dépannage

- **`no such table`** : lancer `python manage.py migrate`.
- **Port occupé** : `python manage.py runserver 8001`.
- **Mot de passe oublié** : `python manage.py changepassword <identifiant>`.
- **Repartir de zéro (développement)** : supprimer `db.sqlite3`, puis `migrate` et `seed`.
- **Caisse ou gestion inaccessibles** : le compte doit être du personnel (`createsuperuser`).

## Pistes d'amélioration

Paiement Mobile Money et carte réel (ou écran simulé), filtres longueur et couleur, envoi de photos depuis l'admin, SMS de notification, déploiement (gunicorn, PostgreSQL, HTTPS).

Auteur : _à compléter_. Projet académique.
