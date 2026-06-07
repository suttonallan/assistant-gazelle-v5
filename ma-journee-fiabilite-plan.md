# Ma Journée — Plan de fiabilité du briefing

> Statut : actif (conception validée + revue adversariale intégrée, en cours d'application)
> Créé : 2026-06-07
> Dernière mise à jour : 2026-06-07
> Prochain pas : Phase 0 corrigée — (1) `locale` sur les DEUX queries (complète ET incrémentale), (2) flag dans la clé de cache, (3) `event_type`/`is_all_day`, (4) initiale Margot
> Bloqué par : rien
>
> **IMPORTANT : lire §7 (corrections de la revue adversariale) AVANT de coder une phase.** Plusieurs hypothèses du plan original sont fausses ou dangereuses ; §7 est contraignant et prime sur le texte des phases.

Sous-projet : fiabiliser l'assistant « Ma Journée » (briefing quotidien des techniciens) de Piano Tek Musique.
Coeur du code : `modules/briefing/client_intelligence_service.py` (`NarrativeBriefingService`).

---

## 1. Diagnostic — un seul défaut, trois symptômes

Le pipeline actuel est **« données brutes → un prompt géant → texte libre »**. Il n'existe aucune couche intermédiaire où un fait existe en tant qu'objet portant sa **date**, sa **source**, son **entité** (piano/client) et son **statut** (courant/historique). Tout le raisonnement temporel et de scope est délégué à l'IA Haiku, qui n'en est pas capable de façon fiable. De ce défaut unique découlent les trois familles de problèmes rapportées par Nicolas et Allan :

### Symptôme 1 — Info périmée présentée comme actuelle, sans provenance
- Le flag PLS est un booléen sans date : `has_pls = bool(piano.get('dampp_chaser_installed'))` (l.331). Aucune notion d'installation/remplacement/entretien daté.
- `_call_narrative_ai` (l.482-522) jette les 15 dernières entrées timeline en vrac (`[date] (tech, type) text[:300]`), triées par date mais **sans logique de supersession** : une note « PLS ancien » de 2022 et un « remplacement PLS » de 2025 coexistent comme égales ; l'IA choisit arbitrairement → Montreal West United Church.
- Le prompt n'oblige jamais l'IA à reporter la date/source dans sa sortie, et le JSON de sortie ne contient que `narrative` + `action_items`. Aucune structure `fait → source → date` n'existe → « touches qui collent » sans date, « d'où vient ça ? » impossible.
- Une observation/réparation déjà faite ressort comme à faire car rien ne la marque résolue.

### Symptôme 2 — Mauvais scope d'entité
- **Estimés scopés au client, pas au piano.** `_batch_fetch_gazelle_estimates` (l.1177) interroge `allEstimates(filters: {clientId})`. `_summarize_estimate` capture pourtant `piano_id` (l.1297) **mais ne l'utilise jamais pour filtrer** → l'estimé « cordelettes de ressort de marteau Yamaha » de janvier 2026 remonte sur un RV PdA d'un autre piano.
- **Langue depuis le foyer, pas le client.** `_detect_language_from_locale` (l.696) lit `client.get('locale')` — **mais `locale` n'est jamais synchronisé** (la sync `sync_clients` ne l'écrit pas, alors que la query GraphQL `defaultClientLocalization { locale }` le récupère déjà). La source « autoritaire » est donc morte, et on tombe toujours sur `_detect_language_from_client` (l.707) qui matche « anglo » n'importe où dans les notes fusionnées du foyer → Hélène Langevin (francophone) taggée anglophone à cause de son mari.

### Symptôme 3 — Données manquantes
- Pas de date du dernier entretien annuel PLS, pas de détection des PLS en retard (>12 mois).
- Événements PERSONNELS (Orford…) non affichés : le sync **extrait** `type` et `isAllDay` (`sync_appointments` l.808-809) mais **ne les écrit jamais** (aucune colonne `event_type`/`is_all_day` sur `gazelle_appointments`), et `_generate_one_briefing` droppe tout RV sans `client_external_id` (l.237-239).
- RV de Margot sans initiale : `resolve_technician_name` retourne `""` pour les `ADMIN_STAFF_IDS` (dont Margot), donc le frontend n'a aucune initiale à afficher.

**Conclusion :** la fiabilité est impossible tant que les faits ne sont pas réifiés. La solution centrale est d'introduire une **couche de Faits** entre l'extraction et la génération.

