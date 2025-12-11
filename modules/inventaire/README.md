# Module Inventaire - Assistant Gazelle V5

Système de gestion d'inventaire pour les techniciens de pianos.

## Structure du Module

```
modules/inventaire/
├── README.md                                    # Cette documentation
├── migrations/
│   └── 001_create_inventory_tables.sql         # Script SQL pour créer les tables
└── (à venir: frontend React pour l'interface)
```

## Architecture

### Base de données (Supabase)

Le module utilise 3 tables dans Supabase:

1. **produits_catalogue** - Catalogue des produits
   - `code_produit` (TEXT, unique): Code unique du produit (ex: "CORD-001")
   - `nom` (TEXT): Nom du produit
   - `categorie` (TEXT): Catégorie (ex: "Cordes", "Feutres", "Outils")
   - `description` (TEXT): Description détaillée
   - `unite_mesure` (TEXT): Unité de mesure (défaut: "unité")
   - `prix_unitaire` (DECIMAL): Prix de référence
   - `fournisseur` (TEXT): Nom du fournisseur principal

2. **inventaire_techniciens** - Inventaire par technicien
   - `code_produit` (TEXT): Référence au produit
   - `technicien` (TEXT): Nom du technicien
   - `quantite_stock` (DECIMAL): Quantité en stock
   - `emplacement` (TEXT): Localisation (ex: "Atelier", "Camion")
   - `notes` (TEXT): Notes additionnelles
   - `derniere_verification` (TIMESTAMP): Date dernière vérification
   - Contrainte unique: (code_produit, technicien, emplacement)

3. **transactions_inventaire** - Historique des mouvements
   - `inventaire_id` (UUID): Référence à l'inventaire
   - `code_produit` (TEXT): Code du produit
   - `technicien` (TEXT): Technicien concerné
   - `type_transaction` (TEXT): Type (ajout, retrait, transfert, correction)
   - `quantite` (DECIMAL): Quantité (valeur absolue)
   - `quantite_avant` (DECIMAL): Stock avant transaction
   - `quantite_apres` (DECIMAL): Stock après transaction
   - `motif` (TEXT): Raison de la transaction
   - `reference_client` (TEXT): Référence client si applicable
   - `reference_facture` (TEXT): Référence facture si applicable
   - `created_by` (TEXT): Qui a créé la transaction

### Backend API (FastAPI)

Le backend expose les routes suivantes:

#### Catalogue de produits

- `GET /inventaire/catalogue?categorie={categorie}` - Liste les produits
- `POST /inventaire/catalogue` - Ajoute un produit
- `PUT /inventaire/catalogue/{code_produit}` - Met à jour un produit
- `DELETE /inventaire/catalogue/{code_produit}` - Supprime un produit

#### Inventaire par technicien

- `GET /inventaire/stock/{technicien}` - Inventaire d'un technicien
- `POST /inventaire/stock/ajuster` - Ajuste le stock (ajout/retrait)

#### Historique et statistiques

- `GET /inventaire/transactions?technicien={technicien}&code_produit={code}&limit={n}` - Historique
- `GET /inventaire/stats/{technicien}` - Statistiques d'un technicien

### Client Supabase (Python)

Méthodes disponibles dans `core/supabase_storage.py`:

#### Méthodes génériques
- `update_data(table_name, data, id_field, upsert)` - Mise à jour générique
- `get_data(table_name, filters, select, order_by)` - Récupération générique
- `delete_data(table_name, id_field, id_value)` - Suppression générique

#### Méthodes spécifiques inventaire
- `get_produits_catalogue(categorie)` - Liste les produits
- `get_inventaire_technicien(technicien)` - Inventaire d'un technicien
- `update_stock(code_produit, technicien, quantite_ajustement, emplacement, motif, created_by)` - Ajuste le stock
- `get_transactions_inventaire(technicien, code_produit, limit)` - Historique des transactions

## Installation

### 1. Créer les tables Supabase

1. Connectez-vous à votre dashboard Supabase
2. Allez dans **SQL Editor**
3. Ouvrez le fichier `modules/inventaire/migrations/001_create_inventory_tables.sql`
4. Copiez-collez le contenu dans l'éditeur SQL
5. Cliquez sur **Run** pour exécuter le script

Le script créera:
- La fonction `update_updated_at_column()` pour les timestamps automatiques
- Les 3 tables avec leurs index et triggers
- Des données de test (5 produits + inventaire Allan) - optionnel

**Données de test incluses:**
- CORD-001: Corde #1 (Do)
- CORD-002: Corde #2 (Ré)
- FELT-001: Feutre tête de marteau
- TOOL-001: Clé d'accord
- CLEAN-001: Nettoyant touches

Pour **production**, commentez les sections `INSERT INTO` avant d'exécuter.

### 2. Vérifier les tables

Dans Supabase Dashboard → **Table Editor**, vérifiez que les tables apparaissent:
- `produits_catalogue`
- `inventaire_techniciens`
- `transactions_inventaire`

### 3. Configurer Row Level Security (RLS) - OPTIONNEL

