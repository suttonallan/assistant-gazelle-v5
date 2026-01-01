# Documentation V6 - Index

**Date création:** 2025-12-29

---

## 🎯 Les 6 Piliers (Documents "Source de Vérité")

Ces documents définissent l'architecture complète de l'Assistant Gazelle V6. **Lisez-les AVANT toute implémentation.**

### 1. [ARCHITECTURE_MAP.md](ARCHITECTURE_MAP.md)
**📐 Structure & Organisation**

- Structure complète des dossiers V6
- Rôle de chaque module (Fetcher, Reconciler, Models, Utils, API, Sync)
- Patterns architecturaux (Separation of Concerns, Strategy, Repository)
- Migration V5 → V6 (4 phases sur 6 semaines)
- Principes DO/DON'T

**Quand le lire:**
- Avant de créer un nouveau fichier/module
- Avant de refactorer du code existant
- Pour comprendre où va quelle logique

---

### 2. [SYNC_STRATEGY.md](SYNC_STRATEGY.md)
**⏰ Synchronisation Gazelle + Timezone UTC (CRITIQUE)**

- Architecture 2-stages (Gazelle → Staging → Production)
- **Solution timezone UTC** (TOUJOURS à lire avant import!)
- Gestion des erreurs et rollback
- Monitoring et observabilité
- Tests de synchronisation

**⚠️ RÈGLE CRITIQUE:**
> Toujours stocker `appointment_time` en **UTC**. Conversion Montréal seulement pour affichage.

**Quand le lire:**
- **OBLIGATOIRE** avant tout import de données Gazelle
- Avant d'implémenter un job de sync
- Si problèmes de timezone détectés
- Avant de modifier les scripts d'import

---

### 3. [DATA_DICTIONARY.md](DATA_DICTIONARY.md)
**🗂️ Schéma Complet des Données**

- Tables production (contacts, locations, clients, appointments, pianos, timeline)
- Tables staging (backup données brutes)
- Relations Contact ↔ Location ↔ Client
- Contraintes et validations
- Requêtes SQL courantes

**⚠️ RÈGLE CRITIQUE:**
> Codes d'accès TOUJOURS liés à `gazelle_locations`, JAMAIS à `gazelle_clients`.

**Quand le lire:**
- Avant de créer/modifier une table
- Avant d'écrire une requête SQL complexe
- Pour comprendre les relations entre entités
- Avant d'utiliser le Reconciler

---

### 4. [USER_ROLES_SECURITY.md](USER_ROLES_SECURITY.md)
**🔐 Rôles, Permissions & Voûtes**

- Matrice Rôles × Permissions (Admin, Assistant, Technicien, Stagiaire)
- Architecture des Voûtes (Tout, Mes Données, Lecture Seule)
- Row-Level Security (RLS) avec Supabase
- Politiques SQL par rôle
- Protection codes d'accès

**⚠️ RÈGLE CRITIQUE:**
> RLS doit être activé AVANT mise en production! Test avec utilisateurs réels obligatoire.

**Quand le lire:**
- Avant d'implémenter une nouvelle fonctionnalité accessible selon rôle
- Avant d'activer RLS en production
- Pour comprendre qui voit quoi
- Avant de créer une politique SQL

---

### 5. [GEOGRAPHY_LOGIC.md](GEOGRAPHY_LOGIC.md)
**🗺️ Mapping Codes Postaux → Quartiers**

- Dictionnaire 100+ codes postaux (Montréal, Laval, Rive-Sud, Rive-Nord)
- Fonctions `get_neighborhood_from_postal_code()` et `format_neighborhood_display()`
- Optimisation tournées (grouper RV par quartier)
- Enrichissement données V5 → V6

**⚠️ RAPPEL:**
> Toujours fournir `fallback_city` pour codes inconnus!

**Quand le lire:**
- Avant d'afficher une adresse/localisation
- Avant de créer un rapport par région
- Pour comprendre le mapping postal
- Avant d'enrichir les données géographiques

---

### 6. [UI_UX_STANDARDS.md](UI_UX_STANDARDS.md)
**🎨 Standards Interface & Design**

- Principe Progressive Disclosure (Cards → Drawer → Modal)
- Mobile-First Design (thumb-friendly)
- Design System (couleurs, typo, espacements)
- Composants standards (AppointmentCard, Drawer, etc.)
- Accessibilité (ARIA, keyboard nav, contraste)

