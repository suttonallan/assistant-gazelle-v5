# 🏛️ Alertes Maintenance Institutionnelle

## Vue d'ensemble

Carte spéciale de dashboard qui affiche les alertes de maintenance (Housse, Alimentation/PL, Réservoir) **uniquement pour les 3 clients institutionnels prioritaires**:
- Vincent d'Indy
- Place des Arts
- Orford

## ✨ Fonctionnalités

### Affichage visuel
- **Clignotement rouge**: La carte clignote avec un fond rouge si des alertes non résolues sont détectées
- **Badges de couleur**:
  - 🛡️ Housse (orange)
  - 🔌 Alimentation/PL (rouge)
  - 💧 Réservoir (bleu)
- **Statistiques**: Total, Non résolues, Résolues
- **Auto-refresh**: Actualisation automatique toutes les 5 minutes

### Détails des alertes
- Nom du client
- Type d'alerte (housse, alimentation, réservoir)
- Description de l'alerte
- Information du piano (marque, modèle)
- Date d'observation
- Statut (résolu/non résolu)

### Interactions
- Bouton de rafraîchissement manuel
- Section collapsible pour les alertes résolues
- Horodatage de dernière mise à jour

## 🔧 Implémentation technique

### Backend - API Route
**Fichier**: `api/humidity_alerts_routes.py`

**Endpoints**:
```python
GET /api/humidity-alerts/institutional
# Retourne les alertes pour Vincent d'Indy, Place des Arts, Orford uniquement

GET /api/humidity-alerts/all?limit=100&resolved=false
# Retourne toutes les alertes avec filtres

GET /api/humidity-alerts/stats
# Statistiques globales incluant institutional_unresolved
```

**Format de réponse** (`/institutional`):
```json
{
  "alerts": [
    {
      "alert_type": "housse",
      "client_name": "Vincent d'Indy",
      "piano_make": "Steinway",
      "piano_model": "B",
      "description": "Housse enlevée détecté",
      "is_resolved": false,
      "observed_at": "2026-01-07T10:30:00Z"
    }
  ],
  "stats": {
    "total": 5,
    "unresolved": 2,
    "resolved": 3
  }
}
```

### Frontend - React Component
**Fichier**: `frontend/src/components/MaintenanceAlertsCard.jsx`

**Features**:
- Functional component avec hooks (useState, useEffect)
- Fetch depuis `/api/humidity-alerts/institutional`
- Animations CSS personnalisées:
  ```css
  @keyframes pulse-slow {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.8; }
  }
  ```
- Tailwind CSS pour le styling responsive

### Intégration Dashboard
**Fichier**: `frontend/src/components/InventaireDashboard.jsx`

**Modifications**:
1. Import du composant MaintenanceAlertsCard
2. Ajout de l'onglet "🚨 Alertes Maintenance" (admin uniquement)
3. Positionné en premier onglet pour visibilité maximale
4. Border rouge pour l'onglet actif (au lieu de bleu)

```jsx
{activeTab === 'alertes' && currentUserIsAdmin && (
  <div>
    <MaintenanceAlertsCard />
  </div>
)}
```

## 🎨 Style et UX

### États visuels
1. **Pas d'alertes**:
   - Fond blanc
   - Icône verte avec checkmark
   - Message rassurant

2. **Alertes non résolues**:
   - Fond rouge clignotant (`bg-red-50`)
   - Border rouge épaisse (`border-2 border-red-500`)
   - Animation pulse lente (2s)
   - Icône d'alerte avec bounce

3. **Alertes résolues**:
   - Section collapsible
   - Fond vert pâle
   - Border verte

### Responsive
- Design adaptatif pour mobile et desktop
- Grille flexible pour les statistiques
- Scroll automatique pour listes longues

## 🔐 Sécurité et Permissions

- **Visibilité**: Admin uniquement (`currentUserIsAdmin`)
- **Données**: Filtrées côté backend (pas de trust frontend)
- **API**: Utilise `SupabaseStorage` avec clés sécurisées

## 📊 Source de données

Les alertes proviennent du système de scan automatisé:
- **Table Supabase**: `humidity_alerts_active` (vue)
- **Scan**: 4x par jour via GitHub Actions
- **Détection**: Pattern matching + AI (OpenAI GPT-4o-mini)
- **Keywords**: 28 mots-clés problèmes + 23 mots-clés résolution

## 🚀 Déploiement

### Backend
Déjà déployé - Routes enregistrées dans `api/main.py`:
```python
# IMPORTANT: humidity_alerts_router AVANT institutions_router
app.include_router(humidity_alerts_router)
app.include_router(humidity_alerts_router, prefix="/api")
```

### Frontend
Déjà intégré dans InventaireDashboard:
- Accessible via onglet "Alertes Maintenance"
- Visible uniquement pour admins (Louise, Allan)

## ✅ Tests

### Backend
```bash
# Test endpoint institutional
curl http://localhost:8000/api/humidity-alerts/institutional

# Test statistiques
curl http://localhost:8000/api/humidity-alerts/stats

# Test all alerts
curl 'http://localhost:8000/api/humidity-alerts/all?limit=10'
```

### Frontend
1. Se connecter en tant qu'admin (Louise PIN 6343 ou Allan PIN 1234)
2. Aller dans Dashboard Inventaire
3. Cliquer sur l'onglet "🚨 Alertes Maintenance"
4. Vérifier:
   - Affichage correct
   - Bouton refresh fonctionne
   - Pas d'erreurs console

## 📈 Utilisation future

Quand le scan détecte une alerte pour Vincent d'Indy, Place des Arts ou Orford:
1. L'alerte est enregistrée dans `humidity_alerts` (Supabase)
2. Le système envoie notification Slack (Louise + Nicolas)
3. La carte dashboard clignote en rouge
4. Louise/Allan peuvent voir les détails dans l'onglet Alertes
5. Une fois le problème résolu, l'alerte passe en "résolue" (collapsible)

## 🔗 Fichiers modifiés/créés

### Nouveau
- `api/humidity_alerts_routes.py` - API endpoints
- `frontend/src/components/MaintenanceAlertsCard.jsx` - Composant React
- `docs/ALERTES_MAINTENANCE_INSTITUTIONNELLE.md` - Cette documentation

### Modifié
- `api/main.py` - Enregistrement des routes
- `frontend/src/components/InventaireDashboard.jsx` - Intégration de la carte

## 🎯 Prochaines étapes (optionnel)

1. **Notification push**: Badge sur l'onglet avec nombre d'alertes
2. **Historique**: Graphique des alertes dans le temps
3. **Export**: Télécharger rapport PDF/Excel des alertes
4. **Mobile**: Version optimisée pour téléphone
5. **Sons**: Alerte sonore optionnelle si nouvelle alerte critique