Si vous utilisez l'authentification Supabase, activez RLS:

```sql
-- Activer RLS
ALTER TABLE produits_catalogue ENABLE ROW LEVEL SECURITY;
ALTER TABLE inventaire_techniciens ENABLE ROW LEVEL SECURITY;
ALTER TABLE transactions_inventaire ENABLE ROW LEVEL SECURITY;

-- Exemple de policies (à adapter selon vos besoins)
-- Permettre lecture à tous les utilisateurs authentifiés
CREATE POLICY "Lecture catalogue pour utilisateurs authentifiés"
ON produits_catalogue FOR SELECT
TO authenticated
USING (true);

-- Permettre à un technicien de voir son propre inventaire
CREATE POLICY "Technicien voit son inventaire"
ON inventaire_techniciens FOR SELECT
TO authenticated
USING (technicien = auth.jwt() ->> 'email');
```

### 4. Déployer le backend

Le backend est déjà configuré si vous utilisez l'API principale:

```bash
# En local
cd /Users/allansutton/Documents/assistant-gazelle-v5
source .env
python3 -m uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

Testez l'API:
```bash
# Vérifier que les routes sont disponibles
curl http://localhost:8000/ | jq

# Récupérer le catalogue
curl http://localhost:8000/inventaire/catalogue | jq

# Récupérer l'inventaire d'Allan (si données de test chargées)
curl http://localhost:8000/inventaire/stock/Allan | jq
```

## Utilisation

### Exemples d'utilisation Python

```python
from core.supabase_storage import SupabaseStorage

storage = SupabaseStorage()

# 1. Ajouter un produit au catalogue
storage.update_data(
    "produits_catalogue",
    {
        "code_produit": "CORD-003",
        "nom": "Corde #3 (Mi)",
        "categorie": "Cordes",
        "prix_unitaire": 13.00
    },
    id_field="code_produit"
)

# 2. Récupérer tous les produits de catégorie "Cordes"
cordes = storage.get_produits_catalogue(categorie="Cordes")
print(f"Nombre de cordes: {len(cordes)}")

# 3. Récupérer l'inventaire d'Allan
inventaire = storage.get_inventaire_technicien("Allan")
for item in inventaire:
    print(f"{item['code_produit']}: {item['quantite_stock']} {item.get('emplacement', 'N/A')}")

# 4. Ajouter 10 cordes #1 pour Allan
storage.update_stock(
    code_produit="CORD-001",
    technicien="Allan",
    quantite_ajustement=10,
    emplacement="Atelier",
    motif="Achat fournisseur",
    created_by="Allan"
)

# 5. Retirer 2 cordes (utilisées pour un client)
storage.update_stock(
    code_produit="CORD-001",
    technicien="Allan",
    quantite_ajustement=-2,
    emplacement="Atelier",
    motif="Utilisation client: Piano Steinway local 301",
    created_by="Allan"
)

# 6. Consulter l'historique des transactions
transactions = storage.get_transactions_inventaire(
    technicien="Allan",
    limit=10
)
for t in transactions:
    print(f"{t['created_at']}: {t['type_transaction']} {t['quantite']} {t['code_produit']}")
```

### Exemples d'utilisation API (curl)

```bash
# 1. Lister le catalogue (tous les produits)
curl http://localhost:8000/inventaire/catalogue

# 2. Filtrer par catégorie
curl "http://localhost:8000/inventaire/catalogue?categorie=Cordes"

# 3. Ajouter un produit
curl -X POST http://localhost:8000/inventaire/catalogue \
  -H "Content-Type: application/json" \
  -d '{
    "code_produit": "CORD-004",
    "nom": "Corde #4 (Fa)",
    "categorie": "Cordes",
    "prix_unitaire": 13.25
  }'

# 4. Mettre à jour un produit
curl -X PUT http://localhost:8000/inventaire/catalogue/CORD-004 \
  -H "Content-Type: application/json" \
  -d '{"prix_unitaire": 13.50}'

# 5. Récupérer l'inventaire d'Allan
curl http://localhost:8000/inventaire/stock/Allan

# 6. Ajuster le stock (ajouter 15 cordes)
curl -X POST http://localhost:8000/inventaire/stock/ajuster \
  -H "Content-Type: application/json" \
  -d '{
    "code_produit": "CORD-001",
    "technicien": "Allan",
    "quantite_ajustement": 15,
    "emplacement": "Atelier",
    "motif": "Réapprovisionnement",
    "created_by": "Allan"
  }'

# 7. Retirer du stock (retrait de 5 unités)
curl -X POST http://localhost:8000/inventaire/stock/ajuster \
  -H "Content-Type: application/json" \
  -d '{
    "code_produit": "CORD-001",
    "technicien": "Allan",
    "quantite_ajustement": -5,
    "emplacement": "Atelier",
    "motif": "Utilisation client XYZ",
    "created_by": "Allan"
  }'

# 8. Consulter l'historique (toutes les transactions)
curl http://localhost:8000/inventaire/transactions

# 9. Filtrer transactions par technicien
curl "http://localhost:8000/inventaire/transactions?technicien=Allan&limit=20"

