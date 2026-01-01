# Assistant v6 - Synthèse Complète

## ✅ Ce qui a été créé

### 1. Structure du projet
```
assistant-v6/
├── README.md                   # Documentation principale
├── QUICKSTART.md              # Guide de démarrage rapide
├── SUMMARY.md                 # Ce fichier
├── start_v6.sh                # Script de démarrage (charge .env)
├── api/
│   └── assistant_v6.py        # Endpoint FastAPI (port 8001)
├── modules/
│   ├── assistant/
│   │   └── services/
│   │       ├── parser_v6.py   # Parser avec priorités claires
│   │       └── queries_v6.py  # Logique instrument-centric
│   └── storage/
│       └── supabase.py        # Connexion Supabase
└── tests/
    └── test_ab_comparison.py  # Tests A/B v5 vs v6
```

### 2. Les 4 Piliers Implémentés

#### ✅ Pilier #1: Mapping Instrument-Centric
**Fichier**: `modules/assistant/services/queries_v6.py`
**Fonctions clés**:
- `get_client_pianos(client_id)` → Récupère tous les pianos d'un client
- `get_timeline_for_entities(ids)` → Requête timeline pour client + pianos
- `_execute_timeline_query()` → Logique Client → Pianos → Timeline

**Pourquoi c'est important**: Les notes de service sont liées aux pianos, pas aux clients. Cette architecture garantit qu'on trouve TOUTES les notes de service.

#### ✅ Pilier #2: Parser de Priorité
**Fichier**: `modules/assistant/services/parser_v6.py`
**Fonctions clés**:
- `parse_query(question)` → Détecte le type avec règles de priorité
- `extract_entity_name(question)` → Extrait le nom du client/technicien

**Règles de priorité**:
1. "historique" / "notes de service" → FORCER TIMELINE
2. "demain" / "mes rv" → FORCER APPOINTMENTS
3. "trouve" / "cherche" → FORCER SEARCH_CLIENT

**Pourquoi c'est important**: Évite les ambiguïtés (ex: "historique" détecté comme APPOINTMENTS dans v5).

#### ✅ Pilier #3: Déduplication Propre
**Fichier**: `modules/assistant/services/queries_v6.py`
**Fonctions clés**:
- `normalize_name(name)` → Normalise les noms (minuscules, sans espaces multiples)
- `deduplicate_clients(clients)` → Déduplique avec priorité client > contact

**Pourquoi c'est important**: Élimine les doublons (Michelle Alie qui apparaît 2 fois).

#### ✅ Pilier #4: Connexion Supabase Directe
**Fichier**: `modules/storage/supabase.py`
**API utilisée**: PostgREST (REST API directe sur Supabase)

**Tables accédées**:
- `gazelle_timeline_entries` → Historique de service
- `gazelle_pianos` → Inventaire des instruments
- `gazelle_clients` → Informations clients
- `gazelle_contacts` → Contacts associés

**Pourquoi c'est important**: Accès direct sans couche d'abstraction complexe. Tri sur `created_at` car `occurred_at` souvent vide.

### 3. Tests et Validation

#### Tests du Parser
Le parser a été testé avec 6 questions représentatives:
- ✅ "historique de Monique Hallé" → TIMELINE (95%)
- ✅ "mes rv demain" → APPOINTMENTS (90%)
- ✅ "trouve Michelle Alie" → SEARCH_CLIENT (85%)
- ✅ "a payé en retard" → CLIENT_INFO (27%)
- ✅ "apporter le kit" → DEDUCTIONS (22%)
- ✅ "calendrier de Nick" → APPOINTMENTS (90%)

#### Tests A/B
**Fichier**: `tests/test_ab_comparison.py`

Compare v5 vs v6 sur:
- Temps de réponse
- Type détecté
- Nombre de résultats
- Taux de succès

## 🚀 Comment tester

### Option 1: Démarrage direct (recommandé)
```bash
cd /Users/allansutton/Documents/assistant-gazelle-v5/assistant-v6
./start_v6.sh
```

Le serveur démarre sur **http://localhost:8001**

### Option 2: Tester le parser seul
```bash
cd /Users/allansutton/Documents/assistant-gazelle-v5/assistant-v6/modules/assistant/services
python3 parser_v6.py
```

