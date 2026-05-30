# Digest quotidien — fiches d'accord à pousser vers Gazelle

**Statut :** 🟢 actif
**Créé le :** 2026-04-18
**Dernière mise à jour :** 2026-04-19
**Prochain pas :** Tester en live (`python scripts/test_push_digest.py --live`), puis commit + push vers Render pour activer le cron 17h ET livrer la simplification du workflow (retrait bouton Terminé + retrait Nettoyer anciens + fix filtre Tout valider).
**Bloqué par :** rien.

---

## Contexte

Nicolas (collaborateur principal de validation) a exprimé de la confusion sur le workflow des fiches d'accord pour Vincent d'Indy (et par extension les autres institutions). Quand il ouvre un piano (ex. Local 240) pour entrer une nouvelle fiche, il voit parfois du texte pré-existant et n'a pas de moyen rapide de savoir si c'est :
- Un ancien service déjà poussé vers Gazelle (contexte historique)
- Un brouillon d'un collègue en attente de validation
- Une entrée validée mais pas encore poussée

**Allan a identifié que la vraie cause** n'est pas un manque d'information à l'UI, mais un manque de discipline sur la poussée quotidienne. Si Nicolas valide ET pousse chaque jour, il n'y a jamais d'accumulation, et l'ambiguïté disparaît naturellement.

**Solution retenue (le 2026-04-18) :** envoyer un digest quotidien à 17h listant les fiches validées mais pas encore poussées, pour rappeler de finir la journée propre. **Ne pas** ajouter de bandeau UI pour l'instant — on mise tout sur la notif, on reviendra au bandeau seulement si insuffisant après quelques semaines.

---

## Décisions prises

| Décision | Valeur |
|---|---|
| Destinataire | `info@piano-tek.com` (Nicolas lit cette boîte) |
| Heure d'envoi | 17h America/Montreal, **lun-ven** |
| Si zéro fiche en attente | Pas d'email (zéro bruit) |
| Déclencheur de push | Manuel — Nicolas clique « Pousser » (par entrée ou batch). Digest rappelle, ne déclenche pas. |
| Escalation | Si une fiche validée traîne depuis **≥ 3 jours** (`ESCALATION_DAYS`) → Allan en CC |
| Déduplication | **Aucune** — le but EST de re-rappeler chaque jour tant que pas poussé |
| Bandeau UI | Skipped pour l'instant |

---

## Ce qui a été livré

### Code
- **Nouveau module** : `C:\PTM\assistant-gazelle-v5\modules\briefing\push_digest.py`
  - Fonction publique async `run_push_digest() -> Dict` — appelée par le scheduler
  - Query Supabase : `piano_service_records` WHERE `status = 'validated'` (pas poussées par définition)
  - Groupement par `institution_slug`, enrichissement `age_days` + `escalate`
  - Rendu HTML et texte plain
  - Envoi via `EmailNotifier` (Resend) aux recipients selon escalation
- **Wrapper scheduler** : `task_push_digest()` dans `core/scheduler.py` (entre `task_critical_estimate_digest` et `task_process_late_assignment_queue`)
- **Job cron** : `scheduler.add_job(..., day_of_week='mon-fri', hour=17, minute=0, timezone='America/Montreal')` (après le job `follow_up_digest` 8h)

### Tests
- **`scripts/test_push_digest.py`** — 9 tests unitaires sur la logique pure (exécution : `python scripts/test_push_digest.py`). Tous verts.
- Mode `--live` : exécute `run_push_digest()` contre la vraie Supabase mais **intercepte** `EmailNotifier.send_email` (monkey-patch) pour ne pas envoyer d'email réel — affiche ce qui aurait été envoyé.

---

## Vérification de bout en bout

### Étape 1 — Tests unitaires (✅ fait)
```bash
cd C:\PTM\assistant-gazelle-v5
python scripts/test_push_digest.py
# Attendu : "Tous les tests unitaires passent."
```

### Étape 2 — Live dry-run (à faire avant déploiement)
```bash
python scripts/test_push_digest.py --live
# Sortie : nombre de fiches validées en attente + contenu de l'email (sans envoi réel)
```

### Étape 3 — Envoi manuel de test (optionnel)
Retirer temporairement le monkey-patch, exécuter `python -m modules.briefing.push_digest` depuis la racine `assistant-gazelle-v5`. Vérifier que l'email arrive dans `info@piano-tek.com`. Cliquer le lien → arrive sur `https://suttonallan.github.io/assistant-gazelle-v5/`.

### Étape 4 — Déploiement
```bash
cd C:\PTM\assistant-gazelle-v5
git add modules/briefing/push_digest.py scripts/test_push_digest.py core/scheduler.py
git commit -m "Add 17h push digest reminder for validated service records"
git push origin main
# Render redéploie automatiquement
```

