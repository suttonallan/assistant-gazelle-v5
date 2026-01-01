# Plan: Script de Sync Gazelle → API

## Objectif
Pousser les modifications locales (Supabase `vincent_dindy_piano_updates`) vers l'API Gazelle pour maintenir une synchronisation bidirectionnelle.

## Problématique actuelle

### Flow actuel (READ-ONLY)
```
API Gazelle → usePianos hook → Supabase overlays → UI
     ↓                              ↓
  (lecture)                    (lecture + écriture)
```

**Problème**: Les modifications faites dans Supabase ne sont PAS poussées vers Gazelle.

### Flow souhaité (BIDIRECTIONNEL)
```
API Gazelle ←→ Sync Script ←→ Supabase
     ↑                              ↑
  (lecture + écriture)        (lecture + écriture)
```

## Architecture proposée

### 1. Identifier les modifications à synchro

**Table Supabase**: `vincent_dindy_piano_updates`

Colonnes à synchroniser:
- ✅ `status` → Doit devenir un tag dans Gazelle (ex: "top", "problematic")
- ✅ `notes` → Ajouter comme commentaire/note dans Gazelle
- ✅ `observations` → Ajouter dans description/notes
- ✅ `travail` → Description du travail effectué
- ❌ `is_hidden` → NE PAS synchroniser (métadonnée locale uniquement)
- ❌ `completed_in_tournee_id` → NE PAS synchroniser (workflow interne)

### 2. Mapping Supabase → Gazelle

#### Status → Tags Gazelle
```typescript
const STATUS_TO_TAG: Record<PianoStatus, string> = {
  'top': 'TOP',
  'normal': 'NORMAL',
  'problematic': 'PROBLEMATIQUE',
  'needs_replacement': 'A_REMPLACER'
};
```

#### Notes → Comments Gazelle
```typescript
interface GazelleComment {
  text: string;
  created_at: string;
  created_by: string;
}
```

### 3. Détecter les changements (Delta detection)

**Option A**: Timestamp-based
```sql
-- Sélectionner pianos modifiés depuis dernière sync
SELECT gazelle_id, status, notes, observations, updated_at, updated_by
FROM vincent_dindy_piano_updates
WHERE updated_at > $last_sync_timestamp
  AND is_hidden = false  -- Ne pas synchro pianos masqués
ORDER BY updated_at ASC;
```

**Option B**: Dirty flag (recommandé)
```sql
-- Ajouter colonne needs_sync
ALTER TABLE vincent_dindy_piano_updates
ADD COLUMN needs_sync boolean DEFAULT true;

-- Sélectionner pianos à synchroniser
SELECT gazelle_id, status, notes, observations
FROM vincent_dindy_piano_updates
WHERE needs_sync = true
  AND is_hidden = false;
```

### 4. API Gazelle - Endpoints requis

#### A. Update Piano Tags
```http
PATCH /api/v1/pianos/{piano_id}/tags
Authorization: Bearer {GAZELLE_TOKEN}
Content-Type: application/json

{
  "tags": ["TOP", "GRAND"]
}
```

#### B. Add Comment/Note
```http
POST /api/v1/pianos/{piano_id}/comments
Authorization: Bearer {GAZELLE_TOKEN}
Content-Type: application/json

{
  "text": "Piano accordé le 2026-01-01. Cordes remplacées.",
  "created_by": "allan@pianosmtl.com"
}
```

#### C. Update Piano Details
```http
PATCH /api/v1/pianos/{piano_id}
Authorization: Bearer {GAZELLE_TOKEN}
Content-Type: application/json

{
  "observations": "Son excellent après réparation",
  "last_serviced": "2026-01-01"
}
```

### 5. Script de synchronisation

#### Structure
```
refactor/vdi/
├── scripts/
│   └── sync_to_gazelle.ts
└── lib/
    └── gazelle_sync_client.ts
```

#### Pseudo-code
```typescript
// scripts/sync_to_gazelle.ts

async function syncToGazelle() {
  // 1. Charger pianos à synchroniser
  const { data: pianos } = await supabase
    .from('vincent_dindy_piano_updates')
    .select('*')
    .eq('needs_sync', true)
    .eq('is_hidden', false);

  console.log(`🔄 ${pianos.length} piano(s) à synchroniser`);

  // 2. Pour chaque piano
  for (const piano of pianos) {
    try {
      // a. Update tags (status)
      if (piano.status) {
        await gazelleClient.updateTags(piano.gazelle_id, [
          STATUS_TO_TAG[piano.status]
        ]);
      }

      // b. Ajouter notes
      if (piano.notes) {
        await gazelleClient.addComment(piano.gazelle_id, {
          text: piano.notes,
          created_by: piano.updated_by
        });
      }

      // c. Update observations
      if (piano.observations) {
        await gazelleClient.updatePiano(piano.gazelle_id, {
          observations: piano.observations
        });
      }

      // 3. Marquer comme synchronisé
      await supabase
        .from('vincent_dindy_piano_updates')
        .update({ needs_sync: false, last_synced_at: new Date() })
        .eq('gazelle_id', piano.gazelle_id);

      console.log(`✅ ${piano.gazelle_id} synchronisé`);
    } catch (err) {
      console.error(`❌ Erreur ${piano.gazelle_id}:`, err);
      // Continuer avec les autres pianos
    }
  }

  console.log('🎉 Synchronisation terminée');
}
```

