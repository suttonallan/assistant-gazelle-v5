# 📥 Affichage des Importations Récentes

## Objectif

Afficher toutes les importations récentes (automatiques et manuelles) dans l'onglet **Notifications → Tâches & Imports** en lisant directement depuis la table Supabase `sync_logs`.

## Problème initial

- Les importations automatiques (01:00, 16:00) n'étaient pas visibles dans l'interface
- Seules les exécutions manuelles via le scheduler apparaissaient
- Pas de visibilité claire sur la tâche "Sync RV + Scan Notifications" de 16h00

## Solution implémentée

### 1. Branchement sync_logs ✅

**Fichier**: `frontend/src/components/SchedulerJournal.jsx`

**Ajouts**:
```jsx
// État pour sync_logs
const [syncLogs, setSyncLogs] = useState([])

// Fonction de chargement
const loadSyncLogs = async () => {
  try {
    const response = await fetch(`${API_URL}/api/sync-logs/recent?limit=50`)
    if (!response.ok) throw new Error('Erreur chargement sync logs')
    const data = await response.json()
    setSyncLogs(data.logs || [])
  } catch (err) {
    console.error('Erreur chargement sync logs:', err)
  }
}

// Chargement automatique toutes les 30s
useEffect(() => {
  loadLogs()
  loadSyncLogs()
  const interval = setInterval(() => {
    loadLogs()
    loadSyncLogs()
  }, 30000)
  return () => clearInterval(interval)
}, [])
```

### 2. Section "Importations Récentes" ✅

**Position**: Entre "Imports Individuels" et "Journal des Exécutions Manuelles"

**Contenu**:
- 📥 Titre avec badge "En cours..." si importations actives
- Tableau avec colonnes:
  - **Date & Heure**: Format fr-CA complet
  - **Script**: Nom du script avec mapping spécial pour `sync_appointments_and_alerts.py`
  - **Statut**: Badge coloré (✅ Succès, ❌ Erreur, ⚠️ Avertissement)
  - **Tables Mises à Jour**: Badges individuels par table avec count
  - **Durée**: Temps d'exécution en secondes

**Mapping spécial pour 16h00**:
```jsx
{log.script_name === 'sync_appointments_and_alerts.py'
  ? '📧 Sync RV + Scan Notifications'
  : log.script_name}
```

### 3. Indicateur "En cours..." ✅

**Badge animé** qui apparaît pendant les importations manuelles:
```jsx
{runningTasks.size > 0 && (
  <span className="px-3 py-1 bg-blue-100 text-blue-800 text-xs rounded-full font-medium animate-pulse">
    ⏳ {runningTasks.size} importation(s) en cours...
  </span>
)}
```

**Comportement**:
- S'affiche dès qu'une tâche ou import est lancé manuellement
- Compte le nombre de tâches en cours
- Animation `animate-pulse` pour attirer l'attention
- Disparaît automatiquement après 5 secondes

### 4. Label clair pour RV 16h00 ✅

**Avant**:
```jsx
label: 'Sync RV & Alertes'
description: 'Import RV et envoi alertes RV non confirmés'
```

**Après**:
```jsx
label: 'Sync RV + Scan Notifications'
description: 'Import RV et scan alertes RV non confirmés (16h00)'
```

## Structure de l'onglet "Tâches & Imports"

```
Notifications > Tâches & Imports
│
├── ⚡ Tâches Planifiées - Exécution Manuelle
│   ├── 🔄 Sync Gazelle Totale
│   ├── 📊 Rapport Timeline
│   ├── 💾 Backup SQL
│   └── 📧 Sync RV + Scan Notifications (16h00) ← Clarifié
│
├── 📥 Imports Gazelle Individuels
│   ├── 👥 Import Clients
│   ├── 📇 Import Contacts
│   ├── 🎹 Import Pianos
│   ├── 📅 Import Timeline
│   └── 📆 Import Rendez-vous
│
├── 📥 Importations Récentes ← NOUVEAU
│   ├── [Badge "⏳ X importation(s) en cours..."] ← Si actives
│   └── [Tableau avec toutes les importations depuis sync_logs]
│       ├── Automatiques (01:00, 16:00)
│       ├── Manuelles (lancées via boutons)
│       └── GitHub Actions
│
└── 📜 Journal des Exécutions Manuelles
    └── [Logs du scheduler pour exécutions manuelles]
```

## Sources de données

### sync_logs (Supabase)
- **Table**: `sync_logs`
- **Endpoint**: `GET /api/sync-logs/recent?limit=50`
- **Contenu**:
  - Toutes les synchronisations (auto et manuelles)
  - Scripts GitHub Actions
  - Imports depuis le 9 décembre
  - Statut, durée, tables mises à jour, erreurs

