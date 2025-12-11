# 📋 Règles de Migration V4 → V5

**Date:** 2025-01-15  
**Projet:** Assistant Gazelle V5

---

## 🚫 Règle Fondamentale

**ON NE TOUCHE PAS À V4!**

Tous les scripts et processus de migration doivent respecter cette règle absolue.

---

## ✅ Principe de Migration

### V4 (Ancien Système - SQL Server Gazelle)
- ✅ **Lecture seule** - On lit les données pour les migrer
- ❌ **Aucune modification** - On ne touche à rien
- ✅ **Continue de fonctionner** - V4 reste opérationnel pendant la migration

### V5 (Nouveau Système - Supabase + React)
- ✅ **Développement actif** - On développe sur V5
- ✅ **Nouvelle base de données** - Supabase (séparée de V4)
- ✅ **Import des données** - Copie depuis V4 (sans modifier V4)

---

## 📋 Checklist pour Tous les Scripts

Avant d'écrire ou modifier un script de migration:

- [ ] ✅ Le script lit UNIQUEMENT depuis V4 (SELECT seulement)
- [ ] ✅ Le script écrit UNIQUEMENT dans V5 (Supabase)
- [ ] ❌ Le script ne modifie JAMAIS V4
- [ ] ❌ Le script n'utilise JAMAIS UPDATE/DELETE/INSERT sur V4
- [ ] ✅ Le script est documenté avec la règle "lecture seule V4"

---

## 🔍 Exemples

### ✅ CORRECT

```python
# Lecture depuis V4 (SQL Server)
def fetch_from_gazelle():
    query = "SELECT * FROM inv.Products WHERE IsDeleted = 0"  # SELECT seulement
    return cursor.fetchall()

# Écriture dans V5 (Supabase)
def import_to_v5(data):
    storage = SupabaseStorage()  # V5
    storage.update_data("produits_catalogue", data)  # Écriture V5
```

### ❌ INCORRECT

```python
# ❌ NE JAMAIS FAIRE ÇA
def modify_v4():
    cursor.execute("UPDATE inv.Products SET ...")  # ❌ Modification V4
    cursor.execute("DELETE FROM inv.Products ...")  # ❌ Suppression V4
    cursor.execute("INSERT INTO inv.Products ...")  # ❌ Insertion V4
```

---

## 📁 Structure

```
assistant-gazelle-v5/          ← V5 (Mac + Web)
├── api/                       ← Backend V5 (FastAPI)
├── frontend/                  ← Frontend V5 (React)
├── core/                      ← Core V5 (Supabase)
└── scripts/                   ← Scripts de migration V4 → V5
    └── import_gazelle_product_display.py  ← Migration V4 → V5

assistant-gazelle-v4/          ← V4 (NE PAS TOUCHER)
└── ...                        ← Continue de fonctionner
```

---

## 🎯 Résumé

**V4:**
- ✅ Lecture seule pour migration
- ❌ Aucune modification
- ✅ Continue de fonctionner normalement

**V5:**
- ✅ Développement actif
- ✅ Nouvelle base de données (Supabase)
- ✅ Import des données depuis V4

**Migration:**
- ✅ Copie V4 → V5
- ❌ Ne modifie jamais V4

---

## 📞 En Cas de Doute

**Si vous n'êtes pas sûr:**
1. Demander avant de modifier
2. Vérifier que vous travaillez sur V5
3. Vérifier que vous ne modifiez pas V4

**Règle d'or:** En cas de doute, ne pas modifier!
