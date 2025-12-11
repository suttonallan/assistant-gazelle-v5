# 📋 Processus Standardisé pour les Migrations Futures

**Date:** 2025-01-15  
**Objectif:** Établir un processus clair et reproductible pour les prochaines migrations

---

## 🎯 Principes Fondamentaux

### 1. Règle V4 (Absolue)
- ✅ **LECTURE SEULE** depuis V4
- ❌ **AUCUNE MODIFICATION** de V4
- ✅ V4 continue de fonctionner normalement

### 2. Vérification Avant Code
- ✅ **Vérifier la structure réelle** de V4 (schéma SQL)
- ✅ **Vérifier les noms de colonnes** réels
- ✅ **Vérifier le code existant** avant de proposer des modifications
- ❌ Ne pas supposer que les colonnes existent

### 3. Séparation V4/V5
- ✅ V4 = Source de données (lecture)
- ✅ V5 = Destination (écriture)
- ✅ Mapping clair entre les deux

---

## 📋 Processus Standardisé (6 Étapes)

### Étape 1: Analyse de la Source V4 (30 min)

**Objectif:** Comprendre exactement ce qui existe dans V4

**Actions:**
1. ✅ Examiner le schéma SQL Server Gazelle
2. ✅ Lister les tables et colonnes réelles
3. ✅ Identifier les relations entre tables
4. ✅ Documenter les types de données

**Livrable:** `docs/ANALYSE_V4_[MODULE].md`

**Exemple:**
```markdown
# Analyse V4 - Module Inventaire

## Table: inv.Products
- ProductId (INT)
- Sku (TEXT) ← Note: pas "Code"
- Name (TEXT)
- Active (BOOLEAN) ← Note: pas "IsDeleted"
- UnitPrice (DECIMAL)
- ...

## Table: inv.ProductDisplay
- ProductId (INT, FK)
- Category (TEXT)
- VariantGroup (TEXT)
- VariantLabel (TEXT)
- DisplayOrder (INT)
- IsActive (BOOLEAN)
- ❌ HasCommission (N'EXISTE PAS)
- ❌ CommissionRate (N'EXISTE PAS)
```

---

### Étape 2: Conception du Mapping V4 → V5 (20 min)

**Objectif:** Définir comment mapper les données V4 vers V5

**Actions:**
1. ✅ Créer un tableau de mapping colonne par colonne
2. ✅ Identifier les valeurs par défaut pour V5
3. ✅ Identifier les transformations nécessaires
4. ✅ Documenter les colonnes qui n'existent pas dans V4

**Livrable:** `docs/MAPPING_V4_V5_[MODULE].md`

**Exemple:**
```markdown
# Mapping V4 → V5 - Produits Catalogue

| V4 (Gazelle) | V5 (Supabase) | Transformation | Notes |
|--------------|---------------|----------------|-------|
| inv.Products.Sku | code_produit | Direct | |
| inv.Products.Name | nom | Direct | |
| inv.ProductDisplay.Category | categorie | Direct | |
| inv.Products.Active | is_active | Inverser (!Active) | |
| ❌ N'existe pas | has_commission | FALSE (défaut) | |
| ❌ N'existe pas | commission_rate | 0.00 (défaut) | |
```

---

### Étape 3: Création de la Migration SQL V5 (15 min)

**Objectif:** Créer les tables V5 avec toutes les colonnes nécessaires

**Actions:**
1. ✅ Créer le script SQL de migration
2. ✅ Inclure les colonnes V4 (mappées)
3. ✅ Inclure les nouvelles colonnes V5 (valeurs par défaut)
4. ✅ Tester la migration dans Supabase

**Livrable:** `modules/[module]/migrations/XXX_create_tables.sql`

---

### Étape 4: Création du Script d'Import (30 min)

**Objectif:** Script Python pour migrer les données

**Actions:**
1. ✅ Créer le script dans `scripts/import_[module]_from_v4.py`
2. ✅ Implémenter `fetch_from_v4()` avec les VRAIES colonnes
3. ✅ Implémenter `map_v4_to_v5()` selon le mapping
4. ✅ Implémenter `import_to_v5()` avec SupabaseStorage
5. ✅ Ajouter mode `--dry-run` pour test

