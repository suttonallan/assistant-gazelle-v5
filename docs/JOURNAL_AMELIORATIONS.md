# Journal des améliorations de l'Assistant Gazelle

Une ligne par amélioration, en langage clair, la plus récente en haut.
Les modifications purement techniques (diagnostics, nettoyage) n'y figurent pas ;
l'historique complet reste dans git.

## Octobre 2026

### 30 octobre
- **« Créer le RV » Place des Arts : la journée de tous les techniciens** : la fenêtre affiche côte à côte la journée de Nick, JP, Margot et Allan à la date demandée, lue en direct dans Gazelle (RV et blocs perso), plus les RV « À attribuer » du jour. On clique sur la colonne du technicien pour le choisir ; dès que l'heure est inscrite, un ✓ ou un ⚠︎ indique qui est libre, et le RV en conflit s'affiche en rouge.
- **Réservation en ligne : plus de demande rattachée à la mauvaise fiche** : quand un client est reconnu seulement par son numéro de téléphone, la demande n'est rattachée à sa fiche que si le nom de famille ou le code postal correspond aussi. Un numéro partagé (école, bureau, numéro réattribué) crée désormais une nouvelle fiche plutôt que de se coller sur celle de quelqu'un d'autre.
### 29 octobre
- **Demandes de RV hors zone : impossibles à oublier** : chaque demande reçue par la réservation en ligne pour un client à plus de 45 km devient une tâche « RV hors zone à fixer » dans le volet Tâches (assignée à Allan pendant l'absence de Louise), avec les coordonnées, les frais affichés au client, ses préférences et une échéance interne à deux jours ouvrables. Aucun délai n'est promis au client. Le courriel dans info@ continue d'arriver ; si l'un des deux échoue, la demande n'est plus perdue.
- **Avis « a déjà un rendez-vous » : fini les répétitions** : l'avis n'apparaît plus que sur un nouveau message d'un client (message vocal, texto, nouveau courriel), une seule fois par client, et jamais quand l'équipe est déjà en échange avec lui (réponse « Re: » ou dernier message venant de nous).
- **Fin des avis « on a reçu une demande Place des Arts »** : redondants, puisque le courriel d'Isabelle arrive déjà dans info@ avec l'étiquette Place des Arts. La vérification de chaque matin de semaine reste en place : elle signale dans Front toute demande sans réponse, absente de l'assistant ou sans RV dans Gazelle.
- **Une demande Place des Arts = une seule conversation dans Front** : l'assistant n'envoie plus d'avis séparé « [PDA — à réviser] » ; il écrit sa détection en commentaire directement sur le courriel d'Isabelle (l'avis séparé ne sert plus qu'en secours si le courriel n'est pas encore dans Front). La fenêtre « Créer le RV » est aussi allégée : la disponibilité se vérifie dans Gazelle avant de répondre, la fenêtre ne la répète plus.
- **Place des Arts : Gazelle fait foi pour les RV créés** : on change le technicien, le jour ou l'heure, ou on annule, directement dans Gazelle — l'assistant suit tout seul. Le menu « Qui le fait » est verrouillé dès qu'un RV existe (« 🔒 changer dans Gazelle »), l'heure réelle du RV s'affiche sous l'heure demandée, et un RV annulé dans Gazelle remet la demande à « Nouveau » (le bouton « Créer le RV » réapparaît).
- **Bouton « Créer le RV » toujours visible** : il est maintenant au début de chaque ligne du tableau Place des Arts, et reste collé à gauche quand on fait défiler le tableau, sur cellulaire comme sur ordinateur.
- **Demandes Place des Arts marquées « traité » dans Front** : quand on crée le RV depuis l'assistant, un commentaire interne « ✅ Traité » (technicien, date, heure) s'ajoute tout seul au courriel de la demande et à l'avis « à réviser » de l'assistant. Toute l'équipe voit d'un coup d'œil que c'est réglé.
- **Un seul avis par rendez-vous** : les avis « Nouveau rendez-vous » mis en attente pendant la nuit arrivaient parfois en plusieurs exemplaires à 7 h 05. Chaque avis n'est maintenant envoyé qu'une seule fois.

### 28 octobre
- **Créer le RV Gazelle directement depuis une demande Place des Arts** : un bouton « 📅 Créer le RV » sur chaque demande sans rendez-vous ouvre une petite fenêtre — on choisit le technicien, on voit sa journée pour confirmer qu'il est libre, on inscrit l'heure confirmée, et un clic crée le RV dans Gazelle (titre habituel, diapason, piano lié) et relie la demande. Plus besoin de ressaisir dans Gazelle.
- **Calculateur de frais plus clair pour Louise** : il affiche la distance et le temps aller, le calcul du tarif (4,50 $ × km au-delà de 20 km) et, au-delà de 45 km, un montant suggéré pour un déplacement seul, avec un renvoi au calculateur de tournée pour répartir les frais quand on regroupe des visites.
- **Nouveau tarif de déplacement, simple et graduel** : 4,50 $ par kilomètre au-delà de 20 km du métro Outremont, jusqu'à 45 km. Plus de saut à la sortie de la zone gratuite, et le même prix pour la même adresse à chaque fois (le temps de route n'entre plus en compte). Au-delà de 45 km, la coordonnatrice fixe le rendez-vous et les frais. La page de réservation, Ma Journée et le calculateur du site appliquent la règle automatiquement.
- **Rapport hebdomadaire des fiches clients en double** : chaque lundi matin, info@ reçoit la liste des nouvelles fiches qui semblent en double (même téléphone ou même courriel), avec la fiche à garder suggérée et le lien Gazelle de chacune. Les groupes déjà revus par Allan ne reviennent pas. Pas de courriel s'il n'y a rien de nouveau.
- **Bilan quotidien de la réservation en ligne** : chaque matin à 7 h 45, info@ reçoit un message résumant la veille sur la nouvelle page de réservation — combien de visiteurs à chaque étape, les demandes envoyées, et les personnes parties sans envoyer après avoir laissé leurs coordonnées. Les chiffres ne se perdent plus quand le service redémarre.
- **Fini les fiches clients en double après un message vocal** : quand un client laisse un message vocal, rappelle, ou que Zoom complète son résumé, l'assistant ajoute la note à la fiche déjà créée au lieu d'en créer une nouvelle. Avant de créer une fiche, il vérifie maintenant directement dans Gazelle (téléphone et courriel), et non plus seulement dans sa copie de la veille.

### 27 octobre
- **Calculateur de kilomètres, lieu propre au rendez-vous** : quand un rendez-vous (ou un bloc perso lié à un client) a son propre lieu dans Gazelle — un aéroport, un entrepôt, une salle — c'est ce lieu qui compte dans les kilomètres, et non l'adresse de la fiche client.

### 26 octobre
- **Frais de déplacement, l'île n'est plus gratuite partout** : l'île de Montréal est gratuite jusqu'à 20 km du métro Outremont, comme ailleurs. Plus loin (Roxboro, Pierrefonds, Pointe-Claire, Kirkland, Sainte-Anne-de-Bellevue, Pointe-aux-Trembles…), le temps de route compte de nouveau : kilomètres au-delà de 40 km aller-retour et minutes au-delà de 40 min aller-retour. Exemple : Roxboro (H8Y 3R9) passe de gratuit à 28,38 $. Longueuil, Brossard et Saint-Lambert restent gratuits.
- **Place des Arts : plus d'alerte « doublon » pour un événement à plusieurs pianos** : quand un même événement demande deux pianos différents (ex. ADISQ, Steinway D + 7') et que le rendez-vous Gazelle les contient tous, le vérificateur du matin ne le signale plus. Un même piano demandé deux fois reste signalé.
- **Moins de fausses alertes de stationnement (Place des Arts)** : le vérificateur du matin tient maintenant compte des notes « stat » ajoutées sans auteur (par exemple par l'assistant) ou écrites par Louise, sur le piano du rendez-vous.
- **Place des Arts : liaison des demandes aux rendez-vous plus fiable** : l'assistant reconnaît maintenant un rendez-vous Gazelle même si les accents ou les abréviations diffèrent de la demande (ex. « Opéra de mtl » = « Opera de Montréal »). Les demandes de l'Opéra à l'UQAM, restées « en attente », se lient d'elles-mêmes.
- **Textos reçus lisibles** : les accents des textos transférés à info@ s'affichent correctement (« parlé », « être ») au lieu de codes comme « \u00E9 ».
- **Notes d'appels fiables à partir de l'enregistrement** : quand un appel est enregistré, l'assistant lit la transcription complète (et non plus le seul résumé de Zoom) et en tire la note Gazelle : coordonnées, piano, disponibilités du client, accès, et un avertissement si le prix entendu ne correspond pas au tarif. Actif dès que Zoom donne à l'assistant la permission de lire les enregistrements.
- **Liens de réservation : toujours la bonne adresse** : les liens préparés par l'assistant (Front, courriel, chat) pointent maintenant toujours vers reserver.pianotechniquemontreal.com, jamais vers l'ancienne adresse technique.
- **Résumés d'appels Zoom complets** : quand Zoom complète un résumé d'appel quelques minutes après l'appel (préférences du client, détails), la version complète est maintenant traitée à son tour au lieu d'être ignorée.
- **Le nom du client s'affiche dans Zoom quand il appelle** : chaque nuit, tous les clients Gazelle sont copiés dans les contacts partagés de Zoom Phone (nom et numéros). Louise et les techniciens voient donc qui appelle au lieu d'un simple numéro. Les contacts entrés à la main dans Zoom ne sont pas touchés.

### 25 octobre
- **Frais de déplacement plus justes** : l'île de Montréal, Longueuil, Brossard et Saint-Lambert sont maintenant toujours sans frais. Ailleurs, on ne facture que la partie du trajet au-delà de 20 km du métro Outremont (kilomètres et temps de route de ce bout seulement) : plus de saut brusque juste après 20 km.
- **Frais de déplacement : une seule règle, la même partout** : les frais d'un client se calculent maintenant depuis un point fixe au centre du territoire (station de métro Outremont), en auto. Aucuns frais si le client est à 20 km ou moins ; au-delà, 0,59 $/km et 57,50 $/h pour la distance et le temps qui dépassent 20 km et 20 minutes (aller et retour). Le montant ne dépend plus du technicien. Le calculateur de l'assistant, la page de réservation, le chat et le site utilisent la même règle.
- **Écrire à l'assistant par courriel (assistant@piano-tek.com)** : l'équipe peut envoyer une question ou transférer le courriel d'un client avec une consigne (ex. « fais-lui un lien de réservation ») ; l'assistant répond dans le fil en quelques minutes. Il ne répond qu'aux adresses de l'équipe. Actif dès que la boîte « Assistant » existe dans Front.
- **« Ma Journée » sait préparer un lien de réservation prérempli** : demandez-le à l'assistant avec les coordonnées du client.
- **Lien de réservation prérempli en un clic dans Front** : ajoutez l'étiquette « Lien RV » à un courriel de client ; en deux minutes, l'assistant ajoute un commentaire interne avec un lien vers la page de réservation où ses coordonnées et son piano sont déjà inscrits (il n'a qu'à ajouter son numéro civique). Si le client est déjà dans Gazelle, c'est son lien personnel. Il suffit de coller le lien dans la réponse.
- **Inventaire, Margot a maintenant sa colonne** : Margot apparaît dans l'inventaire des techniciens au même titre que Nicolas, Jean-Philippe et Allan, et peut y entrer ses propres quantités.
- **Calculateur de kilomètres, chaque journée part de la maison** : sur une période (plusieurs jours ou un trimestre), le trajet est maintenant calculé jour par jour : maison → clients → maison. Avant, l'assistant allait directement du dernier client d'une journée au premier client du lendemain, ce qui faussait le total, surtout quand le technicien change de mode de déplacement (auto ou vélo) d'un jour à l'autre. Chaque trajet affiche aussi sa date.

### 24 octobre
- **Vincent-d'Indy, fin des « accords collectifs » dans l'agenda de Nicolas** : quand on pousse les fiches terminées vers Gazelle, chaque piano reçoit maintenant une simple note dans son historique d'entretien, datée du jour réel du service. Plus aucun rendez-vous n'est créé, donc plus rien n'atterrit dans un agenda. Les pianos inactifs restent inactifs, et la date du dernier service du piano est mise à jour.

### 23 octobre
- **Place des Arts, « À confirmer »** : dans le doute, l'assistant demande au lieu de deviner. Une demande n'est rattachée toute seule que si le rendez-vous Gazelle nomme sa salle ou son événement. Sinon, un encadré orange montre les rendez-vous possibles du jour, et on clique sur le bon (ou « Aucun »). Ce choix est mémorisé, et la synchro ne le défait jamais.
- **Place des Arts, rattachement sans devinette** : le bouton « Synchroniser » ne peut plus coller une demande au rendez-vous d'une autre ni changer un technicien choisi à la main. Un rendez-vous annulé n'est plus jamais rattaché. Quand un rendez-vous Gazelle ne dit ni la salle ni l'événement et pourrait convenir à deux demandes du même jour, aucune des deux n'est rattachée : elles restent « à lier ».
- **Place des Arts, mauvais technicien** : une nouvelle demande ne peut plus être rattachée au rendez-vous Gazelle d'une autre demande, ni à un rendez-vous d'une autre salle ou à plus de 3 h d'écart. La demande 5E/Stella du 27 oct. avait hérité d'Allan parce qu'elle avait été collée au rendez-vous de Loreena McKennitt (MS, 13h) ; elle redevient « à attribuer » jusqu'à ce que son vrai rendez-vous existe dans Gazelle.
- **Place des Arts, demandes à plusieurs pianos** : quand une demande liste deux pianos pour le même événement (ex. Adisq, 8 nov., Steinway 9' et 7'), l'import crée maintenant une ligne par piano au lieu d'en garder une seule — chaque piano est donc facturé.
- **Place des Arts, doublons** : une demande n'est considérée comme doublon que si tout est identique (date, salle, événement, piano et heure). Avant, deux pianos de même marque, ou « avant 11h » et « après 11h », pouvaient être confondus et l'un des deux disparaissait.

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
