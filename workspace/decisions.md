# PTM - Decisions techniques

> Ne jamais supprimer une entree. Ajouter les nouvelles decisions en haut du fichier.

---

## 2026-05-30 — Watchdog : psutil + Scheduled Task, pas service Windows

### DECISION : Garder la Scheduled Task, remplacer WMI par psutil
**Contexte** : WMI/CIM cassé sur la machine (OutOfMemoryException depuis mai 2026). `Get-CimInstance` échoue à 100%. Tentative de service Windows Python (pywin32) abandonnée : un service SYSTEM ne peut pas spawner claude.exe dans la session utilisateur (CreateProcessAsUser + complexité UAC).
**Solution** : Script Python one-shot (`watchdog.py`) appelé par la même Scheduled Task existante. `psutil` lit le command line des process directement depuis le PEB, zéro dépendance WMI. Keepalive réseau ajouté (HEAD api.anthropic.com toutes les 5 min).

---

## 2026-05-24 — Fiabilisation des avis d'annulation de RV (dernière minute)

### DECISION : Centraliser l'avis d'annulation dans un balayage idempotent, plutôt qu'au moment de la transition
**Contexte** : Incident Margot — un RV conjoint (Margot + Nicolas) à Vincent-d'Indy annulé sans qu'aucun avis ne parte. Diagnostic : 18 des 25 annulations de dernière minute depuis le 22 avril (~72 %) n'ont généré aucun avis, pour tous les techniciens. L'avis n'était émis qu'au moment précis de la transition ACTIVE→CANCELLED, par un bloc fragile (re-requête + `try/except` muet, garde-fou « +10 » qui bloque tout), et un 2e chemin (nettoyage 16h `_cleanup_ghost_appointments`) marquait CANCELLED sans jamais notifier.
**Choix** : Nouvelle méthode `_sweep_cancellation_notices()` appelée à chaque sync — balaye les RV passés CANCELLED dans la fenêtre 7 jours (annulés < 48h), et met en file l'avis manquant. Idempotente, et le chemin inline défaillant est supprimé. Le nettoyage 16h écrit désormais `updated_at` pour être vu par le balayage.
**Raison** : L'avis ne dépend plus du chemin qui a marqué l'annulation ni d'un envoi inline fragile. Un seul point fiable.

### DECISION : La dédup de la file d'alertes doit tenir compte du `change_type`
**Contexte** : L'anti-doublon de `_queue_late_assignment_alert` était keyé sur (RV, technicien, date) sans le type. Un avis « nouveau » déjà envoyé bloquait à tort l'avis « annulé » du même RV.
**Choix** : Ajouter `change_type` au filtre anti-doublon.

### DECISION : L'avis d'annulation applique la même règle institution/client que les avis de création
**Contexte** : Le balayage notifiait pour des RV strictement personnels (« Retrait? », « Francine Deraps » = note de planif sans client). Règle métier d'Allan : un RV personnel ne compte (km + avis) que s'il est rattaché à une institution (VD, PDA, Orford) ou à un client.
**Choix** : Filtrer le balayage avec `has_client_or_institution` (`bool(client_external_id) or _is_institution_appointment(...)`), identique à la ligne ~820 du sync.

## 2026-05-01 — Cerveau PTM, parking PDA, soumissions critiques

### DECISION : Le Cerveau PTM dans Supabase remplace les mémoires locales comme source de vérité partageable
**Contexte** : Les mémoires Claude Code sont dans `~/.claude/` sur un seul PC. Elles meurent avec la session, ne sont pas accessibles à l'équipe, et changent de machine = repartir à zéro.
**Choix** : 4 tables `knowledge_*` dans Supabase avec recherche full-text en français. Le chat v5 cherche dans le Cerveau pour répondre aux questions de l'équipe. Les mémoires Claude Code continuent d'exister ET sont dupliquées dans le Cerveau.
**Raison** : Premier pas vers le Compagnon d'entreprise. Le savoir d'Allan doit survivre aux sessions et être accessible à tous.

### DECISION : Parking PDA = un seul par technicien par jour
**Contexte** : "stat 20" dans les notes veut dire 20$ de stationnement pour la visite, pas par piano. Quand Allan fait 2 pianos PDA le même jour, le système doublait le parking.
**Choix** : Tracking `(tech_id, date)` — le parking est assigné au premier RV traité, les suivants du même tech/jour sont ignorés.

