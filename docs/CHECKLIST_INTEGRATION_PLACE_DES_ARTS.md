# Checklist: Intégration Place des Arts

## Phase 1: Analyse (À faire dans le prochain chat)

- [ ] Identifier la source de données actuelle
- [ ] Lister toutes les entités/tables
- [ ] Documenter les relations entre entités
- [ ] Identifier les utilisateurs et leurs besoins
- [ ] Lister les fonctionnalités critiques

## Phase 2: Conception

- [ ] Créer le schéma Supabase pour Place des Arts
- [ ] Définir les RLS policies
- [ ] Concevoir les API endpoints
- [ ] Planifier l'interface utilisateur
- [ ] Décider de la stratégie de migration

## Phase 3: Implémentation

### Backend
- [ ] Créer les tables Supabase
- [ ] Implémenter les endpoints API
- [ ] Configurer RLS
- [ ] Créer script de migration des données
- [ ] Tests API

### Frontend
- [ ] Créer composants React
- [ ] Intégrer avec API
- [ ] Ajouter au dashboard existant
- [ ] Tests interface utilisateur

### Synchronisation
- [ ] Script import données initiales
- [ ] Synchronisation automatique (si nécessaire)
- [ ] Validation des données

## Phase 4: Migration

- [ ] Backup des données existantes
- [ ] Import test (environnement de test)
- [ ] Validation import test
- [ ] Import production
- [ ] Validation production
- [ ] Formation utilisateurs

## Phase 5: Déploiement

- [ ] Deploy backend sur Render
- [ ] Deploy frontend sur GitHub Pages
- [ ] Tests end-to-end
- [ ] Documentation utilisateur
- [ ] Go-live

## Notes importantes

### Données actuelles Supabase (déjà en place)
- ✅ 1000 clients Gazelle
- ✅ 988 pianos Gazelle
- ✅ 582 rendez-vous Gazelle
- ⏳ Timeline entries (en attente service_role key)

### Points d'attention
- ⚠️ Ne pas casser l'existant Gazelle
- ⚠️ Prévoir rollback si problème
- ⚠️ Tester avant production
- ⚠️ Backup obligatoire avant migration

### Ressources disponibles
- Infrastructure Supabase prête
- Backend API FastAPI déployé
- Frontend React déployé
- Scripts de synchronisation existants
