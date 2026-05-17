# Nouvelles features et correctifs — À intégrer dans v6

> Ce fichier documente les changements v5 qui doivent être pris en compte lors du développement v6.
> Ne pas supprimer les entrées — elles servent de référence architecturale.

---

## 2026-04-22 — Fix Late Assignment : filtrer par date de création Gazelle, pas de modification

### Problème
Nicolas recevait un avis "nouveau rendez-vous assigné" pour un RV modifié le 31 mars. Le trigger se basait sur l'absence de `old_record` en Supabase pour détecter un "nouveau" RV, mais si le lookup Supabase échouait ou si le RV avait été nettoyé de la DB, un vieux RV modifié était traité comme nouveau.

### Cause racine
La détection `if not old_record` ne distingue pas entre :
- Un RV vraiment nouveau (créé dans les dernières 24h)
- Un vieux RV absent de Supabase (nettoyé, erreur réseau, première sync)

### Fix v5
1. Ajouté `createdAt` à la requête GraphQL `allEventsBatched` (timestamp Gazelle réel de création)
2. Remplacé la logique de détection :
   - **Avant** : `not old_record` → alerte (faux positifs sur vieux RV modifiés)
   - **Après** : `not old_record AND createdAt < 24h` → alerte ; sinon → pas d'alerte (vieux RV)
3. Le changement de technicien reste détecté normalement (old_tech != new_tech)
4. **Fenêtre élargie de 24h à 7 jours** : les techniciens planifient leur semaine le dimanche. Un RV de jeudi dont le tech change mardi doit être notifié immédiatement — pas attendre mercredi soir (< 24h). La constante `ALERT_WINDOW_HOURS = 168` (7 jours) remplace l'ancien `< 24`.
5. **Unicité garantie** par deux couches de dédup :
   - `last_notified_tech_id` en DB → empêche la re-détection à chaque sync
   - Anti-doublon dans `_queue_late_assignment_alert` → si `sent` existe déjà pour ce RV+tech, on skip

### Recommandation v6
En v6, implémenter la détection late assignment dès le départ avec ces règles :
- **Fenêtre 7 jours** : alerter dès que le RV est dans les 7 prochains jours
- **Alerter** si : (RV créé récemment **OU** technicien assigné/changé) **ET** pas déjà notifié
- **Ne jamais alerter** pour une simple modification (notes, heure, etc.) sur un vieux RV
- **Une seule alerte par assignation** — pas de rappels
- Stocker `gazelle_created_at` comme colonne distincte de `created_at` (Supabase row insertion)
- Stocker `first_assigned_at` ou `tech_changed_at` pour tracer le moment exact de l'assignation

### Détection élargie : 4 types de changement

| Type | `change_type` | Sujet email | Quand |
|---|---|---|---|
| Nouveau RV | `new` | "Nouveau rendez-vous" | Créé < 24h dans Gazelle |
| Tech changé | `reassigned` | "Rendez-vous assigné" | Technicien différent du précédent |
| Horaire modifié | `rescheduled` | "Rendez-vous déplacé" | Date ou heure changée |
| RV annulé | `cancelled` | "Plage libérée" | RV disparaît de Gazelle (CANCELLED) |

### Anti-doublon pour les changements d'horaire
Nouveau champ `last_notified_schedule` dans `gazelle_appointments` : snapshot `"YYYY-MM-DD HH:MM"` de la date/heure lors de la dernière notification. Si le snapshot actuel est identique, pas de re-notification.

### Fichiers modifiés (v5)
- `core/gazelle_api_client.py` — ajout `createdAt` dans la query GraphQL
- `modules/sync_gazelle/sync_to_supabase.py` — logique de détection (4 types) + alerte annulation dans le nettoyage CANCELLED
- `modules/late_assignment/late_assignment_notifier.py` — email adapté selon `change_type`
- `sql/add_change_type_to_late_assignment.sql` — migration (colonne `change_type` + `last_notified_schedule`)
