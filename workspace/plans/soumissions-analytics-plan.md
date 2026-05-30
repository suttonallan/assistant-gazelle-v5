# Sous-projet — Analytics des soumissions PTM

**Statut :** 🟡 en attente (pré-requis : phase 3 du sous-projet soumissions doit être stable)
**Créé le :** 2026-04-15
**Dernière mise à jour :** 2026-04-15
**Prochain pas :** Une fois la phase 3 (digest info@ à 8h + convention `relance-faite`) déployée et adoptée par l'équipe pendant ~2 semaines, ajouter les 3 autres tags Gazelle (`acceptée`, `refusée`, `réalisée`) et écrire un SOP court pour l'équipe.
**Bloqué par :** Phase 3 du sous-projet `soumissions-plan.md` (digest follow-up info@). Le tagging systématique commence par `relance-faite`, l'analytics arrive ensuite.

---

## Pourquoi ce sous-projet

Allan, 2026-04-15 : *« Si nous avions une connaissance approfondie de toutes les soumissions qui ont été faites, envoyées, exécutées, nous pourrions faire des statistiques concernant le taux de succès à travers nos améliorations et suivi… »*

L'idée : on a investi beaucoup d'efforts cette semaine à améliorer la qualité narrative et structurelle des soumissions PTM (refonte des bundles, descriptions personnalisées, inclusion stricte des tiers, avertissements dans les notes, etc.). Sans données, impossible de mesurer si ces améliorations convertissent vraiment mieux. Avec des données, on peut prouver le ROI — et ajuster le tir là où ça ne fonctionne pas.

PTM serait probablement la première entreprise d'accordage de pianos au Québec à mesurer ses soumissions de cette façon.

## Métriques cibles

| Métrique | Ce qu'elle révèle |
|---|---|
| **Taux d'acceptation global** (% envoyées → acceptées) | Baseline de conversion. Benchmark interne. |
| **Taux d'acceptation par type de service** | Les grands entretiens passent mieux que les restaurations lourdes ? Le PLS se vend mieux avec ou sans housse ? |
| **Impact du suivi dans les 7 jours** | Les soumissions relancées ont-elles un taux d'acceptation 2x supérieur ? Hypothèse forte à valider. |
| **Délai moyen envoi → décision** | Qui traîne le plus ? Faut-il relancer à 5 jours ou à 10 ? |
| **Taux d'exécution** (% acceptées → vraiment faites) | Combien de « oui » se perdent entre le devis signé et la job faite ? |
| **Conversion par technicien** | Certains rédigent-ils des soumissions plus convaincantes ? |
| **Valeur moyenne par soumission** | Par segment (privé/institutionnel), par type de piano, par saison. |
| **Impact des améliorations narratives v2** | Les soumissions refondues semaine du 12 avril 2026 (Deraps, Murray, Sutton, Grands Ballets) convertissent-elles mieux que l'ancien format ? |

## Ce qu'il manque dans Gazelle (le défi)

Gazelle ne track pas nativement le statut « acceptée » ni « exécutée » d'une soumission. Les seuls champs disponibles sont :
- `isArchived` (boolean) — peut signifier « acceptée », « refusée », ou « juste vieille »
- `expiresOn` (date)
- `tags` (liste de strings — c'est ici qu'on injecte notre logique)

**Solution : utiliser les tags Gazelle comme source de vérité pour le cycle de vie.** Convention par tag :

| Tag | Pose quand | Posée par |
|---|---|---|
| `relance-faite` | Le suivi a été effectué auprès du client | La personne au bureau qui appelle |
| `acceptée` | Le client confirme qu'il accepte le devis | Allan / Nicolas / Louise |
| `refusée` | Le client refuse explicitement | Allan / Nicolas / Louise |
| `réalisée` | Les travaux ont été effectués (facturés) | Le tech qui complète le RV de travail |

Une soumission peut avoir 0, 1, 2, 3 ou 4 tags simultanément selon où elle en est dans le cycle. L'absence d'un tag ne prouve rien — la présence d'un tag est une preuve.

## Architecture proposée

### Couche 1 — Tags Gazelle (source de vérité)
- Convention de tagging documentée
- SOP court écrit pour l'équipe (1 page)
- Liste des tags pré-créée dans Gazelle pour faciliter le clic
- Discipline d'équipe : tagger systématiquement

### Couche 2 — Vérification croisée par invoices (sécurité)
- Quand une facture est créée dans Gazelle avec des items qui matchent une soumission, on **infère** automatiquement que la soumission a été exécutée
- Comparaison `amount` + fuzzy match sur les noms d'items
- Permet de rattraper les `réalisée` oubliés
- Ne crée pas de tag — juste une inférence stockée séparément pour les stats

### Couche 3 — Dashboard analytics
- Nouvelle page dans v5 : `/soumissions-stats`
- Lit Gazelle live + invoices + cache Supabase
- Filtres : période, technicien, client type (privé/institutionnel), type de service, segment de prix
- Visualisations : taux de conversion, funnels, heatmaps temporelles, comparaisons avant/après amélioration narrative

### Couche 4 — A/B testing implicite
- Tagger les soumissions refondues semaine 12 avril 2026 avec `format-v2`
- Comparer le taux d'acceptation v2 vs v1 sur des cohortes équivalentes
- Première mesure d'impact narratif après ~6 mois

## Séquence d'implémentation

1. **[Phase 0]** Phase 3 du sous-projet `soumissions-plan.md` (digest info@ + tag `relance-faite`) déployée et adoptée. ⏳ en attente.
2. **[Phase 1]** Ajouter les 3 tags supplémentaires (`acceptée`, `refusée`, `réalisée`). Documenter le SOP de tagging.
3. **[Phase 2]** Laisser tourner ~50-100 soumissions taguées pour avoir une masse critique.
4. **[Phase 3]** Bâtir la page `/soumissions-stats` dans v5, derrière un feature flag pour Allan d'abord.
5. **[Phase 4]** Ajouter la couche invoice matching (couche 2).
6. **[Phase 5]** Tagger rétroactivement les soumissions refondues semaine 12 avril avec `format-v2` pour préparer le A/B.
7. **[Phase 6]** Premier rapport d'impact à Allan après 6 mois — décisions stratégiques basées sur les données.

## Liens

- Sous-projet pré-requis : `soumissions-plan.md`
- Sous-projet adjacent : `bundles-checklists-plan.md` (qualité des bundles influence la conversion)
- Skill associé : `.claude/skills/gazelle/` (pour tout accès Gazelle)
