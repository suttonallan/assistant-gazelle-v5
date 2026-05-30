# Piano Tek Musique — Projets en cours

Imprimé le 15 avril 2026

---

## 1. Refonte des soumissions Gazelle

**Statut :** 🟢 actif
**Plan file :** `soumissions-plan.md`

**Ce qu'on fait :** Améliorer la qualité et la lisibilité des soumissions envoyées aux clients. Remplacer les items à 0 $, les descriptions génériques et les avertissements mal placés par des soumissions professionnelles avec des listes d'actions claires, des notes structurées et des options (tiers) logiques pour le client.

**Ce qui est fait :**
- Module v6 avec 6 bundles de service prêts (grand entretien droit/queue, cordes basses, marteaux droit, assemblage marteaux queue, mortaises clavier)
- Nouvel item MSL créé dans Gazelle : assemblage complet des marteaux piano à queue (3 800 $)
- 7 soumissions réelles reconstruites ou améliorées (#11915 Murray, #11916 Deraps, #11919 Sutton, #11920 Ariza, #11921 Murray v2, #11922 Grands Ballets touches, #11880 Grands Ballets PLS+housse)
- Garde de sécurité `update_estimate_safe` pour ne jamais contaminer une soumission par erreur
- Taxes automatiquement cochées (fix du champ `name: tps/tvq`)
- 132 tests automatisés verts dans v6
- Digest quotidien 7h à Louise : clients avec RV imminent qui ont une soumission critique non confirmée (déployé)

**Ce qui reste :**
- Phase 3 : digest quotidien 8h à info@ des soumissions sans relance (tag `relance-faite` dans Gazelle)
- Phase 4 : script CLI pour créer des soumissions sans écrire du code
- Phase 5 : intégrer le workflow dans l'interface v5 pour Nicolas
- Message d'équipe sur le suivi des soumissions (brouillon prêt)

---

## 2. Amélioration des checklists des bundles

**Statut :** 🟡 en attente
**Plan file :** `bundles-checklists-plan.md`

**Ce qu'on fait :** Valider avec Nicolas que les actions par défaut de chaque bundle (ce qui est coché automatiquement quand on sélectionne "Grand entretien droit") correspondent à ce qu'il fait réellement dans 90 % des cas. Si les bundles ne sont pas "tout de suite bons", les techniciens ne les utiliseront pas.

**Ce qui est fait :**
- 6 bundles créés avec des actions plausibles (mais pas validées par Nicolas)
- Contrainte documentée : pas d'accord 3 semaines post-PLS dans les bundles install

**Ce qui reste :**
- 1-2 heures de travail avec Nicolas (idéalement pendant qu'il rédige une vraie soumission) pour passer en revue chaque bundle et corriger les actions par défaut
- Reformulation des libellés pour le client (pas de jargon technique)
- Expansion du catalogue (bundles manquants : PLS install droit/queue, grand entretien queue 2 jours, etc.)

**Bloqué par :** disponibilité de Nicolas

---

## 3. Analytics des soumissions

**Statut :** 🟡 en attente
**Plan file :** `soumissions-analytics-plan.md`

**Ce qu'on fait :** Mesurer le taux de succès des soumissions pour savoir si nos améliorations (meilleure rédaction, suivi systématique) se traduisent en mandats. PTM serait la première entreprise d'accordage au Québec à suivre ça rigoureusement.

**Ce qui est fait :**
- Plan documenté avec les métriques cibles (taux d'acceptation, impact du suivi 7 jours, conversion par technicien, par type de service, etc.)
- Architecture proposée : tags Gazelle comme source de vérité (`relance-faite`, `acceptée`, `refusée`, `réalisée`)

**Ce qui reste :**
- Attendre que la phase 3 (suivi avec `relance-faite`) soit en production 2-3 semaines pour avoir de la donnée
- Ajouter les 3 tags supplémentaires (`acceptée`, `refusée`, `réalisée`) + SOP pour l'équipe
- Accumuler 50-100 soumissions taguées
- Bâtir le dashboard dans v5 (`/soumissions-stats`)

**Bloqué par :** phase 3 du projet soumissions (le tag `relance-faite` est le premier à déployer)

---

## 4. Assistant Gazelle (boîte chat v5)

**Statut :** 🟢 actif (en production)

**Ce qu'on fait :** Transformer la boîte "Accès rapide client" de Ma Journée en assistant intelligent pour Allan et Louise. Recherche client + commandes en langage naturel.

**Ce qui est fait (déployé en production) :**
- Recherche client réparée (cherche par prénom, nom et compagnie — avant ça ne fonctionnait pas)
- Workflow 1 : RV conjoint — « ajoute Margot au RV de Nicolas demain à 14h »
- Workflow 2 : Révision soumission — « améliore la soumission #11919 »
- Workflow 3 : Recherche par mot-clé — « chez quel client JP a réparé du polyester récemment »
- Interprétation temporelle (« récemment » = 3 mois, « cette année » = 12 mois, etc.)
- Visible pour Allan et Louise dans Ma Journée

**Ce qui reste :**
- Ajouter d'autres workflows au fur et à mesure des besoins (ex: marquer client inactif, envoyer relance)
- Éventuellement ouvrir à Nicolas/JP/Margot avec des permissions appropriées

---

## 5. Skill Gazelle (Claude Code)

**Statut :** 🟢 actif

**Ce qu'on fait :** Un "skill" dans Claude Code qui formalise toute la connaissance accumulée sur l'API Gazelle — les pièges du schéma GraphQL, les workflows testés en production, les conventions PTM. Chaque nouvelle session Claude Code charge ce skill automatiquement.

**Ce qui est fait :**
- SKILL.md principal avec les 10 règles absolues
- `reference/schema_gotchas.md` — 20+ pièges validés en production
- `reference/bundles.md` — catalogue + philosophie des bundles
- `workflows/create_estimate.md` — créer une soumission intelligente
- `workflows/clone_appointment_joint.md` — RV conjoint apprenti
- `workflows/read_estimate.md` — lire et analyser une soumission existante

**Ce qui reste :**
- Ajouter les nouveaux workflows au fur et à mesure (search_by_keyword, review_estimate, etc.)
- Tester le skill dans une vraie session fraîche

---

## 6. Quiz PTM

**Statut :** 🟢 actif (contenu à enrichir)

**Ce qu'on fait :** Quiz interactif pour former les techniciens aux bonnes pratiques PTM (comportement chez le client, préparation, nettoyage, etc.)

**Ce qui est fait :**
- Quiz fonctionnel avec thèmes sélectionnables
- Thèmes existants : Préparation avant le RV, Comportement chez le client, Matériel et nettoyage, et d'autres

**Ce qui reste :**
- Allan ajoute des questions au fil du temps (dernière ajoutée : "l'aspirateur en haut")
- Créer un quiz séparé pour la coordinatrice (accueil téléphonique, suivi des soumissions, planification, communication avec les techniciens)

---

## Rappels et éléments en suspens

- **SQL à exécuter** : Allan doit coller `sql/create_critical_estimate_notifications.sql` + `sql/fix_timeline_entry_type_complete.sql` dans Supabase SQL Editor pour activer la déduplication des digests + régler les syncs en warning
- **Password DB Supabase** : le `SUPABASE_DB_PASSWORD` dans .env ne fonctionne plus — réinitialiser dans Dashboard > Project Settings > Database pour débloquer les futures migrations automatiques
- **Message équipe** : brouillon prêt sur le suivi des soumissions ("comme notre jardinier") — à envoyer quand la phase 3 sera déployée
- **Soumissions test à archiver** : #11915 (Murray contaminée), #11917 (vide), #11918 (taxes cassées) — archiver dans Gazelle quand c'est possible
