# User Roles & Security - Assistant Gazelle V6

## 📋 Document "Source de Vérité"

**Objectif:** Définir les rôles, permissions, et stratégie de sécurité (Row-Level Security / Voûtes)

**Date création:** 2025-12-29
**Dernière mise à jour:** 2025-12-29

---

## 🎯 Principe Fondamental: Vault-Based Security

**Vision V6:**
```
Utilisateur → Rôle → Voûte(s) → Données autorisées
```

**Vocabulaire:**
- **Rôle:** Ensemble de permissions (ex: `admin`, `technicien`, `stagiaire`)
- **Voûte:** Partition de données (ex: "Tout", "Mes RV seulement", "Lecture seule")
- **Permission:** Action autorisée (ex: `view_appointments`, `edit_inventory`)

**Différence avec systèmes classiques:**
- Pas de "admin peut tout voir" → Admin a accès à voûte "Tout"
- Technicien ne voit PAS les RV des autres → Voûte "Mes RV"
- Isolation complète des données selon le contexte

---

## 👥 Rôles et Permissions

### Matrice Rôles × Permissions

| Permission | Admin | Assistant | Technicien | Stagiaire |
|------------|-------|-----------|------------|-----------|
| **Rendez-vous** |
| `view_appointments` | ✅ Tous | ✅ Tous | ✅ Siens seulement | ✅ Lecture seule |
| `edit_appointments` | ✅ | ✅ | ✅ Siens seulement | ❌ |
| `create_appointments` | ✅ | ✅ | ❌ | ❌ |
| `delete_appointments` | ✅ | ✅ | ❌ | ❌ |
| **Clients** |
| `view_clients` | ✅ | ✅ | ✅ Liés à ses RV | ✅ Lecture seule |
| `edit_clients` | ✅ | ✅ | ❌ | ❌ |
| `view_billing` | ✅ | ✅ | ❌ | ❌ |
| **Inventaire** |
| `view_inventory` | ✅ | ✅ | ✅ | ✅ Lecture seule |
| `edit_inventory` | ✅ | ✅ | ✅ | ❌ |
| **Assistant Chat** |
| `use_assistant` | ✅ | ✅ | ✅ | ❌ |
| **Rapports** |
| `generate_reports` | ✅ | ✅ | ❌ | ❌ |
| `view_analytics` | ✅ | ❌ | ❌ | ❌ |
| **Administration** |
| `manage_users` | ✅ | ❌ | ❌ | ❌ |
| `sync_gazelle` | ✅ | ❌ | ❌ | ❌ |
| `view_logs` | ✅ | ❌ | ❌ | ❌ |

---

## 🏛️ Architecture des Voûtes

### Concept de Voûte

**Définition:**
Une voûte est un **filtre de données** appliqué automatiquement selon le rôle de l'utilisateur.

**Exemple:**
```sql
-- Voûte Admin: Voit TOUT
SELECT * FROM gazelle_appointments;

-- Voûte Technicien (Nick): Voit SEULEMENT ses RV
SELECT * FROM gazelle_appointments
WHERE technicien = 'Nicolas';  -- ← Filtre automatique

-- Voûte Stagiaire: Lecture seule, ses RV
SELECT * FROM gazelle_appointments
WHERE technicien = 'Stagiaire123'
  AND (current_user_can_edit = false);  -- ← Pas de modification
```

### Types de Voûtes

#### 1. Voûte "Tout" (Admin)

**Utilisateurs:** Admin (Allan), Assistant (Louise)

**Règle:**
```sql
-- Aucun filtre
SELECT * FROM gazelle_appointments;
```

**Use case:**
- Allan: Supervision globale
- Louise: Coordination des techniciens

#### 2. Voûte "Mes Données" (Technicien)

**Utilisateurs:** Nicolas, Jean-Philippe, autres techniciens

**Règle:**
```sql
-- Filtre par technicien
SELECT * FROM gazelle_appointments
WHERE technicien = current_user_technician_name();
```

**Use case:**
- Technicien voit SEULEMENT ses propres rendez-vous
- Pas de divulgation des RV des collègues

**Sécurité:**
- Empêche les techniciens de voir les notes personnelles des clients des autres
- Protège les codes d'accès (seulement pour les RV assignés)

#### 3. Voûte "Lecture Seule" (Stagiaire)

