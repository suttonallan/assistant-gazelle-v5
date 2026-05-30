# PTM - Progress Tracker

> Journal de travail. Ne jamais supprimer d'entrees. Ajouter en haut du fichier.

---

## 2026-05-30 — Watchdog v2 : Python/psutil + keepalive réseau

### Watchdog remote-control — migration PowerShell → Python
- [x] **Diagnostic** : WMI/CIM cassé depuis le 27 mai (OutOfMemoryException, 700+ erreurs). Le watchdog PowerShell ne pouvait plus détecter ni respawn claude.exe.
- [x] **Nouveau `watchdog.py`** : `psutil.process_iter()` remplace `Get-CimInstance`. Même logique one-shot, même Scheduled Task.
- [x] **Keepalive réseau** : HEAD vers api.anthropic.com toutes les 5 min (garde NAT/routeur chaud).
- [x] **Tentative service Windows native** : testée et abandonnée — SYSTEM ne peut pas spawner dans la session user.
- [x] **CLAUDE.md** mis à jour avec architecture v2.

---

## 2026-04-30 → 2026-05-01 — Cerveau PTM, parking PDA, soumissions, Compagnon d'entreprise

### Parking PDA — 3 fix
- [x] **Filtre par technicien** : `_extract_parking_from_appointment()` cherchait "stat 20" dans TOUTES les notes du jour → appliquait le parking d'Allan aux RV de Nicolas. Fix : filtre par `user_id` du tech assigné.
- [x] **Nettoyage 11 faux positifs Nicolas** : parking mis à null sur 11 PDA requests.
- [x] **Un seul parking par tech par jour** : "stat 20" = 20$ pour la visite, pas par piano. Fix : tracking `(tech, date)` déjà assigné. 4 doublons nettoyés.

### Soumissions
- [x] **QRS PNOmation** : ajout transport UPS (1 800$ options A/B, à déterminer option C) + note frais exacts via Drive API export/re-upload.
- [x] **#11932 Émile Proulx Cloutier** : ajout Option 2 (GE + étouffoirs 1½ jour, 1 500$) avec notes de tier et notes de soumission comparatives.
- [x] **Description étouffoirs** : correction Allan → "Rogner et ajuster les étouffoirs pour un fonctionnement parfait, sans bruits parasites ni friction ajoutée au toucher du piano." Sauvée dans le Cerveau.

### Digest soumissions critiques — fix logique
- [x] **#11592 Jacqueline Ifergan** : soumission avril 2024 (2 327$) remontait en alerte alors que facture #5959 (2 327,09$) payée en sept 2024. Fix : vérification automatique des factures PAID dont le montant matche la soumission (±5%).
- [x] Archivé #11592 manuellement en attendant.

### Le Cerveau PTM (Compagnon d'entreprise — Phase 1)
- [x] **4 tables Supabase** créées : `knowledge_entries`, `knowledge_documents`, `knowledge_links`, `knowledge_learning_log` + fonction `search_knowledge()` full-text français.
- [x] **28 mémoires migrées** depuis Claude Code → knowledge_entries.
- [x] **Chat v5 branché sur le Cerveau** : les questions qui ne matchent pas date/RV/client cherchent dans le Cerveau au lieu de retourner "requête non reconnue". Testé : 7/7 questions trouvent la bonne réponse.

### Documentation et workflow
- [x] **Workflow Google Docs** : documenté dans `workflows/edit_google_doc.md` — toujours Drive API export/re-upload, jamais le MCP (API Docs pas activée). Mémoire permanente créée.
- [x] **Plan Compagnon d'entreprise** : `compagnon-entreprise-plan.md` créé avec vision complète (Cerveau, Capteur, Poste de commande, Kit PME).

### VDI
- [x] **Entrées de test supprimées** : 2 fiches draft de test (vd219/vd233) supprimées de `piano_service_records`.

## 2026-04-26 → 2026-04-29 — Grosse session : bugs sync, briefings, PDA, AEC, QRS

### Bugs critiques corrigés (sync Gazelle → Supabase)
- [x] **Sync clients cassée** : 11 colonnes fantômes (`client_type`, `locale`, `preferred_technician_id`, etc.) dans l'upsert → Supabase retournait 400 → aucun nouveau client synchée depuis des semaines. Fix : retirer les colonnes inexistantes.
- [x] **RV invisibles (JP et autres)** : FK violations (`client_external_id` absent de `gazelle_clients`) comptées comme succès (409 silencieux). Fix : détecter `23503` dans le body du 409.
- [x] **Rapport timeline vide après avril 10** : `_fetch_clients_map()` limité à 1000 clients (défaut PostgREST) → PDA/VDI/UQAM introuvables → entries catégorisées "Inconnu" → rapport quasi vide. Fix : pagination. Résultat : Vincent 48→1874 rows, PDA 25→325.
- [x] **Parser PDA dates ISO** : `parse_date_flexible()` ne supportait pas `YYYY-MM-DD` → toutes les lignes tabulaires avec dates ISO ignorées → room vide → warning "champ manquant". Fix : ajout pattern ISO au début de la fonction.
- [x] **Parser PDA colonnes décalées** : quand nom de salle en colonne 0 (ex: "salle claude léveillée"), tout le mapping était décalé. Fix : détection auto du décalage.
- [x] **Parking PDA jamais extrait** : `_extract_parking_from_appointment()` filtrait par `entry_type='SERVICE'` qui n'existe pas (devrait être `SERVICE_ENTRY_MANUAL`/`SERVICE_ENTRY_AUTOMATED`). Fix : correction du filtre.