**Structure standard:**
```python
def fetch_from_v4() -> List[Dict]:
    """Lit UNIQUEMENT depuis V4 (SELECT seulement)"""
    # Utiliser les VRAIES colonnes V4
    query = "SELECT Sku, Name, Active FROM inv.Products WHERE Active = 1"
    # Ne JAMAIS utiliser UPDATE/DELETE/INSERT

def map_v4_to_v5(v4_data: Dict) -> Dict:
    """Mappe V4 → V5 selon le mapping documenté"""
    return {
        "code_produit": v4_data["Sku"],  # Mapping correct
        "nom": v4_data["Name"],
        "is_active": not v4_data["Active"],  # Transformation
        "has_commission": False,  # Valeur par défaut (n'existe pas dans V4)
        "commission_rate": 0.00,  # Valeur par défaut
    }

def import_to_v5(v5_data: Dict):
    """Écrit dans V5 via SupabaseStorage"""
    storage = SupabaseStorage()
    storage.update_data("table_v5", v5_data, upsert=True)
```

**Livrable:** `scripts/import_[module]_from_v4.py`

---

### Étape 5: Test et Validation (20 min)

**Objectif:** S'assurer que tout fonctionne

**Actions:**
1. ✅ Exécuter la migration SQL dans Supabase
2. ✅ Tester le script avec `--dry-run`
3. ✅ Vérifier le mapping des données
4. ✅ Exécuter l'import réel
5. ✅ Vérifier les données dans Supabase Dashboard
6. ✅ Vérifier les données dans l'interface React

**Checklist:**
- [ ] Migration SQL exécutée
- [ ] Test `--dry-run` réussi
- [ ] Import réel réussi
- [ ] Données visibles dans Supabase
- [ ] Données visibles dans React
- [ ] Aucune modification de V4

---

### Étape 6: Documentation (15 min)

**Objectif:** Documenter pour référence future

**Actions:**
1. ✅ Créer `docs/MIGRATION_[MODULE]_COMPLETE.md`
2. ✅ Documenter le processus utilisé
3. ✅ Documenter les problèmes rencontrés
4. ✅ Documenter les solutions trouvées

**Livrable:** `docs/MIGRATION_[MODULE]_COMPLETE.md`

---

## 📋 Template de Script Standard

