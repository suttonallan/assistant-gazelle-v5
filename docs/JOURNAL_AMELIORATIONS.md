# Journal des améliorations de l'Assistant Gazelle

Une ligne par amélioration, en langage clair, la plus récente en haut.
Les modifications purement techniques (diagnostics, nettoyage) n'y figurent pas ;
l'historique complet reste dans git.

## Octobre 2026

### 21 octobre
- **Réservation en ligne, clients éloignés** : à plus de 45 km du technicien le plus proche (ex. Saint-Jérôme, Mirabel, Orford), le client voit l'estimation des frais de déplacement et indique ses préférences et indisponibilités au lieu de choisir une plage ; la demande arrive dans Front (info@) pour que la coordonnatrice fixe le rendez-vous.
- **Chat du site, demandes de rappel** : quand un client demande dans le chat qu'on l'appelle, sa demande (prénom, téléphone, meilleur moment et résumé de la conversation) arrive dans Front, boîte info@. Le client sait qu'on le rappelle d'ici deux jours ouvrables.
- **Ménage de Front** : les conversations sans activité depuis le 7 octobre dans info@ et asutton@ sont archivées (rien n'est effacé ; une conversation revient d'elle-même si le client réécrit). Combiné au bouton « Send & archive », ce qui reste dans la liste est ce qui demande de l'attention.

### 20 octobre
- **Stationnement PdA saisi par le bureau** : un « stat 13$ » écrit par Louise dans la note d'un technicien (Allan, Margot, Nicolas, Jean-Philippe) est maintenant reporté sur le RV. Une note écrite par un autre technicien ne compte toujours pas, pour éviter les doublons.
- **Réservation en ligne : le client reste dans Gazelle même si la demande est refusée.** La nouvelle page crée (ou retrouve, par courriel ou téléphone) la fiche du client avant d'envoyer la demande, dans sa langue, et ajoute une note dans sa chronologie avec la plage, le service et le piano demandés.
- **Numéro client dans Gazelle** : le champ « Numéro client » de chaque fiche est rempli automatiquement (et chaque nuit pour les nouveaux clients). Il servira aux rappels pour envoyer chaque client vers la nouvelle page de réservation, avec son dossier déjà reconnu.

### 19 octobre
- **Commentaires sur la réservation en ligne** : les clients qui essaient la nouvelle page de réservation peuvent laisser une note (1 à 5) et un commentaire ; ils arrivent par courriel dans la boîte info de Front.
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