**Utilisateurs:** Stagiaires, invités

**Règle:**
```sql
-- Filtre + pas de modification
SELECT * FROM gazelle_appointments
WHERE technicien = current_user_technician_name()
  AND has_permission('edit_appointments') = false;
```

**Use case:**
- Formation: voir sans pouvoir modifier
- Audit: accès temporaire

---

## 🔐 Implémentation Row-Level Security (RLS)

### Activation RLS sur Tables

**Toutes les tables contenant des données sensibles:**

```sql
-- Activer RLS
ALTER TABLE gazelle_appointments ENABLE ROW LEVEL SECURITY;
ALTER TABLE gazelle_clients ENABLE ROW LEVEL SECURITY;
ALTER TABLE gazelle_contacts ENABLE ROW LEVEL SECURITY;
ALTER TABLE gazelle_locations ENABLE ROW LEVEL SECURITY;
ALTER TABLE gazelle_timeline_entries ENABLE ROW LEVEL SECURITY;
```

### Politique Admin (Voûte "Tout")

```sql
-- Politique: Admin voit tout
CREATE POLICY admin_all_access ON gazelle_appointments
FOR ALL
TO authenticated
USING (
  -- Vérifier si utilisateur est admin
  EXISTS (
    SELECT 1 FROM user_roles
    WHERE user_id = auth.uid()
      AND role = 'admin'
  )
);
```

### Politique Technicien (Voûte "Mes Données")

```sql
-- Politique: Technicien voit seulement ses RV
CREATE POLICY technician_own_appointments ON gazelle_appointments
FOR SELECT
TO authenticated
USING (
  -- RV assignés à ce technicien
  technicien = (
    SELECT technician_name FROM user_roles
    WHERE user_id = auth.uid()
  )
);

-- Politique: Technicien modifie seulement ses RV
CREATE POLICY technician_edit_own_appointments ON gazelle_appointments
FOR UPDATE
TO authenticated
USING (
  technicien = (
    SELECT technician_name FROM user_roles
    WHERE user_id = auth.uid()
  )
)
WITH CHECK (
  -- Empêcher de réassigner à un autre technicien
  technicien = (
    SELECT technician_name FROM user_roles
    WHERE user_id = auth.uid()
  )
);
```

### Politique Client (Voûte "Clients Liés")

```sql
-- Technicien ne voit que les clients de ses RV
CREATE POLICY technician_client_via_appointments ON gazelle_clients
FOR SELECT
TO authenticated
USING (
  external_id IN (
    SELECT client_id
    FROM gazelle_appointments
    WHERE technicien = (
      SELECT technician_name FROM user_roles
      WHERE user_id = auth.uid()
    )
  )
);
```

### Politique Codes d'Accès (CRITIQUE)

```sql
-- Les codes d'accès SEULEMENT pour locations de RV assignés
CREATE POLICY technician_location_with_code ON gazelle_locations
FOR SELECT
TO authenticated
USING (
  -- Location d'un de ses RV
  id IN (
    SELECT location_id
    FROM gazelle_appointments
    WHERE technicien = (
      SELECT technician_name FROM user_roles
      WHERE user_id = auth.uid()
    )
  )
);

-- ⚠️ CRITIQUE: Empêcher SELECT * FROM gazelle_locations
-- Un technicien curieux ne peut PAS dump tous les codes
```

---

## 👤 Table user_roles (Mapping Utilisateurs)

### Schéma SQL

```sql
CREATE TABLE user_roles (
    -- Identifiant
    user_id UUID PRIMARY KEY REFERENCES auth.users(id),

    -- Profil
    email TEXT UNIQUE NOT NULL,
    full_name TEXT NOT NULL,
    role TEXT NOT NULL,           -- 'admin', 'assistant', 'technicien', 'stagiaire'

    -- Mapping technicien (si applicable)
    technician_name TEXT,         -- "Nicolas", "JP", "Allan", etc.

    -- Permissions custom (JSON)
    custom_permissions JSONB DEFAULT '[]',

    -- Métadonnées
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now(),
    last_login_at TIMESTAMPTZ,

    -- Contraintes
    CONSTRAINT valid_role CHECK (role IN ('admin', 'assistant', 'technicien', 'stagiaire'))
);

-- Indexes
CREATE INDEX idx_user_roles_email ON user_roles(email);
CREATE INDEX idx_user_roles_tech ON user_roles(technician_name);
```