```python
#!/usr/bin/env python3
"""
Script d'importation depuis Gazelle V4 vers Supabase V5.

⚠️  RÈGLE IMPORTANTE: MIGRATION V4 → V5
- LECTURE SEULE depuis V4 (SQL Server Gazelle) - Ne jamais modifier V4
- ÉCRITURE dans V5 (Supabase) - Nouvelle base de données
- V4 continue de fonctionner normalement, on ne le touche pas
"""

import sys
import os
from typing import List, Dict, Any
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.supabase_storage import SupabaseStorage


def fetch_from_v4() -> List[Dict[str, Any]]:
    """
    Récupère les données depuis Gazelle V4.
    
    ⚠️  RÈGLE IMPORTANTE: LECTURE SEULE!
    - Cette fonction lit UNIQUEMENT depuis V4 (SQL Server Gazelle)
    - Ne JAMAIS modifier, supprimer ou altérer les données V4
    - Utiliser uniquement des requêtes SELECT (lecture seule)
    
    Returns:
        Liste des données depuis V4
    """
    import pyodbc
    
    # Configuration SQL Server V4
    DB_CONN_STR = os.environ.get('DB_CONN_STR') or (
        "DRIVER={ODBC Driver 17 for SQL Server};"
        "SERVER=PIANOTEK\\SQLEXPRESS;"
        "DATABASE=PianoTek;"
        "Trusted_Connection=yes;"
    )
    
    try:
        conn = pyodbc.connect(DB_CONN_STR)
        cursor = conn.cursor()
        
        # ⚠️  IMPORTANT: Utiliser les VRAIES colonnes V4
        # Vérifier le schéma avant d'écrire cette requête!
        query = """
        SELECT
            -- Utiliser les VRAIES colonnes V4
            p.Sku AS code_produit,  -- Pas "Code"!
            p.Name AS nom,
            p.Active,  -- Pas "IsDeleted"!
            pd.Category AS categorie
            -- Ne PAS essayer de lire des colonnes qui n'existent pas
        FROM inv.Products p
        LEFT JOIN inv.ProductDisplay pd ON p.ProductId = pd.ProductId
        WHERE p.Active = 1  -- Pas "IsDeleted = 0"!
        """
        
        cursor.execute(query)
        columns = [column[0] for column in cursor.description]
        
        data = []
        for row in cursor.fetchall():
            data.append(dict(zip(columns, row)))
        
        cursor.close()
        conn.close()
        
        return data
        
    except Exception as e:
        print(f"❌ Erreur: {e}")
        raise


def map_v4_to_v5(v4_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Mappe les données V4 vers le format V5.
    
    Args:
        v4_data: Données depuis V4
        
    Returns:
        Données au format V5
    """
    return {
        # Mapping direct
        "code_produit": v4_data.get("code_produit"),
        "nom": v4_data.get("nom"),
        "categorie": v4_data.get("categorie", "Produit"),
        
        # Transformations
        "is_active": not v4_data.get("Active", False),  # Inverser
        
        # Valeurs par défaut (colonnes qui n'existent pas dans V4)
        "has_commission": False,
        "commission_rate": 0.00,
        
        # Métadonnées
        "last_sync_at": datetime.now().isoformat()
    }


def import_to_v5(v5_data: Dict[str, Any], table_name: str):
    """
    Importe les données dans Supabase V5.
    
    Args:
        v5_data: Données au format V5
        table_name: Nom de la table Supabase
    """
    storage = SupabaseStorage()
    storage.update_data(
        table_name,
        v5_data,
        id_field="code_produit",
        upsert=True
    )


def main():
    """Point d'entrée principal."""
    import argparse
    
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    
    print("🔄 Migration V4 → V5...")
    
    # 1. Lire depuis V4
    print("📥 Lecture depuis V4...")
    v4_data = fetch_from_v4()
    print(f"   ✅ {len(v4_data)} enregistrements récupérés")
    
    # 2. Mapper vers V5
    print("🔄 Mapping V4 → V5...")
    v5_data_list = [map_v4_to_v5(item) for item in v4_data]
    
    # 3. Importer dans V5
    if not args.dry_run:
        print("📦 Importation dans V5...")
        for v5_data in v5_data_list:
            import_to_v5(v5_data, "produits_catalogue")
        print("✅ Import terminé!")
    else:
        print("🔍 [DRY-RUN] Aucune modification")
        for v5_data in v5_data_list[:5]:  # Afficher les 5 premiers
            print(f"   {v5_data}")


if __name__ == "__main__":
    main()
```

---

## ✅ Checklist pour Chaque Migration

### Avant de Commencer
- [ ] Analyser le schéma V4 réel
- [ ] Documenter le mapping V4 → V5
- [ ] Créer la migration SQL V5
- [ ] Vérifier que V4 n'est pas modifié

### Pendant le Développement
- [ ] Utiliser les VRAIES colonnes V4
- [ ] Ne pas supposer que les colonnes existent
- [ ] Tester avec `--dry-run` d'abord
- [ ] Vérifier le mapping des données

### Après l'Import
- [ ] Vérifier les données dans Supabase
- [ ] Vérifier les données dans React
- [ ] Documenter le processus
- [ ] Vérifier que V4 n'a pas été modifié

---

## 🎯 Résumé

**Processus standardisé:**
1. ✅ Analyser V4 (vraies colonnes)
2. ✅ Créer mapping V4 → V5
3. ✅ Migration SQL V5
4. ✅ Script d'import (vraies colonnes V4)
5. ✅ Test et validation
6. ✅ Documentation

**Règle d'or:** Toujours vérifier le schéma V4 réel avant d'écrire du code!

---

## 📝 Template de Documentation

Pour chaque migration, créer:

```
docs/
├── ANALYSE_V4_[MODULE].md      ← Structure réelle V4
├── MAPPING_V4_V5_[MODULE].md   ← Mapping colonnes
└── MIGRATION_[MODULE]_COMPLETE.md ← Processus complet
```

**Cela permettra de réutiliser le processus pour les prochaines migrations!**
