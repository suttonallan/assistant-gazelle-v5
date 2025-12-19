# Guide: Synchronisation PC → Supabase (SANS RISQUE)

## 📋 Ce que fait le script

Le script `scripts/pc_sync_dual_write.py` synchronise les données Gazelle vers Supabase **EN PLUS** de SQL Server (pas à la place).

**Aucune modification aux processus existants** - c'est juste une copie supplémentaire des données.

## ✅ Installation sur le PC Windows

### Étape 1: Copier le script

Le script se trouve dans `scripts/pc_sync_dual_write.py` de ce projet.

Copiez-le sur votre PC Windows dans le même emplacement.

### Étape 2: Ajouter les credentials Supabase

Ajoutez ces lignes dans le fichier `.env` à la racine du projet sur le PC:

```env
# Supabase (pour synchro cloud)
SUPABASE_URL=https://beblgzvmjqkcillmcavk.supabase.co
SUPABASE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImJlYmxnenZtanFrY2lsbG1jYXZrIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTk5MDA2OTMsImV4cCI6MjA3NTQ3NjY5M30.h8DPImDps9pfRLcyYlXRRbYIYAT7cm_3ej4WDGhJVDc
```

### Étape 3: Test manuel (RECOMMANDÉ)

**Avant d'automatiser**, testez une fois manuellement:

```bash
python scripts/pc_sync_dual_write.py
```

Vous verrez:
- ✅ Nombre de clients synchronisés
- ✅ Nombre de pianos synchronisés
- ✅ Nombre de rendez-vous synchronisés
- ✅ Nombre de timeline entries synchronisées

**Si tout fonctionne**, vous pouvez automatiser.

### Étape 4: Automatisation (OPTIONNEL)

Pour synchroniser automatiquement chaque nuit à 3h du matin:

1. Ouvrez **Planificateur de tâches Windows** (Task Scheduler)
2. Créer une tâche de base:
   - **Nom**: "Sync Gazelle vers Supabase"
   - **Déclencheur**: Quotidien à 3h00
   - **Action**: Démarrer un programme
   - **Programme**: `python`
   - **Arguments**: `scripts/pc_sync_dual_write.py`
   - **Démarrer dans**: `C:\chemin\vers\assistant-gazelle-v5`

## 🔒 Garanties de sécurité

- ✅ **SQL Server reste intact** - Aucune modification
- ✅ **Scripts actuels continuent de fonctionner** comme avant
- ✅ **Supabase = copie additionnelle** - Pas de remplacement
- ✅ **En cas d'erreur Supabase**, le script continue et écrit dans SQL Server normalement

## ❓ Dépannage

**Si le script échoue:**
- Vérifiez que `SUPABASE_URL` et `SUPABASE_KEY` sont dans le `.env`
- Vérifiez que `python-dotenv` et `requests` sont installés: `pip install python-dotenv requests`
- Lancez en mode debug pour voir les erreurs

**Le script n'écrit pas dans Supabase:**
- Vérifiez la connexion internet
- Testez l'accès à Supabase: `curl https://beblgzvmjqkcillmcavk.supabase.co`

## 📊 Vérification après sync

Sur le Mac ou dans Supabase dashboard, vérifiez:

```sql
SELECT COUNT(*) FROM timeline_entries;
```

Si le nombre augmente, la synchronisation fonctionne! 🎉
