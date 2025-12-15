# 💬 Guide de l'Assistant Conversationnel Gazelle

**Version :** 5.0
**Disponible pour :** Tous les profils (Admin, Nick, Louise, Jean-Philippe)

---

## 🚀 Démarrer

### Ouvrir l'Assistant

1. Connectez-vous à l'application
2. Cliquez sur le **bouton bleu flottant** en bas à droite de l'écran (💬)
3. L'assistant s'ouvre dans une fenêtre de chat

### Poser une Question

- Tapez votre question dans la zone de texte en bas
- Appuyez sur **Entrée** ou cliquez sur **Envoyer**
- L'assistant répond en quelques secondes

---

## 📖 Commandes Disponibles

### Commandes Générales (Tous)

| Commande | Description | Exemple |
|----------|-------------|---------|
| `.aide` | Affiche toutes les commandes disponibles | `.aide` |
| `.help` | Alias de `.aide` | `.help` |

### Rendez-vous

| Commande | Description | Exemple |
|----------|-------------|---------|
| `.mes rv` | Vos prochains rendez-vous | `.mes rv` |
| `.rv demain` | Rendez-vous de demain | `.rv demain` |
| `.rv cette semaine` | Rendez-vous de la semaine | `.rv cette semaine` |

### Recherche

| Commande | Description | Exemple |
|----------|-------------|---------|
| `.cherche [terme]` | Recherche un client ou piano | `.cherche Yamaha` |
| `.cherche client [nom]` | Recherche un client spécifique | `.cherche client Dupont` |
| `.piano [numéro]` | Infos d'un piano par numéro de série | `.piano 123456` |

### Inventaire (Nick, Louise, Jean-Philippe)

| Commande | Description | Exemple |
|----------|-------------|---------|
| `.stock [produit]` | Vérifier le stock d'un produit | `.stock cordes` |
| `.stock cordes` | Stock de cordes disponible | `.stock cordes` |
| `.stock marteaux` | Stock de marteaux disponible | `.stock marteaux` |

### Statistiques (Admin, Louise)

| Commande | Description | Exemple |
|----------|-------------|---------|
| `.stats` | Statistiques générales du système | `.stats` |
| `.stats mois` | Statistiques du mois en cours | `.stats mois` |
| `.stats année` | Statistiques de l'année | `.stats année` |

### Tournées (Nick)

| Commande | Description | Exemple |
|----------|-------------|---------|
| `.prochaines tournées` | Prochaines tournées planifiées | `.prochaines tournées` |
| `.tournées semaine` | Tournées de la semaine | `.tournées semaine` |

---

## 💡 Exemples de Questions en Langage Naturel

L'assistant comprend aussi le langage naturel ! Essayez :

### Questions sur les Clients

```
Cherche tous les clients Yamaha
Trouve le client avec le piano numéro 123456
Combien de clients ai-je à Montréal ?
```

### Questions sur les Rendez-vous

```
Quels sont mes rendez-vous cette semaine ?
Ai-je des accords demain ?
Combien de rendez-vous ai-je ce mois-ci ?
```

### Questions sur l'Inventaire

```
Combien de cordes il me reste ?
Ai-je assez de marteaux pour la semaine ?
Quel est mon stock de feutres ?
```

### Questions sur les Statistiques

```
Combien de clients actifs ?
Combien de pianos dans la base ?
Quels sont les stats du mois dernier ?
```

---

## 🎯 Suggestions Rapides (Par Profil)

### Nick (Gestionnaire)

Quand vous ouvrez l'assistant, vous verrez:
- `.mes rv` - Mes prochains rendez-vous
- `.prochaines tournées` - Mes tournées à venir
- `.stock cordes` - Stock de cordes disponible
- `.aide` - Voir toutes les commandes

### Louise (Assistante)

Quand vous ouvrez l'assistant, vous verrez:
- `.rv demain` - Rendez-vous de demain
- `.cherche client` - Chercher un client
- `.stats mois` - Stats du mois
- `.aide` - Voir toutes les commandes

### Jean-Philippe (Technicien)

Quand vous ouvrez l'assistant, vous verrez:
- `.mes rv` - Mes prochains rendez-vous
- `.piano [numéro]` - Infos d'un piano
- `.stock marteaux` - Stock de marteaux
- `.aide` - Voir toutes les commandes

