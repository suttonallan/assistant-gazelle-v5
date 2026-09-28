# Assistant Gazelle — État & principes

Document vivant à tenir à jour. À déposer dans le Projet Claude
« Assistant Gazelle » comme *project knowledge* pour que chaque
nouvelle conversation démarre avec ce contexte.

---

## Principes non négociables

### 1. Traçabilité en un clic

Toute donnée affichée dans l'assistant doit avoir sa **source cliquable**.
Aucune info « anonyme » — si on ne peut pas dire d'où ça vient, ça ne
s'affiche pas.

Concrètement :

- Chaque carte / tâche / piano-row stocke son origine :
  `source_type` (front / drive / gazelle / manuel) + `source_id` +
  libellé (« Soumission mars 2026 », « Plan avril 2026 », etc.)
- Le frontend rend un chip cliquable → ouvre la source dans l'app native
  (Front, Drive, Gazelle)
- Quand une info est *créée* dans l'assistant (extraite d'un email, d'un
  plan, d'un commentaire équipe), la source est captée automatiquement
- Louise ou Nicolas doivent pouvoir consulter d'où vient chaque info
  sans quitter la carte

Exemple : pour le Steinway B de Théâtre Maisonneuve, l'email qui tient
lieu de soumission = une conversation Front. Le chip « Soumission » sur
la carte ouvre `https://app.frontapp.com/open/{conversation_id}` — un
clic, elle est dedans.

### 2. Le document est l'archive, l'assistant est l'état vivant

Le plan Drive (ex. `Plan_Entretien_PdA_2026-2027_PTM 1.pdf`) est un
document historique — il reste tel qu'il a été écrit. **Personne ne
retourne le modifier après coup.**

L'assistant reflète l'état actuel — y compris les décisions comme « on
ne fait pas le Baldwin, reporté en 2027 ». Cette décision vit dans
l'assistant (état de la carte + commentaire), pas dans le PDF.

### 3. L'équipe travaille dans l'assistant, pas dans les outils sources

Louise, Nicolas, Allan doivent voir d'un coup d'œil tout ce qui a été
évoqué à propos d'un client / piano. Ils ne vont dans Drive, Front ou
Gazelle qu'en dernier recours (pour consulter la source d'une info
précise).

---

## Ce que c'est

App interne pour **Piano Technique Montréal** — gestion des accords,
restaurations, briefings techniciens, alertes humidité. Codebase
français, FastAPI + React.

- 3 institutions : Vincent-d'Indy (121 pianos), Place des Arts (16),
  Orford (61)
- Prod backend : Render (`assistant-gazelle-v5-api.onrender.com`)
- Prod frontend : GitHub Pages (`suttonallan.github.io/assistant-gazelle-v5/`)
- Repo : `suttonallan/assistant-gazelle-v5`

## Équipe

| Personne | Rôle | Dans Front ? |
|---|---|---|
| Allan Sutton | Fondateur, tech | ✅ `asutton@piano-tek.com` |
| Nicolas Lessard | Tech, RPT | ✅ `nlessard@piano-tek.com` |
| Louise Paradis | Coordonnatrice | ✅ `info@piano-tek.com` |
| Margot Charignon | Tech | ✅ `margotcharignon@gmail.com` |
| JP Reny | Tech externe | ❌ |
| Ilyan | Tech externe | ❌ |

**Inboxes Front** : Demo Inbox, `info` (Gmail), Chat WordPress.

## Contacts institutionnels clés

- **Place des Arts** : Guy Levesque (principal), Isabelle Clairoux (cc)
- **Vincent-d'Indy** : Julio Gonzalo (Directeur adjoint / Fondation)
- **Orford Musique** : Wonny Song
- **Fournisseur marteaux/cordes** : Brooks LTD Piano Products
  (`office@brooksltdonline.com`) — Josi, Melanie

## Ce qui est en place aujourd'hui

- **Intégration Front** (`core/front_client.py`) — lecture + commentaires
  internes + brouillons de réponse. `FRONT_API_KEY` sur Render.
- **Endpoints Front** (`api/front_routes.py`) — `/front/{me,inboxes,
  teammates,search}`, `/front/conversations/{id}` (agrège messages +
  commentaires), écriture de commentaires et brouillons.
- **Agrégation campagne par client** (`modules/campaigns/campaign_service.py`)
  — `get_campaign_context(client_name)` combine conversations Front +
  commentaires équipe.
- **Endpoint campagnes** (`api/campaigns_routes.py`) —
  `/campaigns/{client}/context`.
- **Module Tâches** (`frontend/src/components/TachesDashboard.jsx` +
  `sql/auto/002_taches.sql`) — vue campagnes + tableau À faire / En
  cours / Fait, avec coupe-circuit et déploiement progressif (Allan
  d'abord).
- **Scripts de test** : `scripts/test_front.py`,
  `scripts/test_campaign.py` (aucun effet de bord).

## Maquette de référence

**Tâches Gazelle v7** — https://claude.ai/artifact/JZNfg4axWan3EHZUnwdns3

Vue à deux étages :
- **Campagnes** (Place des Arts, Orford, Vincent-d'Indy) en haut, avec
  liste pianos-enfants, ajouts inline, commentaires équipe
- **Tâches** (À faire / En cours / Fait) en bas, cartes riches avec
  progression + liens sources

À ajouter dans une prochaine passe : recherche globale, cartes campagne
collapsibles, tri auto de l'urgent en haut.

## Chantiers connus

1. **Amorcer les cartes-pianos** depuis les plans d'entretien Drive
   (parseur simple ou copie assistée) — pour que Louise et Nicolas
   voient la campagne PDA habitée dès demain
2. **Traçabilité complète** — vérifier que chaque carte créée porte
   bien sa source cliquable (voir principe #1)
3. **Brancher les commentaires Front** sur les cartes-campagne du module
   Tâches (déjà exposés côté API, pas encore consommés côté frontend)
4. **Enrichir Ma Journée** avec les commentaires Front récents liés au
   client visité
5. **Auto-création de tâches** depuis les commentaires équipe qui
   contiennent des scope-additions (« +2 j pour l'attrape »)
6. **Retirer le coupe-circuit** du module Tâches quand tests validés
