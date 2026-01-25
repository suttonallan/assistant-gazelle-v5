# 🌐 Gestion du Temps et Fuseaux Horaires
- **Référence Locale :** L'heure de travail est toujours `America/Montreal` (EST/EDT) [1].
- **Conformité API Gazelle :** Gazelle envoie les dates en format ISO UTC (ex: 2027-01-25T10:00:00Z) [3].
- **Règle de Comparaison :** Toujours convertir les dates UTC de l'API en `America/Montreal` avant de calculer les alertes.
- **Calcul des 24h :** Une alerte est déclenchée si `Date_RDV - Heure_Actuelle < 24h` (heure locale).

## 🧩 Conformité et Robustesse de l'API
- **Import Unique :** Le module `requests` doit être importé uniquement au niveau global pour éviter le "shadowing".
- **Mode Incrémental :** Prioriser la synchronisation des données futures (2025+) et récentes. Ne jamais lancer de full backfill historique sans instruction explicite [4].
- **Single Sender :** L'envoi d'email doit strictement utiliser `asutton@piano-tek.com` (SendGrid).

## 🏗️ Structure des Données (Spécifique V5)
- **Types Critiques :** Pour l'historique d'entretien, inclure impérativement le type `SERVICE` (en plus de `NOTE` et `APPOINTMENT`) car il contient les relevés d'humidité [8][9].
- **Zéro Devinage :** Ne jamais tenter d'extraire le modèle du piano depuis le texte des notes. Utiliser exclusivement `piano_id`, `instrument_id` ou le `Client Token` pour faire les jointures SQL [7].
- **Stockage Hybride :** Les données fixes (Marque, Série) viennent de la table `gazelle_pianos`. Les données variables (Humidité, Température) viennent de la `Timeline` (CSV/API) [10].
