# 💻 Commandes PowerShell pour Windows

**⚠️ IMPORTANT: Copiez-collez UNIQUEMENT les commandes, pas le formatage markdown!**

---

## 🔍 Vérifier le Nombre de Produits Importés

### Commande Simple (Recommandée)

Copiez-collez cette commande dans PowerShell:

```
$r = Invoke-RestMethod "http://localhost:8000/inventaire/catalogue"; Write-Host "Produits: $($r.count)"
```

### Alternative avec Python

```
curl http://localhost:8000/inventaire/catalogue | python -c "import sys, json; print('Produits:', json.load(sys.stdin)['count'])"
```

**Note:** Sur Windows, c'est `python` (pas `python3`)

### Voir le JSON Complet

```
curl http://localhost:8000/inventaire/catalogue
```

---

## ✅ Vérifier que le Backend Fonctionne

```powershell
curl http://localhost:8000/health
```

**Résultat attendu:**
```json
{"status":"healthy"}
```

---

## 📊 Vérifier les Pianos

```powershell
$response = Invoke-RestMethod -Uri "http://localhost:8000/vincent-dindy/pianos"
Write-Host "Nombre de pianos: $($response.count)"
```

---

## 🔍 Vérifier un Produit Spécifique

```powershell
$response = Invoke-RestMethod -Uri "http://localhost:8000/inventaire/catalogue?categorie=Cordes"
Write-Host "Cordes: $($response.count)"
```

---

## 📋 Commandes Utiles

### Vérifier les Variables d'Environnement

```powershell
# Vérifier SUPABASE_URL
$env:SUPABASE_URL

# Vérifier SUPABASE_KEY (affiche les 30 premiers caractères)
$env:SUPABASE_KEY.Substring(0, [Math]::Min(30, $env:SUPABASE_KEY.Length))
```

### Tester la Connexion Supabase

```powershell
cd "C:\Allan Python projets\assistant-gazelle\assistant-gazelle-v5"
python scripts/test_supabase_connection.py
```

### Vérifier les Migrations

```powershell
python scripts/verify_migrations.py
```

---

## 🚀 Commandes d'Import

### Test (dry-run)

```powershell
python scripts/import_gazelle_product_display.py --dry-run
```

### Import réel

```powershell
python scripts/import_gazelle_product_display.py
```

---

## 📝 Notes

- **Sur Windows:** Utiliser `python` (pas `python3`)
- **PowerShell:** Utiliser `Invoke-RestMethod` pour les requêtes HTTP
- **curl:** Fonctionne aussi mais retourne du texte brut

---

## 🎯 Commande Rapide pour Vérifier

**Vérifier le nombre de produits importés:**

```powershell
$r = Invoke-RestMethod "http://localhost:8000/inventaire/catalogue"; Write-Host "Produits: $($r.count)"
```

**Une seule ligne, copiez-collez!** ✅