### Données Initiales

```sql
-- Admin
INSERT INTO user_roles (email, full_name, role, technician_name) VALUES
('asutton@piano-tek.com', 'Allan Sutton', 'admin', 'Allan');

-- Assistant
INSERT INTO user_roles (email, full_name, role) VALUES
('info@piano-tek.com', 'Louise', 'assistant');

-- Techniciens
INSERT INTO user_roles (email, full_name, role, technician_name) VALUES
('nlessard@piano-tek.com', 'Nicolas Lessard', 'technicien', 'Nicolas'),
('jpreny@gmail.com', 'Jean-Philippe Reny', 'technicien', 'JP');

-- Stagiaire (exemple)
INSERT INTO user_roles (email, full_name, role, technician_name) VALUES
('stagiaire@piano-tek.com', 'Stagiaire Été 2026', 'stagiaire', 'Stagiaire2026');
```

---

## 🔧 Helper Functions SQL

### Fonction: current_user_role()

```sql
CREATE OR REPLACE FUNCTION current_user_role()
RETURNS TEXT AS $$
  SELECT role FROM user_roles
  WHERE user_id = auth.uid()
$$ LANGUAGE sql SECURITY DEFINER;
```

### Fonction: current_user_technician_name()

```sql
CREATE OR REPLACE FUNCTION current_user_technician_name()
RETURNS TEXT AS $$
  SELECT technician_name FROM user_roles
  WHERE user_id = auth.uid()
$$ LANGUAGE sql SECURITY DEFINER;
```

### Fonction: user_has_permission()

```sql
CREATE OR REPLACE FUNCTION user_has_permission(permission TEXT)
RETURNS BOOLEAN AS $$
DECLARE
  user_role TEXT;
  is_admin BOOLEAN;
BEGIN
  -- Récupérer rôle
  SELECT role INTO user_role FROM user_roles WHERE user_id = auth.uid();

  -- Admin a toutes les permissions
  IF user_role = 'admin' THEN
    RETURN true;
  END IF;

  -- Vérifier permission selon rôle
  CASE permission
    WHEN 'view_appointments' THEN
      RETURN user_role IN ('admin', 'assistant', 'technicien', 'stagiaire');
    WHEN 'edit_appointments' THEN
      RETURN user_role IN ('admin', 'assistant', 'technicien');
    WHEN 'view_billing' THEN
      RETURN user_role IN ('admin', 'assistant');
    WHEN 'use_assistant' THEN
      RETURN user_role IN ('admin', 'assistant', 'technicien');
    ELSE
      RETURN false;
  END CASE;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;
```

---

## 🖥️ Frontend: Vérification Permissions

### Config Roles (V5 Actuel)

**Fichier:** `frontend/src/config/roles.js`

```javascript
export const ROLES = {
  admin: {
    name: 'Administrateur',
    permissions: ['*'],  // Tout
    dashboards: ['inventaire', 'commissions', 'stats', 'admin', 'sync_gazelle', 'tournees'],
    technicianName: 'Allan'
  },

  louise: {
    name: 'Louise (Assistante)',
    permissions: [
      'view_inventory',
      'edit_inventory',
      'view_tours',
      'use_assistant'
    ],
    dashboards: ['inventaire', 'tournees']
  },

  nick: {
    name: 'Nick (Gestionnaire)',
    permissions: [
      'view_inventory',
      'manage_own_inventory',
      'create_tours',
      'view_tours',
      'use_assistant'
    ],
    dashboards: ['inventaire', 'tournees'],
    technicianName: 'Nicolas'  // ← Mapping technicien
  },

  jeanphilippe: {
    name: 'Jean-Philippe (Technicien)',
    permissions: [
      'view_inventory',
      'edit_inventory',
      'view_tours',
      'use_assistant'
    ],
    dashboards: ['inventaire', 'tournees'],
    technicianName: 'JP'
  }
};

export function hasPermission(userEmail, permission) {
  const role = getUserRole(userEmail);
  const roleConfig = ROLES[role];

  if (!roleConfig) return false;
  if (roleConfig.permissions.includes('*')) return true;

  return roleConfig.permissions.includes(permission);
}
```

### V6 Enhanced: Permission Checks