### Étape 5 — Vérification prod
1. Dans les logs Render, confirmer la ligne `"✅ 17:00 - Digest fiches d'accord a pousser (info@, lun-ven) configurée"` au démarrage.
2. Un jour ouvrable à 17h : vérifier que l'email arrive dans info@ (ou qu'il n'arrive pas si aucune fiche en attente).
3. Si besoin, déclencher manuellement la tâche via l'admin du scheduler.

### Étape 6 — Boucle de feedback avec Nicolas
- Après 1 semaine : demander à Nicolas si le rappel aide, ajuster heure/format si besoin.
- Après 2-3 semaines :
  - Si ça marche → classer le sous-projet ✅
  - Sinon → envisager le bandeau UI dans `VDI_NotesView.jsx` en complément

---

## Fichiers critiques

| Fichier | Rôle |
|---|---|
| `C:\PTM\assistant-gazelle-v5\modules\briefing\push_digest.py` | Module digest (nouveau) |
| `C:\PTM\assistant-gazelle-v5\core\scheduler.py` | Wrapper `task_push_digest` + job cron 17h lun-ven |
| `C:\PTM\assistant-gazelle-v5\scripts\test_push_digest.py` | Tests unitaires + live dry-run |
| `C:\PTM\assistant-gazelle-v5\modules\briefing\critical_estimate_digest.py` | Référence de pattern (7h Louise) |
| `C:\PTM\assistant-gazelle-v5\modules\briefing\follow_up_digest.py` | Référence de pattern (8h info@) |
| `C:\PTM\assistant-gazelle-v5\api\service_records.py` | Ligne 323 : `validated_at` ; ligne 534 : `pushed_at` |

---

## Simplification du workflow validate/push (2026-04-19)

Découvert en debug avec Nicolas : il voyait des indicateurs « À valider » qui restaient même après clic sur « Tout valider ». Trois problèmes identifiés :

1. **Le bouton « Tout valider » filtrait silencieusement** sur les fiches `completed` seulement (celles où le tech avait cliqué Terminé). Les `draft` étaient ignorées → Nicolas avait l'impression que le bouton ne marchait pas.
2. **Le step `Terminé` côté tech était un intermédiaire artificiel** qui créait cette confusion. Allan a décidé de le retirer : le tech saisit, Nicolas valide tout, on pousse. Le statut `completed` est maintenant legacy (existant en base, traité comme `draft`).
3. **Le bouton « Nettoyer anciens »** devenait dangereux avec le workflow simplifié (il aurait pu effacer le travail légitime du jour). Retiré complètement.

### Changements livrés
- **`frontend/src/components/VincentDIndyDashboard.jsx`** :
  - `handleValidateAll` : retrait du filtre `.filter(p => p.isCompleted)` → valide TOUT ce qui est pending
  - Retrait de `handleCleanup`, du state `tourneeInProgress` et du bouton « Nettoyer anciens »
  - Retrait de la fonction `markWorkCompleted` (n'est plus passée à la vue tech)
  - Retrait du passage de prop `markWorkCompleted` à `<VDI_TechnicianView>`
- **`frontend/src/components/vdi/VDI_TechnicianView.jsx`** :
  - Retrait du prop `markWorkCompleted` du destructuring
  - Retrait des deux boutons Terminé (le badge compact ○/✓ et le bouton pleine largeur)
  - Retrait de l'indicator ✓ vert (devenait mort)

### Changements backend
Aucun — le backend `validate_service_records` acceptait déjà `draft` ET `completed` dans son filtre. L'endpoint `/complete` reste pour compat (potentiels appels legacy) mais n'est plus appelé par l'UI. L'endpoint `tournee-terminee` reste aussi (pas encore retiré, mais plus appelé).

### Test manuel recommandé
1. Lancer dev : `npm run dev` dans `frontend/`
2. Ouvrir vue Vincent d'Indy
3. Saisir du travail sur un piano côté tech → observer qu'il n'y a plus de bouton Terminé
4. Basculer sur la vue gestion → vérifier que le piano apparaît en « À valider »
5. Cliquer « Tout valider » → le piano disparaît de la liste, apparaît en « Validé »
6. Cliquer « Pousser vers Gazelle » → le piano disparaît, apparaît dans l'historique

## Notes pour la prochaine session

- Pas de déduplication du digest : si Nicolas reçoit le même digest jour après jour, c'est justement le signal à escalader — pas un bug.
- L'escalation CC Allan est le mécanisme de second niveau. Si Allan voit un CC depuis >1 semaine → discuter directement avec Nicolas.
- Si on veut plus tard ajouter un bouton « Pousser tout maintenant » depuis l'email, il faudrait créer un endpoint signé (token one-shot) côté API. Pas prioritaire.
- Dead code à retirer un jour (cleanup non bloquant) :
  - Endpoint backend `POST /service-records/{institution}/piano/{id}/complete` (plus d'appelant UI)
  - Endpoint backend `POST /vincent-dindy/service-history/tournee-terminee` (plus d'appelant UI)
  - State `isWorkCompleted` / `setIsWorkCompleted` dans `VincentDIndyDashboard.jsx` (plus rendu)