# 10. Statistiques d'un technicien
curl http://localhost:8000/inventaire/stats/Allan
```

## Flux de travail typique

### Scénario 1: Achat de matériel

1. Ajouter les produits au catalogue (si nouveaux)
2. Ajouter le stock pour le technicien:
   ```python
   storage.update_stock(
       code_produit="CORD-001",
       technicien="Allan",
       quantite_ajustement=50,  # Positif = ajout
       emplacement="Atelier",
       motif="Achat fournisseur XYZ - Facture #12345",
       created_by="Allan"
   )
   ```
3. La transaction est automatiquement enregistrée dans `transactions_inventaire`

### Scénario 2: Utilisation chez un client

1. Retirer du stock lors de l'intervention:
   ```python
   storage.update_stock(
       code_produit="CORD-001",
       technicien="Allan",
       quantite_ajustement=-3,  # Négatif = retrait
       emplacement="Atelier",
       motif="Client: École Vincent-d'Indy, Piano Steinway D #158104",
       created_by="Allan"
   )
   ```
2. La transaction enregistre: quantité avant, quantité après, motif

### Scénario 3: Inventaire physique (vérification)

1. Récupérer l'inventaire actuel du technicien
2. Comparer avec le stock physique
3. Ajuster si nécessaire:
   ```python
   # Si on trouve 47 unités au lieu de 50 (écart de -3)
   storage.update_stock(
       code_produit="CORD-001",
       technicien="Allan",
       quantite_ajustement=-3,
       emplacement="Atelier",
       motif="Correction inventaire physique",
       created_by="Allan"
   )
   ```

### Scénario 4: Transfert entre emplacements

```python
# Option 1: Utiliser 2 transactions
# Retirer de l'Atelier
storage.update_stock(
    code_produit="CORD-001",
    technicien="Allan",
    quantite_ajustement=-10,
    emplacement="Atelier",
    motif="Transfert vers Camion",
    created_by="Allan"
)

# Ajouter au Camion
storage.update_stock(
    code_produit="CORD-001",
    technicien="Allan",
    quantite_ajustement=10,
    emplacement="Camion",
    motif="Transfert depuis Atelier",
    created_by="Allan"
)
```

## Prochaines étapes

### Frontend React (à développer)

Le frontend pourrait inclure:

1. **Page Catalogue**
   - Liste des produits avec filtres par catégorie
   - Formulaire d'ajout/modification de produits
   - Recherche par nom/code

2. **Page Mon Inventaire**
   - Vue de l'inventaire du technicien connecté
   - Groupé par emplacement (Atelier, Camion, etc.)
   - Boutons rapides: +/- pour ajuster les quantités
   - Indicateurs visuels: stock bas, dernière vérification

3. **Page Transactions**
   - Historique des mouvements
   - Filtres: date, type, produit
   - Export CSV/PDF

4. **Page Statistiques**
   - Valeur totale du stock
   - Graphiques d'utilisation
   - Alertes de stock bas
   - Rapports mensuels

### Fonctionnalités futures

- [ ] Alertes automatiques pour stock bas (email/SMS)
- [ ] Code-barres / QR codes pour scan rapide
- [ ] Intégration avec système de facturation
- [ ] Prévisions de consommation (machine learning)
- [ ] Gestion des commandes fournisseurs
- [ ] Multi-devises pour prix
- [ ] Photos des produits
- [ ] Historique des prix

## Support et maintenance

### Backup des données

Les données sont stockées dans Supabase avec backup automatique. Pour un backup manuel:

```sql
-- Export catalogue
SELECT * FROM produits_catalogue;

-- Export inventaire
SELECT * FROM inventaire_techniciens;

-- Export transactions (6 derniers mois)
SELECT * FROM transactions_inventaire
WHERE created_at >= NOW() - INTERVAL '6 months'
ORDER BY created_at DESC;
```

### Troubleshooting

**Problème: Erreur "SUPABASE_URL et SUPABASE_KEY requis"**
- Vérifier que les variables d'environnement sont définies:
  ```bash
  echo $SUPABASE_URL
  echo $SUPABASE_KEY
  ```

**Problème: Stock négatif**
- Les quantités négatives sont autorisées (pour inventaire en attente de livraison)
- Pour empêcher: ajouter une contrainte CHECK en SQL:
  ```sql
  ALTER TABLE inventaire_techniciens
  ADD CONSTRAINT quantite_positive CHECK (quantite_stock >= 0);
  ```

**Problème: Performance lente sur transactions**
- Les index sont déjà créés sur: technicien, code_produit, type, date
- Si > 10,000 transactions, envisager l'archivage:
  ```sql
  -- Archiver transactions > 1 an
  CREATE TABLE transactions_inventaire_archive AS
  SELECT * FROM transactions_inventaire
  WHERE created_at < NOW() - INTERVAL '1 year';

  DELETE FROM transactions_inventaire
  WHERE created_at < NOW() - INTERVAL '1 year';
  ```

## Contact

Pour questions ou suggestions: allan@pianoteknik.com
