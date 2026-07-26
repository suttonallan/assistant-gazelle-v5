# Système « Institutions » — doc canonique

> **But de ce document** : source unique pour comprendre et modifier **en sécurité** le
> système multi-institutions (Vincent-d'Indy, Orford, Place des Arts…) sans avoir à
> fouiller le code. Écrit pour qu'un développeur — ou Claude piloté par un non-développeur
> (Nicolas, Margot) — puisse intervenir sans casser la prod.
>
> **Dernière mise à jour :** 2026-07-26

---

## 1. Vue d'ensemble

Une « institution » = un client Gazelle avec un parc de pianos géré en lot (accords,
tournées, historique de service). Chaque institution a un **slug** (`vincent-dindy`,
`orford`, `place-des-arts`) et une config stockée dans la table Supabase `institutions`.

Fichiers clés :

| Fichier | Rôle |
|---|---|
| `api/institutions.py` | Routes dynamiques `/{institution}/…` (pianos, stats, tournées, pianos-ready), `get_institution_config`, discovery. |
| `api/service_records.py` | **Push unifié** `/service-records/{institution}/push`, cycle de vie des fiches, table `piano_service_records`. |
| `api/vincent_dindy.py` | VDI + `vdi_router` (invités/admin), tournées, historique de service. Contient des routes **dépréciées**. |
| `api/place_des_arts.py` | Spécifique Place des Arts. |
| `frontend/…/OrfordDashboard.jsx`, `VincentDIndyDashboard.jsx`, `vdi/VDI_ManagementView.jsx` (partagé), `place_des_arts/PlaceDesArtsDashboard.jsx` | Interfaces. |

---

## 2. Contrat de routage (piège important)

Le routeur institutions est monté **EN DERNIER** dans `api/main.py` (voir commentaires
`main.py:193` et `:221` : « DOIT ÊTRE EN DERNIER »), parce que ses routes sont des
**catch-all** `/{institution}/…`. Le routeur humidité est monté **avant** (`main.py:169`).

**Conséquence à connaître :** toute URL `/api/{quelquechose}/…` mal tapée ou pointant vers
une route inexistante est **avalée par le catch-all** et renvoie un 404 « institution non
trouvée » — trompeur. Si un appel frontend échoue avec « institution 'xxx' non trouvée »,
vérifier d'abord que l'URL existe vraiment (voir §6, endpoints morts).

---

## 3. Ajouter une nouvelle institution (honnêtement, pas « 10 secondes »)

Le docstring `institutions.py:326` suggère un simple `INSERT`. C'est **incomplet** : la
découverte automatique dépend aussi de mappings **codés en dur**.

Étapes réelles :
1. **Supabase** — insérer une ligne dans `institutions` : `slug`, `name`, `gazelle_client_id`
   (l'ID `cli_…` du client Gazelle), `active = true`.
2. **Code** — si on veut que la discovery auto reconnaisse l'institution :
   - `institutions.py` : `INSTITUTION_NAME_MAPPING` (~ligne 62-73) mappe nom Gazelle → slug.
   - `institutions.py` : bloc `FORCED_MAPPINGS` (~ligne 158-164) — mappings explicites.
3. **Frontend** — créer/adapter un dashboard (souvent réutiliser `VDI_ManagementView`).

> `gazelle_client_id` : se récupère dans Gazelle (fiche du client, ID `cli_…`). Sans lui,
> `get_institution_config` lève une 500.

---

## 4. Modèle de données à DEUX tables (état de la migration)

Il existe deux tables, héritage d'une migration en cours :

- **`vincent_dindy_piano_updates`** — overlay *legacy*. Détient encore aujourd'hui :
  `a_faire`, `status`, `is_hidden`, `sync_status`.
- **`piano_service_records`** — nouveau système. **Fait autorité pour `travail`** : le
  chemin de lecture force `legacy_travail = ''` (`institutions.py:488-490`), donc l'overlay
  legacy n'est plus lu pour ce champ en v5.

**Matrice d'autorité (v5, aujourd'hui) :**

| Champ | Source d'autorité |
|---|---|
| `travail` | `piano_service_records` (overlay legacy ignoré) |
| `a_faire` | overlay `vincent_dindy_piano_updates` |
| `status`, `is_hidden`, `sync_status` | overlay `vincent_dindy_piano_updates` |

> Note : `workspace/decisions.md` (section 2026-03-28) documente le double-stockage de
> **`a_faire`** (overlay + `piano_service_records`) et son correctif v5 (sync
> bidirectionnelle), plus le plan v6 (éliminer l'overlay, fiche unique). C'est toujours
> exact. À ne pas confondre avec `travail`, qui lui est déjà lu uniquement depuis
> `piano_service_records` en v5 (overlay bypassé, `institutions.py:488-490`).

---

## 5. Flux push → Gazelle (bout en bout)

**Point d'entrée UNIQUE :** `POST /api/service-records/{institution}/push`
(`service_records.py:348`). Corps `PushRequest` : `technician_id`, `dry_run`, `skip_gazelle`.

Cycle de vie d'une fiche : `draft → completed → validated → pushed`. Le push traite toutes
les fiches `validated` de l'institution.

Étapes du push réel (`service_records.py:432-597`) :
1. Active les pianos `INACTIVE → ACTIVE` (limite facturable Gazelle).
2. Construit les notes combinées par piano.
3. **`createEvent`** — UN SEUL événement multi-pianos, `start` = `completed_at` le plus
   récent du lot, `isTuning: true`.
4. **`completeEvent`** — `serviceHistoryNotes` par piano (entre dans l'historique de service).
5. Remet les pianos activés en `INACTIVE`.
6. Marque les fiches `pushed`, nettoie les overlays legacy.

**Calendrier de l'événement (`userId`) — RÈGLE IMPORTANTE :**
```
push_user_id = CALENDRIER_NON_ASSIGNE_USER_ID   si institution ∈ INSTITUTIONS_PUSH_NON_ASSIGNE
             = body.technician_id                sinon (défaut Nicolas usr_HcCiFk7o0vZ9xAI0)
```
Défini en tête de `service_records.py` (~ligne 27-30). Voir §6 (particularités).

Modes : `dry_run` (n'écrit rien, aperçu) ; `skip_gazelle` (marque `pushed` sans écrire dans
Gazelle).

---

## 6. Particularités par institution

| Institution | Particularité | Où |
|---|---|---|
| **Orford** | Le push crée le RV dans le calendrier **« Avis système inutiles Piano »** (`usr_naFcjSiNRcnqU5mF`, non assigné) au lieu d'un vrai technicien — un humain réassigne ensuite dans Gazelle. | `service_records.py` `INSTITUTIONS_PUSH_NON_ASSIGNE = {"orford"}` |
| **Orford** | `a_faire` / `observations` / `notes` supprimés de certaines sorties. | `institutions.py:505-508` |
| **Orford** | `clean-orphan-statuses` réservé à Orford. | `institutions.py:857` |
| **Orford (équipe)** | Louise et Margot sont routées vers le dashboard VDI avec `institution="orford"`. | `progress.md:135` |
| Autres (VDI…) | Push assigné au `technician_id` fourni (défaut Nicolas). | `service_records.py` |

---

## 7. Endpoints morts connus (ne pas réintroduire)

- `POST /api/{institution}/push-to-gazelle` — **n'existe pas** (404). Historiquement appelé
  par les dashboards ; corrigé le 2026-07-26 pour pointer vers
  `/api/service-records/{institution}/push`. Si tu revois cet URL dans du code, c'est un bug.
- `POST /api/vincent-dindy/push-to-gazelle` (`vincent_dindy.py:1410`) — **déprécié**. Ne pas
  utiliser ; passer par le point d'entrée unique service-records.

---

## 8. Pour Nicolas / Margot — comment demander un aménagement

Objectif du système : tu n'as **pas besoin de coder**. Tu décris le changement voulu en
français à Claude, et il l'implémente en sécurité.

**Bonne façon de formuler une demande :**
- **Quoi** : ce que tu veux changer (ex. « pour Orford, les accords devraient aller dans tel
  calendrier au lieu de tel autre »).
- **Où** : l'écran/institution concerné (ex. « dans la gestion des accords à Orford »).
- **Pourquoi** : le besoin métier (aide Claude à choisir la bonne solution).

**Filets de sécurité en place :**
- La CI *smoke* (`.github/workflows/ci_smoke.yml`) vérifie que le backend compile et que les
  dépendances tiennent à chaque push — attrape les cassures avant la prod.
- Principe de travail : **réversible d'abord**, tester avant de déployer, un seul changement
  à la fois.

**Ce qui se passe après ta demande :** Claude localise le bon fichier, fait le changement
minimal, le vérifie, puis le déploie (Render backend + GitHub Pages frontend, ~2-3 min).

---

## 9. Voir aussi

- `workspace/DEVELOPER-GUIDE.md` — vue d'ensemble des dashboards et règles métier.
- `workspace/decisions.md` — décisions techniques (dont la migration v6 des fiches).
- `workspace/skills/gazelle/reference/schema_gotchas.md` — modèle GraphQL Gazelle
  (`createEvent`/`completeEvent`, `userId` singulier).
- `C:\PTM\transferabilite-plan.md` — plan de transférabilité opérationnelle (faire tourner
  l'entreprise sans le PC d'Allan).
