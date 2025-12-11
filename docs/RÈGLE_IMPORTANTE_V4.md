# ⚠️ RÈGLE IMPORTANTE: Ne Pas Toucher à V4

**Date:** 2025-01-15  
**Projet:** Assistant Gazelle V5

---

## 🚫 Règle Fondamentale

**ON NE TOUCHE PAS À V4!**

- ❌ Ne pas modifier le code V4
- ❌ Ne pas modifier les données V4
- ❌ Ne pas modifier la base de données V4
- ❌ Ne pas modifier les scripts V4

---

## ✅ Ce Qu'on Fait

**Migration vers V5 uniquement:**

1. ✅ **Sur Mac:** Développement V5
2. ✅ **Web:** Interface React V5
3. ✅ **Supabase:** Nouvelle base de données V5
4. ✅ **Import:** Copie des données V4 → V5 (lecture seule depuis V4)

---

## 📋 Principe de Migration

### V4 (Ancien Système)
- ✅ **Lecture seule** - On lit les données pour les migrer
- ❌ **Aucune modification** - On ne touche à rien
- ✅ **Continue de fonctionner** - V4 reste opérationnel

### V5 (Nouveau Système)
- ✅ **Développement actif** - On développe sur V5
- ✅ **Nouvelle base de données** - Supabase (séparée de V4)
- ✅ **Import des données** - Copie depuis V4 (sans modifier V4)

---

## 🔍 Scripts d'Import

**Tous les scripts d'import doivent:**

1. ✅ **Lire depuis V4** (SQL Server Gazelle) - Lecture seule
2. ✅ **Écrire dans V5** (Supabase) - Nouvelle base
3. ❌ **Ne jamais modifier V4**

**Exemple:**
```python
# ✅ CORRECT: Lire depuis V4, écrire dans V5
gazelle_data = read_from_sql_server()  # Lecture seule
supabase_storage.update_data("produits_catalogue", gazelle_data)  # Écriture V5

# ❌ INCORRECT: Modifier V4
sql_server.execute("UPDATE ...")  # NE JAMAIS FAIRE ÇA
```

---

## 📁 Structure du Projet

```
assistant-gazelle-v5/          ← V5 (Mac + Web)
├── api/                       ← Backend V5 (FastAPI)
├── frontend/                  ← Frontend V5 (React)
├── core/                      ← Core V5 (Supabase)
└── scripts/                   ← Scripts de migration V4 → V5

assistant-gazelle-v4/          ← V4 (NE PAS TOUCHER)
├── ...                        ← Ancien système
└── ...                        ← Continue de fonctionner
```

---

## ✅ Checklist Avant Toute Modification

Avant de modifier quoi que ce soit, vérifier:

- [ ] Est-ce que je modifie V4? → ❌ **ARRÊTER**
- [ ] Est-ce que je modifie V5? → ✅ **OK**
- [ ] Est-ce que je lis depuis V4? → ✅ **OK** (lecture seule)
- [ ] Est-ce que j'écris dans V5? → ✅ **OK**

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