```typescript
// v6/frontend/src/hooks/usePermissions.ts
import { useAuth } from './useAuth';

export function usePermissions() {
  const { user } = useAuth();

  const hasPermission = (permission: string): boolean => {
    if (!user) return false;

    // Admin bypass
    if (user.role === 'admin') return true;

    // Vérifier permission depuis RLS
    return user.permissions.includes(permission);
  };

  const canViewAppointment = (appointment: Appointment): boolean => {
    if (user.role === 'admin' || user.role === 'assistant') {
      return true;  // Voûte "Tout"
    }

    if (user.role === 'technicien') {
      // Voûte "Mes Données"
      return appointment.technicien === user.technicianName;
    }

    return false;
  };

  const canEditAppointment = (appointment: Appointment): boolean => {
    if (user.role === 'stagiaire') return false;

    return canViewAppointment(appointment);  // Si peut voir, peut éditer
  };

  return {
    hasPermission,
    canViewAppointment,
    canEditAppointment
  };
}
```

### Usage dans Composants

```typescript
// v6/frontend/src/components/AppointmentCard.tsx
import { usePermissions } from '@/hooks/usePermissions';

export function AppointmentCard({ appointment }) {
  const { canViewAppointment, canEditAppointment } = usePermissions();

  // Vérifier accès
  if (!canViewAppointment(appointment)) {
    return null;  // Carte cachée
  }

  const isEditable = canEditAppointment(appointment);

  return (
    <Card>
      <CardContent>
        <Typography>{appointment.client_name}</Typography>
        <Typography>{appointment.time_slot}</Typography>

        {isEditable && (
          <Button onClick={() => handleEdit(appointment)}>
            Modifier
          </Button>
        )}

        {!isEditable && (
          <Chip label="Lecture seule" size="small" />
        )}
      </CardContent>
    </Card>
  );
}
```

---

## 🧪 Tests de Sécurité

### Test 1: RLS Empêche Accès Cross-Technicien

```python
# tests/security/test_rls.py
def test_technician_cannot_view_other_appointments():
    """Technicien ne voit PAS les RV des collègues."""

    # Login Nick
    supabase_nick = create_client_as_user('nlessard@piano-tek.com')

    # Essayer de récupérer TOUS les RV
    result = supabase_nick.table('gazelle_appointments').select('*').execute()

    # Vérifier que SEULEMENT les RV de Nick sont retournés
    for apt in result.data:
        assert apt['technicien'] == 'Nicolas', \
            f"Nick voit RV de {apt['technicien']} - VIOLATION RLS!"
```

### Test 2: Codes d'Accès Protégés

```python
def test_technician_cannot_dump_all_access_codes():
    """Technicien ne peut PAS dumper tous les codes d'accès."""

    # Login JP
    supabase_jp = create_client_as_user('jpreny@gmail.com')

    # Essayer SELECT * FROM gazelle_locations
    result = supabase_jp.table('gazelle_locations').select('access_code').execute()

    # Vérifier que SEULEMENT les locations de SES RV
    jp_appointment_location_ids = get_jp_appointment_location_ids()

    for loc in result.data:
        assert loc['id'] in jp_appointment_location_ids, \
            "JP voit codes d'accès hors de ses RV - VIOLATION!"
```

### Test 3: Stagiaire Lecture Seule

```python
def test_stagiaire_cannot_edit():
    """Stagiaire ne peut PAS modifier de données."""

    # Login stagiaire
    supabase_stagiaire = create_client_as_user('stagiaire@piano-tek.com')

    # Tenter UPDATE
    try:
        supabase_stagiaire.table('gazelle_appointments')\
            .update({'notes': 'Test modification'})\
            .eq('external_id', 'evt_test123')\
            .execute()

        assert False, "Stagiaire a pu modifier - VIOLATION!"

    except Exception as e:
        assert 'permission denied' in str(e).lower()
```

---

## 📋 Checklist Sécurité Production

### Avant Déploiement

- [ ] RLS activé sur TOUTES les tables sensibles
- [ ] Politique admin testée
- [ ] Politique technicien testée (cross-access bloqué)
- [ ] Codes d'accès protégés
- [ ] Tests automatisés passent
- [ ] Audit logs activés
- [ ] Rate limiting API configuré
- [ ] HTTPS forcé
- [ ] Supabase API keys rotées

### Monitoring Continu