### Nouvelles fonctionnalités briefings (Ma Journée)
- [x] **Badge mode de paiement** : détecte le mode habituel du client (Comptant/Carte/Virement/Chèque/Débit) depuis les `INVOICE_PAYMENT` du timeline, affiché comme badge 💳 sur la carte.
- [x] **Détection auto soumissions réalisées** : matching keywords items soumission vs SERVICE_ENTRY postérieures (min 2 keywords distincts). Sépare "en attente" vs "réalisées" dans le prompt IA.
- [x] **Prompt soumissions corrigé** : ne demande plus "vérifier avec le client si les travaux ont été faits".

### AEC Saint-Laurent (drive partagé `0AHCFgvwXVis-Uk9PVA`)
- [x] Script mini-enseignement réglage (5-6 min) — audition chargé de cours
- [x] Document "Conception et planification du cours" (18 semaines, 5 blocs, structure type d'un cours)
- [x] Document "Gestion des profils hétérogènes" (pas débutant/avancé, mais musicien/manuel/méthodique/luthier)

### QRS PNOmation (drive partagé `0AIgWHt0PeVQlUk9PVA`)
- [x] Drive partagé créé
- [x] Soumission complète : 3 options (PNO4 Touch / PNO4 NV / OT Over-The-Top), en-tête PTM, liens vidéo, librairie 4200 pièces + 295$/an, extensions garantie 2/4/10 ans, conditions (dépôt, transport en sus, réglage état neuf requis, entretien annuel, délai fin juin)
- [x] Notes de travail QRS

### Alerte RV non confirmé (Lina Vanelli)
- [x] Diagnostic : l'alerte n'a pas été envoyée pour Lina, probablement lié au bug de sync. Le checker fonctionne maintenant correctement.

## 2026-04-22 — Marketing autonome + fix notifications late assignment

### Marketing
- [x] Étude du ton du site pianotechniquemontreal.com → `C:\PTM\guide-ton-ptm.md` (11 sections, DO/DON'T, exemples comparés)
- [x] Plan marketing complet → `C:\PTM\marketing-plan.md` (4 piliers : veille, plan, newsletter, agent conversationnel)
- [x] Agent veille piano quotidien créé (trigger `trig_01TjK51qwUDXSrmCRoKxvHEH`, lun-ven 7h27 Montréal)
- [x] Agent rappel marketing hebdo créé (trigger `trig_016iCuWv9bLBqfADJMkxEneV`, lundi 8h13 Montréal)
- [x] Protocole de session marketing : quand Allan ouvre `marketing-plan.md`, l'agent agit comme une directrice marketing (briefing, propositions, rédaction)
- [x] Premier brouillon d'article de blog : "Combien coûte un accord de piano à Montréal ?" → `C:\PTM\tmp\blog_cout_accord_piano_montreal.md`
- [x] CLAUDE.md mis à jour (sous-projet marketing ajouté)
- [x] Mémoire mise à jour (approbation obligatoire, agent doit avoir le contexte)

### Fix notifications v5 (commits `0f95754` + `1db17c1`)
- [x] **Bug** : Nicolas recevait un avis "nouveau RV" pour un vieux RV modifié. Le trigger se basait sur l'absence en Supabase au lieu de la date de création Gazelle.
- [x] **Fix 1** : Ajout `createdAt` à la query GraphQL — vérifie que le RV a été créé < 24h avant d'alerter "nouveau"
- [x] **Fix 2** : Fenêtre élargie de 24h à 7 jours — les techs planifient leur semaine le dimanche
- [x] **Fix 3** : 4 types de changement détectés avec emails adaptés :
  - `new` → "Nouveau rendez-vous"
  - `reassigned` → "Rendez-vous assigné"
  - `rescheduled` → "Rendez-vous déplacé" (détecte changement date/heure)
  - `cancelled` → "Plage libérée" (RV annulé dans les 7 prochains jours)
- [x] **Anti-doublon horaire** : nouveau champ `last_notified_schedule` (snapshot date+heure) pour éviter les re-notifications
- [x] **Fallback gracieux** : le code fonctionne même sans la migration SQL (retry sans les nouvelles colonnes)
- [x] **NOUVELLES-FEATURES.md** créé pour documenter les changements pour v6
- [x] **Migration SQL** : `sql/add_change_type_to_late_assignment.sql` (à exécuter dans Supabase)

### Fait plus tard dans la session
- [x] Migration SQL Supabase exécutée (change_type + last_notified_schedule)
- [x] Fix #2 critical estimate digest : exclure clients institutionnels (PDA/VDI/Orford) — commit `5903458`
- [x] Fix #3 critical estimate digest : exclure soumissions archivées — commit `d45b21a`
- [x] Refonte MSL marteaux : "Assemblage complet des marteaux (Abel, manches bambou)" à 3 800 $ (FR + EN)
- [x] Soumission #11929 Mme Joly (Gaveau) créée avec 3 options : GE / +marteaux / +cordes basses
- [x] Soumission #11928 Levasseur (Yamaha G1) refaite avec 3 options (mêmes bundles)
- [x] Les deux soumissions assignées à JP (technicien original)
- [x] Nouvelle règle mémoire : soumissions refaites gardent le technicien original
- [x] Nouvelle règle mémoire : GE ≠ "remise en état complète" → "Révision approfondie pour tirer le maximum des composantes actuelles"

### À faire (Allan)
- [ ] Créer un compte Mailchimp gratuit (mailchimp.com)
- [ ] Relire et approuver le brouillon de blog `tmp/blog_cout_accord_piano_montreal.md`
- [ ] Vérifier visuellement #11928 et #11929 dans Gazelle

---

## 2026-04-21 — Fix alertes RV non confirmés + migration Gmail API + fix Orford Louise

### Contexte
Allan a rapporté que les alertes J-1 pour RV non confirmés n'étaient pas reçues par les collaborateurs (Nicolas pour 2 RV du 20/04, JP pour 1 RV du 21/04). Le statut `alert_logs.status='sent'` mentait : le code entrait silencieusement en « mode simulation » qui retournait True sans rien envoyer.

### Fait
- [x] **Diagnostic root cause** : `modules/alertes_rv/email_sender.py` avait un fallback SMTP qui retournait True en mode simulation. Le `RESEND_API_KEY` manquait (ou le domaine pas vérifié), SMTP aussi → simulation → `status='sent'` dans la DB alors que rien ne partait.
- [x] **Fix fallback JP** (`d5d7e2c`) : `jp@pianotekinc.com` → `jpreny@gmail.com` dans `TECHNICIAN_EMAILS`. L'adresse précédente n'existait pas.
- [x] **Fix menteur simulation** (`34ddc4a`) : retire le `return True` en mode simulation. Désormais si l'envoi échoue, `status='failed'` dans `alert_logs`.
- [x] **Migration Gmail API** (`9eabb4f`) : merge partiel de la branche `claude/gmail-auth-setup-dhvw4` (jamais mergée depuis mars) qui apportait :
  - `core/gmail_sender.py` (nouveau) — OAuth2 avec token chargé depuis `system_settings.GMAIL_TOKEN_JSON` (déjà dans Supabase depuis le 13 mars)
  - `core/email_notifier.py` — Gmail API en priorité, Resend en fallback
  - `modules/alertes_rv/email_sender.py` — chaîne Gmail → Resend → SMTP
  - Scripts test (`test_gmail_send.py`, `test_gmail_from_supabase.py`)
  - Patch import : `SupabaseStorage` direct au lieu de `get_supabase_storage()` qui n'existait pas sur main
- [x] **Test end-to-end validé** : email envoyé à `suttonallan@gmail.com` via Gmail API (id `19db076ec319b0d8`), Allan a confirmé réception dans sa boîte principale.
- [x] **Retrait scheduler doublon** (`3f98d6b`) : `api/alertes_rv.py` avait son propre `BackgroundScheduler` qui dupliquait les jobs 16h/9h de `core/scheduler.py`. Résultat : chaque alerte partait 2 fois. Supprimé, core/scheduler.py reste source unique.
- [x] **Louise — onglet Orford full** (`73a2eb0`) : Louise/Margot étaient routées vers `OrfordDashboard` simple (pas de vue À valider). Maintenant route vers `VincentDIndyDashboard` avec `institution="orford"` comme admin le fait déjà. 3-lignes de changement dans `App.jsx`.

### À noter
- Expéditeur Gmail API = `info@piano-tek.com` (compte autorisé lors de l'OAuth en mars)
- **Pas besoin de `RESEND_API_KEY` sur Render maintenant** — mais le code garde Resend en fallback si le token Gmail expire.
- Le token Gmail se rafraîchit automatiquement via son `refresh_token` — pas d'intervention nécessaire.

### À suivre
- Surveiller les prochaines alertes 16h (ce soir, RV de demain si non confirmés)
- Bug report Nicolas confusion workflow validate/push déjà classé (voir entry 2026-04-19)

---

## 2026-04-19 — Digest 17h + simplification workflow fiches d'accord

### Contexte
Nicolas a exprimé de la confusion sur le workflow validate/push des fiches d'accord. Session de diagnostic qui a révélé plusieurs problèmes en cascade.

### Fait
- [x] **Nouveau module `modules/briefing/push_digest.py`** — digest quotidien 17h lun-ven à info@ listant les fiches validées non poussées, avec escalation CC Allan si ≥3 jours. Aucun email si zéro en attente. Pas de dédup (on veut rappeler tant que pas poussé).
- [x] **Scheduler** — `task_push_digest()` + entrée cron 17h lun-ven dans `core/scheduler.py`.
- [x] **Tests** — `scripts/test_push_digest.py` avec 9 tests unitaires + mode `--live` (monkey-patch EmailNotifier.send_email pour dry-run).
- [x] **Bug fix digest** — première version utilisait `piano_service_records.piano_local` qui n'existe pas. Corrigé par JOIN avec `gazelle_pianos.location` (via `piano_id`/`external_id`).
- [x] **Simplification workflow validate/push** (frontend VDI uniquement) :
  - Retiré le bouton « Terminé » côté tech (step intermédiaire artificiel qui causait 80% de la confusion)
  - Retiré le filtre `.filter(p => p.isCompleted)` dans `handleValidateAll` (bug qui ignorait silencieusement les `draft`)
  - Retiré le bouton « Nettoyer anciens » (devenait dangereux sous nouveau flow — aurait effacé le travail du jour)
  - Cleanup : fonction `markWorkCompleted`, `handleCleanup`, state `tourneeInProgress`, boutons dans `VDI_TechnicianView.jsx`
- [x] **Plan file** — `C:\PTM\digest-accords-plan.md` créé + ligne ajoutée dans tableau « Sous-projets PTM » de CLAUDE.md.
- [x] **Commit + push** — `31b1cef feat(service-records): simplify validation workflow + 17h push digest` → Render auto-redeploy.

### Non fait (cleanup non bloquant, noté dans le plan file)
- Endpoint backend `POST /service-records/{inst}/piano/{id}/complete` — plus d'appelant UI mais laissé en place
- Endpoint backend `POST /vincent-dindy/service-history/tournee-terminee` — idem
- State `isWorkCompleted` / `setIsWorkCompleted` dans `VincentDIndyDashboard.jsx` — dead state harmless

### À suivre
- Nicolas teste le nouveau workflow et le digest 17h pendant 2-3 semaines
- Si le digest ne suffit pas à résoudre la confusion, on reviendra implémenter le bandeau de statut sur le formulaire (option écartée pour l'instant)
- Discussion avec Nicolas re: il croyait avoir tout validé et tout nettoyé — expliquer qu'en réalité il n'avait pas cliqué « Pousser vers Gazelle » (3e bouton)

---

## 2026-04-12 — Skill Gazelle créé

### Fait
- [x] **Skill `gazelle` créé** dans `C:\PTM\.claude\skills\gazelle\` — 6 fichiers :
  - `SKILL.md` — point d'entrée, architecture, imports, 10 règles absolues, triggerwords
  - `reference/schema_gotchas.md` — tous les pièges validés en prod (taxes, nommage, création 2 étapes, mutationErrors, etc.)
  - `reference/bundles.md` — philosophie des bundles, catalogue actuel (4) et cible (13), contrainte PLS
  - `workflows/create_estimate.md` — flow complet soumission intelligente (items → groupes → tiers → create/update, avec exemples #11915 et #11916)
  - `workflows/clone_appointment_joint.md` — flow RV conjoint apprenti (clone type PERSONAL, pas APPOINTMENT)
  - `workflows/read_estimate.md` — lecture/analyse d'une soumission existante (query, filtres, détection de frictions)
- Le skill sera discovert automatiquement au prochain démarrage de session Claude Code dans C:\PTM

---

## 2026-04-11 (suite) — Francine Deraps #11916 + skill-creator + sous-projet checklists

### Fait
- [x] Reconstruction de #11913 Francine Deraps (Lesage 1900 droit) → **#11916 test** (7 482,59 $, total identique à l'original)
  - Démo de **3 bundles** d'un coup : `remplacement_marteaux_droit`, `grand_entretien_droit`, `cordes_basses_complet`
  - Tier 2 strictement inclusif de Tier 1 (l'original l'était déjà — confirmé)
  - Description des garnitures contre-attrapes nettoyée (URL Google Drive tronquée retirée)
  - 3 avertissements piano 1900 remontés dans les notes de soumission
- [x] Email à Nicolas rédigé pour expliquer #11916 vs #11913 et annoncer le sous-projet checklists
- [x] **`anthropic-skills` cloné** dans `~/.claude/skills/anthropic-skills/` + `skill-creator` copié au top-level `~/.claude/skills/skill-creator/` → disponible au prochain démarrage de session Claude Code
- [x] **Sous-projet lancé** : `C:\PTM\bundles-checklists-plan.md` — amélioration des checklists d'actions par défaut des bundles pour qu'ils soient "tout de suite bons" à l'invocation
- [x] **Contrainte dure sauvée** : pas d'accord 3 semaines post-PLS install dans les bundles `pls_install_*` (mémoire `feedback_pls_install_no_followup_tuning.md`)

### Introspection Gazelle — RV conjoints
- **Finding** : Gazelle = **1 event = 1 technicien** (`PrivateEvent.user` singulier, `PrivateEventInput.userId` singulier). Pas de modèle multi-tech natif.
- **Conséquence pour workflow RV conjoint apprenti** : on crée 2 events parallèles, **le 2ᵉ doit être `type: PERSONAL`** (pas `APPOINTMENT`) pour éviter que le client reçoive 2 avis de RV. Sauvé en mémoire (`project_rv_conjoint_personal_type.md`).

### À faire par Allan (ou lors de la prochaine session)
- [ ] Valider visuellement #11915 et #11916 dans Gazelle, donner feedback mise en page
- [ ] Planifier session de travail avec Nicolas pour le sous-projet checklists
- [ ] (rappel mémoire 2026-04-13) Scoper l'exposition des features v6 dans l'UI v5

---

## 2026-04-11 — Refonte soumissions Gazelle : Phase 1 + Phase 2 (bundles + #11915)

### Fait (v6 — module gazelle, Phase 1)
- [x] `service_bundles.py` créé avec 4 bundles pilote (IDs MSL + montants tirés de `allMasterServiceItems` en live) :
  - `grand_entretien_droit` — mit_l6o2sjpCLZn9ZUHi, 1 045 $
  - `grand_entretien_queue_1j` — mit_FQKKxagZOiQQQHYh, 1 045 $
  - `cordes_basses_complet` — mit_2HBYLndAxf1C993j, 2 000 $ (matériel + install fusionnés)
  - `remplacement_marteaux_droit` — mit_pDYrT2B8oxWAJ7ou, 1 250 $
- [x] `build_service_bundle_item()` ajouté à `estimates.py` — surcharge dynamique de `description` avec les actions sélectionnées, respect de l'ordre du bundle
- [x] `build_estimate_notes(body, warnings, signature)` — avertissements dans les notes (plus jamais en items à 0 $)
- [x] `validate_tier_inclusion(tier_base, tier_ext)` — vérifie l'inclusion stricte Tier 2 ⊇ Tier 1 (règle UX friction #1)
- [x] Exports dans `__init__.py` (BUNDLES, BundleError, get_bundle, list_bundle_codes + les 3 helpers)
- [x] 32 nouveaux tests unitaires — **122/122 verts** (90 existants + 32)

### Fait (Phase 2 — validation visuelle sur #11914 Isabelle Murray)
- [x] Lecture de la structure actuelle de #11914 via GraphQL — confirmé la friction #1 : Tier 2 RETIRE le traitement du sommier (200 $) au lieu d'ajouter
- [x] Reconstruction sur le même client (cli_gHubBDzfTFvSfNWI) et piano Schomaker (ins_VXe90AmRj6uneZbD) comme **soumission #11915**
- [x] Tier 1 "Option essentielle" — 5 groupes, total 8 120,70 $ (identique au Tier 1 de #11914)
- [x] Tier 2 "Option recommandée" — inclut TOUT Tier 1 (sommier réintégré) + cordes non-filées + resurfaçage V ; validation d'inclusion stricte passée
- [x] Démo du bundle `cordes_basses_complet` : une seule ligne 2 000 $ avec 5 actions en puces au lieu de 2 lignes séparées
- [x] Avertissements (cordes neuves vont s'étirer, sommier fatigué) dans les notes de soumission, plus aucun item à 0 $
- [x] Notes de soumission marquées `[TEST — ne pas envoyer au client]` en en-tête

### À faire par Allan
- [ ] **Vérifier visuellement #11915 dans Gazelle** vs #11914 original et donner feedback sur la mise en page
- [ ] Valider la liste finale des bundles (Phase 3) — le plan liste 13 bundles cibles
- [ ] Si OK : archiver #11915 (test) une fois la validation faite

### Notes
- v6 client Gazelle n'a pas accès à `system_settings` (anon key seulement) → pour les appels live j'ai utilisé le client v5 qui lit le token Supabase, tout en construisant le payload avec les builders v6
- Le plan complet reste dans `C:\PTM\soumissions-plan.md` (section 7 = checklist)

---

## 2026-04-08 — SEO complet + revue commentaires WP automatisée

### Fait (SEO pianotechniquemontreal.com)
- [x] Audit complet site (29 pages publiques)
- [x] Meta descriptions et titles optimisés sur 28 pages (Yoast via REST API)
- [x] Focus keywords Yoast sur 29 pages
- [x] Open Graph tags (titre + description) sur 29 pages
- [x] Alt text descriptif sur 84 images (102/197 maintenant, vs 18/197 ce matin)
- [x] Code PHP `register_rest_field` ajouté à functions.php pour exposer Yoast à l'API REST
- [x] Rapport SEO complet : `tmp/rapport_seo_complet.md` (incl. plan de maillage interne pour 10 pages)

### Fait (Commentaires WordPress)
- [x] 40 spams supprimés (casinos, SEO bots, pharmacie) sur les 44 en attente
- [x] 3 commentaires légitimes approuvés et répondus en ligne (Steven Young Chang, Martin Perrin accréditation, Martine Allard U1 Dampp Chaser)
- [x] Réponse à Martine inclut lien Gazelle scheduling + offre inspection à distance Zoom/FaceTime lundi/vendredi
- [x] **Trigger quotidien créé** : `Revue commentaires WP PTM` (8h Montréal / 12h UTC)
  - Trie spam vs légitime, supprime spams, crée brouillon Gmail avec suggestions de réponses pour approbation
  - ID: trig_01DtMDpdBhVsGAkyxzQEo2FY

### Reste à décider
- [ ] Commentaire 665 (Touron — Bösendorfer 1/2) : contexte flou, à clarifier ou jeter
- [ ] Maillage interne manuel (10 pages, page builder Elementor — pas API)
- [ ] Enrichissement des 8 pages thin content (<300 mots)

---

## 2026-04-05 — Institutions v6 + fix VDI + plan frontend test

### Fait (v6)
- [x] Module institutions complet : config, pianos, service records, tours, humidité (13 tests, 95 total)
- [x] Config centralisée 4 institutions avec diapason par salle
- [x] Documentation architecture frontend PDA/OSM unifié
- [x] Documentation volet institutions (2 modèles : tour vs request)
- [x] v6 backend lancé localement sur Mac (localhost:8080, Swagger fonctionnel)

### Fait (v5)
- [x] Fix validation fiches de service : le gestionnaire peut valider draft directement (pas besoin de "compléter" d'abord)
- [x] Nettoyé 3 fiches VDI bloquées en draft (poussées manuellement)

### Plan : Frontend v6 test (prochaine session)
- [ ] App React légère avec données mock (pas de Supabase)
- [ ] 4 pages : Ma Journée, PDA/OSM, Client, VDI
- [ ] Testable localement sur Mac dans le navigateur

---

## 2026-04-04→05 — Intelligence briefing + watchdog PDA + alertes corrigées

### Fait (v5 — intelligence briefing)
- [x] Fix matching piano par numéro de série et salle (priorité SN > location > make > model)
- [x] Enrichissement briefing avec données PDA (salle, piano, diapason de la demande PDA)
- [x] Prompt narratif revu pour institutions : pas de réparations, pas de nombre de pianos, "terminé avant Xh" pas "arriver avant"
- [x] Distinction diapason : institution = règle fixe ("Accord à 440Hz") vs client privé = observation ("Dernier accord à 441.25Hz")
- [x] Anti-hallucination : NE JAMAIS inventer codes d'accès, téléphones, diapasons
- [x] Ne pas mélanger les infos de lieux différents d'un même client (Maison Symphonique vs Espace OSM)
- [x] Ne pas dire "premier RV" pour les pianos d'institutions
- [x] Fix RV fantômes : exclusion des CANCELLED des briefings + nettoyage sync étendu à J+14
- [x] Fix alertes non confirmées : Resend au lieu de SendGrid (les emails ne partaient pas)
- [x] Institutions exclues des alertes "non confirmé" (pas de confirmation attendue)
- [x] Institutions incluses dans alertes "dernière minute" (un autre tech peut être assigné)
- [x] Fix late assignment : ne pas envoyer pour des RV déjà passés + dates en français + fallback nom client
- [x] Animation bouton sync PDA
- [x] Noms techniciens dans le dashboard (plus de codes usr_xxx)

### Fait (v5 — watchdog PDA/OSM)
- [x] Scanner Gmail automatique — surveille @placedesarts.com et @osm.ca
- [x] Flag `pda_auto_scanner` ACTIVÉ
- [x] Détection intelligente des réponses (structure, pas mots-clés) — ignore les "ok merci" d'Isabelle/Annie
- [x] Watchlist : demandes détectées mais PAS importées (Nicolas garde le contrôle)
- [x] Alerte après 24h si aucun RV Gazelle créé pour une demande détectée
- [x] Gmail reader mergé depuis branche Mac + fix import SupabaseStorage

### Fait (v6 — documentation)
- [x] Architecture frontend PDA/OSM unifié : un dashboard paramétrable pour les deux sources
- [x] 10 composants (~790 lignes) au lieu de 1 monolithe (1800 lignes)

---

## 2026-04-03 — Feature flags + PDA v6 activé en production + Email parser v6

### Fait
- [x] Système de feature flags (`core/feature_flags.py`) — flags dans Supabase system_settings, cache 60s
- [x] Endpoint `/admin/flag` pour activer/désactiver les flags à distance
- [x] **Flag `pda_v6_matcher` ACTIVÉ** — matching intelligent (données structurées + stop words + IA tiebreaker)
- [x] **Flag `pda_v6_parser` ACTIVÉ** — parsing email par IA au lieu de regex
- [x] Parser v6 copié dans v5 (`modules/pda_v6_email_parser.py`)
- [x] Mark PdA correctement matché à "Marketing Pda" (Nicolas) au lieu de OSM (À attribuer)
- [x] Fix scoring : +10 seulement pour client PDA ou titre "Place des Arts", pas pour clients associés
- [x] Margot Charignon ajoutée dans techniciens_config.py
- [x] Endpoint `/admin/pda-compare` pour comparaison v5 vs v6 (88 demandes testées)
- [x] Résultats comparaison : 63 accords, 4 divergences v6 meilleur, 2 corrigées (stop words)
- [x] Module PDA v6 complet : email_parser + matcher + orphan_detector + sync + compare (82 tests verts)
- [x] Documentation v6 mise à jour (spec PDA, decisions session)

### Plan : Scanner automatique PDA/OSM
- Scanner Gmail détecte emails PDA + OSM automatiquement (gmail_reader.py sur branche Mac)
- Import automatique dans place_des_arts_requests
- Commentaire ajouté dans Front (via Pipedream) pour confirmer à Louise
- Alertes : demande non traitée (PENDING > 24h), pas assigné (À attribuer à J-2)

---

## 2026-04-01→03 — Fixes v5 + Module PDA v6

### Fait (v5 — fixes production)
- [x] Fix rapport Google Sheets vidé : onglets recréés au lieu de clear() + append_rows au lieu de insert_rows (limite 10M cellules)
- [x] Rapport généré une seule fois par nuit (GitHub Actions seulement, scheduler Render désactivé)
- [x] Fix PDA matching : inclure les RV sous d'autres clients (OSM) + chercher par titre "Place des Arts"
- [x] Fix PDA orphan detection : vérifier TOUTES les demandes (liées ou non), pas seulement les non-liées
- [x] Fix PDA sync : revérifier les demandes liées à "À attribuer" quand un meilleur RV existe
- [x] Ajout Margot Charignon dans techniciens_config.py
- [x] Endpoint `/admin/pda-stats` pour statistiques jour/heure PDA
- [x] Réécriture `client_since` : 3 sources, meilleur formatage
- [x] Vérification données historiques : 287,446 entrées timeline présentes

### Fait (v6 — Module PDA)
- [x] `modules/pda/matcher.py` — Matching par données structurées (date + salle + for_who)
- [x] `modules/pda/orphan_detector.py` — Vérifie toutes les demandes
- [x] `modules/pda/sync.py` — Sync complète (link, improve, tech sync, completion)
- [x] 18/18 tests (56 total v6), incluant les 5 cas réels échoués en v5
- [x] Documentation : `docs/v5_analysis/volet_pda_refactoring_spec.md`
- [x] Documentation : `docs/v5_analysis/decisions_session_2026-03-30-31.md`
- [x] Commit : `cfdeecb`

---

## 2026-03-30 — Volet 3 + fixes v5 (notifications, langue, feedback review)

### Fait (v6)
- [x] Volet 3 — Module résumés clients construit (7 fichiers, 723 lignes)
  - `modules/clients/data_fetcher.py` — Fetch async (client, pianos, timeline, appointments, feedback)
  - `modules/clients/smart_summary.py` — Résumés intelligents Python pur (fréquence, mois préféré, climat, réparations, problèmes récurrents)
  - `modules/clients/service.py` — Orchestration + détection overdue (nouveau v6)
  - `api/clients.py` — GET `/clients/{id}/summary` + GET `/clients/search`
  - Détection overdue basée sur l'intervalle moyen réel entre services
  - 17/17 tests pytest verts
  - Documentation : `docs/v5_analysis/volet_3_resumes_clients.md`
  - Commit : `babda2c`

### Fait (v6 — Volet 4)
- [x] Module chat langage naturel construit (6 fichiers)
  - `modules/chat/intent.py` — Détection d'intention 2 tiers (regex rapide + Claude Haiku fallback)
  - `modules/chat/handlers.py` — Handlers par intention réutilisant briefing + clients
  - `modules/chat/service.py` — Orchestration
  - `api/chat.py` — POST + GET `/chat/query`
  - Supporte: day_overview, client_search, client_summary, piano_search, client_history, search_notes, humidity_readings
  - 21/21 tests pytest verts (38 total)
  - Commit : `8d59957`

### Fait (v5 — fixes production)
- [x] Suppression Tier 3 détection de langue (heuristique timeline) — faux positifs type Ariane Girard flaggée bilingue
- [x] Nouveau composant `FeedbackReviewPanel.jsx` — panneau de revue des notes d'intelligence dans Ma Journée
- [x] Fix notifications late assignment :
  - Bug 1 : Nicolas/JP ne recevaient rien (lookup dans table `users` vide → remplacé par `techniciens_config.py`)
  - Bug 2 : Allan recevait des alertes pour des RV anciens (logique `last_notified is None` + `updated_at` faussé par syncs → simplifié à "nouveau RV ou changement de technicien" seulement)
- [x] Analyse et application de feedbacks Place des Arts (Maison Symphonique / Steinway Hambourg)
- [x] Fix multi-pianos dans briefings : quand un client a plusieurs pianos (ex: Polyvalente Sainte-Thérèse), l'IA reçoit maintenant la liste complète et les mentionne tous. Le label piano affiche "+N autre(s)". Règle globale ajoutée dans ai_training_feedback.
- [x] Réécriture `client_since` : 3 sources (timeline + appointments + created_at), suppression logique _SAFETY_BLOCKED
- [x] Amélioration formatage : "depuis 1 an et 7 mois" au lieu de "depuis 1 an"
- [x] Vérification données historiques : 287,446 entrées timeline présentes (2016-2026) ✅
- [x] Fix rapport Google Sheets vidé : ne plus faire clear() quand aucune donnée à écrire
- [x] Endpoint `/admin/timeline-stats` pour vérifier la couverture historique
- [x] Endpoint `/admin/backfill-all` pour relancer un import complet si nécessaire

---

## 2026-03-29 — Fix critique "Ajuster l'Intelligence" + analyse intelligente des feedbacks

### Fait
- [x] Diagnostic : `save_feedback()` appelait `storage.insert_data()` qui n'existe pas dans `SupabaseStorage` → les notes d'Allan n'étaient JAMAIS sauvegardées
- [x] Fix : remplacement par appel REST direct (`http_requests.post()`)
- [x] Ajout support règles globales : notes avec `client_id='__GLOBAL__'` s'appliquent à TOUS les clients
- [x] Nouveau endpoint GET `/api/briefing/feedback` pour consulter toutes les notes
- [x] Nouveau endpoint DELETE `/api/briefing/feedback/{id}` pour désactiver une note
- [x] Commit + push : `594a412`
- [x] **Nouveau flux "Ajuster l'Intelligence" avec analyse IA** :
  - POST `/api/briefing/feedback/analyze` : envoie le commentaire d'Allan à Claude qui suggère des actions (client-spécifique et/ou globale)
  - POST `/api/briefing/feedback/apply` : sauvegarde les actions approuvées
  - Frontend BriefingCard.jsx réécrit : note → Analyser → suggestions avec checkboxes → Appliquer
  - Les actions globales sont injectées dans le prompt de TOUS les briefings
- [x] Build frontend + commit + push : `230df04`

- [x] **Introspection Gazelle API** : endpoint temporaire GET `/briefing/introspect/{type}` pour découvrir les champs disponibles
- [x] **Découverte majeure** : `PrivateClient` a 45 champs (on en fetchait 10), `PrivatePiano` a 46 champs (on en fetchait 12)
- [x] **Champ langue trouvé** : `defaultClientLocalization { locale }` — c'est LE champ officiel (fr_CA/en_US)
- [x] Requête GraphQL GetClients enrichie : +locale, preferredTechnicianId, clientType, lifecycleState, referredBy, noContact*, contact prefs
- [x] Requête GraphQL GetPianos enrichie : +status, size, calculatedLastService, calculatedNextService, serviceIntervalMonths, rental, hasIvory, tags, etc.
- [x] Sync Supabase mis à jour pour stocker tous les nouveaux champs
- [x] Détection langue 3 niveaux : Gazelle locale > notes client > heuristique timeline
- [x] Migration SQL créée : `sql/add_client_locale_fields.sql`
- [x] Commits : `60f9c33`, `0303ce7`

### À faire par Allan
- [ ] Exécuter `sql/add_client_locale_fields.sql` dans le SQL Editor de Supabase pour créer les colonnes
- [ ] La prochaine sync remplira automatiquement le champ `locale` pour tous les clients

### Note
- La table `ai_training_feedback` existait et était correcte, mais jamais alimentée à cause du bug
- Render (backend) + GitHub Pages (frontend) redéploient automatiquement
- Endpoint `/briefing/introspect/{type}` est temporaire — à retirer une fois l'exploration terminée

---

## 2026-03-28 22h30 — Volet 2 : Module Ma Journée construit

### Fait
- [x] Analyse exhaustive du module briefing v5 (935 lignes de service principal)
- [x] Documentation : `docs/v5_analysis/volet_2_ma_journee.md`
- [x] Module Ma Journée v6 reconstruit (7 fichiers, architecture modulaire) :
  - `modules/briefing/constants.py` — Prompt AI, mappings techniciens, config
  - `modules/briefing/flags.py` — Calcul Python des flags (piano_label, client_since, langue, PLS, chien, enfants)
  - `modules/briefing/data_fetcher.py` — Fetch parallèle Supabase (6 requêtes async)
  - `modules/briefing/narrative.py` — Génération narrative Claude Haiku
  - `modules/briefing/service.py` — Orchestration briefings quotidiens + single client
  - `modules/briefing/cache.py` — Cache Supabase system_settings (TTL 4h)
  - `api/briefing.py` — 7 endpoints REST
- [x] 24/24 tests pytest verts
- [x] Commit + push : `c5bd6af`
- [x] Repo GitHub créé : `suttonallan/assistant-v6` (privé)

### Note
- Pas de test end-to-end avec l'API Anthropic (pas de clé ANTHROPIC_API_KEY locale)
- Les mappings techniciens sont encore hardcodés (comme en v5), à dynamiser plus tard

---

## 2026-03-28 21h50 — Volet 1 : Skeleton v6 construit et testé

### Fait
- [x] Vérification auto-start PC : déjà configuré (bat dans Startup + permissions wildcard)
- [x] Création structure dossiers v6 (docs/, sandbox/, tests/)
- [x] Analyse complète du codebase v5 (80+ endpoints, 21 tables, 20 services core)
- [x] Documentation : `assistant-v6/docs/v5_analysis/volet_1_infrastructure.md`
- [x] FastAPI skeleton v6 construit dans `sandbox/` :
  - `app/main.py` — FastAPI app avec CORS, lifespan, versioning API `/api/v1/`
  - `app/config.py` — Pydantic Settings, .env support
  - `app/core/db.py` — Client Supabase (service_role ou anon fallback)
  - `app/core/auth.py` — JWT auth middleware (Supabase tokens)
  - `app/core/timezone.py` — Utils timezone Montreal/UTC
  - `app/core/logging.py` — Structured JSON logging
  - `app/core/notifications.py` — Email (Resend) + Slack
  - `app/core/scheduler_logger.py` — Task logging vers Supabase
  - `app/api/health.py` — Health check avec test DB
- [x] Connexion Supabase validée en lecture (clé anon, pianos OSM visibles)
- [x] Health endpoint testé : `{"api": "ok", "database": "ok"}`
- [x] 9/9 tests pytest verts (config, health, timezone)
- [x] Dockerfile + render.yaml prêts
- [x] GitHub Actions CI workflow créé
- [x] .gitignore configuré

### Note
- `SUPABASE_SERVICE_ROLE_KEY` n'est pas sur ce PC (dans GitHub Secrets + Render)
- La clé anon suffit pour le dev en lecture seule
- Pour le déploiement Render v6, il faudra copier la service role key

### Prochaine étape
- Commit + push vers GitHub
- Commencer volet 2 : module Ma Journée

---

## 2026-03-28 — Fix sync a_faire volet VDI

### Fait
- [x] Diagnostic du bug : a_faire stocke dans 2 tables (overlay + service_records), pas de sync entre les vues
- [x] Fix v5 : sync bidirectionnelle dans `api/vincent_dindy.py` (overlay → service_records) et `api/service_records.py` (service_records → overlay)
- [x] Decision v6 loguee : source de verite unique, eliminer l'overlay

### A deployer
- [x] Commit + push assistant-gazelle-v5 pour que le fix arrive sur Render (verifie 2026-03-28 — deja pousse, commit 666d231 sur origin/main)

---

## 2026-03-28 — Setup initial

### Fait
- [x] Configuration Claude Code en mode autonomie maximale (auto-approve all)
- [x] Clone de tous les repos GitHub dans C:\PTM\
  - assistant-gazelle-v5
  - ptm-chat
  - ptm-chat-api
  - piano-tek-ai
  - ptm-quiz
- [x] Creation du CLAUDE.md global PTM avec protocole de session
- [x] Creation de progress.md (ce fichier)
- [x] Creation de decisions.md avec les 3 premieres decisions
- [x] Creation de todo.md avec les taches initiales
- [x] Memoire Claude Code configuree (profil Allan, projet PTM, preferences autonomie)

### Notes
- Repo `assistant-v6` etait deja present dans C:\PTM\ avant le setup
- GitHub account : suttonallan
- Git config : Allan Sutton <suttonallan@gmail.com>