### 6. Gestion des conflits

**Scénario**: Piano modifié dans Gazelle ET Supabase simultanément

**Stratégie**: Last-Write-Wins (LWW)
```typescript
// Comparer timestamps
if (gazelleData.updated_at > supabaseData.updated_at) {
  // Gazelle plus récent → Skip sync
  console.warn(`⚠️ Piano ${id}: Gazelle plus récent, skip`);
  return;
}

// Sinon, pousser modifications Supabase → Gazelle
await syncToGazelle(supabaseData);
```

### 7. Scheduler (Automatisation)

**Option A**: Cron job (serveur)
```bash
# Sync toutes les heures
0 * * * * cd /app && npm run sync:gazelle
```

**Option B**: UI Button (manuel)
```tsx
<button onClick={handleSyncToGazelle}>
  🔄 Synchroniser avec Gazelle
</button>
```

**Option C**: Webhook Supabase (temps réel)
```sql
-- Trigger sur update
CREATE OR REPLACE FUNCTION notify_sync()
RETURNS trigger AS $$
BEGIN
  -- Appeler endpoint externe
  PERFORM net.http_post(
    url := 'https://your-api.com/sync-webhook',
    body := json_build_object('piano_id', NEW.gazelle_id)
  );
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER on_piano_update
AFTER UPDATE ON vincent_dindy_piano_updates
FOR EACH ROW
WHEN (OLD.* IS DISTINCT FROM NEW.*)
EXECUTE FUNCTION notify_sync();
```

## Migration SQL requise

```sql
-- Ajouter colonnes pour tracking sync
ALTER TABLE vincent_dindy_piano_updates
ADD COLUMN IF NOT EXISTS needs_sync boolean DEFAULT true,
ADD COLUMN IF NOT EXISTS last_synced_at timestamptz,
ADD COLUMN IF NOT EXISTS sync_error text;

-- Index pour queries rapides
CREATE INDEX IF NOT EXISTS idx_needs_sync
ON vincent_dindy_piano_updates(needs_sync)
WHERE needs_sync = true;

-- Commentaire
COMMENT ON COLUMN vincent_dindy_piano_updates.needs_sync IS
  'Si true, les modifications doivent être poussées vers API Gazelle';
```

## Sécurité

### Token Gazelle
```bash
# .env
GAZELLE_API_URL=https://api.gazelle.com
GAZELLE_API_TOKEN=your-secret-token
```

### Rate limiting
```typescript
// Throttle requests (max 10 req/sec)
const delay = (ms: number) => new Promise(resolve => setTimeout(resolve, ms));

for (const piano of pianos) {
  await syncPiano(piano);
  await delay(100); // 100ms entre chaque requête
}
```

## Logs et monitoring

### Table de logs
```sql
CREATE TABLE sync_gazelle_logs (
  id serial PRIMARY KEY,
  piano_id text NOT NULL,
  action text NOT NULL,  -- 'update_tags', 'add_comment', etc.
  status text NOT NULL,  -- 'success', 'error'
  error_message text,
  synced_at timestamptz DEFAULT now()
);
```

### Alerting
```typescript
// Envoyer email si trop d'erreurs
if (errorCount > 10) {
  await sendEmail({
    to: 'admin@pianosmtl.com',
    subject: '⚠️ Sync Gazelle: Erreurs détectées',
    body: `${errorCount} erreurs lors de la sync`
  });
}
```

## Tests

### Test unitaire
```typescript
describe('syncToGazelle', () => {
  it('should update tags correctly', async () => {
    const piano = { gazelle_id: 'test-123', status: 'top' };
    await syncToGazelle(piano);

    // Vérifier API appelée
    expect(gazelleClient.updateTags).toHaveBeenCalledWith(
      'test-123',
      ['TOP']
    );
  });
});
```

### Test d'intégration
```typescript
// Tester avec vrai piano
const testPiano = await supabase
  .from('vincent_dindy_piano_updates')
  .select()
  .limit(1)
  .single();

await syncToGazelle();

// Vérifier dans Gazelle
const gazelleData = await gazelleClient.getPiano(testPiano.gazelle_id);
expect(gazelleData.tags).toContain('TOP');
```

## Estimation temps

- **Migration SQL**: 30 min
- **Client Gazelle API**: 2h
- **Script de sync**: 3h
- **UI dans Dashboard**: 1h
- **Tests**: 2h
- **Documentation**: 1h

**Total**: ~9h de développement

## Risques

1. **API Gazelle rate limiting** → Throttling nécessaire
2. **Conflits de données** → Stratégie LWW à valider
3. **Perte de données** → Backup avant sync
4. **Token expiration** → Refresh token automatique

## Conclusion

La synchronisation bidirectionnelle est **faisable** et suit un pattern classique de sync entre systèmes. La partie critique est la **gestion des conflits** et le **mapping exact** entre les structures Supabase et Gazelle.

**Recommandation**: Commencer par un **MVP** qui synchro uniquement le `status` (tags), puis itérer pour ajouter notes/observations.
