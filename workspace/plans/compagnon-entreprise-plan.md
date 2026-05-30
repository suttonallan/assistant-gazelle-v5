# Compagnon d'entreprise — Plan directeur

**Statut :** 🟢 actif
**Créé :** 2026-04-30
**Dernière mise à jour :** 2026-04-30
**Prochain pas :** Inventaire des connaissances PTM déjà capturées + architecture du Cerveau
**Bloqué par :** rien

---

## La thèse

Chaque PME a une ou deux personnes qui portent 80% du savoir opérationnel dans leur tête. Ce savoir meurt quand elles partent. Les solutions actuelles (wikis, manuels, formations) échouent parce qu'elles demandent un effort séparé du travail. Le Compagnon d'entreprise capture le savoir **pendant** que le dirigeant travaille, le structure automatiquement, et le rend accessible à l'équipe via un assistant intelligent.

PTM est le laboratoire. Le produit est universel.

---

## Architecture cible

```
┌──────────────────────────────────────────────────────────┐
│                    INTERFACES                            │
│                                                          │
│  Dirigeant          Équipe              Clients          │
│  (Claude Code,      (Chat web/mobile,   (Chatbot,        │
│   Mac, PC,          interface rôle,     self-service)     │
│   mobile)           notifications)                       │
├──────────────────────────────────────────────────────────┤
│                 COUCHE INTELLIGENCE                      │
│                                                          │
│  Capteur de savoir    Moteur de jugement   Orchestrateur │
│  (observe, extrait,   (applique les        (agit : crée  │
│   propose des règles) règles au contexte)  RV, soumission│
│                                            facture, etc.)│
├──────────────────────────────────────────────────────────┤
│                   LE CERVEAU                             │
│                                                          │
│  Règles métier ─── Savoir-faire ─── Jugement             │
│  (quoi)            (comment)        (pourquoi)           │
│                                                          │
│  Vocabulaire ──── Relations ──── Erreurs                 │
│  (notre langue)   (clients,      (ce qui n'a             │
│                    fournisseurs)  pas marché)             │
├──────────────────────────────────────────────────────────┤
│                 CONNECTEURS                              │
│                                                          │
│  Google Drive   CRM (Gazelle)   Email   Calendrier       │
│  Comptabilité   Supabase        SMS     Fournisseurs     │
└──────────────────────────────────────────────────────────┘
```

### Le Poste de commande (vision Allan)

Le dirigeant ne devrait pas jongler entre 6 sessions Claude Code, 4 remote triggers,
et 3 onglets de navigateur pour suivre ses projets. Il devrait avoir UN écran qui montre tout.