---

## 2. Architecture cible

### 2.1 Principe directeur : déplacer le raisonnement hors de l'IA
On insère une **couche de Faits** (Fact layer). Un Fait est l'unité atomique traçable. L'IA ne reçoit plus de données brutes : elle reçoit une liste de Faits **déjà datés, sourcés, scopés au bon piano/client, et classés courant/historique**, plus un bloc **« État actuel faisant autorité »** résolu en Python. Le prompt passe de « résume tout ça » à « raconte ces faits-ci, tels quels, sans juger leur fraîcheur ».

> **Décision d'architecture #1 — l'IA raconte, le Python décide.** Le scoring récence/supersession, le scope piano, la langue et l'état PLS sont calculés en Python déterministe. L'IA ne fait que rédiger. Compromis assumé : moins de souplesse narrative, mais la fiabilité prime.

### 2.2 Le modèle de Fait (contrat entre couches)
```python
@dataclass
class Fact:
    text: str               # "PLS remplacé par un neuf"
    category: str           # PLS | REPAIR | ESTIMATE | LANGUAGE | ACCESS | DIAPASON | PREFERENCE
    entity_type: str        # 'piano' | 'client'
    entity_id: str          # external_id du piano OU du client concerné
    source_type: str        # 'timeline' | 'estimate' | 'piano_field' | 'client_notes' | 'invoice'
    source_id: str          # external_id de l'entrée/estimé source (pour "d'où vient ça")
    source_label: str       # "Note de Nicolas du 2025-03-12" / "Soumission #1234 du 2026-01-08"
    occurred_on: date|None  # None = non daté => signal de prudence, jamais présenté comme actuel
    status: str             # 'current' | 'historical' | 'superseded' | 'resolved' | 'done' | 'undated'
    superseded_by: str|None # source_id du fait plus récent qui l'annule
    confidence: float       # 1.0 champ structuré, 0.6 heuristique texte
```

> **Décision d'architecture #2 — Faits en mémoire/cache, pas de table en phases 1-3.** Les Faits sont calculés à la volée et sérialisés (`asdict`) dans le dict briefing, donc dans le cache existant (`briefing_cache.py`, `system_settings`, TTL 4h). Aucune migration. Une table `briefing_facts` ne devient utile qu'en phase 5 (audit/correction fait-par-fait). *Désaccord résolu :* la conception qualité_donnees proposait des tables `source_corrections` / `data_quality_issues` dès le début — on les repousse en phase 5, hors du chemin critique.

### 2.3 Nouveau sous-package
```
modules/briefing/facts/
├── __init__.py
├── fact_model.py      # dataclass Fact + sérialisation JSON
├── extractors.py      # data brute -> List[Fact] (un extracteur par source)
├── scoping.py         # filtre les Faits sur le bon piano / bon client
├── recency.py         # scoring date + supersession + courant/historique
├── language.py        # détection langue robuste (remplace les 2 heuristiques actuelles)
└── pls_lifecycle.py   # état PLS : installé/remplacé + dernier entretien + retard >12 mois
```

### 2.4 Flux cible dans `_generate_one_briefing`
```
appt + client + pianos + timeline + estimates + past_appts
  -> [1] EXTRACTION   extractors.extract_all(...)        -> List[Fact] daté, sourcé
  -> [2] SCOPING      scoping.scope_to_appointment(...)  -> estimés/notes du BON piano
  -> [3] RECENCE      recency.resolve(...) + pls_lifecycle -> current/historical/superseded
  -> [4] LANGUE       language.detect(client)            -> EN/None + source
  -> [5] GÉNÉRATION   _call_narrative_ai(facts_current, facts_historical, pls_status)
  -> [6] VALIDATION   drop des faits cités sans source traçable
  -> briefing = { narrative, action_items, facts[], flags, pls, language_source, ... }
```

### 2.5 Contrat de sortie IA — hybride (narratif + faits)
> **Décision d'architecture #3 — sortie hybride, additive, rétrocompatible.** *Désaccord résolu :* architecte/qualité voulaient garder `narrative` quasi inchangé ; ia_prompt voulait du structuré. On garde `narrative` (Nicolas veut un paragraphe) ET on ajoute `facts[]`/`faits_cles[]` pour l'UI et la validation. Un frontend qui ignore `facts[]` continue de marcher.