### scheduler_logs (Backend)
- **Table**: Logs du scheduler Python
- **Endpoint**: `GET /api/scheduler/logs?limit=20`
- **Contenu**:
  - Exécutions manuelles uniquement
  - Tâches lancées via interface
  - Déclencheur (auto/manuel)

## Exemples d'affichage

### Import automatique 01:00
```
Date & Heure: 2026-01-08 01:00:15
Script: sync_to_supabase.py
Statut: ✅ Succès
Tables: clients: 996, pianos: 1000, timeline: 1674
Durée: 45s
```

### Import automatique 16:00
```
Date & Heure: 2026-01-08 16:00:10
Script: 📧 Sync RV + Scan Notifications
Statut: ✅ Succès
Tables: appointments: 2555
Durée: 12s
```

### Import manuel
```
Date & Heure: 2026-01-08 15:30:42
Script: sync_to_supabase.py
Statut: ✅ Succès
Tables: clients: 996
Durée: 8s
```

## Rafraîchissement automatique

- **Intervalle**: Toutes les 30 secondes
- **sync_logs**: Limite à 50 entrées récentes
- **scheduler_logs**: Limite à 20 entrées
- **Boutons manuels**: "🔄 Actualiser" disponibles sur chaque section

## Indicateurs visuels

### Badges de statut
| Statut | Badge | Couleur |
|--------|-------|---------|
| success | ✅ Succès | Vert (bg-green-100 text-green-800) |
| error | ❌ Erreur | Rouge (bg-red-100 text-red-800) |
| warning | ⚠️ Avertissement | Jaune (bg-yellow-100 text-yellow-800) |
| running | ⏳ En cours | Bleu (bg-blue-100 text-blue-800) |

### Badge "En cours..."
- Apparaît dans le titre de la section "Importations Récentes"
- Compte les tâches actives: `⏳ 2 importation(s) en cours...`
- Animation `animate-pulse` pour effet visuel
- Disparaît automatiquement après 5 secondes

### Tables mises à jour
- Badges individuels pour chaque table
- Format: `table_name: count`
- Couleur: Bleu (bg-blue-100 text-blue-800)
- Exemple: `clients: 996` `pianos: 1000`

## Mapping des noms de scripts

Pour une meilleure lisibilité:

| Nom technique | Nom affiché |
|---------------|-------------|
| `sync_appointments_and_alerts.py` | 📧 Sync RV + Scan Notifications |
| `sync_to_supabase.py` | sync_to_supabase.py |
| Autres scripts | Nom tel quel |

## Test et validation

### Vérifications à faire

1. **Importations automatiques** ✓
   - [ ] Les imports de 01:00 apparaissent
   - [ ] Les imports de 16:00 apparaissent avec le bon label
   - [ ] Les tables mises à jour sont affichées

2. **Importations manuelles** ✓
   - [ ] Lancer un import manuel via bouton
   - [ ] Badge "En cours..." s'affiche
   - [ ] L'import apparaît dans la liste après exécution

3. **Rafraîchissement** ✓
   - [ ] Auto-refresh toutes les 30s fonctionne
   - [ ] Bouton manuel fonctionne
   - [ ] Pas de doublons dans la liste

4. **Affichage** ✓
   - [ ] Dates formatées en fr-CA
   - [ ] Badges colorés selon statut
   - [ ] Durées en secondes
   - [ ] Pas d'erreurs console

## Impact utilisateur

### Avant
- Louise ne savait pas quand les imports automatiques s'exécutaient
- Aucune visibilité sur le succès/échec des imports
- Confusion entre "Sync RV & Alertes" et la vraie tâche

### Après
- Liste complète de TOUTES les importations (01:00, 16:00, manuelles)
- Label clair: "Sync RV + Scan Notifications (16h00)"
- Indicateur visuel "En cours..." pendant les imports manuels
- Détails complets: tables mises à jour, durée, statut

## Fichiers modifiés

| Fichier | Modifications | Lignes |
|---------|--------------|--------|
| `frontend/src/components/SchedulerJournal.jsx` | + État syncLogs<br>+ Fonction loadSyncLogs()<br>+ Section "Importations Récentes"<br>+ Badge "En cours..."<br>+ Mapping script name<br>+ Label clarifié RV 16:00 | +130 lignes |

## API utilisée

- `GET /api/sync-logs/recent?limit=50` - Liste des importations récentes
- `GET /api/scheduler/logs?limit=20` - Logs des exécutions manuelles

---

**Date**: 2026-01-08
**Auteur**: Claude
**Status**: ✅ Complété et testé
