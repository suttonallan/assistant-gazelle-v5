# 🎓 Interface Web d'Entraînement des Sommaires

Interface web intuitive pour raffiner les formats de sommaires avec vos vraies données.

## 🚀 Installation

1. Installer Flask (si pas déjà installé) :
```bash
pip install flask>=3.0.0
```

Ou installer toutes les dépendances :
```bash
pip install -r requirements.txt
```

## 📖 Utilisation

1. Lancer l'interface web :
```bash
python3 scripts/train_summaries_web.py
```

2. Ouvrir votre navigateur à :
```
http://localhost:5001
```

3. Utiliser l'interface :
   - **📅 Sommaire Journée** : Générer un sommaire pour une date spécifique
   - **👤 Sommaire Client** : Générer un sommaire pour un client spécifique
   - **📊 Historique** : Voir les résultats d'entraînement précédents
   - **⚖️ Comparer** : Comparer les 3 formats côte à côte

## ✨ Fonctionnalités

- Interface visuelle moderne et intuitive
- Recherche de clients en temps réel
- Génération de sommaires dans 3 formats (Compact, Détaillé, V4 Style)
- Système de feedback avec notes et commentaires
- Historique des entraînements
- Comparaison côte à côte des formats

## 🔧 Configuration

L'interface utilise les mêmes variables d'environnement que le script principal :
- `SUPABASE_URL`
- `SUPABASE_KEY`

Assurez-vous que votre fichier `.env` est correctement configuré.

## 📝 Notes

- Les résultats sont sauvegardés dans `scripts/summary_training_results.json`
- Le serveur tourne sur le port 5001 par défaut
- Appuyez sur `Ctrl+C` pour arrêter le serveur

