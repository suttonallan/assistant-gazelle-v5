# Journal des améliorations de l'Assistant Gazelle

Une ligne par amélioration, en langage clair, la plus récente en haut.
Les modifications purement techniques (diagnostics, nettoyage) n'y figurent pas ;
l'historique complet reste dans git.

## Octobre 2026

### 19 octobre
- **Résumés d'appels Zoom : numéro retrouvé** : le numéro du client n'était pas fourni avec le résumé, d'où des avis « client introuvable — numéro : inconnu » même pour des clients connus. L'assistant va maintenant chercher le numéro dans l'historique d'appels Zoom, retrouve la fiche Gazelle et y verse la note.

### 16 octobre
- **Avis au technicien** : quand un technicien crée une facture pour un client qui a déjà une facture récente impayée, il reçoit un courriel dans le quart d'heure pour vérifier que ce n'est pas un doublon (par exemple une facture déjà préparée par Louise).
- **Factures en double** : aux 15 minutes (7 h à 21 h), l'assistant repère dans Gazelle un client qui a deux factures rapprochées (moins de 3 semaines) avec des montants semblables, et écrit à info@ pour que Louise annule celle de trop. Rien n'est modifié automatiquement ; les institutions sont exclues.
- **Note « déjà un rendez-vous »** : la note dans Front nomme maintenant le client de la fiche Gazelle et dit comment il a été reconnu (numéro ou courriel), pour éviter de confondre deux clients.
- **Message d'un client qui a déjà son rendez-vous** : quand un client laisse un message (vocal, texto, courriel) et que sa fiche Gazelle a un rendez-vous à venir, l'assistant ajoute dans la conversation Front une note interne « Ce client a déjà un rendez-vous : jour, heure, technicien ». Vérifié aux 15 minutes : un rendez-vous pris en ligne après le message est aussi signalé. Rien n'est fermé automatiquement.
- **Factures du contrat Vincent-d'Indy automatiques** : 3 semaines avant chaque échéance (1er août, 15 octobre, 15 janvier, 15 avril), l'assistant prépare la facture du versement en brouillon dans Gazelle (montants indexés de 5 % chaque année) et écrit à Louise et Allan pour qu'elle l'envoie depuis QuickBooks à Julio Gonzalo et à la comptabilité de l'École. Jamais de doublon : si la facture existe déjà, rien n'est créé.
- **Factures préparées par Claude** : Claude peut maintenant créer une facture Gazelle (taxes TPS/TVQ cochées) en brouillon, jamais envoyée — l'envoi reste fait par l'équipe dans Gazelle. Premier usage : versement d'octobre du contrat Vincent-d'Indy.

### 14 octobre
- **Appels Zoom → Gazelle** : quand Zoom produit le résumé d'un appel, l'assistant le réécrit (court, en français, noms et adresses corrigés) et l'ajoute à la chronologie du client, retrouvé par son numéro. *En attente : clés Zoom dans Render + abonnement « Call Summary Changed ».*
- **Numéro inconnu** : l'assistant vérifie d'abord si c'est un client existant qui appelle d'un autre numéro (même courriel, ou même nom + même code postal) et rattache la note à sa fiche. En cas de doute, rien n'est créé : courriel à info@ avec les fiches possibles.
- **Nouveau client par téléphone** : si personne ne correspond et que c'est une vraie demande de service, la fiche est créée comme client potentiel (nom, téléphone, courriel, adresse, référence) avec le résumé de l'appel. Fournisseurs et démarcheurs : note envoyée à info@.
- **Photos de piano** : « ajoute au piano de X les photos de son courriel » dépose les images d'un courriel Front sur le piano dans Gazelle.
- **RV d'accompagnement** : un RV personnel d'institution (Place des Arts…) compte comme RV client.
- **Heures** : l'assistant n'affiche plus jamais l'heure UTC (un RV à 9 h n'apparaît plus à 13 h).
- **Téléphone** : l'application se met à jour toute seule ; le bouton d'envoi ➤ reste toujours visible.

### 13 octobre
- **Accès** : l'Assistant Gazelle est réservé à Allan, Louise et Nicolas.
- **Suivi des connexions** de l'équipe (Google ou NIP), visible par Allan.
- **Menu « Ce que je sais faire »** avec exemples ; les demandes que l'assistant ne sait pas traiter sont envoyées à Allan, sans fausse promesse de « revenir ».
- **Frais de déplacement partagés** entre plusieurs clients d'une tournée, calculés sur le trajet optimisé ; accessible directement depuis Ma Journée.
- **Tâches** : les cases cochées s'enregistrent tout de suite.

### 12 octobre
- **Tâches** : mise à jour en direct, étapes assignables, visibilité par membre ; Margot voit seulement ses tâches ; Allan peut « voir comme » un membre.

### 7 octobre
- **Textos Zoom** : les avis vont toujours à info@piano-tek.com.

### 2 octobre
- **Tâches** : un seul fil de discussion par tâche, dans Front (commenter et prévenir en un geste) ; Jean-Philippe est avisé par courriel.
