# 🔄 Configuration Supabase Realtime - Guide Complet

## Objectif

Activer **Supabase Realtime** pour synchronisation instantanée Mac ↔ iPad des données pianos et tournées.

---

## ✅ Prérequis

1. **Compte Supabase**: [app.supabase.com](https://app.supabase.com)
2. **Projet Supabase** créé (ou en créer un nouveau)
3. **Plan**: Realtime inclus dès le plan **Pro** ($25/mois)
   - Plan gratuit: Realtime limité (200 connexions simultanées max, OK pour petits projets)

---

## 📋 Étape 1: Exécuter les Migrations SQL

### A. Via Dashboard Supabase (Recommandé)

1. Aller sur [app.supabase.com](https://app.supabase.com)
2. Sélectionner ton projet Vincent d'Indy
3. Menu gauche → **SQL Editor**
4. Cliquer **New Query**

5. **Migration 1**: Créer table `tournees`
   - Copier tout le contenu de [sql/001_create_tournees_table.sql](sql/001_create_tournees_table.sql)
   - Coller dans l'éditeur SQL
   - Cliquer **Run** (ou Ctrl+Enter)
   - ✅ Tu devrais voir: "Success. No rows returned"

6. **Migration 2**: Ajouter colonne `completed_in_tournee_id`
   - Copier tout le contenu de [sql/002_alter_piano_updates_add_tournee.sql](sql/002_alter_piano_updates_add_tournee.sql)
   - Coller dans un nouveau query
   - Cliquer **Run**
   - ✅ Tu devrais voir des messages de test: "Test 1 OK", "Test 2 OK"

### B. Via psql (CLI)

Si tu préfères la ligne de commande:

```bash
# Récupérer DATABASE_URL depuis Supabase Dashboard
# Settings → Database → Connection String (URI)

export DATABASE_URL="postgresql://postgres:[YOUR-PASSWORD]@db.[YOUR-PROJECT-REF].supabase.co:5432/postgres"

# Exécuter migrations
psql $DATABASE_URL -f sql/001_create_tournees_table.sql
psql $DATABASE_URL -f sql/002_alter_piano_updates_add_tournee.sql
```

### C. Vérifier Tables Créées

Dans SQL Editor, run:

```sql
-- Check table tournees existe
SELECT * FROM information_schema.tables WHERE table_name = 'tournees';

-- Check colonne completed_in_tournee_id existe
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_name = 'vincent_dindy_piano_updates'
  AND column_name = 'completed_in_tournee_id';
```

✅ Les deux queries doivent retourner des résultats.

---

## 📋 Étape 2: Activer Realtime sur les Tables

Par défaut, Realtime est **désactivé** sur toutes les tables. Il faut l'activer manuellement.

### Via Dashboard (Le Plus Simple)

1. **Menu gauche → Database → Replication**

2. **Activer Realtime pour `vincent_dindy_piano_updates`**:
   - Trouver la table `vincent_dindy_piano_updates` dans la liste
   - Toggle le switch **"Realtime"** à ON (vert)
   - Confirm

3. **Activer Realtime pour `tournees`**:
   - Trouver la table `tournees`
   - Toggle "Realtime" à ON
   - Confirm

### Via SQL (Alternative)

```sql
-- Enable Realtime on vincent_dindy_piano_updates
ALTER PUBLICATION supabase_realtime ADD TABLE public.vincent_dindy_piano_updates;

-- Enable Realtime on tournees
ALTER PUBLICATION supabase_realtime ADD TABLE public.tournees;

-- Verify
SELECT schemaname, tablename
FROM pg_publication_tables
WHERE pubname = 'supabase_realtime';
```

✅ Tu devrais voir les deux tables listées.

---

## 📋 Étape 3: Configurer Row Level Security (RLS)

Les migrations SQL ont déjà créé les policies RLS, mais vérifions:

### Via Dashboard

1. **Menu → Authentication → Policies**
2. Vérifier table `tournees` a ces policies:
   - ✅ "Enable read access for all users" (SELECT)
   - ✅ "Enable insert for authenticated users" (INSERT)
   - ✅ "Enable update for creator and admins" (UPDATE)
   - ✅ "Enable delete for admins" (DELETE)

### Via SQL (Vérification)

```sql
-- Check policies existent
SELECT tablename, policyname, cmd
FROM pg_policies
WHERE tablename IN ('tournees', 'vincent_dindy_piano_updates');
```

---

## 📋 Étape 4: Récupérer Clés API

Tu as besoin de 2 clés pour `.env`:

### Via Dashboard

1. **Menu → Settings → API**

2. **Project URL**:
   - Copier "URL" (ex: `https://abcdefgh.supabase.co`)
   - Dans `.env`: `VITE_SUPABASE_URL=https://abcdefgh.supabase.co`

3. **anon public key**:
   - Section "Project API keys"
   - Copier la clé **"anon" (public)**
   - Dans `.env`: `VITE_SUPABASE_ANON_KEY=eyJhbGc...`

**IMPORTANT**: N'utilise **JAMAIS** la clé `service_role` côté client! C'est une clé admin secrète.

---

## 📋 Étape 5: Tester Realtime

### Test 1: Subscription Console

Dans SQL Editor, run:

```sql
-- Insérer test tournée
INSERT INTO public.tournees (
  id, nom, date_debut, date_fin, status, etablissement,
  technicien_responsable, piano_ids, created_by
) VALUES (
  'tournee_test_realtime',
  'Test Realtime',
  '2025-01-15',
  '2025-02-15',
  'planifiee',
  'vincent-dindy',
  'test@example.com',
  '[]',
  'system'
);

-- Attendre 2 secondes

-- Modifier
UPDATE public.tournees
SET nom = 'Test Realtime MODIFIÉ'
WHERE id = 'tournee_test_realtime';

-- Supprimer
DELETE FROM public.tournees WHERE id = 'tournee_test_realtime';
```

### Test 2: Depuis Code TypeScript

Créer un fichier `test-realtime.ts`:

```typescript
import { supabase, subscribeToTournees } from './refactor/vdi/lib/supabase.client';

// Subscribe
const unsubscribe = subscribeToTournees('vincent-dindy', (event) => {
  console.log('🔥 REALTIME EVENT:', event.eventType);
  console.log('New data:', event.new);
  console.log('Old data:', event.old);
});

console.log('✅ Listening for Realtime events...');
console.log('Open Supabase SQL Editor and INSERT/UPDATE/DELETE a tournée');

// Cleanup après 60 secondes
setTimeout(() => {
  unsubscribe();
  console.log('❌ Unsubscribed');
}, 60000);
```

Run:
```bash
npm install --save-dev tsx
npx tsx test-realtime.ts
```

✅ Tu devrais voir les events s'afficher en temps réel quand tu modifies la DB!

---

## 📋 Étape 6: Vérifier Limites Realtime

### Check Plan Actuel

1. **Menu → Settings → Billing**
2. Vérifier section "Realtime"
   - **Free plan**: 200 concurrent connections, 2 Million messages/mois
   - **Pro plan**: Unlimited connections, 5 Million messages/mois

### Pour Vincent d'Indy

- **Users Max Simultanés**: ~5-10 (Michelle, Nick, Nicolas, JP, Louise)
- **Connections**: ~10-20 (chaque user = 2-3 subscriptions)
- **Messages/mois**: ~100K (largement en dessous des limites)

✅ **Free plan suffit** pour Vincent d'Indy!

---

## 🐛 Troubleshooting

### Erreur: "Realtime is not enabled"

**Solution**:
1. Vérifier Étape 2 (Activer Realtime sur tables)
2. Refresh browser après avoir activé
3. Attendre 1-2 minutes (propagation)

### Erreur: "RLS policy violation"

**Solution**:
1. Vérifier RLS policies existent (Étape 3)
2. Check user est authentifié (ou policies permettent anon)
3. SQL: `SELECT * FROM pg_policies WHERE tablename = 'tournees';`

### Events ne s'affichent pas

**Checklist**:
- ✅ Realtime activé sur table (Étape 2)
- ✅ RLS policies correctes (Étape 3)
- ✅ Clés API correctes dans `.env` (Étape 4)
- ✅ `VITE_ENABLE_REALTIME=true` dans `.env`
- ✅ Subscription channel name correct

**Debug**:
```typescript
import { logRealtimeStatus } from '@lib/supabase.client';

// Affiche channels actifs
logRealtimeStatus();
```

### Latence élevée

**Causes possibles**:
- Réseau lent
- Serveur Supabase distant (check région)
- Throttling (>10 events/sec)

**Solution**:
- Vérifier région Supabase proche (ex: US East pour Montréal)
- Utiliser batch updates au lieu de N updates individuels

---

## 🎯 Résumé: Checklist Complète

- [ ] 1. Migrations SQL exécutées (001 + 002)
- [ ] 2. Realtime activé sur `vincent_dindy_piano_updates`
- [ ] 3. Realtime activé sur `tournees`
- [ ] 4. RLS policies vérifiées
- [ ] 5. Clés API copiées dans `.env`
- [ ] 6. Test subscription fonctionne
- [ ] 7. Vérifier limites plan Supabase

---

## 📚 Ressources

- [Supabase Realtime Docs](https://supabase.com/docs/guides/realtime)
- [RLS Policies Guide](https://supabase.com/docs/guides/auth/row-level-security)
- [Realtime Quotas](https://supabase.com/docs/guides/platform/going-into-prod#realtime-quotas)

---

## ✅ Configuration Réussie!

Si tous les tests passent, tu es prêt! 🎉

**Prochaines étapes**:
1. Lancer l'app: `npm run dev`
2. Ouvrir sur Mac ET iPad
3. Modifier piano sur Mac → Voir changement instantané sur iPad ✨

**Need help?** Check console browser pour logs Realtime.

---

*Généré pour VDI v7.0 - Architecture TypeScript robuste* 🚀