```json
{
  "narrative": "Paragraphe québécois, chaque fait daté.",
  "action_items": ["..."],
  "facts": [
    {"fact": "PLS remplacé par un neuf", "date": "2025-04-12", "status": "current",
     "source_label": "Soumission #1234, avril 2025", "category": "PLS"}
  ]
}
```
La provenance vit d'abord dans le **pré-traitement Python** (les Faits). `facts[]` sert l'UI (badge date + tooltip source, repli « historique ») et la **validation post-IA** : tout fait cité dont la source n'existe pas dans la liste d'entrée est retiré avant retour. Anti-hallucination transformé d'une règle molle en contrainte vérifiée.

### 2.6 Provenance côté frontend (`BriefingCard.jsx`)
- `narrative` reste l'affichage principal (inchangé).
- Sous le narratif / niveau 2 « Voir plus » : rendre `facts` (status `current`/`undated`) en puces avec `source_label` + date — le « d'où vient ça ? » de Nicolas.
- `undated` → mention discrète « (date inconnue) ». `superseded`/`historical` → repliés sous « Historique », jamais en niveau 1.
- PLS : badge rouge si `pls_overdue`.

### 2.7 Cohabitation cache & coût
- Scoring déterministe calculé **avant** mise en cache → pas de recalcul au service.
- Le prompt **rétrécit** (faits triés/dédupliqués, superseded et hors-piano retirés vs timeline brute) → coût IA stable ou en baisse, malgré le JSON de sortie. Un seul appel IA par RV, en parallèle (`asyncio.gather`).
- Les blocs PERSONAL ne déclenchent **aucun** appel IA (court-circuit) → allègement supplémentaire.

---

## 3. Phases livrables

> Mécanique de bascule : feature flag `flag_briefing_facts` (mécanisme `/admin/flag` déjà présent, briefing_routes l.929). Run A/B sur les 3 cas réels (Montreal West, PdA cordelettes, Hélène) avant adoption.

### Phase 0 — Fondation & quick wins (aucun risque, valeur immédiate)
**Objectif :** débloquer les sources mortes côté sync + livrer les corrections isolées que Nicolas mesure tout de suite. Aucun changement du pipeline IA.

**Fichiers touchés :**
- `modules/sync_gazelle/sync_to_supabase.py` :
  - `sync_clients` (~l.445) : écrire `'locale': (client_data.get('defaultClientLocalization') or {}).get('locale')` dans `client_record` (la query le récupère déjà ; colonne `gazelle_clients.locale` via `add_client_locale_fields.sql` déjà présent — vérifier/appliquer).
  - `sync_appointments` (l.829-847) : écrire `event_type = appt_data.get('type')` et `is_all_day = appt_data.get('isAllDay')` dans `appointment_record` (+ colonnes SQL `event_type text`, `is_all_day boolean`).
