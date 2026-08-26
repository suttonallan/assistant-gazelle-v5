# Compléter le système — ce qui a manqué à une session Claude Code web

**Contexte :** session web du 2026-08-26, demande d'Allan « fais une soumission complète pour
restaurer le vieux Willis de mon RV » (client Éric Le Reste, RV 12 h 30). La soumission a été
composée, chiffrée et validée, mais **n'a pas pu être créée dans Gazelle** depuis le nuage.
Ce document liste tout ce qui a bloqué ou coûté du temps, avec la correction et son test
d'acceptation. À traiter par Claude Code sur le PC (là où le `.env` existe).

**Livré malgré tout :** branche `claude/willis-rv-restoration-ltsqwr`,
`scripts/soumission_willis_restauration.py` (6 commits). Commande finale :
`python3 scripts/soumission_willis_restauration.py --client-search "Éric Le Reste" --yes`

---

## P0 — Ce qui a rendu Gazelle inatteignable

### 1. La clé Supabase de l'environnement web est invalide
- **Symptôme :** tout appel REST renvoie `401 {"message":"Unregistered API key"}`.
- **Cause :** `SUPABASE_SERVICE_ROLE_KEY` de l'environnement Claude Code est une clé
  `sb_secret_…` (41 caractères, pas un JWT) que le projet `beblgzvmjqkcillmcavk` ne reconnaît
  pas — révoquée, ou émise pour un autre projet.
- **Conséquence en cascade :** pas de Supabase → pas de `system_settings.gazelle_oauth_token`
  → `GazelleAPIClient()` lève `ConnectionError` → aucune lecture ni écriture Gazelle.
  C'est exactement le cas prévu par le message d'erreur de `_generate_new_token()`.
- **Correction :** émettre une clé valide et la poser dans les variables d'environnement de
  l'environnement Claude Code (pas dans le repo, pas dans le chat).
- **Test :** depuis une session web, `GET {SUPABASE_URL}/rest/v1/system_settings?select=key&limit=1`
  renvoie 200.

### 2. Aucune autre source de jeton dans le conteneur
- `.env` et `config/token.json` sont gitignorés (correct) — donc absents du clone nuage.
- Gazelle **ne supporte pas** le grant `client_credentials` (constat du 2026-08-09 documenté
  dans `core/gazelle_api_client.py`), donc une session web ne peut pas minter son propre jeton.
- Le port Postgres est fermé depuis le conteneur : `psql` vers
  `aws-0-…pooler.supabase.com:6543` et `db.….supabase.co:5432` expirent tous les deux.
  `SUPABASE_DB_PASSWORD` est donc inutilisable ici — seul le HTTPS sort.
- **Conséquence :** le point 1 est le **seul** levier. Tant qu'il n'est pas réglé, aucune
  session web ne peut lire ou écrire quoi que ce soit dans le système.

### 3. Secrets OAuth en dur dans le code
- `core/gazelle_api_client.py`, lignes 43-45 : `client_id` et `client_secret` Gazelle sont
  écrits en clair comme valeurs de repli (« Force credentials from DEPLOY_NOW.md »). Ils sont
  donc dans l'historique Git. Le fichier `DEPLOY_NOW.md` cité n'est plus dans le repo, mais le
  commentaire suggère qu'il a existé et pourrait porter les mêmes valeurs ailleurs.
- **Correction :** les retirer, exiger les variables d'environnement, **révoquer et régénérer**
  la paire côté Gazelle.
- **Test :** `git log -S "Force credentials" --oneline` ne trouve plus la valeur dans HEAD, et
  le client lève une erreur explicite si les variables manquent.

---

## P1 — Le trou fonctionnel : rien ne peut créer une soumission

### 4. Aucune surface ne compose une soumission neuve
Inventaire de ce qui existe aujourd'hui :

| Surface | Peut créer une soumission ? |
|---|---|
| `POST /chat/action/execute` | Non — MVP qui journalise et répond « à finaliser manuellement » |
| `POST /assistant/converse` (tool loop) | Non — ses outils sont `duplicate_estimate`, `review_estimate`, `search_keyword`, `joint_appointment` |
| `POST /assistant/duplicate-estimate` | Copie une soumission existante seulement |
| Module v6 (`estimates.py`) | Oui, mais uniquement depuis le PC d'Allan |

C'est la **phase 4 de `soumissions-plan.md`** (« script CLI pour créer des soumissions sans
écrire du code ») qui n'est pas faite, et la phase 5 (interface) encore moins.

- **Correction proposée :** un service `create_estimate(client, piano, lignes[], notes)` dans
  l'API, qui résout le client et le piano, tire les prix du catalogue MSL, passe le lint, crée
  en deux étapes et applique la garde d'identité. Puis l'exposer **deux fois** : comme outil du
  tool loop `/assistant/converse` (pour demander une soumission en langage naturel depuis le
  téléphone) et comme route `POST /assistant/create-estimate`.
  `scripts/soumission_willis_restauration.py` contient déjà toute cette logique — elle est à
  extraire vers `modules/`, pas à réécrire.
