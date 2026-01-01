# Diagnostic: Page Blanche Vincent d'Indy

**Date:** 2025-12-30
**Symptôme:** Page blanche lors de la sélection de Vincent d'Indy

---

## Tests Effectués

### 1. Test API Backend ✅
```bash
curl http://localhost:8000/vincent-dindy/pianos
```

**Résultat:** ✅ API fonctionne parfaitement
- Retourne 94 pianos
- Structure JSON valide
- Tous les champs requis présents: `gazelleId`, `dernierAccord`, `isInCsv`, etc.

**Exemple de piano retourné:**
```json
{
  "id": "191111",
  "gazelleId": "ins_wbXNVWqrqwwf1UZ9",
  "local": "VD219 salle Marie-Stéphane",
  "piano": "Steinway",
  "modele": "D",
  "serie": "191111",
  "type": "G",
  "dernierAccord": "2025-12-09",
  "prochainAccord": "2026-01-09",
  "status": "normal",
  "isInCsv": true,
  "gazelleStatus": "ACTIVE"
}
```

### 2. Frontend Dev Server ✅
```bash
cd frontend && npm run dev
```

**Résultat:** ✅ Serveur démarre sur http://localhost:5173

---

## Analyse du Code Frontend

### App.jsx - Routing Logic

**Fichier:** `frontend/src/App.jsx`

**Ligne 268-275:** Bouton "Pianos" (admin seulement)
```javascript
<button
  onClick={() => setCurrentView('pianos')}
  className={...}
>
  🎹 Pianos
</button>
```

**Ligne 174:** Rendu par défaut → VincentDIndyDashboard
```javascript
} else {
  return <VincentDIndyDashboard currentUser={effectiveUser} />
}
```

**Conclusion:** Lorsque `currentView === 'pianos'`, le composant VincentDIndyDashboard est censé être rendu.

---

## Hypothèses de la Cause

### Hypothèse 1: Erreur JavaScript dans le composant ❓
**Probabilité:** HAUTE

**Raison:** L'API fonctionne, mais le frontend affiche une page blanche. Cela suggère une erreur JavaScript qui empêche le rendu du composant.

**Vérification nécessaire:**
1. Ouvrir la Console du navigateur (F12)
2. Sélectionner "Vincent d'Indy"
3. Chercher les erreurs JavaScript rouges

**Erreurs possibles:**
- `TypeError: Cannot read property 'X' of undefined`
- Problème avec les nouveaux champs: `modele`, `isInCsv`, `gazelleStatus`
- Problème avec `type` (était "D"/"G" avant, maintenant "GRAND"/"UPRIGHT" dans Gazelle)

### Hypothèse 2: Problème de compatibilité des données ❓
**Probabilité:** MOYENNE

**Raison:** Le composant VincentDIndyDashboard s'attend peut-être à une structure de données différente.

**Champs potentiellement problématiques:**
- `piano.modele` (nouveau champ ajouté dans la migration V6)
- `piano.type` (transformation "GRAND" → "G" dans l'API, mais peut-être problème)
- `piano.isInCsv` (nouveau champ booléen)
- `piano.gazelleStatus` (nouveau champ)

**Vérification:**
Chercher dans VincentDIndyDashboard.jsx les accès à des propriétés qui pourraient causer `undefined`:
```javascript
// Exemple de code problématique:
piano.someField.toUpperCase()  // Si someField est undefined → CRASH
```

### Hypothèse 3: Erreur CORS ou Réseau ❓
**Probabilité:** FAIBLE

**Raison:** L'API est accessible localement via curl.

**Vérification:**
- Console réseau (Network tab) pour voir si la requête vers `/vincent-dindy/pianos` aboutit
- Chercher des erreurs CORS (Cross-Origin Resource Sharing)

---

## Prochaines Étapes

### Étape 1: Console du Navigateur (PRIORITAIRE)
```
1. Ouvrir http://localhost:5173 dans le navigateur
2. Ouvrir les DevTools (F12 ou Cmd+Option+I)
3. Aller dans l'onglet Console
4. Sélectionner "Vincent d'Indy" dans l'interface
5. Noter toute erreur JavaScript affichée en rouge
```

### Étape 2: Vérifier l'Appel API
```
1. Dans DevTools, aller dans l'onglet Network
2. Sélectionner "Vincent d'Indy"
3. Chercher la requête vers `/vincent-dindy/pianos`
4. Vérifier:
   - Status code (doit être 200)
   - Response (doit être JSON valide)
   - Erreurs CORS
```

### Étape 3: Ajouter Logs de Debug
Si les étapes 1-2 ne révèlent rien, modifier temporairement VincentDIndyDashboard.jsx:

```javascript
// Dans loadPianosFromAPI(), après ligne 64
console.log('✅ Données reçues:', data);
console.log('📊 Nombre de pianos:', data.count || data.pianos?.length || 0);
console.log('🔍 Premier piano:', data.pianos?.[0]); // NOUVEAU
```

---

## Fichiers Impliqués

| Fichier | Description |
|---------|-------------|
| `frontend/src/App.jsx` | Routing principal, détermine quel composant afficher |
| `frontend/src/components/VincentDIndyDashboard.jsx` | Composant du dashboard Vincent d'Indy |
| `frontend/src/api/vincentDIndyApi.js` | Client API pour `/vincent-dindy/*` |
| `api/vincent_dindy.py` | Backend API (✅ fonctionne) |

---

## Actions à Faire

- [ ] Ouvrir Console du navigateur
- [ ] Noter les erreurs JavaScript
- [ ] Vérifier l'onglet Network
- [ ] Partager les erreurs trouvées