### DECISION : Soumissions critiques — vérifier les factures PAID avant d'alerter
**Contexte** : Les techs n'archivent pas les soumissions réalisées dans Gazelle. Résultat : des soumissions d'il y a 1-2 ans remontaient en alerte à chaque nouveau RV du client.
**Choix** : Avant de flagger une soumission comme critique, vérifier si le client a une facture PAID dont le montant matche (±5%). Si oui, le travail est fait — pas d'alerte.
**Raison** : Cas Jacqueline Ifergan #11592 (2 327$, avril 2024) = facture #5959 (2 327,09$) payée en sept 2024.

### DECISION : Google Docs — toujours Drive API, jamais MCP ni API Docs
**Contexte** : 45 min perdues le 30 avril à essayer le MCP google-drive qui utilise l'API Docs (pas activée sur le projet GCP). Le doc QRS avait été créé le 28 avril via Drive API (export HTML / re-upload).
**Choix** : Toujours utiliser `files().export(mimeType='text/html')` → modifier HTML → `files().update(supportsAllDrives=True)`. Documenté dans `workflows/edit_google_doc.md`.

## 2026-04-29 — Détection auto complétion soumissions + sync robustesse

### DECISION : Détecter la complétion des soumissions automatiquement, jamais demander au client
**Contexte** : Le prompt IA demandait au tech de "vérifier avec le client si les travaux ont été faits". Allan ne veut pas ça.
**Choix** : Matching automatique des items de soumission contre les SERVICE_ENTRY postérieures. Minimum 2 keywords distincts pour éviter les faux positifs. Les soumissions sont séparées en "en attente" vs "réalisées" dans le contexte du prompt.
**Raison** : Pas de question gênante au client. Le système infère intelligemment.

### DECISION : Toujours paginer les requêtes Supabase REST qui peuvent dépasser 1000 rows
**Contexte** : `_fetch_clients_map()` (rapport timeline) et `get_data()` (storage générique) ne paginaient pas. Avec 4000+ clients, les 3000 derniers étaient invisibles, cassant silencieusement les rapports et les joins.
**Choix** : Pagination systématique par blocs de 1000 pour toute requête qui pourrait retourner plus de 1000 rows.
**Raison** : Le défaut PostgREST est 1000 rows max. Ne jamais assumer que les données tiennent en une page.

### DECISION : Distinguer les 409 Supabase — conflit d'upsert vs FK violation
**Contexte** : Le sync comptait TOUS les 409 comme "déjà synchée". Mais les FK violations (23503) retournent aussi 409 → des RV disparus silencieusement quand le client manquait de `gazelle_clients`.
**Choix** : Vérifier `23503` dans le body de la réponse 409. Si présent = erreur FK = compter comme erreur, pas comme succès.

### DECISION : Google Drive PTM accessible via service account Supabase
**Contexte** : Allan a configuré la délégation de domaine pour le service account Google stocké dans Supabase (`GOOGLE_SHEETS_JSON`).
**Choix** : Utiliser `subject='asutton@piano-tek.com'` avec scope `drive` pour accéder aux shared drives PTM. Code de connexion documenté dans la mémoire.
**IDs clés** : AEC Saint-Laurent `0AHCFgvwXVis-Uk9PVA`, QRS PNOmation `0AIgWHt0PeVQlUk9PVA`, Soumissions `0ABe1y7szTc16Uk9PVA`.

---

## 2026-04-11 — Refonte soumissions : bundles = 1 item MSL surchargé

