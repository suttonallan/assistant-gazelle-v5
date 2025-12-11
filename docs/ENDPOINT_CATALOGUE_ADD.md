# Endpoint `/api/catalogue/add` - Guide d'Utilisation

## ✅ Statut

**Implémenté et prêt à l'emploi** avec validation Pydantic complète.

---

## 📍 Endpoint

```
POST /api/catalogue/add
```

---

## 🔒 Validation Pydantic

L'endpoint utilise **Pydantic** pour valider automatiquement toutes les données entrantes :

### Champs Requis
- `code_produit` (str, 1-50 caractères) - Code unique du produit
- `nom` (str, 1-200 caractères) - Nom du produit
- `categorie` (str, 1-100 caractères) - Catégorie du produit

### Champs Optionnels
- `description` (str, max 1000 caractères) - Description détaillée
- `unite_mesure` (str, max 20 caractères) - Unité de mesure (défaut: "unité")
- `prix_unitaire` (float ≥ 0) - Prix unitaire en dollars
- `fournisseur` (str, max 100 caractères) - Nom du fournisseur

### Validations Automatiques
- ✅ Types de données vérifiés
- ✅ Longueurs min/max respectées
- ✅ Prix positif si fourni
- ✅ Code produit normalisé en majuscules
- ✅ Champs vides rejetés

---

## 📝 Exemple de Requête

### cURL
```bash
curl -X POST "http://localhost:8000/api/catalogue/add" \
  -H "Content-Type: application/json" \
  -d '{
    "code_produit": "CORD-001",
    "nom": "Corde de piano #1",
    "categorie": "Cordes",
    "description": "Corde de piano standard pour piano droit",
    "unite_mesure": "unité",
    "prix_unitaire": 12.50,
    "fournisseur": "Fournisseur ABC"
  }'
```

### Python (requests)
```python
import requests

url = "http://localhost:8000/api/catalogue/add"
data = {
    "code_produit": "CORD-001",
    "nom": "Corde de piano #1",
    "categorie": "Cordes",
    "description": "Corde standard",
    "unite_mesure": "unité",
    "prix_unitaire": 12.50,
    "fournisseur": "Fournisseur ABC"
}

response = requests.post(url, json=data)
print(response.json())
```

### JavaScript (fetch)
```javascript
const response = await fetch('http://localhost:8000/api/catalogue/add', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({
    code_produit: 'CORD-001',
    nom: 'Corde de piano #1',
    categorie: 'Cordes',
    description: 'Corde standard',
    unite_mesure: 'unité',
    prix_unitaire: 12.50,
    fournisseur: 'Fournisseur ABC'
  })
});

const result = await response.json();
console.log(result);
```

---

## ✅ Réponse en Cas de Succès

**Status Code**: `200 OK`

```json
{
  "success": true,
  "message": "Produit CORD-001 ajouté au catalogue",
  "produit": {
    "code_produit": "CORD-001",
    "nom": "Corde de piano #1",
    "categorie": "Cordes",
    "description": "Corde de piano standard pour piano droit",
    "unite_mesure": "unité",
    "prix_unitaire": 12.50,
    "fournisseur": "Fournisseur ABC",
    "updated_at": "2024-01-15T10:30:00"
  }
}
```

---

## ❌ Réponses d'Erreur

### 422 - Validation Pydantic Échouée

**Exemple**: Code produit manquant
```json
{
  "detail": [
    {
      "type": "missing",
      "loc": ["body", "code_produit"],
      "msg": "Field required",
      "input": {}
    }
  ]
}
```

**Exemple**: Prix négatif
```json
{
  "detail": [
    {
      "type": "greater_than_equal",
      "loc": ["body", "prix_unitaire"],
      "msg": "Input should be greater than or equal to 0",
      "input": -5.0
    }
  ]
}
```

### 500 - Erreur Serveur

**Exemple**: Configuration Supabase manquante
```json
{
  "detail": "Configuration manquante: SUPABASE_URL et SUPABASE_KEY requis."
}
```

**Exemple**: Erreur de base de données
```json
{
  "detail": "Échec de l'ajout au catalogue. Vérifiez les logs du serveur."
}
```

---

## 🔍 Documentation Interactive

Une fois le serveur démarré, accédez à la documentation interactive :

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

Vous pourrez tester l'endpoint directement depuis le navigateur !

---

## 🚀 Démarrage du Serveur

```bash
# Depuis la racine du projet
python -m uvicorn api.main:app --reload --port 8000

# Ou directement
python api/main.py
```

---

## 📚 Endpoints Similaires

- `POST /inventaire/catalogue` - Même fonctionnalité, chemin différent
- `GET /api/catalogue` - Liste les produits du catalogue
- `GET /inventaire/catalogue` - Liste avec filtres avancés

---

## 🎯 Avantages de la Validation Pydantic

1. **Sécurité** - Rejette automatiquement les données invalides
2. **Documentation** - Schémas JSON automatiques dans Swagger
3. **Performance** - Validation rapide côté serveur
4. **Type Safety** - Types Python garantis dans le code
5. **Messages d'erreur clairs** - Indique exactement ce qui ne va pas

---

## 🔄 Mode UPSERT

L'endpoint utilise le mode **UPSERT** :
- Si le produit existe déjà (même `code_produit`), il sera **mis à jour**
- Si le produit n'existe pas, il sera **créé**

Cela évite les erreurs de doublons et permet de mettre à jour facilement les produits existants.