- **Attention :** une route de mutation sur une API publique sans authentification est à
  proscrire — prévoir le même contrôle que le reste de `/assistant/*`.
- **Test :** depuis le téléphone, demander la soumission d'Éric à l'assistant et obtenir un
  numéro Gazelle.

### 5. Le module v6 est hors du repo
`C:\PTM\assistant-v6\sandbox\app\modules\gazelle\` contient les builders, `lint_estimate`,
`update_estimate_safe`, `clone_estimate` et `service_bundles.py`. Rien de tout ça n'est
accessible au nuage, donc le lint, les blocs de taxes et la garde d'identité ont dû être
**réimplémentés** dans le script de cette session — deuxième implémentation qui va dériver.
- **Correction :** rapatrier le module gazelle de v6 dans ce repo (ou le publier en paquet
  installable) et faire pointer les deux surfaces dessus.
- **Test :** `from modules.gazelle.estimates import lint_estimate` fonctionne dans une session
  web fraîchement clonée.

### 6. Le skill `gazelle` existe en deux copies qui dérivent
`workspace/skills/gazelle/SKILL.md` le documente lui-même : les deux copies ont divergé dans
les deux sens entre avril et août 2026, avec des conséquences réelles (soumissions à 0 $ de
taxe). Même maladie que le point 5.
- **Correction :** une seule copie, l'autre en lien symbolique ou en sous-module, plus un
  `diff -rq` en garde dans un hook.

---

## P2 — Ce qui a coûté du temps sans bloquer

### 7. Les courriels « Nouveau rendez-vous » ne portent aucun identifiant
C'est par eux que le client a été retrouvé (« Éric Le Reste à 12:30 »), mais ils ne contiennent
ni `cli_…`, ni `ins_…`, ni lien vers Gazelle. Trois recherches Gmail et une recherche Drive ont
été nécessaires pour obtenir un simple nom de famille — et les IDs n'ont jamais été trouvés.
- **Correction :** ajouter au corps du courriel le lien Gazelle du client et du rendez-vous, et
  les identifiants du client et du piano.
- **Test :** le prochain courriel de RV permet d'agir sans ouvrir Gazelle.

### 8. Le catalogue MSL n'est pas synchronisé dans Supabase
Le catalogue ne vit que dans Gazelle et dans un document tenu à la main
(`docs/knowledge_estimate_review.md`). Sans jeton, une session ne peut que faire confiance à des
copies — et elles se contredisent déjà :

| Item | `bundles.md` L29 et `progress.md` L223 | `knowledge_estimate_review.md` L126 |
|---|---|---|
| `mit_pDYrT2B8oxWAJ7ou` marteaux droit | 1 250 $ | 1 200 $ |

Seul Gazelle peut trancher, et aucune des deux copies ne sait laquelle est périmée.

Les prix des bundles sont recopiés dans au moins quatre fichiers
(`reference/bundles.md`, `progress.md`, `projets-en-cours.md`, `service_bundles.py`).
- **Correction :** synchroniser `allMasterServiceItems` dans une table Supabase
  (`gazelle_master_service_items`) avec les autres syncs nocturnes, et faire lire les bundles et
  la doc depuis cette table plutôt que depuis des copies.
- **Test :** un changement de prix dans Gazelle apparaît le lendemain dans l'aperçu d'une
  soumission, sans édition manuelle.

### 9. Deux règles maison qui se contredisent sur les items à 0 $
- `docs/knowledge_estimate_review.md` § « Pattern bonus/suivi » **recommande** des items à 0 $
  pour montrer la valeur offerte.
- La règle 9 du skill gazelle et le lint `ZERO_DOLLAR_ITEM` de v6 les **interdisent**.
- Des soumissions existantes violent l'une ou l'autre (#11967 porte une ligne à 0 $).
- **Correction :** trancher, puis aligner les deux documents et le lint.

### 10. Aucun test n'exerce les soumissions dans ce repo
Pas de pytest, pas de CI de test. Les 132 tests verts mentionnés dans `projets-en-cours.md`
sont dans v6, donc hors d'atteinte du nuage. Toute la validation de cette session a été faite
par `--dry-run` et lecture de code.
- **Correction :** avec le point 5, rapatrier aussi les tests et les brancher sur un workflow
  GitHub Actions.

---

## Ordre suggéré

1. **Clé Supabase valide** (P0-1) — débloque tout le reste, cinq minutes.
2. **Rotation des secrets en dur** (P0-3) — à faire en même temps, c'est la même séance.
3. **Rapatrier le module gazelle de v6** (P1-5) — préalable au reste, évite une 3ᵉ implémentation.
4. **Service `create_estimate` + outil converse** (P1-4) — c'est la fonctionnalité qui manquait.
5. **Sync du catalogue MSL** (P2-8) puis identifiants dans les courriels de RV (P2-7).
6. Contradiction 0 $ (P2-9) et tests (P2-10) au fil de l'eau.

Avec 1, 3 et 4, la demande d'origine — « fais une soumission pour ce client » depuis un
téléphone, sans toucher à un terminal — devient possible.
