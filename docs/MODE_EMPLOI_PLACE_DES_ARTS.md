# Mode d'emploi - Place des Arts
## Pour Louise et Nicolas

---

## 📋 Table des matières

1. [Vue d'ensemble](#vue-densemble)
2. [Navigation et onglets](#navigation-et-onglets)
3. [Légende des couleurs](#légende-des-couleurs)
4. [Importer une demande](#importer-une-demande)
5. [Gérer les techniciens](#gérer-les-techniciens)
6. [Statuts des demandes](#statuts-des-demandes)
7. [Synchronisation avec Gazelle](#synchronisation-avec-gazelle)
8. [Actions en lot](#actions-en-lot)
9. [Astuces et bonnes pratiques](#astuces-et-bonnes-pratiques)

---

## 🎯 Vue d'ensemble

Le module **Place des Arts** permet de gérer toutes les demandes de service pour les pianos de la Place des Arts. Il synchronise automatiquement avec Gazelle pour suivre les rendez-vous et les techniciens assignés.

### Accès
- Allez dans le menu « institutions » → **Place des Arts**
- Deux onglets disponibles : **Demandes** et **Inventaire Pianos**

---

## 📑 Navigation et onglets

### Onglet "Demandes"
Affiche toutes les demandes de service avec leurs statuts, techniciens assignés, et informations de facturation.

### Onglet "Inventaire Pianos"
Liste tous les pianos de la Place des Arts avec leur localisation, état, et dernière date d'accord.

---

## 🎨 Légende des couleurs

Chaque ligne du tableau des demandes a une couleur qui indique son état :

| Couleur | Signification |
|---------|---------------|
| 🔴 **Rouge** | Pas encore de RV donné à un technicien actif<br>→ **Action requise** : Créer le RV dans Gazelle ou assigner un technicien |
| ⚪ **Blanc** (pas de couleur) | RV créé avec technicien actif confirmé, mais pas encore complété<br>→ **Tout est OK**, en attente de réalisation |
| 🟢 **Vert** | RV complété<br>→ **Terminé**, prêt pour facturation si nécessaire |
| 🔵 **Bleu** | Ligne sélectionnée (case cochée)<br>→ Pour effectuer des actions en lot |

### Exemples
- **Ligne rouge** : Demande créée mais pas encore de RV dans Gazelle, ou RV avec technicien "À attribuer"
- **Ligne blanche** : RV créé dans Gazelle avec Nick, Allan ou JP assigné
- **Ligne verte** : Service complété, le technicien a terminé le travail

---

## 📥 Importer une demande

### Méthode 1 : Copier-coller depuis un email

1. **Copiez le texte de l'email** contenant la demande
2. **Collez-le** dans la zone de texte "Import depuis email"
3. Cliquez sur **"👁️ Prévisualiser"**
4. **Vérifiez** les champs détectés automatiquement :
   - Date du rendez-vous
   - Salle
   - Pour qui (artiste/organisation)
   - Piano
   - Diapason
   - Heure
   - Demandeur
5. **Complétez** les champs manquants si nécessaire
6. Cliquez sur **"💾 Importer"**

### Méthode 2 : Ajout manuel

1. Cliquez sur **"➕ Ajouter manuellement"**
2. Remplissez tous les champs requis
3. Cliquez sur **"Enregistrer"**

---

## 👷 Gérer les techniciens

### Affichage des techniciens

Dans la colonne **"Qui le fait"**, vous verrez :

- **Dropdown normal (blanc)** : Technicien assigné correctement
- **Dropdown orange** : Technicien "À attribuer" dans Gazelle
- **Dropdown jaune** : ⚠️ **Incohérence détectée** entre PDA et Gazelle

### Cas particuliers

#### 🔶 Technicien "À attribuer"
- **Quand** : Le RV existe dans Gazelle mais aucun technicien actif n'est encore assigné
- **Affichage** : Dropdown orange avec "⚠️ À attribuer"
- **Action** : Assignez un technicien (Nick, Allan ou JP) dans Gazelle, puis synchronisez

#### ⚠️ Incohérence détectée (fond jaune)
- **Quand** : Le technicien dans PDA ne correspond pas à celui dans Gazelle
- **Exemple** : PDA indique "Allan" mais Gazelle a "À attribuer"
- **Action** : 
  1. Cliquez sur l'icône **🔄** à côté du dropdown
  2. Confirmez la synchronisation
  3. Le technicien sera mis à jour pour correspondre à Gazelle

### Changer un technicien

**Important** : Les techniciens doivent être assignés directement dans Gazelle. Une fois assigné dans Gazelle, cliquez sur **"🔄 Synchroniser tout avec Gazelle"** pour mettre à jour automatiquement les techniciens dans PDA. Le système synchronisera automatiquement les changements depuis Gazelle.

---

## 📊 Statuts des demandes

| Statut | Signification | Couleur badge |
|--------|---------------|---------------|
| **Nouveau** | Demande importée, pas encore traitée | 🟡 Jaune |
| **Créé Gazelle** | RV créé dans Gazelle (même si technicien "À attribuer") | 🔵 Bleu |
| **Assigné** | Technicien actif assigné (Nick, Allan ou JP) | 🟢 Vert clair |
| **Complété** | Service terminé | ⚪ Gris |
| **Facturé** | Facturation effectuée | 🟣 Violet |

### Évolution normale d'un statut

```
Nouveau → Créé Gazelle → Assigné → Complété → Facturé
```

---

## 🔄 Synchronisation avec Gazelle

### Synchronisation automatique

La synchronisation automatique se fait en arrière-plan avec les autres synchronisations du système. Elle met à jour :
- Les RV créés dans Gazelle
- Les techniciens assignés
- Les statuts "Complété"

**Note** : Pour une mise à jour immédiate, utilisez la synchronisation manuelle ci-dessous.

### Synchronisation manuelle

#### Bouton "🔄 Synchroniser tout avec Gazelle"
Ce bouton unique effectue toutes les synchronisations nécessaires :
- Trouve et lie les RV correspondants dans Gazelle
- Met à jour les statuts (y compris "Complété" si le RV est complété dans Gazelle)
- Synchronise tous les techniciens depuis Gazelle (source de vérité)
- Corrige les incohérences entre PDA et Gazelle

**Quand l'utiliser** :
- Après avoir créé des RV dans Gazelle
- Après qu'un technicien ait complété un service
- Si vous voyez des incohérences entre PDA et Gazelle

### Quand synchroniser ?

- **Après avoir créé des RV dans Gazelle** : Cliquez sur "🔄 Synchroniser tout avec Gazelle"
- **Après qu'un technicien ait complété un service** : Cliquez sur "🔄 Synchroniser tout avec Gazelle"
- **Si vous voyez des incohérences** : Utilisez l'icône 🔄 sur la ligne concernée ou synchronisez tout

---

## 📦 Actions en lot

### Sélectionner plusieurs demandes

1. **Cochez les cases** à gauche des lignes à sélectionner
2. Ou cochez la case d'en-tête pour **tout sélectionner**

### Actions disponibles

Une fois des lignes sélectionnées, vous pouvez :

- **Facturer** : Cliquez sur "Facturer" pour marquer les demandes comme facturées
- **Supprimer** : Cliquez sur "Supprimer" (⚠️ Attention : action irréversible)

**Note** : Les actions de changement de statut et d'année sont réservées à l'administration du système.

### Actions rapides par statut

- **Facturer** : Passe les demandes sélectionnées au statut "Facturé"

---

## 💡 Astuces et bonnes pratiques

### ✅ À faire

1. **Toujours prévisualiser** avant d'importer une demande
2. **Vérifier les champs détectés** automatiquement et les corriger si nécessaire
3. **Synchroniser régulièrement** avec Gazelle, surtout après avoir créé des RV
4. **Utiliser "Synchroniser tout avec Gazelle"** une fois par jour pour mettre à jour les statuts et techniciens
5. **Vérifier les incohérences** (lignes jaunes) et les corriger avec l'icône 🔄

### ❌ À éviter

1. **Ne pas ignorer les lignes rouges** : Elles indiquent qu'une action est requise
2. **Ne pas changer un technicien directement dans PDA** : Assignez-le dans Gazelle, puis synchronisez
3. **Ne pas supprimer** des demandes sans être certain (action irréversible)

### 🔍 Dépannage

#### "Ma demande est rouge mais le RV existe dans Gazelle"
→ Cliquez sur "🔄 Synchroniser tout avec Gazelle" pour lier le RV

#### "Le technicien est différent entre PDA et Gazelle"
→ Cliquez sur l'icône 🔄 à côté du dropdown pour synchroniser, ou utilisez "🔄 Synchroniser tout avec Gazelle"

#### "Le statut ne passe pas à 'Complété'"
→ Cliquez sur "🔄 Synchroniser tout avec Gazelle" pour mettre à jour les statuts

#### "Je ne vois pas 'À attribuer' dans le dropdown"
→ C'est normal ! "À attribuer" n'apparaît que si le RV existe dans Gazelle avec ce technicien

---

## 📞 Support

Si vous rencontrez un problème ou avez une question :
1. Vérifiez d'abord ce mode d'emploi
2. Vérifiez les couleurs et les icônes d'avertissement
3. Contactez Allan pour assistance technique

---

## 📝 Notes importantes

- **Gazelle est la source de vérité** : Les informations dans Gazelle ont priorité
- **Les couleurs sont automatiques** : Elles reflètent l'état réel des demandes
- **La synchronisation est importante** : Elle garantit la cohérence entre PDA et Gazelle
- **"À attribuer" est temporaire** : Une fois un technicien assigné dans Gazelle, la ligne devient blanche

---

*Dernière mise à jour : Janvier 2026*