```sql
-- Vue: Tentatives d'accès suspectes
CREATE OR REPLACE VIEW v_suspicious_access AS
SELECT
    auth.uid() as user_id,
    u.email,
    COUNT(*) as blocked_queries,
    MAX(created_at) as last_attempt
FROM audit_logs
WHERE event_type = 'RLS_POLICY_VIOLATION'
GROUP BY auth.uid(), u.email
HAVING COUNT(*) > 10;  -- Plus de 10 violations = suspect
```

---

## 🔄 Migration V5 → V6

### Phase 1: Créer user_roles

```sql
-- Créer table
CREATE TABLE user_roles (...);

-- Migrer depuis config frontend
INSERT INTO user_roles (email, full_name, role, technician_name)
SELECT
    email,
    name,
    CASE
        WHEN email = 'asutton@piano-tek.com' THEN 'admin'
        WHEN email = 'info@piano-tek.com' THEN 'assistant'
        ELSE 'technicien'
    END,
    technician_name
FROM (VALUES
    ('asutton@piano-tek.com', 'Allan Sutton', 'Allan'),
    ('info@piano-tek.com', 'Louise', NULL),
    ('nlessard@piano-tek.com', 'Nicolas Lessard', 'Nicolas'),
    ('jpreny@gmail.com', 'Jean-Philippe Reny', 'JP')
) AS users(email, name, technician_name);
```

### Phase 2: Activer RLS

```sql
-- Activer progressivement table par table
ALTER TABLE gazelle_appointments ENABLE ROW LEVEL SECURITY;

-- Créer politique permissive temporaire (tous peuvent voir)
CREATE POLICY temp_allow_all ON gazelle_appointments
FOR SELECT
TO authenticated
USING (true);

-- Tester, puis resserrer
DROP POLICY temp_allow_all ON gazelle_appointments;
CREATE POLICY technician_own_appointments ON gazelle_appointments (...);
```

### Phase 3: Tester en Production

```bash
# Connexion comme technicien Nick
curl -H "Authorization: Bearer <nick_jwt>" \
  https://api.piano-tek.com/api/chat/query \
  -d '{"query": "mes rendez-vous demain"}'

# Résultat attendu: SEULEMENT RV de Nick
# Vérifier qu'aucun RV de JP ou Allan n'apparaît
```

---

## 🔗 Documents Liés

- [ARCHITECTURE_MAP.md](ARCHITECTURE_MAP.md) - Structure modules
- [DATA_DICTIONARY.md](DATA_DICTIONARY.md) - Schéma tables
- [UI_UX_STANDARDS.md](UI_UX_STANDARDS.md) - Affichage selon permissions

---

## 📝 Règles Critiques

### ✅ DO (À FAIRE)

1. **Toujours activer RLS sur tables sensibles**
   - Appointments, Clients, Locations, Timeline

2. **Tester RLS avec utilisateurs réels**
   - Login Nick → vérifier qu'il ne voit PAS RV de JP

3. **Logger toutes les violations RLS**
   - Audit trail pour détecter tentatives d'accès

4. **Codes d'accès = Locations SEULEMENT**
   - Jamais dans `gazelle_clients`

5. **Frontend vérifie permissions AVANT affichage**
   - Pas de bouton "Modifier" si stagiaire

### ❌ DON'T (À ÉVITER)

1. **Jamais désactiver RLS en production**
   ```sql
   -- ❌ DANGEREUX
   ALTER TABLE gazelle_appointments DISABLE ROW LEVEL SECURITY;
   ```

2. **Jamais bypass RLS avec SECURITY DEFINER**
   ```sql
   -- ❌ DANGEREUX
   CREATE FUNCTION get_all_appointments() ... SECURITY DEFINER;
   -- Permet à n'importe qui de contourner RLS!
   ```

3. **Jamais exposer codes d'accès dans logs**
   ```python
   # ❌ MAUVAIS
   logger.info(f"Code accès: {location.access_code}")  # Fuite dans logs

   # ✅ BON
   logger.info(f"Code accès présent: {bool(location.access_code)}")
   ```

---

**Version:** 1.0
**Auteur:** Assistant Gazelle Team
**Prochaine révision:** Après activation RLS production

**RAPPEL CRITIQUE:** RLS doit être activé AVANT mise en production! Test avec utilisateurs réels obligatoire.