- `modules/briefing/ai_extraction_engine.py` (`resolve_technician_name`, l.148-156) : retirer le early-return `ADMIN_STAFF_IDS` pour que Margot retourne son prénom comme **propriétaire de RV**.
- `modules/briefing/client_intelligence_service.py` (l.489-490) : déplacer le filtrage `ADMIN_STAFF_IDS` ici (point d'usage timeline), pour qu'il s'applique **uniquement** à l'historique technique, pas à l'affichage du propriétaire de RV.

**Quick wins inclus** (voir §4) : initiale Margot, persistance `locale`, persistance `event_type`/`is_all_day` (pré-requis Orford et scope).

**Garde-fous :** aucune mutation Gazelle (lecture/sync seule) ; ne pas réécrire `dampp_chaser_installed`. Découplage admin = ne pas repolluer l'historique technique avec Margot/Louise.

**Vérification :** après un sync, `gazelle_clients.locale` peuplé pour un échantillon (Hélène, quelques privés) ; `gazelle_appointments.event_type`/`is_all_day` peuplés ; un RV de Margot affiche « M » dans Ma Journée ; ses notes restent hors historique technique d'un piano.

---

### Phase 1 — Extraction, scoping & langue (le coeur des bugs de scope)
**Objectif :** réifier les sources en Faits, scoper estimés/notes au bon piano, fiabiliser la langue. Livre **le fix PdA** et **le fix Hélène**.

**Fichiers touchés :**
- `modules/briefing/facts/fact_model.py`, `extractors.py`, `scoping.py`, `language.py` (créés).
- `modules/briefing/client_intelligence_service.py` : brancher extraction+scoping+langue dans `_generate_one_briefing` derrière `flag_briefing_facts`.
- `core/gazelle_api_client.py` / `gazelle_api_client_incremental.py` : confirmer que le champ langue du `defaultContact`/`defaultClientLocalization` est bien récupéré dans toutes les queries clients (incrémentale incluse). Vérifier le nom exact via `/briefing/introspect`.

**Détails :**
- `extractors.py` : un extracteur par source. `extract_estimate_facts` émet **un Fact par estimé avec `entity_id = piano_id`** (l.1297 enfin exploité). `extract_repair_facts` détecte les marqueurs de résolution (« réparé », « réglé », « remplacé », « fait ») → pré-classe `resolved`. Chaque Fact porte un `source_label` lisible.
- `scoping.py` : un Fact `entity_type='piano'` ne passe que si `entity_id == piano_du_RV.external_id`. Estimé **sans piano** → rétrogradé en Fact client à faible priorité. Estimé d'un **autre** piano → exclu du prompt mais **conservé** dans le payload (`critical_estimates_autres_pianos`) pour audit/UI, jamais fusionné au piano courant.
- **Garde-fou piano non matché :** `_match_piano_from_context` doit renvoyer un booléen `matched_confidently` (True seulement si match par SN ou par salle/location). Si le piano est un fallback (`pianos[0]`), **ne pas affirmer le scope** : rabattre tous les estimés en « client_sans_piano » (règle prudente). Évite d'attribuer faussement un estimé sur un RV institutionnel mal matché.
- `language.py` — priorité stricte avec source :
  1. `client.locale` (autoritaire). Si présent et `fr*` → retourner un sentinelle « FR confirmé » qui **bloque** le fallback notes (corrige le bug : aujourd'hui `fr*` retourne `None` et déclenche le fallback).
  2. Sinon, note du **client** seulement, marqueur **non rattaché à un tiers** : ignorer « anglo » si à proximité de `mari/conjoint/époux/épouse/femme/partenaire/fils/fille/enfant`.
  3. Ambigu → `None`, pas de badge. **Sous-signaler plutôt que mal signaler.**

> **Désaccord résolu (langue) :** tous les spécialistes convergent — `locale` autoritaire d'abord, heuristique durcie en secours, `None` si doute. On retient en plus le sentinelle « FR confirmé » (domaine_piano) pour empêcher le fallback de réécraser un `fr` fiable.

**Garde-fous :** ne pas supprimer d'info utile (estimés d'autres pianos conservés en bucket séparé) ; pas d'invention ; aucune mutation. Comparer ancien vs nouveau pipeline sur PdA + Hélène avant bascule du flag.

**Vérification :** sur le RV PdA, l'estimé cordelettes Yamaha **n'apparaît plus** (mauvais piano). Hélène Langevin **n'est plus** taggée anglophone (`language_source` = `locale_gazelle` ou `None`). Un RV avec piano fallback ne montre aucun estimé scopé à tort.

---

### Phase 2 — Récence, supersession & cycle de vie PLS
**Objectif :** donner l'état actuel faisant autorité, étiqueter le périmé, dater le PLS et détecter les retards. Livre **le fix Montreal West**.

**Fichiers touchés :**
- `modules/briefing/facts/recency.py`, `pls_lifecycle.py` (créés).
- `modules/briefing/client_intelligence_service.py` : appeler `recency.resolve` + `pls_lifecycle`, réécrire `NARRATIVE_PROMPT`, enrichir `flags`/`action_items`.

**Détails :**
- `recency.py` : grouper par `(category, entity_id)`. Le plus récent daté = `current` ; les antérieurs = `superseded` (`superseded_by` = source_id du courant). Non daté = `undated`. Supersession **par catégorie+entité**, pas par NLP (déterministe, débuggable).
- `pls_lifecycle.py` encode les transitions métier connues (installé → remplacé → retiré) pour que « PLS remplacé/neuf 2025 » annule explicitement « PLS ancien/à vérifier » même formulation différente.
  - **Définition métier de l'entretien annuel PLS** (signal fort) : entrée timeline du **piano** contenant `pad`/`buvard`/`traitement de l'eau`/`pad treatment`/`humidtreat`/`bouteille`/`mèche`/`entretien PLS` + verbe d'action. Distinct du **signal faible** (relevé humidité/température via `service_reports._extract_temp_humidity`, « réservoir rempli », « housse ») qui prouve que le système a été vu mais pas entretenu.
  - Calcul : `pls_last_serviced` (dernier signal fort), `pls_last_seen` (signal fort ou faible).
  - Seuils : à jour < 12 mois (silence) ; **en retard ≥ 13 mois** (tolérance 1 mois) → `pls_overdue=True` ; PLS présent mais aucun signal fort jamais trouvé → `pls_maintenance_unknown=True` (jamais « jamais entretenu » : la fenêtre sync timeline est limitée).
  - **Garde-fou non-invention :** « en retard » ne se déclenche **que** si `pls_last_serviced` est une vraie date. Sinon « dernier entretien non daté dans l'historique disponible ».
- `flags` enrichis : `{pls, pls_last_serviced, pls_overdue, pls_maintenance_unknown}`. Si overdue → **action_item Python déterministe** (pas via l'IA) en tête : « PLS : dernier entretien {date} (+{n} mois) — vérifier réservoir/pads ».
- Réécriture `NARRATIVE_PROMPT` autour de FAITS COURANTS / FAITS HISTORIQUES + bloc « ÉTAT ACTUEL DU PLS (faisant autorité) » :
  - current → présentable comme actuel ; historical/superseded → seulement « auparavant », jamais « à faire » ; undated → dire explicitement « date inconnue », ne pas inventer.
  - Datation obligatoire : tout fait cité porte son mois+année issu de la ligne source.
  - Ne jamais qualifier d'« ancien » un élément marqué neuf/remplacé dans l'état actuel.

**Piège fenêtre timeline :** la sync timeline courante est limitée (~30 j). Pour un calcul fiable du retard >12 mois, s'appuyer sur le backfill complet (`/admin/backfill-all`) déjà disponible ; à défaut, requête live Gazelle ciblée par piano au moment du briefing (au plus un appel par piano PLS).

**Garde-fous :** pas de supersession sans preuve (un défaut sans entrée de résolution postérieure reste « signalé en [date], statut inconnu », pas « résolu ») ; UTC→Montréal pour les dates affichées (corriger le `[:10]` brut, l.484) ; aucune mutation.

**Vérification :** Montreal West → « PLS remplacé en 2025 », l'ancienne note marquée historique, jamais « PLS ancien » au présent. Un piano PLS sans entretien >13 mois génère l'action_item overdue. « Touches qui collent » d'Andrea Chavez s'affiche daté ou « (date inconnue) », jamais comme certitude actuelle.

---

### Phase 3 — Événements personnels & calendrier complet
**Objectif :** afficher Orford/perso/fériés comme entrées de calendrier sans IA.

**Fichiers touchés :**
- `modules/briefing/client_intelligence_service.py` : `_fetch_appointments` (l.1005) laisse passer PERSONAL/HOLIDAY (garder CANCELLED + batch-push exclus) ; ajouter `display_kind ∈ {appointment, personal, holiday}` à partir de `event_type`. `_generate_one_briefing` : court-circuit en tête — si `display_kind != 'appointment'` ou pas de client → retourner un objet minimal `{kind, appointment:{time,title,is_all_day}, narrative:"", flags:{}}` **sans appel IA**.
- `frontend` (`MaJournee.jsx`/`BriefingCard.jsx`) : rendre les entrées `personal`/`holiday` en lecture seule (heure ou « journée » si `is_all_day`, titre brut, marqueur « perso »).

**Garde-fous :** ne jamais inventer la logistique d'un bloc perso (titre brut seulement, pas de phrase sur « le piano »/« l'accès ») ; MEMO/BLOCKED masqués par défaut (à confirmer avec Allan) ; règle institutionnelle km/avis inchangée (elle gouverne les alertes, pas l'affichage).

**Vérification :** un bloc Orford apparaît dans Ma Journée avec son titre et son horaire, sans narratif IA ni flags client.

---

### Phase 4 — Provenance frontend complète
**Objectif :** rendre visible le « d'où vient ça ? » sur chaque fait.

**Fichiers touchés :** `frontend/src/components/BriefingCard.jsx` (sérialisation `facts[]` déjà au dict en phase 1-2 ; ici on enrichit l'affichage : badge date, tooltip `source_label`, repli « Historique », style grisé pour historical, mention « (date inconnue) »).

**Garde-fous :** additif, rétrocompatible.

**Vérification :** Nicolas peut, sur chaque fait, voir date + source et déplier l'historique.

---

### Phase 5 — Raffinements (optionnel, après adoption ≥ 2 semaines)
**Objectif :** boucle de correction à la source + audit qualité.

**Fichiers touchés (créés/étendus) :**
- Table `briefing_facts` (audit/correction fait-par-fait) branchée sur « Ajuster l'Intelligence » (`ai_training_feedback`).
- `api/briefing_routes.py` : scope `source` dans `/feedback/analyze` (proposition de correction Gazelle, **jamais auto-appliquée**) → table `source_corrections` (status `pending`) + notif Allan ; route d'application après approbation.
- `modules/briefing/data_quality_checks.py` (cron post-sync) : `locale manquant`, `conflit langue locale vs note`, `PLS installé sans entretien <12 mois`, `PLS fantôme (notes disent retiré)`, `estimé orphelin sans piano_id`, `note non datée`.
- `briefing_cache.py` : invalidation ciblée du briefing après correction appliquée.
- Mutations : réutiliser le pattern `rv_item_enrichment.py` (`enrich_rv` : dry-run, vérif identité client/piano, `mutationErrors`, read-modify-write sur un seul champ).

**Garde-fous :** **aucune** mutation auto ; approbation Allan obligatoire ; vérif identité avant écriture (anti-contamination type #11915) ; jamais de mutation sur `dampp_chaser_installed`/`tags`/token par cette voie ; aucune création de piano (limite ~1000).

**Vérification :** un signalement « faux » de Nicolas remonte une `source_correction`, Allan approuve, la mutation s'applique en dry-run d'abord, le cache du briefing est invalidé.

---

## 4. Quick wins sans risque (Phase 0, livrables en parallèle)

| Quick win | Action | Fichier |
|---|---|---|
| **Initiale Margot** | Retirer early-return `ADMIN_STAFF_IDS` de `resolve_technician_name` ; filtrer admin au point timeline | `ai_extraction_engine.py` l.148-156 ; `client_intelligence_service.py` l.489-490 |
| **Persister `locale`** (débloque tag Hélène) | Écrire `locale` dans `sync_clients` | `sync_to_supabase.py` ~l.445 |
| **Persister `event_type`/`is_all_day`** (débloque perso) | Écrire dans `appointment_record` + colonnes SQL | `sync_to_supabase.py` l.829-847 |
| **Tag Hélène** (fix logique, complète Phase 1) | Durcir l'heuristique : ignorer marqueur langue rattaché à un tiers ; `locale fr*` bloque le fallback | `client_intelligence_service.py` `_detect_language_*` |
| **Scope piano des estimés** (fix logique, Phase 1) | Filtrer `e['piano_id'] == rv_piano_id` avant le prompt ; bucket séparé pour les autres pianos | `_generate_one_briefing` |
| **Date dernier PLS** (Phase 2) | `pls_lifecycle` : `pls_last_serviced` + `pls_overdue` | `facts/pls_lifecycle.py` |

> Les trois premiers sont du pur sync/config (risque nul). Les trois suivants sont du Python isolé mais bénéficient du flag pour A/B — d'où leur ancrage formel en Phase 1-2, livrables tôt.

---

## 5. Risques & garde-fous transverses

- **Ne jamais inventer.** Validation post-IA (drop des faits sans source traçable) + règle « date inconnue » + seuils PLS qui ne se déclenchent que sur vraie date. Donnée manquante = « inconnu dans l'historique disponible », jamais une valeur devinée.
- **Ne pas supprimer d'info utile.** Le périmé est **étiqueté historique**, pas masqué ; les estimés d'autres pianos restent dans le payload (bucket d'audit). On écarte/étiquette dans le prompt, on ne détruit rien.
- **Mutations Gazelle prudentes.** Phases 0-4 = lecture seule, zéro mutation. Phase 5 seulement : dry-run, vérif identité client/piano, jamais `dampp_chaser_installed`/`tags`/token, jamais d'auto-application.
- **Limite ~1000 pianos.** Aucune création de piano à aucune phase.
- **Pas d'emojis dans le code** (crash cp1252) : ancres `[F1]`/`facts`, pas de symboles ; ne pas étendre les emojis existants.
- **Français du Québec** dans le prompt et l'UI.
- **Coût/latence.** Prompt qui rétrécit (faits triés, superseded/hors-piano retirés) ; court-circuit perso = zéro token ; un seul appel IA par RV ; cache 4h conservé. Validateur = Python pur, coût nul. Le seul appel réseau supplémentaire possible (requête PLS live par piano, Phase 2) est borné à un par piano PLS et évitable via backfill.
- **Timezone.** UTC→Montréal pour toute date affichée (le `[:10]` brut actuel est un bug latent à corriger en Phase 2).
- **Bascule contrôlée.** `flag_briefing_facts` permet l'A/B sur les 3 cas réels avant adoption ; pas de big-bang.

---

## 6. Ce qu'on attaque EN PREMIER

**Phase 0, dans cet ordre exact (risque croissant, déblocage maximal) :**

1. **`locale` dans `sync_clients`** — une ligne, débloque tout l'étage langue (sans elle, le fix Hélène est impossible). Lancer un sync, vérifier le peuplement.
2. **`event_type` + `is_all_day` dans `sync_appointments`** (+ colonnes SQL) — pré-requis bloquant pour les événements perso (Phase 3) et utile au scope. Sans ça, on coderait des heuristiques de texte fragiles.
3. **Initiale Margot** — découplage `ADMIN_STAFF_IDS` ; mesurable immédiatement par Nicolas.

**Puis Phase 1 (premier vrai gain de scope) :**

4. **Scope piano des estimés** — pur Python isolé, supprime tout de suite le bug PdA Yamaha, faible risque.
5. **Langue par contact** — durcissement + sentinelle `fr*`, règle Hélène par la logique (et la donnée `locale` désormais présente confirme).

Ces cinq points livrent quatre des problèmes rapportés (Margot, Hélène, PdA, fondation perso) **sans toucher au pipeline IA ni au prompt**, donc sans risque de régression narrative. La couche Faits complète (extraction → recency → prompt réécrit) suit en Phases 1-2 derrière le feature flag, avec les 3 cas réels comme tests d'acceptation.

---

## 7. Corrections de la revue adversariale (CONTRAIGNANTES)

La revue a vérifié le plan contre le code réel et trouvé des hypothèses fausses ou dangereuses. Ces corrections **priment** sur le texte des phases ci-dessus.

### Bloquants (sinon échec silencieux)
- **[B1] `locale` n'est PAS récupéré par le sync de prod.** Le nightly « full » tourne `sync_to_supabase.py` SANS `--full` → `incremental_mode=True` → utilise `gazelle_api_client_incremental.py`, qui ne fetch PAS `defaultClientLocalization`. Donc écrire `locale` dans `client_record` est un **no-op** tant que la query INCRÉMENTALE n'est pas patchée aussi. **Correction Phase 0 : patcher les DEUX queries** (complète + incrémentale), vérifier le nom exact du champ par introspection, et **valider via un sync incrémental** (pas full).
- **[B2] Le cache n'encode pas le feature flag** (clé = `briefings_{date}`). Activer `flag_briefing_facts` sert quand même l'ancien briefing jusqu'à 4h (cache) → tout A/B mesure du bruit. **Correction : flag + `pipeline_version` dans la clé de cache, OU purge des clés `briefings_*` à chaque flip du flag. À régler AVANT toute bascule.**
- **[B3] Langue institution.** Garder le court-circuit institution (`language=None`) **en dernier** ; le sentinelle « FR confirmé » doit se résoudre en `None` avant sérialisation. Ajouter un cas institution à l'A/B.

### Graves (résultats faux)
- **[G1] Supersession à LISTE BLANCHE STRICTE.** La supersession par `(category, entity_id)` ne s'applique QU'aux catégories à **état singleton** : PLS, LANGUAGE, DIAPASON (peut-être ACCESS). **JAMAIS** REPAIR / ESTIMATE / PREFERENCE — ce sont des listes d'items indépendants. Sinon « marteau remplacé 2025 » marque « table fissurée 2023 » comme historique → on **cache un vrai problème**. C'est le pire résultat possible.
- **[G2] Résolution REPAIR jamais par mots-clés libres.** « réparé/réglé/fait » apparaît dans « à réparer », « pas encore réglé », « reste à faire ». Exiger une **polarité positive** (exclure si précédé de « à », « pas », « reste à », « non ») ET de préférence un **signal structuré** (entrée SERVICE postérieure même piano, ou facture). Doute → `signalé en [date], suivi inconnu`, jamais `resolved`. (Le `_enrich_estimates_completion` existant exige déjà ≥2 mots-clés, l.944 — reprendre cette prudence.)
- **[G3] Estimé sur piano absent de la liste client** → tombe dans « autres pianos »; ce bucket ne doit JAMAIS remonter au prompt ni en niveau 1 UI (audit profond seulement). **Vérifier sur le cas réel** que l'estimé cordelettes Yamaha a bien un `piano.id` ≠ piano du RV avant de déclarer la victoire.
- **[G4] Piano fallback (`pianos[0]`) : scoper AUSSI notes/PLS/label/SN**, pas que les estimés. Si `matched_confidently=False`, dégrader `piano_notes`, `has_pls`, `piano_label`, `serial_number` en « piano non confirmé » ou les omettre. Sinon on bouche une fuite et on en laisse quatre.
- **[G5] `matched_confidently=True` seulement sur SN ou location exacte/normalisée**, jamais sur sous-chaîne par mot (l.1352-1355 : « Salle E » matche n'importe quoi) ni sur marque/modèle/type.

### Moyens / angles morts
- **[M1] Mesurer les tokens in/out** sur les 3 cas réels avant bascule ; augmenter `max_tokens` (500 actuel risque de tronquer `facts[]` → `json.loads` échoue → fallback « Aucune info » = régression à zéro). Parse tolérant + retry.
- **[M2] Validation anti-hallucination uniquement sur `facts[]`** (clé exacte `source_id`), JAMAIS sur le `narrative` (qu'on ne réécrit pas). Ne pas amputer le narratif par un rapprochement texte flou.
- **[M3] `pls_overdue` seulement si couverture timeline vérifiable.** Une date d'entretien réelle mais antérieure à la fenêtre synchronisée créerait un FAUX retard (= invention). Si couverture incertaine → `pls_maintenance_unknown=True`. (Note : `gazelle_timeline_entries` remonte à 2011, 291k entrées — l'historique long existe, mais le backfill par piano doit être confirmé.)
- **[M4] Brancher le pipeline dans `_generate_one_briefing`** (point commun), pas seulement `get_daily_briefings` — sinon `/client/{id}` (`generate_single_briefing`, `pianos[0]` en dur l.1436) garde le bug.
- **[M5] Auditer TOUS les call-sites de `resolve_technician_name`** (collaboration l.361, past-appts l.515, timeline l.497) avant de retirer le filtre admin — décider par site si Margot/Louise doivent apparaître.
- **[M6] Court-circuit perso (Phase 3) ne doit pas bypasser la logique institution km/avis** pour un bloc perso rattaché à VDI/PDA/Orford (mémoire « RV personnels institutionnels »).

### Les 3 garde-fous les plus importants (à graver)
1. **Supersession à liste blanche stricte** (singleton seulement) — ne jamais cacher une vraie réparation/estimé en attente.
2. **Flag + version dans la clé de cache, purge au flip** — avant toute bascule.
3. **Patcher la query incrémentale pour `locale`** + vérifier par sync incrémental — sinon l'étage langue est mort-né.

---

## Annexe — Fichiers concernés (récapitulatif)

**À créer :** `modules/briefing/facts/{__init__,fact_model,extractors,scoping,recency,language,pls_lifecycle}.py` ; (Phase 5) `modules/briefing/data_quality_checks.py`.

**À modifier :**
- `modules/briefing/client_intelligence_service.py` — coeur : pipeline Faits dans `_generate_one_briefing`, réécriture `NARRATIVE_PROMPT` + `_call_narrative_ai`, scope estimés, langue, `_match_piano_from_context` (booléen confiance), court-circuit perso, `facts[]`/`flags` PLS au dict retourné, filtrage admin au point timeline.
- `modules/sync_gazelle/sync_to_supabase.py` — `sync_clients` (`locale`), `sync_appointments` (`event_type`, `is_all_day`).
- `modules/briefing/ai_extraction_engine.py` — `resolve_technician_name` (Margot).
- `core/gazelle_api_client.py` / `gazelle_api_client_incremental.py` — champ langue du contact dans toutes les queries clients.
- `frontend/src/components/BriefingCard.jsx` (+ `MaJournee.jsx`) — provenance `facts[]`, entrées perso/holiday.
- SQL : colonnes `gazelle_clients.locale` (déjà via `add_client_locale_fields.sql`, à vérifier), `gazelle_appointments.event_type`/`is_all_day` ; (Phase 5) tables `briefing_facts`, `source_corrections`, `data_quality_issues`.