### DECISION : Un bundle = une ligne facturée unique, pas N items à 0 $
**Contexte** : Les techniciens documentaient les services via items à 0 $ (détails) ou items à long libellé (avertissements), ce qui polluait la facture et déroutait le client (#11914 Isabelle Murray exemplaire).
**Choix** : Chaque bundle est lié à UN `masterServiceItem` Gazelle (source de vérité du prix) et son champ `description` est surchargé dynamiquement avec une liste formatée d'actions cochées à la carte. Les avertissements remontent dans les `notes` de la soumission via `build_estimate_notes()`.
**Raison** : Rend la friction #1 (inflation visuelle) et #3 (avertissements) impossibles par construction. Le client voit une liste propre et facturée clairement.
**Impact v6** : Toute nouvelle soumission doit passer par `build_service_bundle_item()` ou `build_item_input()` avec descriptions propres — plus jamais d'items à 0 $.

### DECISION : Tier 2 strictement inclusif de Tier 1
**Contexte** : Sur #11914, le Tier 2 retirait le traitement du sommier et ajoutait des cordes — le client ne comprenait pas la différence entre les options.
**Choix** : Règle formalisée en code via `validate_tier_inclusion()` qui lève si Tier 2 ne contient pas TOUS les items de Tier 1. Comparaison par `(masterServiceItemId, name)`.
**Raison** : UX claire — "si je prends l'option 2, je reçois tout l'option 1 + des extras, je ne renonce à rien."
**Impact v6** : La CLI et tout futur builder de soumission doivent appeler `validate_tier_inclusion()` avant d'envoyer le payload.

### DECISION : Bundles en fichier Python versionné, pas table Supabase
**Contexte** : Il fallait choisir où stocker le catalogue des bundles de service.
**Choix** : Fichier `app/modules/gazelle/service_bundles.py` avec dict `BUNDLES`.
**Raison** : Itération rapide, testable unitairement, pas de dépendance d'infra, changements traçables via git. Migration vers Supabase possible plus tard si Allan veut une UI d'édition.

### DECISION : Cordes basses = bundle fusionné (matériel + install)
**Contexte** : En Gazelle, "Cordes des basses" (1 200 $ matériel) et "Installer les cordes des basses" (800 $ labour) sont 2 MSL distincts — 2 lignes sur la facture, ce qui déroute le client.
**Choix** : Le bundle `cordes_basses_complet` pointe sur le MSL matériel mais facture 2 000 $ en une seule ligne "Cordes des basses — fourniture et installation".
**Raison** : Simplifie la lecture côté client. Le `masterServiceItemId` reste un lien traçable vers Gazelle ; le montant fusionné est explicitement surchargé dans `amount_cents` du bundle.
**Impact v6** : Pattern réutilisable pour d'autres bundles "matériel + labour" (ex: cordes non-filées, chevilles + install).

---

## 2026-04-03 — Feature flags pour migration v5 → v6

### DECISION : Migration progressive par feature flags
**Contexte** : Basculer tout le code v5 vers v6 d'un coup risque de briser des fonctionnalités pour les utilisateurs.
**Choix** : Chaque module v6 est derrière un feature flag dans Supabase (system_settings). Flag activé = v6, flag désactivé = v5. Rollback en 60 secondes.
**Raison** : Les utilisateurs ne voient aucune interruption. Allan contrôle le switch. Si problème → retour immédiat à l'ancien code.
**Flags actifs** : `pda_v6_matcher` (matching PDA), `pda_v6_parser` (parsing email PDA)
**Impact v6** : Ce pattern sera utilisé pour tous les modules (briefing, chat, etc.)

### DECISION : Briefing institutions vs clients privés
**Contexte** : L'IA mélangeait les infos de différents lieux d'un même client (OSM: Maison Symphonique vs Espace OSM), inventait des codes d'accès, suggérait des réparations pour des accords standard, et disait "premier RV" pour des pianos réguliers.
**Choix** : Prompt narratif avec règles distinctes pour institutions. Enrichissement du briefing avec les données PDA (salle, piano, diapason). Anti-hallucination stricte. Matching piano par SN et location en priorité.
**Impact v6** : Le prompt institution doit être un template séparé du prompt client privé.

### DECISION : Dashboard unifié PDA/OSM
**Contexte** : PDA et OSM partagent les mêmes salles, pianos, workflow. Le dashboard v5 fait 1800 lignes et ne supporte que PDA.
**Choix** : Un seul dashboard paramétrable (`source="pda"` ou `source="osm"`). 10 composants réutilisables (~790 lignes total).
**Raison** : Ajouter OSM = une route + une config. Zéro nouveau composant.

### DECISION : Scanner PDA/OSM unifié avec notification Front
**Contexte** : Les demandes PDA sont collées manuellement. Louise ne sait pas si une demande a été importée. OSM envoie aussi des demandes pour PDA.
**Choix** : Scanner Gmail automatique qui détecte PDA + OSM, importe dans la même table, et ajoute un commentaire dans Front pour confirmer.
**Raison** : Réduire les étapes manuelles de 6 à 2. Le système travaille pour l'équipe, pas l'inverse.

---

## 2026-03-30 — Briefings multi-pianos

### DECISION : Toujours montrer tous les pianos d'un client dans le briefing
**Contexte** : Le briefing de Polyvalente Sainte-Thérèse ne montrait qu'un piano (Kawai RX-6) alors qu'il y en avait deux à accorder. Le code sélectionnait un "meilleur match" et ignorait les autres.
**Choix** : Passer la liste complète des pianos à l'IA narrative + ajouter un champ `all_pianos` dans la réponse + afficher "+N autre(s)" dans le label piano.
**Raison** : Le technicien doit savoir combien de pianos il va voir, surtout pour les clients institutionnels qui en ont souvent plusieurs.
**Impact v6** : Le module briefing v6 doit gérer nativement la liste de pianos par client, pas un piano unique.

---

## 2026-03-30 — Notifications late assignment : simplification de la détection

### DECISION : Alerter seulement sur nouveau RV ou changement de technicien
**Contexte** : La logique "last_notified is None" comparait updated_at vs created_at pour deviner si un RV était récent, mais Supabase met à jour updated_at à chaque sync → faux positifs (alertes pour des RV existant depuis une semaine).
**Choix** : Simplifier à 2 cas : (1) nouveau RV (pas de old_record en DB) ou (2) technicien a changé et pas encore notifié. Supprimer le cas "last_notified is None".
**Raison** : ~120 lignes de logique fragile remplacées par 10 lignes claires. Zero faux positif.
**Impact v6** : Implémenter cette logique simplifiée directement.

### DECISION : Résolution email technicien via config, pas via table users
**Contexte** : Le notifier cherchait l'email dans la table Supabase `users` qui n'avait pas les entrées de Nicolas et JP → ils ne recevaient jamais de notifications.
**Choix** : Utiliser `techniciens_config.py` (source de vérité centralisée) au lieu de la table `users`.
**Raison** : La config Python est toujours présente et à jour. La table `users` est un vestige non maintenu.
**Impact v6** : Même approche — config centralisée pour les techniciens.

---

## 2026-03-30 — Détection de langue : suppression de l'heuristique timeline

### DECISION : Langue détectée uniquement par Gazelle locale + notes explicites du technicien
**Contexte** : Le Tier 3 (heuristique comptant les mots anglais vs français dans le service history) causait des faux positifs — ex: Ariane Girard flaggée "bilingue" parce que ses notes de service contenaient des termes techniques anglais.
**Choix** : Supprimer le Tier 3. Garder uniquement Tier 1 (champ `locale` de Gazelle) et Tier 2 (marqueurs explicites dans `personal_notes`/`preference_notes` : "anglophone", "bilingue", "parle français", etc.).
**Raison** : La langue d'un client ne se déduit pas du contenu technique de son historique. Seul un technicien qui connaît le client ou le champ officiel Gazelle sont fiables.
**Impact v6** : Ne pas réimplémenter d'heuristique timeline. Tier 1 + Tier 2 seulement.

---

## 2026-03-28 — Sync a_faire entre vues VDI

### DECISION (v6) : Source de verite unique pour a_faire
**Contexte** : En v5, le champ `a_faire` est stocke dans 2 tables (`vincent_dindy_piano_updates` overlay ET `piano_service_records`). Supprimer dans une vue ne supprime pas dans l'autre.
**Choix** : En v6, eliminer l'overlay completement. `piano_service_records` devient la seule source de verite. Cycle lineaire : `todo → draft → completed → validated → pushed`.
**Raison** : Le double-stockage est un defaut de design. Patcher la sync c'est du spaghetti. La v6 doit avoir une architecture propre des le depart.

### DECISION (v5) : Fix temporaire — sync bidirectionnelle a_faire
**Contexte** : Meme bug que ci-dessus, mais on ne refactore pas la v5.
**Choix** : Quand `a_faire` est vide dans l'overlay (Gestion), on vide aussi dans `piano_service_records` actifs, et inversement. 2 ajouts de ~10 lignes chacun, zero changement frontend.
**Raison** : Fix minimal et sans risque. Si la sync echoue, un try/except log le warning sans casser le flux principal.

---

## 2026-03-28 — Setup initial

### DECISION : Structure multi-repo dans C:\PTM\
**Contexte** : Organisation du workspace local pour tous les projets PTM.
**Choix** : Un dossier racine `C:\PTM\` avec chaque repo clone a plat (pas de monorepo).
**Raison** : Chaque repo a son propre cycle de deploiement et sa propre stack. Un monorepo ajouterait de la complexite sans benefice.

### DECISION : Fichiers de suivi globaux (progress, todo, decisions)
**Contexte** : Besoin de continuite entre les sessions Claude Code.
**Choix** : 4 fichiers markdown a la racine de C:\PTM\ relus/mis a jour a chaque session.
**Raison** : Claude Code perd le contexte entre sessions. Ces fichiers servent de memoire persistante projet.

### DECISION : Claude Code en autonomie maximale
**Contexte** : Allan veut un workflow rapide sans va-et-vient.
**Choix** : Auto-approve toutes les commandes, decisions techniques prises sans confirmation.
**Raison** : Gain de temps. Confirmation requise uniquement pour : suppression de repos/branches, changements d'architecture majeurs, deployments.