```
┌─────────────────────────────────────────────────────────────┐
│  🎹 POSTE DE COMMANDE PTM                    Allan Sutton  │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  AGENTS ACTIFS                                              │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐           │
│  │ Soumissions  │ │  Marketing  │ │  Opérations │           │
│  │ 🟢 en ligne  │ │ 🟢 en ligne │ │ 🟢 en ligne │           │
│  │ 3 en attente │ │ Newsletter  │ │ PDA: 4 RV   │           │
│  │ 1 à relancer │ │ prête       │ │ demain      │           │
│  │              │ │ Blog: brouil│ │ VDI: 2 RV   │           │
│  │ [Ouvrir]     │ │ [Ouvrir]    │ │ [Ouvrir]    │           │
│  └─────────────┘ └─────────────┘ └─────────────┘           │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐           │
│  │  Technique   │ │   Clients   │ │  Formation  │           │
│  │ 🟢 en ligne  │ │ 🟢 en ligne │ │ 🟡 pause    │           │
│  │ Bundles: 4   │ │ Alertes: 2  │ │ AEC: en     │           │
│  │ MSL: 12 tmpl │ │ Suivi PLS:  │ │ attente     │           │
│  │              │ │ 3 à planif  │ │ entrevue    │           │
│  │ [Ouvrir]     │ │ [Ouvrir]    │ │ [Ouvrir]    │           │
│  └─────────────┘ └─────────────┘ └─────────────┘           │
│                                                             │
│  ACTIVITÉ RÉCENTE                                           │
│  10:32  Soumissions  Huizi WANG — PLS détecté sans          │
│                      système installé, enrichissement       │
│                      corrigé                                │
│  10:15  Opérations   Parking Nicolas nettoyé (11 faux+)     │
│  09:45  Marketing    Newsletter mai — brouillon prêt        │
│  08:00  Opérations   Briefing Nicolas généré (5 RV)         │
│                                                             │
│  SANTÉ DU SYSTÈME                                           │
│  Gazelle API: 🟢    Drive: 🟢    Supabase: 🟢              │
│  Cerveau: 847 entrées    Dernière capture: il y a 12 min    │
│                                                             │
│  COLLABORATEURS EN LIGNE                                    │
│  Nicolas (Opérations) — dernière question il y a 2h        │
│  Margot (Formation) — pas encore connectée                  │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

Chaque "agent" est un Claude spécialisé qui :
- A accès au Cerveau (filtré par son domaine)
- Connaît ses workflows (skills spécifiques)
- Peut agir (créer RV, modifier soumission, envoyer email)
- Tourne en continu dans le cloud (pas de session qui meurt)
- Rapporte son activité au poste de commande

Le dirigeant peut :
- Voir l'état de tout en un coup d'oeil
- Cliquer sur un agent pour interagir directement
- Voir ce que ses collaborateurs ont demandé et corrigé
- Recevoir des alertes quand un agent a besoin de son jugement

Les collaborateurs ne voient PAS le poste de commande. Ils voient seulement
leur agent, dans leur domaine, avec leurs permissions.

### Principes non négociables

1. **Zéro serveur chez le client.** Tout cloud. Le dirigeant n'a besoin que d'un navigateur ou d'un téléphone.
2. **Zéro documentation volontaire.** Le savoir se capture en travaillant, jamais en "documentant".
3. **Zéro maintenance technique.** Pas de tokens qui expirent, pas de sessions qui meurent, pas d'API à réactiver.
4. **Le Cerveau survit au dirigeant.** Transferable, versionné, permanent.
5. **Chaque rôle voit son monde.** Le tech ne voit pas la compta. Le marketing ne voit pas les réglages de mécanique.

---

## Phase 0 — Inventaire (ce qui existe déjà chez PTM)

Avant de construire quoi que ce soit, cataloguer ce qu'on a déjà.

### Savoir déjà capturé

| Type | Où | Exemples | Volume estimé |
|------|-----|----------|---------------|
| Règles métier | Mémoires Claude Code | "jamais dépose", "buvards pas tampons", "stat=stationnement" | ~25 règles |
| Workflows | Skills Gazelle | Créer soumission, enrichir RV, cloner RV conjoint, éditer Google Doc | ~6 workflows |
| Décisions techniques | `decisions.md` | Architecture v5/v6, choix Supabase, sync Gazelle | ~50 décisions |
| Bundles de service | `service_bundles.py` | GE droit, GE queue, cordes basses, remplacement marteaux | 4 bundles |
| Templates tech | MSL Gazelle | Templates d'enrichissement par type de service | ~12 templates |
| Terminologie | Mémoires Claude Code | Vocabulaire PTM, ton québécois, formulations clients | ~5 guides |
| Procédures PDA | Code v5 + Supabase | Import email, sync Gazelle, facturation, stationnement | intégré au code |
| Documents | Google Drive | Soumissions, bons de sortie, procédures, marketing | ~8 shared drives |
| Données clients | Gazelle + Supabase | Clients, pianos, historique, mesures, alertes | ~2000 clients |

### Savoir encore dans la tête d'Allan (exemples)

- Comment évaluer l'état d'un piano au téléphone pour donner un prix approximatif
- Quand référer à un autre technicien vs prendre le travail
- Comment gérer un client mécontent d'un prix
- La séquence optimale d'une journée avec 4 RV à PDA
- Comment négocier avec les fournisseurs (QRS, déménageurs, etc.)
- Les particularités de chaque salle de concert (PDA, VDI, Orford)
- Quand un piano vaut la peine d'être réparé vs remplacé

### Tâches Phase 0

- [ ] Exporter et cataloguer toutes les mémoires Claude Code existantes
- [ ] Lister les workflows/skills déjà codifiés
- [ ] Identifier les 20 "jugements" les plus critiques encore dans la tête d'Allan
- [ ] Mapper les shared drives et leur contenu par catégorie
- [ ] Identifier les trous : quel savoir est utilisé quotidiennement mais n'est capturé nulle part

---

## Phase 1 — Le Cerveau (structure de données)

### Objectif
Créer une base de connaissances structurée dans Supabase qui centralise tout le savoir, quelle que soit sa source.

### Schema proposé

```sql
-- Unité atomique de connaissance
CREATE TABLE knowledge_entries (
    id UUID PRIMARY KEY,
    category TEXT NOT NULL,        -- 'regle_metier', 'savoir_faire', 'jugement', 
                                   -- 'vocabulaire', 'relation', 'erreur', 'procedure'
    domain TEXT NOT NULL,          -- 'soumissions', 'marketing', 'operations', 
                                   -- 'pda', 'vdi', 'clients', 'technique'
    title TEXT NOT NULL,           -- Titre court
    content TEXT NOT NULL,         -- Le savoir lui-même
    why TEXT,                      -- Pourquoi cette règle/ce choix existe
    source TEXT,                   -- D'où ça vient ('conversation_claude', 'correction_allan',
                                   -- 'observation_auto', 'document_drive')
    source_ref TEXT,               -- Référence (session ID, doc ID, commit, etc.)
    confidence FLOAT DEFAULT 1.0,  -- 1.0 = confirmé par Allan, 0.5 = inféré, 0.0 = à valider
    applicable_roles TEXT[],       -- {'tech', 'admin', 'marketing', 'direction'}
    created_at TIMESTAMPTZ,
    created_by TEXT,               -- 'allan', 'system', 'nicolas', etc.
    validated_at TIMESTAMPTZ,      -- Quand Allan a confirmé
    superseded_by UUID,            -- Si remplacé par une entrée plus récente
    tags TEXT[]
);

