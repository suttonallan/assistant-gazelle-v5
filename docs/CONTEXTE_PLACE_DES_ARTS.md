# Contexte: Transition système Place des Arts

## 🎯 Objectif
Migrer/intégrer le système de gestion Place des Arts dans l'infrastructure v5 (Supabase + Render).

## 📊 État actuel du système

### Infrastructure v5 (Prête)
✅ **Supabase** - Base de données cloud PostgreSQL
✅ **Render** - Backend API FastAPI déployé
✅ **Frontend React** - Dashboard déployé sur GitHub Pages
✅ **Données synchronisées**:
- 1000 clients Gazelle
- 988 pianos
- 582 rendez-vous
- Timeline entries (en cours - bloqué par RLS)

### Connexions Supabase
- **URL**: `https://beblgzvmjqkcillmcavk.supabase.co`
- **Anon Key**: `eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImJlYmxnenZtanFrY2lsbG1jYXZrIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTk5MDA2OTMsImV4cCI6MjA3NTQ3NjY5M30.h8DPImDps9pfRLcyYlXRRbYIYAT7cm_3ej4WDGhJVDc`
- **Service Role Key**: À obtenir pour écriture sans RLS

## 🔍 Questions à clarifier dans le prochain chat

### 1. Système Place des Arts actuel
- Où sont stockées les données actuellement? (SQL Server local? Fichiers? Cloud?)
- Quelles sont les entités principales? (Clients, Contrats, Factures, Pianos, etc.)
- Y a-t-il une API existante?
- Accès depuis où? (PC Windows? Web? Mobile?)

### 2. Besoin d'intégration
- Remplacer complètement le système actuel ou intégration partielle?
- Les données Place des Arts doivent-elles être liées aux données Gazelle?
- Qui utilise ce système? (Allan seul? Équipe? Clients?)

### 3. Fonctionnalités requises
- Gestion de quoi exactement? (Inventaire? Maintenance? Location?)
- Rapports nécessaires?
- Accès temps réel requis?

## 📁 Structure actuelle du projet v5

```
assistant-gazelle-v5/
├── api/                    # Backend FastAPI
│   ├── main.py            # Point d'entrée API
│   ├── assistant.py       # Endpoints assistant chat
│   ├── inventaire.py      # Endpoints inventaire
│   └── admin.py           # Endpoints admin
├── core/                   # Modules core
│   ├── supabase_storage.py    # Client Supabase
│   └── gazelle_api_client.py  # Client Gazelle API
├── modules/
│   └── sync_gazelle/      # Synchronisation Gazelle→Supabase
├── frontend/              # React dashboard
├── scripts/               # Scripts utilitaires
└── docs/                  # Documentation
```

## 🎬 Prochaines étapes suggérées

1. **Analyser le système Place des Arts existant**
   - Schéma de base de données
   - Fonctionnalités actuelles
   - Points d'accès

2. **Concevoir l'architecture d'intégration**
   - Tables Supabase nécessaires
   - API endpoints requis
   - Interface utilisateur

3. **Plan de migration**
   - Import des données existantes
   - Tests de validation
   - Déploiement progressif

## 💡 Avantages de l'intégration v5

✅ **Accès cloud** - Données accessibles depuis n'importe où
✅ **Temps réel** - Synchronisation automatique
✅ **Sécurité** - RLS Supabase + authentification
✅ **Coûts** - Infrastructure déjà en place
✅ **Maintenance** - Tout centralisé dans un système

## 📝 Fichiers de référence

- [Guide sync PC→Supabase](./GUIDE_SYNC_PC_SUPABASE.md)
- [Migration Timeline](./SUPABASE_TIMELINE_MIGRATION.sql)
- [Script sync dual write](../scripts/pc_sync_dual_write.py)
- [État actuel v5](./ETAT_SESSION_ACTUELLE.md)

---

**Prêt pour le prochain chat!** 🚀

Commencez par décrire le système Place des Arts actuel et vos besoins d'intégration.
