# Message pour Cursor - Tâche Immédiate

**Date:** 2025-12-17

## 🎯 Ce que tu dois faire MAINTENANT

Les commits de Claude Code ont été poussés vers GitHub. Le travail que tu avais commencé (clients cliquables) a été stashé temporairement.

### Étape 1: Restaurer ton travail en cours

```bash
git stash pop
```

Cela va restaurer les fichiers `ClickableMessage.jsx` et `ClientDetailsModal.jsx` que tu avais commencés.

### Étape 2: Suivre les instructions complètes

Ouvre et suis **EXACTEMENT** le fichier:
```
INSTRUCTIONS_CURSOR_FINALISER_CLIENTS_CLIQUABLES.md
```

Ce fichier contient:
- ✅ Le code complet pour `ClickableMessage.jsx`
- ✅ Le code complet pour `ClientDetailsModal.jsx`
- ✅ Les modifications à faire dans `AssistantWidget.jsx`
- ✅ L'endpoint backend `/assistant/client/{id}` à ajouter dans `api/assistant.py`
- ✅ Les tests à effectuer

### Étape 3: Ordre d'implémentation

1. **Frontend d'abord:**
   - Créer/corriger `frontend/src/components/ClickableMessage.jsx`
   - Créer/corriger `frontend/src/components/ClientDetailsModal.jsx`
   - Modifier `frontend/src/components/AssistantWidget.jsx` pour utiliser `ClickableMessage`

2. **Backend ensuite:**
   - Ajouter l'endpoint `@router.get("/client/{client_id}")` dans `api/assistant.py`
   - L'insérer après l'endpoint `/health` (vers la ligne 247)

3. **Tester:**
   - Backend déjà en cours d'exécution (port 8000)
   - Démarrer frontend: `cd frontend && npm run dev`
   - Taper dans le chat: `client michelle`
   - Vérifier que les noms sont cliquables (liens bleus)
   - Cliquer sur un nom → modal doit s'ouvrir avec détails

## ⚠️ Règles Importantes

1. **NE PAS over-engineer** - Utilise EXACTEMENT le code fourni dans les instructions
2. **NE PAS créer de documentation** non demandée
3. **NE PAS modifier** d'autres fichiers que ceux mentionnés
4. **Tester** avant de considérer la tâche terminée

## 📋 Checklist de Complétion

- [ ] `ClickableMessage.jsx` créé avec le code exact des instructions
- [ ] `ClientDetailsModal.jsx` créé avec le code exact des instructions
- [ ] `AssistantWidget.jsx` modifié pour utiliser `ClickableMessage`
- [ ] Endpoint `/assistant/client/{id}` ajouté dans `api/assistant.py`
- [ ] Testé: `client michelle` → noms cliquables → modal fonctionne
- [ ] Commit créé avec message descriptif

## 🔗 Fichiers de Référence

Si tu as besoin de contexte supplémentaire:
- `docs/ETAT_SESSION_ACTUELLE.md` - État complet du projet
- `.cursorrules` - Règles et conventions du projet

## 💡 En Cas de Problème

Si tu rencontres des erreurs:
1. Vérifie que le backend tourne sur port 8000
2. Vérifie que `VITE_API_URL` dans `.env.local` pointe vers `http://localhost:8000`
3. Consulte les logs backend pour comprendre les erreurs API

---

**Allan te remercie d'avance pour ton travail méticuleux!** 🙏
