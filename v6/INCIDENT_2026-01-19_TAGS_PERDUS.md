# 🚨 Post-Mortem : Perte des Tags Institutionnels

**Date :** 2026-01-19  
**Gravité :** Critique  
**Impact :** Inventaire institutionnel invisible, Badge PLS disparu  
**Durée :** ~2 heures  
**Statut :** ✅ Résolu

---

## 📋 Résumé Exécutif

Suite à une modification de `sync_to_supabase.py` pour ajouter les champs `first_name` et `last_name` aux clients, une synchronisation a écrasé **tous les tags** des clients, incluant le tag critique `"institutional"` utilisé pour identifier les institutions (UQAM, Vincent d'Indy, Place des Arts, SMCQ).

**Conséquences :**
- ❌ Inventaire de parc de pianos institutionnels invisible
- ❌ Badge PLS (Piano Life Saver) disparu
- ❌ 340 pianos ont perdu le flag `dampp_chaser_installed`

---

## 🔍 Chronologie des Événements

### 07:00 - Modification du Code
- Ajout des champs `first_name` et `last_name` dans `sync_to_supabase.py`
- Commit des changements

### 07:13 - Synchronisation Gazelle
- Exécution de la sync clients depuis l'API Gazelle
- **Problème** : Le champ `tags` inclus dans l'UPSERT avec valeur vide
- Résultat : Tous les tags écrasés par `[]` ou `NULL`

### 21:00 - Détection du Problème
- Utilisateur signale : "les institutions n'ont plus leur inventaire"
- Utilisateur signale : "j'ai encore perdu le badge PLS"

### 22:00 - Investigation
- Vérification : 0 clients avec tag `"institutional"`
- Vérification : 0 pianos avec `dampp_chaser_installed = true`
- Identification de la cause : sync écrasant les tags

### 22:15 - Correction Badge PLS
- Relance `scripts/detect_dampp_chaser_installations.py --write`
- Résultat : 340 pianos marqués avec PLS

### 22:20 - Correction Tags Institutionnels
- Réassignation manuelle des tags à 5 institutions
- Modification du code sync pour préserver les tags existants

### 22:30 - Résolution Complète
- ✅ Inventaire institutionnel rétabli
- ✅ Badge PLS rétabli
- ✅ Code corrigé pour éviter récurrence

---

## 🐛 Cause Racine

### Code Problématique (AVANT)

```python
# sync_to_supabase.py - ligne 177-228
tags = client_data.get('tags', [])  # Si API ne retourne pas de tags → []

client_record = {
    'external_id': external_id,
    'company_name': company_name,
    'tags': tags,  # ⚠️ Écrase TOUJOURS, même si vide !
    # ...
}
```

**Problème :**
- Si l'API Gazelle ne retourne **pas de tags**, `tags = []`
- L'UPSERT écrase les tags existants avec `[]`
- Les tags manuels (comme `"institutional"`) sont **perdus**

### Effet en Cascade

1. **Tags perdus** → Clients ne sont plus identifiés comme institutionnels
2. **Frontend ne trouve plus les institutions** → Inventaire vide
3. **Sync écrase aussi les pianos** → Flag `dampp_chaser_installed` perdu
4. **Backend ne peut plus générer le badge PLS** → Badge invisible

---

## ✅ Solutions Appliquées

### 1. Protection des Tags dans le Code

**Code Corrigé (APRÈS) :**

```python
# sync_to_supabase.py - ligne 221-241
client_record = {
    'external_id': external_id,
    'company_name': company_name,
    'first_name': first_name if first_name else None,
    'last_name': last_name if last_name else None,
    'status': status,
    # ... autres champs
}

# ⚠️ IMPORTANT: Ne mettre à jour les tags QUE si l'API en retourne
# pour éviter d'écraser les tags existants (ex: 'institutional')
if tags:
    client_record['tags'] = tags
```

**Principe :**
- Ne pas inclure le champ `tags` si l'API n'en retourne pas
- PostgreSQL/Supabase **préserve** les valeurs existantes pour les champs non-fournis dans l'UPSERT

### 2. Réassignation Manuelle des Tags

```python
institutional_clients = [
    ('cli_sos6RK8t4htOApiM', 'Centre Pierre-Péladeau/UQAM'),
    ('cli_HbEwl9rN11pSuDEU', 'Place des Arts'),
    ('cli_9UMLkteep8EsISbG', 'École de musique Vincent-d\'Indy'),
    ('cli_xkMYNQrSX7T7E1q0', 'Fondation Vincent-d\'Indy'),
    ('cli_UVMjT9g1b1wDkRHr', 'Société de musique contemporaine du Québec'),
]

for client_id, name in institutional_clients:
    storage.client.table('gazelle_clients').update({
        'tags': ['institutional']
    }).eq('external_id', client_id).execute()
```

### 3. Restauration des Flags PLS

```bash
cd /Users/allansutton/Documents/assistant-gazelle-v5
nohup python3 -u scripts/detect_dampp_chaser_installations.py --write \
    > logs/detect_pls_$(date +%Y%m%d_%H%M%S).log 2>&1 &
```

**Résultat :** 340 pianos rémarqués

---

## 📊 État Final

### Clients Institutionnels Restaurés

| Institution | External ID | Pianos | Tag |
|-------------|-------------|--------|-----|
| École Vincent-d'Indy | `cli_9UMLkteep8EsISbG` | 121 | ✅ institutional |
| Place des Arts | `cli_HbEwl9rN11pSuDEU` | 16 | ✅ institutional |
| UQAM (Pierre-Péladeau) | `cli_sos6RK8t4htOApiM` | 4 | ✅ institutional |
| SMCQ | `cli_UVMjT9g1b1wDkRHr` | 0 | ✅ institutional |
| Fondation Vincent-d'Indy | `cli_xkMYNQrSX7T7E1q0` | 0 | ✅ institutional |

**Total : 141 pianos institutionnels**

### Pianos avec Dampp-Chaser

- ✅ **340 pianos** avec `dampp_chaser_installed = true`
- ✅ Badge PLS fonctionnel

---

## 🎓 Leçons Apprises

### 1. Préservation des Données Manuelles

**Problème :** Les tags `"institutional"` sont assignés **manuellement** et ne viennent pas de l'API Gazelle.

**Leçon :** Toujours préserver les données qui ne viennent pas de la source de sync.

**Règle :** 
```
Si un champ peut être NULL ou vide dans l'API,
ne pas l'inclure dans l'UPSERT pour préserver les valeurs existantes.
```

### 2. Testing de la Sync

**Problème :** Aucun test n'a vérifié que les tags restaient intacts après la sync.

**Action Future :**
- Ajouter un test : "Sync ne doit pas écraser les tags institutionnels"
- Vérifier les tags avant/après chaque sync

### 3. Effets en Cascade

**Problème :** La perte des tags a eu un **effet domino** :
- Tags perdus → Inventaire invisible
- Sync pianos → Flags PLS perdus
- Users sans external_id → Badge PLS cassé

**Leçon :** Toujours considérer les **dépendances** entre les tables.

### 4. Backup et Rollback

**Problème :** Pas de backup automatique des tags avant sync.

**Action Future :**
- Considérer un système de backup avant chaque sync
- Ou utiliser des migrations versionnées pour les changements de schéma

---

## 🛠️ Actions Préventives

### Immédiat

- [x] Code sync modifié pour préserver les tags
- [x] Tags institutionnels réassignés
- [x] Flags PLS restaurés
- [x] Documentation créée (ce document)

### Court Terme

- [ ] Ajouter test automatisé pour les tags institutionnels
- [ ] Documenter tous les champs "manuels" à préserver
- [ ] Créer script de vérification post-sync

### Moyen Terme

- [ ] Rafraîchir token OAuth pour resync users (external_id manquants)
- [ ] Vérifier si l'API Gazelle peut retourner les tags
- [ ] Considérer une table dédiée `institution_config` pour les métadonnées manuelles

---

## 📚 Références

### Fichiers Modifiés

- `modules/sync_gazelle/sync_to_supabase.py` - Protection des tags (ligne 236-241)
- Scripts utilisés :
  - `scripts/detect_dampp_chaser_installations.py`
  - Script manuel de réassignation des tags

### Documentation Liée

- `v6/RAPPORT_TIMELINE_V5_RECETTE.md` - Documentation du rapport
- Ce document - Post-mortem de l'incident

### Commits

```bash
# Modification originale (cause)
git log --oneline | grep "first_name last_name"

# Correction
git log --oneline | grep "Préserver tags institutionnels"
```

---

## ✅ Checklist de Validation

- [x] Les 5 clients institutionnels ont le tag `"institutional"`
- [x] L'inventaire s'affiche dans le frontend
- [x] 340 pianos ont `dampp_chaser_installed = true`
- [x] Le code de sync préserve maintenant les tags
- [x] Documentation complète créée
- [ ] Token OAuth rafraîchi (nécessaire pour resync users)
- [ ] Tests automatisés ajoutés

---

**Document créé le :** 2026-01-19 22:30  
**Auteur :** Assistant Claude + Allan Sutton  
**Statut :** ✅ Incident Résolu - Préventions en Place