### Option 3: Tests A/B (v5 vs v6)
```bash
# Terminal 1: v5 (déjà running)
cd /Users/allansutton/Documents/assistant-gazelle-v5
uvicorn api.main:app --reload --port 8000

# Terminal 2: v6
cd /Users/allansutton/Documents/assistant-gazelle-v5/assistant-v6
./start_v6.sh

# Terminal 3: Tests A/B
cd /Users/allansutton/Documents/assistant-gazelle-v5/assistant-v6/tests
python3 test_ab_comparison.py
```

### Option 4: Test avec curl
```bash
# Test TIMELINE
curl -X POST http://localhost:8001/v6/assistant/chat \
  -H "Content-Type: application/json" \
  -d '{"question": "montre-moi l'\''historique complet de Monique Hallé avec toutes les notes de service"}'

# Test SEARCH
curl -X POST http://localhost:8001/v6/assistant/chat \
  -H "Content-Type: application/json" \
  -d '{"question": "trouve Michelle Alie"}'

# Health check
curl http://localhost:8001/v6/assistant/health
```

## 📊 Comparaison v5 vs v6

| Aspect | v5 | v6 |
|--------|----|----|
| **Fichiers principaux** | 3-4 fichiers dispersés | 2 fichiers centralisés |
| **Lignes de code** | ~800 lignes | ~400 lignes |
| **Logique timeline** | Cherche client seulement | Client + tous ses pianos ✅ |
| **Parser** | Règles ambiguës | Priorités claires ✅ |
| **Déduplication** | ID-based (doublons) | Nom-based (propre) ✅ |
| **Lisibilité** | Complexe, imbriqué | Simple, séquentiel ✅ |
| **Maintenabilité** | Difficile | Facile ✅ |

## 🎯 Fonctionnalités implémentées

### ✅ Complètes
- **TIMELINE**: Historique de service (client + pianos)
- **SEARCH_CLIENT**: Recherche de clients avec déduplication
- **Parser**: Détection de type avec priorités

### 🚧 En développement
- **APPOINTMENTS**: Rendez-vous futurs
- **CLIENT_INFO**: Informations paiement
- **DEDUCTIONS**: Recommandations basées sur attributs pianos

## 📝 Prochaines étapes

### Phase 1: Compléter les fonctionnalités
- [ ] Implémenter APPOINTMENTS (chercher dans `gazelle_appointments`)
- [ ] Implémenter CLIENT_INFO (chercher infos paiement)
- [ ] Implémenter DEDUCTIONS (analyser attributs pianos)

### Phase 2: Intégration frontend
- [ ] Modifier `AssistantWidget.jsx` pour pointer vers v6
- [ ] Ajouter un switch "v5/v6" pour A/B testing
- [ ] Tester avec utilisateurs réels

### Phase 3: Migration complète
- [ ] Valider que v6 couvre 100% des cas d'usage v5
- [ ] Basculer le frontend vers v6 par défaut
- [ ] Archiver le code v5

## 🔧 Dépannage

### Serveur ne démarre pas
**Erreur**: "SUPABASE_URL non défini"
**Solution**: Vérifier que le fichier `.env` existe dans `/Users/allansutton/Documents/assistant-gazelle-v5/`

### Imports ne fonctionnent pas
**Erreur**: "ModuleNotFoundError: No module named 'parser_v6'"
**Solution**: Vérifier que tous les `__init__.py` existent dans les dossiers `modules/`

### Aucun résultat timeline
**Cause possible**: Client n'a pas de pianos dans `gazelle_pianos`
**Vérification**: Regarder les logs, chercher "🎹 Trouvé X pianos"

## 💡 Concepts clés à retenir

1. **Instrument-Centric**: Toujours passer par les pianos pour l'historique
2. **Règles de priorité**: "historique" → TIMELINE, "demain" → APPOINTMENTS
3. **Déduplication par nom**: Normaliser avant de comparer
4. **Supabase direct**: Utiliser PostgREST API directement

## 📚 Documentation complète

- **README.md**: Vue d'ensemble du projet
- **QUICKSTART.md**: Guide de démarrage en 3 étapes
- **Ce fichier (SUMMARY.md)**: Synthèse complète

## ✨ Conclusion

L'assistant v6 est une réécriture propre du système de chat basée sur 4 piliers solides découverts pendant le débogage de v5. Le code est:
- **Plus simple**: 2 fichiers principaux vs 4
- **Plus fiable**: Logique instrument-centric garantit de trouver toutes les notes
- **Plus maintenable**: Architecture claire, pas de code spaghetti
- **Prêt pour A/B testing**: Peut tourner en parallèle avec v5

Prêt à être testé en local et comparé avec v5! 🚀
