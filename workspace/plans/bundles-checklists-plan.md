# Sous-projet — Amélioration des checklists des bundles de service

**Statut :** 🟡 en attente (besoin d'une session de travail avec Nicolas)
**Créé le :** 2026-04-11
**Dernière mise à jour :** 2026-04-23
**Prochain pas :** Planifier 1-2 heures avec Nicolas (idéalement pendant qu'il rédige une vraie soumission) pour passer en revue les actions par défaut des 7 bundles existants (`grand_entretien_droit`, `grand_entretien_queue_1j`, `cordes_basses_complet`, `remplacement_marteaux_droit`, `assemblage_marteaux_queue`, `mortaises_clavier`, `adsilent_install_queue`). Pour chaque action : valider / reformuler / supprimer / marquer les manquantes.
**Bloqué par :** disponibilité de Nicolas pour une session collaborative.

## 🟠 Décisions en attente pour Allan (2026-04-23)

1. **Doublon MSL marteaux** — Deux items identiques à 3 800 $ :
   - `mit_bHJzHuiI28Gz6EqF` — "Assemblage complet des marteaux (Abel, manches bambou)" — renommé aujourd'hui, utilisé dans #11928, #11929, #11930
   - `mit_zvN0RqqMZeHuYWBj` — "Remplacement de l'assemblage des marteaux (piano à queue)" — existait déjà, contenu similaire
   - **À décider :** archiver lequel ? Le bundle pointe maintenant vers `mit_bHJzHuiI28Gz6EqF`.

2. **MSL Adsilent existants** — À réconcilier avec notre bundle :
   - `mit_fG9TTYyBzuOKGfzy` — "Système 'Silent' pour piano à queue" à **7 000 $**
   - `mit_tycyqSHsyV5MQNKg` — "Système Silent Adsilent pour piano droit" à **4 800 $**
   - `mit_o04b33O4D45Q39DD` — "Révision et maintenance du clavier pour pianos Silent et hybrides" à **455 $**
   - Notre bundle `adsilent_install_queue` est à 5 520 $ (kit + install + livraison, prix Franz 2020 + 10%). Écart avec le MSL existant à 7 000 $.
   - **À décider :** quel prix est le bon ? Mettre à jour le MSL ou utiliser le MSL existant ?

3. **MSL "Système de correction de l'échappement"** — Utilisé dans #11930 à 717 $, mais aucun MSL trouvé avec ce nom. À créer comme MSL standalone pour qu'il soit réutilisable par les techs.

**Lancé le** 2026-04-11 par Allan, en marge du plan soumissions principal (`soumissions-plan.md`).

## Objectif

Rendre les checklists d'actions de chaque bundle **"tout de suite bon"** à l'invocation — c'est-à-dire qu'une fois que Nicolas (ou un autre technicien) clique « Nouvelle soumission intelligente » et sélectionne un bundle, la liste d'actions cochées par défaut corresponde déjà à ce qu'il ferait réellement dans 90 % des cas, sans qu'il ait à décocher ou ajouter quoi que ce soit.

## Pourquoi ce sous-projet

Aujourd'hui (Phase 1 complétée), le catalogue des 4 bundles pilote contient des listes d'actions **plausibles** mais **génériques** — je les ai dérivées de la `description` héritée du `masterServiceItem` Gazelle plus quelques étapes qui me semblaient logiques. Rien n'est validé par un vrai technicien.

Tant qu'on ne passe pas du temps à valider/corriger ces listes avec Nicolas (qui fait le travail réel chaque semaine), le bundle sera utile mais pas optimal — Nicolas devra corriger à la main à chaque invocation, ce qui tue la promesse "une seule ligne, zéro correction".

## Livrables attendus

- [ ] **Validation de chaque action existante** dans les 4 bundles pilote (grand entretien droit, grand entretien queue 1j, cordes basses complet, remplacement marteaux droit) — Nicolas dit pour chaque action : "oui c'est ça / reformule / supprime / manquante"
- [ ] **Ajout des actions manquantes** à la vraie pratique de PTM (ex: vérifier si "feutrage des marteaux" manque dans grand entretien, si "mesure de la flèche du sommier" manque avant cordes basses)
- [ ] **Ajustement des `default: True/False`** — certaines actions peuvent exister dans le bundle mais être décochées par défaut (options rares mais utiles quand le cas se présente)
- [ ] **Reformulation des libellés client** — le texte doit être compréhensible pour un client non technicien, pas du jargon RPT
- [ ] **Expansion du catalogue** — créer les bundles manquants (liste cible : voir `soumissions-plan.md` section 4)

## Contraintes dures (règles à ne JAMAIS violer)

- ❌ **Ne pas inclure "accord de suivi 3 semaines après installation PLS"** dans les bundles `pls_install_*` — c'est un service facturé séparément, pas une étape du bundle. Voir feedback memory `feedback_pls_install_no_followup_tuning.md`. Ajoutée par Allan 2026-04-11.

*(D'autres contraintes à ajouter au fur et à mesure que Nicolas identifie ce qui ne doit PAS figurer dans tel ou tel bundle.)*

## Méthode proposée

1. **Session de travail avec Nicolas** — idéalement en même temps qu'il crée une vraie soumission sur un client, pour capter ses actions réelles en direct
2. **Mise à jour de `service_bundles.py`** — commit par bundle, pour garder l'historique
3. **Test en invocation** — lancer le bundle sur un cas réel et vérifier que zéro correction est nécessaire
4. **Itération** jusqu'à validation

## Interaction avec le plan principal

Ce sous-projet est un **pré-requis à la Phase 5** du plan soumissions (migration de Nicolas vers la CLI / l'UI v5). Sans checklists fiables, l'UI est utile mais le technicien doit corriger chaque fois — ce qui n'apporte rien par rapport au workflow manuel actuel.

## Statut

- 🟡 **Lancé le 2026-04-11**, en attente de la session de travail avec Nicolas
- Référence : soumissions #11915 (Isabelle Murray) et #11916 (Francine Deraps) — preuves de concept de la nouvelle architecture, à montrer à Nicolas comme point de départ de la discussion