**⚠️ RAPPEL CRITIQUE:**
> Mobile-first, Progressive Disclosure, Touch-Friendly (≥ 48px)!

**Quand le lire:**
- Avant de créer un nouveau composant UI
- Avant de modifier un composant existant
- Pour comprendre les standards visuels
- Avant d'implémenter une nouvelle fonctionnalité frontend

---

## 📚 Comment Utiliser Ces Documents

### Stratégie de Lecture

**1. Première fois (Onboarding):**
Lire dans cet ordre:
1. ARCHITECTURE_MAP.md (vue d'ensemble)
2. DATA_DICTIONARY.md (données)
3. SYNC_STRATEGY.md (imports)
4. USER_ROLES_SECURITY.md (sécurité)
5. GEOGRAPHY_LOGIC.md (géo)
6. UI_UX_STANDARDS.md (UI)

**2. Travail quotidien (Référence):**
- Ouvrir le document pertinent selon la tâche
- Chercher la section spécifique (Ctrl+F)
- Suivre les exemples de code

**3. Avant une tâche importante:**
- Relire les sections "RÈGLES CRITIQUES"
- Vérifier les "DO/DON'T"
- Consulter les exemples

### Mise à Jour Incrémentale

**Règle d'or:**
> Mettre à jour le document IMMÉDIATEMENT après une décision architecturale.

**Workflow:**
```bash
# 1. Faire un changement dans le code
git add core/reconciler/client_reconciler.py

# 2. IMMÉDIATEMENT mettre à jour la documentation
# Ouvrir: assistant-v6/docs/ARCHITECTURE_MAP.md
# Ajouter: "ClientReconciler gère aussi les adresses secondaires"

# 3. Commit ensemble
git add assistant-v6/docs/ARCHITECTURE_MAP.md
git commit -m "feat(reconciler): Support adresses secondaires + doc"
```

**Ne JAMAIS:**
- Réécrire tout le document
- Supprimer l'historique V5 Current vs V6 Target
- Changer sans justification

---

## 🔍 Index par Sujet

### Architecture & Code
- Structure dossiers → [ARCHITECTURE_MAP.md](ARCHITECTURE_MAP.md)
- Patterns de design → [ARCHITECTURE_MAP.md](ARCHITECTURE_MAP.md)
- Reconciler → [ARCHITECTURE_MAP.md](ARCHITECTURE_MAP.md) + [DATA_DICTIONARY.md](DATA_DICTIONARY.md)

### Données & Base de Données
- Schéma tables → [DATA_DICTIONARY.md](DATA_DICTIONARY.md)
- Relations entités → [DATA_DICTIONARY.md](DATA_DICTIONARY.md)
- Requêtes SQL → [DATA_DICTIONARY.md](DATA_DICTIONARY.md)
- Validation données → [DATA_DICTIONARY.md](DATA_DICTIONARY.md)

### Synchronisation & Import
- **Timezone UTC** → [SYNC_STRATEGY.md](SYNC_STRATEGY.md) ⚠️ CRITIQUE
- 2-stage sync → [SYNC_STRATEGY.md](SYNC_STRATEGY.md)
- Gestion erreurs → [SYNC_STRATEGY.md](SYNC_STRATEGY.md)
- Staging tables → [SYNC_STRATEGY.md](SYNC_STRATEGY.md)

### Sécurité & Permissions
- Rôles utilisateurs → [USER_ROLES_SECURITY.md](USER_ROLES_SECURITY.md)
- RLS (Row-Level Security) → [USER_ROLES_SECURITY.md](USER_ROLES_SECURITY.md)
- Voûtes → [USER_ROLES_SECURITY.md](USER_ROLES_SECURITY.md)
- Codes d'accès → [USER_ROLES_SECURITY.md](USER_ROLES_SECURITY.md) + [DATA_DICTIONARY.md](DATA_DICTIONARY.md)

### Géographie & Localisation
- Mapping codes postaux → [GEOGRAPHY_LOGIC.md](GEOGRAPHY_LOGIC.md)
- Quartiers Montréal → [GEOGRAPHY_LOGIC.md](GEOGRAPHY_LOGIC.md)
- Optimisation tournées → [GEOGRAPHY_LOGIC.md](GEOGRAPHY_LOGIC.md)

### Interface Utilisateur
- Progressive Disclosure → [UI_UX_STANDARDS.md](UI_UX_STANDARDS.md)
- Mobile-First → [UI_UX_STANDARDS.md](UI_UX_STANDARDS.md)
- Design System → [UI_UX_STANDARDS.md](UI_UX_STANDARDS.md)
- Composants → [UI_UX_STANDARDS.md](UI_UX_STANDARDS.md)
- Accessibilité → [UI_UX_STANDARDS.md](UI_UX_STANDARDS.md)

---

## 🚨 Règles Critiques (Top 5)

Ces règles sont **NON-NÉGOCIABLES** et apparaissent dans plusieurs documents:

### 1. Timezone UTC (SYNC_STRATEGY.md)
```python
# ✅ BON - Stockage UTC pur
appointment_time = "12:00:00"  # UTC

# ❌ MAUVAIS - Conversion à l'import
appointment_time = "07:00:00"  # Montréal (FAUX!)
```

### 2. Codes d'Accès → Locations (DATA_DICTIONARY.md)
```python
# ✅ BON
location.access_code = "1234#"

# ❌ MAUVAIS
client.access_code = "1234#"  # Client peut avoir 10 adresses!
```

### 3. RLS Activé en Production (USER_ROLES_SECURITY.md)
```sql
-- ✅ BON
ALTER TABLE gazelle_appointments ENABLE ROW LEVEL SECURITY;

-- ❌ DANGEREUX (jamais en production!)
ALTER TABLE gazelle_appointments DISABLE ROW LEVEL SECURITY;
```

### 4. Fallback Géographique (GEOGRAPHY_LOGIC.md)
```python
# ✅ BON
neighborhood = get_neighborhood_from_postal_code(postal, city)

# ❌ MAUVAIS (perd l'info si code inconnu)
neighborhood = mapping.get(postal, "")
```

### 5. Mobile-First UI (UI_UX_STANDARDS.md)
```tsx
// ✅ BON
<Button sx={{ minHeight: 48, minWidth: 48 }} />

// ❌ MAUVAIS (trop petit au doigt)
<Button sx={{ height: 32 }} />
```

---

## 📊 Checklist Avant Implémentation

Avant de commencer une nouvelle tâche V6:

- [ ] J'ai lu le document pilier pertinent
- [ ] J'ai vérifié les sections "DO/DON'T"
- [ ] J'ai consulté les exemples de code
- [ ] Je comprends comment mettre à jour la doc après
- [ ] J'ai vérifié les règles critiques

---

## 🔗 Documents Connexes (V5)

Ces documents V5 restent pertinents pour contexte:

- `/docs/DISTINCTION_CLIENT_CONTACT.md` - Spécification Contact vs Client
- `/docs/TIMEZONE_SOLUTION_FINALE.md` - Détails timezone (source pour SYNC_STRATEGY.md)
- `/GAZELLE_DATA_DICTIONARY.md` - Schéma source Gazelle (référence)
- `api/chat/geo_mapping.py` - Implémentation V5 du mapping géographique

**Ne PAS modifier ces fichiers V5, utiliser les docs V6 à la place.**

---

## 📝 Contribuer à la Documentation

### Ajouter une Nouvelle Décision

1. Identifier le document pilier concerné
2. Trouver la section appropriée (ou en créer une)
3. Ajouter:
   - **Contexte:** Pourquoi cette décision?
   - **Solution:** Quelle approche?
   - **Exemple:** Code concret
   - **Règle:** DO/DON'T
4. Mettre à jour la date de "Dernière mise à jour"
5. Commit avec message clair

### Signaler une Incohérence

Si vous trouvez une contradiction entre documents:

1. Créer un issue GitHub
2. Mentionner les 2 documents
3. Proposer une résolution
4. Attendre validation avant modifier

---

**Version:** 1.0
**Auteur:** Assistant Gazelle Team
**Prochaine révision:** Après Phase 1 V6 (implémentation Reconciler)

---

## 🎓 Pour Aller Plus Loin

### Lectures Recommandées

**Architecture:**
- [Clean Architecture (Robert C. Martin)](https://blog.cleancoder.com/uncle-bob/2012/08/13/the-clean-architecture.html)
- [Repository Pattern](https://martinfowler.com/eaaCatalog/repository.html)

**Sécurité:**
- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [Supabase RLS Guide](https://supabase.com/docs/guides/auth/row-level-security)

**UX:**
- [Material Design Guidelines](https://m3.material.io/)
- [Mobile-First Design](https://www.lukew.com/ff/entry.asp?933)

---

**Bon code! 🎵**
