# PTM - Taches prioritaires

> Mettre a jour a chaque session. Les taches terminees vont dans progress.md.

## Refonte soumissions Gazelle (EN COURS — voir soumissions-plan.md)
- [x] Phase 1 — service_bundles.py (4 bundles pilote) + helpers build_service_bundle_item / build_estimate_notes / validate_tier_inclusion
- [x] Phase 1 — tests unitaires (32 nouveaux, 122/122 verts)
- [x] Phase 2 — reconstruction #11914 Isabelle Murray → #11915 test
- [x] Phase 2 — reconstruction #11913 Francine Deraps → #11916 test
- [ ] Phase 2 — **Nicolas + Allan valident visuellement #11915 et #11916** dans Gazelle et donnent feedback mise en page
- [ ] Phase 3 — compléter les ~13 bundles (valider la liste finale avec Allan)
- [ ] Phase 4 — CLI `sandbox/scripts/build_estimate.py`
- [ ] Phase 5 — migrer Nicolas vers le nouveau workflow

## VDI — Notifications et nettoyage
- [ ] **Email à Nicolas le jour même** quand de nouvelles fiches arrivent en `validated` (digest 17h, pas immédiat). Puis rappel chaque jour tant que pas poussé. Vérifier que le digest 17h existant roule bien — c'est exactement ce comportement.
- [ ] **Bouton supprimer** dans l'interface VDI pour les entrées de test/erreurs
- [ ] Vérifier que le digest 17h roule bien sur Render (aucun log trouvé dans scheduler_logs)

## Assistant v5 — Exécution de soumissions (Cerveau)
- [ ] Flow de confirmation pour modifications de soumissions depuis le chat (ajouter tier, modifier item)
- [ ] L'assistant peut agir sur les soumissions, pas juste les analyser en dry-run

## Compagnon d'entreprise (voir compagnon-entreprise-plan.md)
- [x] Phase 1 — Tables Cerveau créées dans Supabase
- [x] Phase 1 — 28 mémoires migrées
- [x] Phase 1 — Chat v5 branché sur le Cerveau (recherche knowledge_entries)
- [ ] Phase 1 — Indexer les documents Google Drive dans knowledge_documents
- [ ] Phase 2 — Hook Claude Code : chaque mémoire sauvée → aussi dans le Cerveau
- [ ] Phase 2.5 — Prototype poste de commande (dashboard état des projets)

## Skill Gazelle (CRÉÉ — voir .claude/skills/gazelle/)
- [x] SKILL.md + reference/ + workflows/ (6 fichiers)
- [ ] Tester le skill en invocation réelle dans une nouvelle session Claude Code
- [ ] Ajouter workflow `update_client.md` (update langue, préférences, tags)
- [ ] Ajouter workflow `query_msl_items.md` (recherche catalogue MSL)

## Sous-projet checklists bundles (LANCÉ — voir bundles-checklists-plan.md)
- [ ] Session de travail avec Nicolas pour valider/corriger les actions par défaut des 4 bundles pilote
- [ ] Ajuster les `default: True/False` pour refléter la pratique réelle
- [ ] Reformulation des libellés client (pas de jargon RPT)
- [ ] Expansion du catalogue (bundles manquants selon soumissions-plan.md)
- **Règle dure** : pas d'accord 3 semaines post-PLS install dans les bundles install

## Volet 1 — Infrastructure de base (FAIT)
- [x] Analyser v5 : structure, endpoints, DB, stack, deploiement
- [x] Documenter dans docs/v5_analysis/volet_1_infrastructure.md
- [x] Setup FastAPI skeleton v6 (sandbox/)
- [x] Connexion Supabase (lecture seule anon, service_role sur Render)
- [x] Auth middleware JWT
- [x] GitHub Actions CI/CD de base
- [x] Config deploiement Render (render.yaml + Dockerfile)
- [x] Tests de base (9/9 pytest verts)
- [ ] Commit + push GitHub

## Volet 2 — Ma Journee (FAIT)
- [x] Analyser le module briefing v5 en detail
- [x] Documenter les inputs/outputs/edge cases
- [x] Construire en v6
- [x] Tests unitaires (24/24 verts)
- [ ] Tests comparatifs v5 vs v6 (requiert ANTHROPIC_API_KEY + données live)

## Volet 3 — Resumes clients (FAIT)
- [x] Analyser les modules client/timeline v5
- [x] Documenter (docs/v5_analysis/volet_3_resumes_clients.md)
- [x] Construire en v6 (7 fichiers)
- [x] Tests (17/17 verts)
- [ ] Tests comparatifs v5 vs v6 (requiert données live)

## Volet 4 — Requêtes langage naturel (FAIT)
- [x] Analyser le module chat/conversation v5
- [x] Construire en v6 (6 fichiers)
- [x] Tests (21/21 verts, 38 total)
- [ ] Tests comparatifs v5 vs v6 (requiert données live)

## Volet PDA/OSM — Place des Arts + OSM (EN PRODUCTION)
- [x] Module PDA v6 complet (matcher IA, parser IA, orphan detector, sync)
- [x] 82 tests v6, feature flags activés (matcher + parser + scanner)
- [x] Watchdog Gmail : surveille @placedesarts.com + @osm.ca, alerte 24h
- [x] Intelligence briefing corrigée (bon piano, bon diapason, pas d'hallucination)
- [x] Alertes non confirmées corrigées (Resend, institutions exclues)
- [x] Architecture frontend v6 documentée (dashboard unifié PDA/OSM)
- [ ] Construire le frontend v6 (10 composants, ~790 lignes)
- [ ] Notification Front (commentaire quand demande détectée)
- [ ] Dashboard OSM (source="osm" dans le même composant)

## Volet Institutions — VDI, Orford, PDA, OSM (EN COURS)
- [x] Config centralisée (4 institutions, diapason par salle, 2 modèles)
- [x] Pianos partagé (inventaire + overlays)
- [x] Service records (draft → completed → validated → pushed)
- [x] Tours (VDI, Orford)
- [x] Humidité (détection + alertes)
- [x] API unifiée (/institutions/{slug}/pianos, service-records, tours, humidity)
- [x] 13 tests (95 total v6)
- [ ] Google Sheets reports par institution
- [ ] Frontend institutions (composants partagés)
- [ ] Frontend venue-requests PDA/OSM (dashboard unifié)

## Frontend v6 test (PROCHAIN)
- [ ] App React minimale avec données mock
- [ ] Page Ma Journée (briefings)
- [ ] Page PDA/OSM (demandes + comparaison v5/v6)
- [ ] Page Client (résumé + pianos)
- [ ] Page VDI (pianos + overlays)
- [ ] Testable localhost sans Supabase

## Volet 5 — Rapports Google Sheets
- [ ] Analyser le module reports v5
- [ ] Construire en v6
- [ ] Tests

## Priorite moyenne
- [ ] Documenter les APIs et endpoints existants (ptm-chat-api)
- [ ] Harmoniser les .env.example / configs entre les repos

## En attente (instructions Allan)
- [ ] Prochaines fonctionnalites a developper
- [ ] Priorites business