### Allan (Admin)

Quand vous ouvrez l'assistant, vous verrez:
- `.aide` - Voir toutes les commandes
- `.mes rv` - Mes prochains rendez-vous
- `.stats` - Statistiques du système
- `.cherche Yamaha` - Chercher un client/piano

---

## 🔧 Fonctionnalités Avancées

### Historique de Conversation

- Les messages restent affichés pendant votre session
- Cliquez sur l'**icône de corbeille** (🗑️) en haut pour effacer l'historique
- L'historique est effacé quand vous fermez l'assistant

### Métadonnées de Réponse

Certaines réponses affichent des informations techniques :
- **Type** : Type de requête détectée par l'assistant
- **Confiance** : Niveau de confiance de la réponse (0-100%)

### Mode Compact

L'assistant s'adapte automatiquement à la taille de votre écran.

---

## ⚠️ Limitations Actuelles

### Ce Que l'Assistant PEUT Faire

✅ Rechercher des clients et pianos
✅ Afficher vos rendez-vous
✅ Vérifier le stock d'inventaire
✅ Afficher des statistiques
✅ Répondre en quelques secondes

### Ce Que l'Assistant NE PEUT PAS (Encore) Faire

❌ Créer ou modifier des rendez-vous
❌ Modifier l'inventaire
❌ Envoyer des emails ou SMS
❌ Générer des factures
❌ Importer des données

---

## 🐛 Troubleshooting

### L'assistant ne répond pas

1. **Vérifiez que l'API est démarrée**
   - Sur votre serveur, l'API doit être en cours d'exécution
   - L'assistant affiche un message d'erreur si l'API est inaccessible

2. **Vérifiez votre connexion Internet**
   - L'assistant nécessite une connexion active

3. **Rechargez la page**
   - Appuyez sur F5 ou Cmd+R pour recharger

### Message "Erreur: HTTP 500"

- L'API a rencontré une erreur
- Contactez Allan pour résoudre le problème
- Essayez de poser votre question différemment

### Réponse "Je n'ai pas compris"

- Reformulez votre question plus simplement
- Utilisez une commande avec un point (ex: `.aide`)
- Essayez une question plus spécifique

---

## 💬 Exemples Complets

### Scénario 1 : Nick Prépare Sa Journée

```
Utilisateur: .mes rv
Assistant: Vous avez 3 rendez-vous aujourd'hui :
           - 9h00 : Accord chez M. Dupont (Yamaha C3)
           - 14h00 : Réparation chez Mme Martin (Steinway B)
           - 16h30 : Estimation chez École St-Jean

Utilisateur: .stock cordes
Assistant: Stock de cordes :
           - Cordes piano droit : 45 unités
           - Cordes piano à queue : 23 unités
           - Cordes basses : 12 unités
```

### Scénario 2 : Louise Cherche un Client

```
Utilisateur: .cherche client Yamaha
Assistant: 12 clients trouvés avec "Yamaha" :
           1. M. Dupont - Yamaha C3 (Montréal)
           2. École St-Jean - Yamaha U1 (Laval)
           3. Mme Tremblay - Yamaha B3 (Québec)
           ...

Utilisateur: .rv demain
Assistant: 5 rendez-vous planifiés pour demain :
           - 8h00 : Accord chez ...
           - 10h30 : Réparation chez ...
           ...
```

### Scénario 3 : Jean-Philippe Vérifie Son Stock

```
Utilisateur: .stock marteaux
Assistant: Stock de marteaux :
           - Marteaux neufs : 34 unités
           - Marteaux rénovés : 12 unités
           - Têtes de marteaux : 67 unités

Utilisateur: .mes rv
Assistant: Vous avez 2 rendez-vous cette semaine :
           - Mercredi 10h : Accord chez M. Leclerc
           - Vendredi 14h : Réparation chez Mme Roy
```

---

## 📞 Support

**Problème technique ?** Contactez Allan
**Suggestion d'amélioration ?** Partagez vos idées !

---

**Créé par :** Claude Code
**Date :** 2025-12-15
**Version :** 5.0.0
