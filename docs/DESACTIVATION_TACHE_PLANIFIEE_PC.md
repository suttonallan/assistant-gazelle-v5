# Désactivation de la Tâche Planifiée Windows - Import Daily Update

**Date:** 2025-12-25
**Raison:** Migration V4 → V5 - Le Mac prend le relais
**Objectif:** Laisser V5 sur Mac prouver qu'elle fait maintenant tout elle-même

---

## 🎯 TÂCHE À DÉSACTIVER

**Nom de la tâche:** `Import_daily_update`

**Ce qu'elle fait actuellement:**
- Importe les données Gazelle → SQL Server
- S'exécute quotidiennement (probablement le matin)
- Script: `c:\Allan Python projets\assistant-gazelle\scripts\Import_daily_update.py`

---

## 🛑 COMMENT LA DÉSACTIVER

### Option 1: Via l'interface graphique (Recommandé)

1. **Ouvrir le Planificateur de tâches Windows:**
   - Appuyer sur `Win + R`
   - Taper: `taskschd.msc`
   - Appuyer sur Entrée

2. **Trouver la tâche:**
   - Dans le panneau de gauche, naviguer dans l'arborescence
   - Chercher "Import_daily_update" ou similaire
   - (Peut être dans "Bibliothèque du Planificateur de tâches")

3. **Désactiver (pas supprimer!):**
   - Clic droit sur la tâche
   - Choisir **"Désactiver"** (PAS "Supprimer")
   - ✅ La tâche reste là mais ne s'exécutera plus

**Pourquoi désactiver et non supprimer?**
- Si V5 a un problème, on peut réactiver facilement
- On garde la configuration intacte
- Permet un rollback rapide si nécessaire

---

### Option 2: Via ligne de commande

```cmd
schtasks /change /tn "Import_daily_update" /disable
```

**Vérifier le statut:**
```cmd
schtasks /query /tn "Import_daily_update" /fo LIST
```

**Pour réactiver si besoin:**
```cmd
schtasks /change /tn "Import_daily_update" /enable
```

---

## ✅ VÉRIFICATION

Après désactivation, vérifier:

1. **La tâche est désactivée:**
   - Dans Planificateur de tâches
   - Statut: "Désactivé"

2. **V5 sur Mac fonctionne:**
   - Import Gazelle quotidien OK
   - Sync Supabase OK
   - Pas de données manquantes

---

## 📋 CHECKLIST AVANT DÉSACTIVATION

**Vérifier que V5 sur Mac fait TOUT:**

- [ ] Import Gazelle API → Supabase (clients, pianos, timeline)
- [ ] Sync quotidien automatique (APScheduler sur Render)
- [ ] Rapports Timeline Google Sheets fonctionnels
- [ ] Alertes humidité fonctionnelles
- [ ] Notifications Slack fonctionnelles
- [ ] Aucune donnée manquante vs V4

**Si tous les ✅ → OK pour désactiver la tâche PC**

---

## 🔄 ROLLBACK (Si problème avec V5)

Si V5 sur Mac ne fonctionne pas bien:

1. **Réactiver la tâche Windows:**
   ```cmd
   schtasks /change /tn "Import_daily_update" /enable
   ```

2. **Ou via interface graphique:**
   - Planificateur de tâches
   - Clic droit → "Activer"

3. **Vérifier que l'import reprend:**
   - Attendre la prochaine exécution planifiée
   - Ou lancer manuellement:
     ```cmd
     cd "c:\Allan Python projets\assistant-gazelle\scripts"
     python Import_daily_update.py
     ```

---

## 📅 PLAN DE MIGRATION

### Phase 1: Préparation (Fait ✅)
- ✅ V5 sur Mac déployée sur Render
- ✅ Sync Gazelle → Supabase fonctionnel
- ✅ Rapports Timeline générés

### Phase 2: Validation (En cours)
- [ ] Cursor Mac termine tous les imports
- [ ] Vérification que toutes les données sont présentes
- [ ] Test des rapports Google Sheets depuis Mac
- [ ] Test des alertes humidité depuis Mac

### Phase 3: Bascule (Prochaine étape)
- [ ] **Désactiver tâche planifiée PC** ← TU ES ICI
- [ ] Monitorer V5 pendant 1 semaine
- [ ] Comparer données V4 PC vs V5 Mac
- [ ] Valider avec les techniciens

### Phase 4: Décommissionnement PC (Futur)
- [ ] Arrêter serveur Flask V4 sur PC
- [ ] Garder SQL Server en lecture seule (backup)
- [ ] Archiver les scripts V4

---

## 🎯 RÉSULTAT ATTENDU

**Après désactivation:**
- ❌ PC ne fait plus d'import automatique
- ✅ Mac V5 fait TOUT (import + sync + rapports + alertes)
- ✅ Tâche PC reste disponible pour rollback si besoin

**Prochaine étape:**
- Monitorer V5 pendant quelques jours
- Si stable → Arrêter complètement V4 sur PC

---

## 💡 CONSEIL

**Ne pas se précipiter:**
1. Désactiver la tâche planifiée PC
2. Laisser tourner V5 seule pendant 3-7 jours
3. Vérifier quotidiennement que tout fonctionne
4. Si OK → Arrêter Flask V4
5. Si problème → Réactiver tâche PC

**Approche "Option 3" (Parallèle → V5 seule):**
- ✅ V4 et V5 tournaient en parallèle (terminé)
- ➡️ Maintenant: V5 seule (validation)
- 🔜 Ensuite: Décommissionnement V4

---

**Créé:** 2025-12-25
**Par:** Claude Code (Windows)
**Pour:** Migration progressive V4 → V5