-- Lien entre connaissances (cette règle dépend de celle-là)
CREATE TABLE knowledge_links (
    from_id UUID REFERENCES knowledge_entries(id),
    to_id UUID REFERENCES knowledge_entries(id),
    link_type TEXT,  -- 'depends_on', 'contradicts', 'refines', 'example_of'
    PRIMARY KEY (from_id, to_id)
);

-- Documents Drive indexés
CREATE TABLE knowledge_documents (
    id UUID PRIMARY KEY,
    drive_file_id TEXT NOT NULL,
    drive_name TEXT,
    drive_path TEXT,               -- ex: 'Procédures/Soumissions/Guide PLS.gdoc'
    domain TEXT,
    summary TEXT,                  -- Résumé auto-généré
    indexed_at TIMESTAMPTZ,
    last_checked TIMESTAMPTZ
);

-- Log d'apprentissage : chaque correction d'Allan
CREATE TABLE knowledge_learning_log (
    id UUID PRIMARY KEY,
    entry_id UUID REFERENCES knowledge_entries(id),
    event_type TEXT,  -- 'created', 'corrected', 'validated', 'deprecated'
    before_value TEXT,
    after_value TEXT,
    context TEXT,     -- Qu'est-ce qu'Allan faisait quand il a corrigé
    occurred_at TIMESTAMPTZ
);
```

### Migration des connaissances existantes

Les mémoires Claude Code (`~/.claude/projects/*/memory/`) → `knowledge_entries`
Les workflows skills → `knowledge_entries` (type `procedure`)
Les bundles → `knowledge_entries` (type `savoir_faire`)
Les documents Drive → `knowledge_documents`

### Tâches Phase 1

- [ ] Créer les tables dans Supabase
- [ ] Script de migration : mémoires Claude Code → knowledge_entries
- [ ] Script de migration : workflows/skills → knowledge_entries
- [ ] Indexeur Google Drive : scan les shared drives, crée les entrées knowledge_documents
- [ ] API de consultation : `GET /knowledge?domain=soumissions&role=tech`
- [ ] API d'ajout : `POST /knowledge` (utilisé par le capteur, phase 2)

---

## Phase 2 — Le Capteur de savoir

### Objectif
Intercepter automatiquement les moments où Allan transmet du savoir, et les convertir en entrées du Cerveau.

### Sources de capture

| Source | Comment | Exemple |
|--------|---------|---------|
| Corrections Claude Code | Allan dit "non, pas comme ça" → le capteur extrait la règle | "jamais dépose" → règle vocabulaire |
| Soumissions construites | Chaque soumission enrichit les templates | Prix PLS 2026, formulations qui fonctionnent |
| Emails envoyés | Ton, formulations, façon de gérer les objections | Comment Allan répond à "c'est trop cher" |
| Décisions prises | Quand Allan choisit A plutôt que B, capturer le pourquoi | "On ne fait pas de GE sur un piano de moins de 10 ans" |
| Conversations avec l'équipe | Quand Allan explique quelque chose à Nicolas | La technique de serrage des vis sur les Steinway |
| Documents créés | Bons de sortie, procédures, checklists | Le bon de sortie = une procédure opérationnelle |

### Mécanisme

1. **Détection passive** : le capteur observe les interactions (conversations Claude, emails, documents créés)
2. **Extraction** : un modèle identifie les "moments de savoir" — corrections, explications, décisions
3. **Proposition** : le capteur propose une entrée au Cerveau → "J'ai compris que [règle]. C'est exact ?"
4. **Validation** : Allan confirme, corrige ou rejette. Le capteur apprend de ses erreurs.
5. **Intégration** : l'entrée validée est ajoutée au Cerveau avec `confidence=1.0`

### Ce qui existe déjà (à exploiter)

- Les mémoires Claude Code sont déjà un capteur manuel (type `feedback`)
- Le `ai_training_feedback` dans Supabase (bouton "Ma Journée" v5)
- L'historique des conversations Claude Code (fichiers `.jsonl`)

### Tâches Phase 2

- [ ] Définir les patterns de "moment de savoir" (correction, explication, décision)
- [ ] Script d'extraction sur les conversations Claude Code existantes
- [ ] Hook Claude Code : à chaque mémoire sauvée, créer aussi une knowledge_entry
- [ ] Pipeline email : scanner les emails sortants d'Allan pour le ton et les formulations
- [ ] Interface de validation : Allan voit les entrées proposées et confirme/corrige d'un clic

---

## Phase 2.5 — Le Poste de commande + Agents permanents

### Objectif
Remplacer les sessions Claude Code manuelles par des agents spécialisés permanents,
orchestrés depuis un tableau de bord unique.

### Le problème actuel

Aujourd'hui, Allan doit :
1. Ouvrir une session Claude Code sur le PC
2. Pointer vers le bon plan file (`ouvre soumissions-plan.md`)
3. Lancer un remote trigger pour les tâches récurrentes
4. Espérer que la session ne meure pas
5. Recommencer pour chaque sous-projet

C'est du dispatching manuel. Le dirigeant est le routeur.

### La cible

Des **agents autonomes** qui tournent dans le cloud, chacun spécialisé :

| Agent | Domaine | Ce qu'il fait en continu | Quand il alerte Allan |
|-------|---------|--------------------------|----------------------|
| Agent Soumissions | Soumissions Gazelle | Surveille les soumissions sans réponse, prépare les relances, révise la qualité | Soumission acceptée, client qui n'a pas répondu en 7 jours |
| Agent Marketing | Newsletter, blog, réseaux | Veille quotidienne, prépare les contenus, planifie les publications | Contenu prêt pour approbation |
| Agent Opérations | RV, PDA, VDI, Orford | Enrichit les RV, sync PDA, génère les briefings, détecte les anomalies | Alerte humidité, RV non assigné, conflit d'horaire |
| Agent Technique | Bundles, MSL, templates | Maintient les templates à jour, propose des améliorations basées sur l'usage | Nouveau bundle suggéré, template obsolète |
| Agent Clients | Relations, suivi, PLS | Suit les clients, planifie les entretiens PLS, détecte les pianos inactifs | Client sans visite depuis 18 mois, PLS à renouveler |
| Agent Formation | AEC, procédures, onboarding | Maintient les docs de formation, répond aux questions des nouveaux | Question sans réponse dans le Cerveau |

### Architecture technique

```
┌─────────────────────────────────────────────────────┐
│          POSTE DE COMMANDE (React/Next.js)          │
│          https://dashboard.piano-tek.com            │
├─────────────────────────────────────────────────────┤
│                                                     │
│  Orchestrateur (backend Node.js ou Python)          │
│  ├── Spawn/kill agents                              │
│  ├── Router de messages (collaborateur → bon agent) │
│  ├── Agrégateur d'état (chaque agent rapporte)      │
│  └── File d'attente de validation (pour Allan)      │
│                                                     │
├──────┬──────┬──────┬──────┬──────┬──────────────────┤
│Agent │Agent │Agent │Agent │Agent │Agent             │
│Soum. │Mktg  │Ops   │Tech  │Cli.  │Form.            │
│      │      │      │      │      │                  │
│Claude│Claude│Claude│Claude│Claude│Claude            │
│API   │API   │API   │API   │API   │API               │
│      │      │      │      │      │                  │
│Skills│Skills│Skills│Skills│Skills│Skills            │
│propre│propre│propre│propre│propre│propre            │
├──────┴──────┴──────┴──────┴──────┴──────────────────┤
│                                                     │
│  CERVEAU (Supabase) + CONNECTEURS (Gazelle, Drive)  │
│                                                     │
└─────────────────────────────────────────────────────┘
```

Chaque agent :
- Est un process persistant (pas une session interactive qui meurt)
- Utilise l'API Claude (Anthropic SDK) avec un system prompt spécialisé
- A son propre contexte chargé depuis le Cerveau (filtré par domaine)
- Peut appeler les mêmes outils que Claude Code (Gazelle, Drive, Supabase, email)
- Rapporte son état et son activité à l'orchestrateur
- Peut être "réveillé" par un événement (nouveau email, RV complété, cron)

### Différence fondamentale avec l'état actuel

| Aujourd'hui | Demain |
|-------------|--------|
| Allan ouvre Claude Code | Les agents tournent tout seuls |
| Allan dit "ouvre soumissions-plan.md" | L'agent Soumissions connaît déjà son mandat |
| La session meurt → tout est perdu | L'agent redémarre avec tout son contexte (Cerveau) |
| Un seul Claude à la fois | 6 agents en parallèle |
| Allan est le seul utilisateur | Chaque collaborateur parle à son agent |
| Remote trigger = cron basique | Événements intelligents (email reçu → action) |

### Tâches Phase 2.5

- [ ] Concevoir le schema de l'orchestrateur (état des agents, file de validation)
- [ ] Prototype : un seul agent (Opérations) qui tourne en continu sur Render
- [ ] Dashboard web minimal : état de l'agent + log d'activité
- [ ] Intégration Claude API avec system prompt chargé depuis le Cerveau
- [ ] Mécanisme de "réveil" par événement (webhook Gazelle, cron, email)
- [ ] Chat collaborateur → agent (Nicolas pose une question à l'agent Opérations)
- [ ] File de validation : l'agent propose, Allan approuve d'un clic sur le dashboard

---

## Phase 3 — L'interface équipe

### Objectif
Donner à chaque collaborateur un accès au Cerveau, filtré par son rôle.

### Concept d'interface

```
┌─────────────────────────────────────────┐
│  🎹 Compagnon PTM          [Nicolas ▾]  │
├─────────────────────────────────────────┤
│                                         │
│  Domaines                               │
│  ┌──────────┐ ┌──────────┐ ┌─────────┐ │
│  │Operations│ │ Clients  │ │Technique│ │
│  │ 42 items │ │ 2031 cli │ │ 18 proc │ │
│  └──────────┘ └──────────┘ └─────────┘ │
│                                         │
│  💬 Pose ta question                    │
│  ┌─────────────────────────────────┐    │
│  │ Le Steinway chez Mme Chen,     │    │
│  │ c'est quoi l'historique ?       │    │
│  └─────────────────────────────────┘    │
│                                         │
│  Réponse :                              │
│  Steinway M #387254, acheté 2018.       │
│  PLS installé mars 2024.                │
│  Dernière visite : accord + GE,         │
│  13 mars 2026 par Nicolas.              │
│  Note Allan : "Très sensible à          │
│  l'humidité, vérifier le PLS à          │
│  chaque visite."                        │
│                                         │
│  📎 Sources : Gazelle #387254,          │
│     Note Allan 2024-03-15,              │
│     Timeline 6 entrées                  │
│                                         │
└─────────────────────────────────────────┘
```

### Fonctionnalités clés

1. **Recherche en langage naturel** dans tout le Cerveau
2. **Réponses sourcées** — chaque affirmation pointe vers sa source (document, règle, historique)
3. **Apprentissage continu** — si le collaborateur signale une réponse incorrecte, ça remonte à Allan
4. **Contexte automatique** — le compagnon sait qui demande et adapte la réponse
5. **Actions intégrées** — pas juste "voici l'info", mais "veux-tu que je crée le RV ?"

### Évolution de l'assistant v5/v6

L'assistant v5 actuel est déjà un embryon de ça. L'évolution :
- v5 actuel : chat IA + outils Gazelle, connaissances dans le code
- v6 cible : chat IA + Cerveau + outils Gazelle + Drive + email, connaissances dans la base

### Tâches Phase 3

- [ ] Concevoir l'interface par rôle (maquettes)
- [ ] Brancher l'assistant sur knowledge_entries (RAG sur le Cerveau)
- [ ] Brancher l'assistant sur knowledge_documents (RAG sur les docs Drive)
- [ ] Système de feedback : le collaborateur peut dire "c'est faux" ou "c'est utile"
- [ ] Notifications : quand une nouvelle procédure est ajoutée, le rôle concerné est notifié
- [ ] Mode "Allan dit" : les collaborateurs peuvent voir le raisonnement d'Allan derrière une règle

---

## Phase 4 — Le produit vendable (Kit PME)

### Le pitch

"Vous avez 30 ans de métier dans la tête. Vos employés vous appellent 10 fois par jour pour des questions. Vous ne pouvez pas partir en vacances. Et quand vous prendrez votre retraite, tout ce savoir disparaîtra. Le Compagnon d'entreprise capture votre expertise pendant que vous travaillez, et la rend accessible à votre équipe — pour toujours."

### Le modèle

1. **Onboarding (1 mois)** : Le dirigeant branche ses outils. Le compagnon l'observe travailler. Premières règles capturées.
2. **Apprentissage (3 mois)** : Le compagnon pose des questions, propose des règles, le dirigeant valide. Le Cerveau se remplit.
3. **Déploiement équipe (mois 4)** : Premier collaborateur accède au compagnon. Le dirigeant voit les questions posées et corrige.
4. **Autonomie (mois 6+)** : Le compagnon gère 80% des questions sans intervention. Le dirigeant ne fait que valider les nouveaux cas.

### Verticals cibles (PME de service avec expertise concentrée)

- Techniciens spécialisés (pianos, ascenseurs, CVC, électricité)
- Cabinets professionnels (architectes, ingénieurs, comptables)
- Artisans (ébénistes, luthiers, horlogers)
- Restauration (recettes, gestion, service)
- Santé (cliniques privées, dentistes, physio)

### Différenciation

| Solution existante | Problème | Compagnon |
|---|---|---|
| Wiki d'entreprise | Personne ne le maintient | Se maintient tout seul |
| Formation en personne | Meurt avec le formateur | Permanent et évolutif |
| CRM (Gazelle, HubSpot) | Données, pas jugement | Données + jugement + contexte |
| ChatGPT/Claude générique | Ne connaît pas TON entreprise | Connaît chaque client, chaque règle, chaque erreur passée |
| Consultant en transfert | Ponctuel et cher | Continu et intégré au travail |

### Tâches Phase 4

- [ ] Documenter le cas PTM comme "case study" fondateur
- [ ] Abstraire le code PTM en framework réutilisable
- [ ] Définir les connecteurs standards (QuickBooks, Google Workspace, Outlook, Calendly, etc.)
- [ ] Construire l'onboarding self-service
- [ ] Pricing et modèle d'affaires
- [ ] Premier client pilote (hors PTM)

---

## Contraintes techniques à résoudre

### Problèmes actuels (vécus chez PTM)

| Problème | Impact | Solution envisagée |
|----------|--------|-------------------|
| Sessions Claude Code qui meurent | Perte de contexte, refaire le travail | Cerveau persistant dans Supabase, pas dans ~/.claude |
| Serveur local requis (HP ProDesk) | Non scalable, panne = arrêt | Tout cloud (Render/Fly.io/Supabase) |
| MCP/API qui cassent sans avertissement | 45 min perdues (cf. Google Docs aujourd'hui) | Couche d'abstraction propre, pas de dépendance aux plugins tiers |
| Mémoires liées à une machine | Changer de PC = repartir à zéro | Cerveau centralisé, accessible de partout |
| Pas d'interface pour l'équipe | Seul Allan peut utiliser le système | Interface web par rôle (Phase 3) |
| OAuth/tokens/scopes fragiles | Casse sans raison apparente | Service account avec tous les scopes, géré une fois |

### Architecture technique cible

```
Client (navigateur/mobile)
    │
    ▼
API Gateway (Render ou Fly.io)
    │
    ├── Assistant API (Claude, RAG sur le Cerveau)
    ├── Connecteur Gazelle (GraphQL)
    ├── Connecteur Drive (service account)
    ├── Connecteur Email (Gmail API)
    └── Capteur de savoir (analyse des interactions)
    │
    ▼
Supabase
    ├── knowledge_entries (le Cerveau)
    ├── knowledge_documents (index Drive)
    ├── knowledge_learning_log (historique d'apprentissage)
    ├── gazelle_* (données CRM sync)
    └── auth (utilisateurs, rôles)
```

---

## Métriques de succès

### Pour PTM (laboratoire)

- Allan peut partir 2 semaines sans que personne l'appelle pour une question opérationnelle
- Un nouveau tech est autonome en 1 mois au lieu de 6
- 90% des questions de l'équipe trouvent une réponse dans le Cerveau
- Temps de création d'une soumission : de 45 min (Allan seul) à 10 min (n'importe qui avec le compagnon)

### Pour le produit

- Onboarding d'un nouveau client en moins de 2 heures
- 100 règles métier capturées dans les 3 premiers mois
- NPS > 70 auprès des dirigeants utilisateurs
- Le dirigeant dit : "c'est exactement comme ça que je l'aurais fait"

---

## Prochain pas immédiat

1. **Inventaire** : cataloguer tout le savoir PTM déjà capturé (mémoires, skills, workflows, documents)
2. **Schema Cerveau** : créer les tables knowledge_* dans Supabase
3. **Migration** : verser les mémoires existantes dans le Cerveau
4. **Preuve de concept** : un endpoint `/ask?q=...&role=tech` qui cherche dans le Cerveau et répond
