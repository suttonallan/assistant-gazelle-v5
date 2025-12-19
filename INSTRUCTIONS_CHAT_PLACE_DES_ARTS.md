# Instructions pour le chat Place des Arts

## 📋 Contexte rapide

### Infrastructure v5 actuelle
- ✅ Supabase PostgreSQL cloud
- ✅ Backend FastAPI sur Render
- ✅ Frontend React sur GitHub Pages
- ✅ 1000 clients + 988 pianos + 582 RV synchronisés depuis Gazelle

### Fichiers préparés
1. **CONTEXTE_PLACE_DES_ARTS.md** - Vue d'ensemble complète
2. **CHECKLIST_INTEGRATION_PLACE_DES_ARTS.md** - Plan d'action détaillé
3. Ce fichier - Instructions pour démarrer

## 🎯 Objectif du chat

Intégrer le système Place des Arts dans l'infrastructure v5 existante.

## 💬 Comment démarrer le chat

### Prompt suggéré pour Allan

```
Bonjour! Je veux intégrer mon système de gestion Place des Arts dans
l'infrastructure v5 (Supabase + Render) qui est déjà en place.

Avant de commencer, lis ces fichiers pour comprendre le contexte:
- docs/CONTEXTE_PLACE_DES_ARTS.md
- docs/CHECKLIST_INTEGRATION_PLACE_DES_ARTS.md

Voici les informations sur mon système Place des Arts actuel:
[Décrire le système ici]

Ensuite, propose-moi un plan d'intégration.
```

## 📝 Informations à fournir à Claude

Pour que Claude puisse bien t'aider, prépare ces informations:

### 1. Système actuel
- Où sont les données? (SQL Server? Fichiers Excel? Autre?)
- Combien de tables/entités?
- Exemples de données (sans info sensible)

### 2. Utilisation
- Qui utilise le système?
- Depuis où? (PC local? Web?)
- Fréquence d'utilisation?

### 3. Fonctionnalités
- Que fait le système actuellement?
- Quels rapports génère-t-il?
- Y a-t-il des intégrations avec d'autres systèmes?

### 4. Besoins
- Que veux-tu améliorer?
- Accès depuis mobile/web nécessaire?
- Fonctionnalités manquantes à ajouter?

## 🔧 Outils disponibles

Claude aura accès à:
- ✅ Tous les fichiers du projet v5
- ✅ Connexion Supabase
- ✅ Scripts de migration existants
- ✅ Code du backend et frontend

## ⚠️ Points d'attention

### Ne pas casser l'existant
- Le système Gazelle doit continuer de fonctionner
- Les 1000 clients + pianos déjà synchronisés ne doivent pas être affectés

### Tester avant production
- Toujours tester sur tables de test
- Valider les migrations avant production

### Backup obligatoire
- Sauvegarder les données Place des Arts avant migration

## 📊 État actuel de Supabase

Tables déjà existantes:
- `gazelle_clients` (1000 enregistrements)
- `gazelle_pianos` (988 enregistrements)
- `gazelle_appointments` (582 enregistrements)
- `timeline_entries` (vide - en attente)
- `vincent_dindy_piano_updates` (modifications pianos)

Nouvelles tables Place des Arts seront ajoutées sans affecter les existantes.

## 🚀 Résultat attendu

À la fin du chat, tu devrais avoir:
1. ✅ Schéma de base de données pour Place des Arts
2. ✅ Plan de migration des données
3. ✅ API endpoints définis
4. ✅ Interface utilisateur conçue
5. ✅ Script de migration prêt

---

**Prêt à démarrer!** Lance le nouveau chat avec le prompt suggéré ci-dessus.
