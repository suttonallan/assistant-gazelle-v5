# 🌐 Assistant Gazelle - Version Web

**Version :** Web (déployable)  
**Base de données :** SQLite (`data/gazelle_web.db`)  
**Status :** En développement

---

## 📋 Vue d'ensemble

Cette version web de l'Assistant Gazelle est conçue pour être déployable sur des plateformes cloud (Render, Railway, VPS) sans nécessiter SQL Server local ou ngrok/Remote Desktop.

**⚠️ IMPORTANT :** Cette version est en développement parallèle. La version V4 locale reste la version officielle de production jusqu'à validation complète.

---

## 🏗️ Structure

```
assistant-gazelle-web/
├── app/                    # Code backend
│   ├── sqlite_data_manager.py
│   ├── assistant_web.py
│   └── ...
├── config/                 # Configuration
├── data/                   # Base de données SQLite
│   └── gazelle_web.db
├── scripts/                # Scripts d'import
│   └── import_gazelle_to_sqlite.py
├── MIGRATION_PLAN.md       # Plan de migration détaillé
├── DEPLOYMENT.md          # Guide de déploiement (à venir)
├── README_WEB.md          # Ce fichier
└── run_web.py             # Point d'entrée
```

---

## 🚀 Utilisation

### Chemin correct

Le dossier `assistant-gazelle-web` est dans le projet parent :

```powershell
# Aller dans le projet parent d'abord
cd "C:\Allan Python projets\assistant-gazelle"

# Puis dans le dossier web
cd assistant-gazelle-web

# Exécuter le script d'import
python scripts\import_gazelle_to_sqlite.py
```

### Ou en une seule commande

```powershell
cd "C:\Allan Python projets\assistant-gazelle\assistant-gazelle-web"
python scripts\import_gazelle_to_sqlite.py
```

---

## 📝 Notes

- **Base de données :** SQLite (pas SQL Server)
- **Framework :** Flask (même que V4)
- **Endpoints :** Identiques à V4 (`/api/assistant`, etc.)
- **Frontend :** Réutilise `templates/assistant.html` sans modification

---

**Dernière mise à jour :** 2025-11-24
