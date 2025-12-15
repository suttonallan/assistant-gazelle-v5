# 🔍 Où trouver les Environment Variables dans Render

## Méthode 1 : Via Settings (le plus commun)

1. Va sur [render.com](https://render.com)
2. Clique sur ton service (ex: `assistant-gazelle-v5-api`)
3. Dans le menu de gauche, cherche **Settings** (icône ⚙️)
4. Fais défiler la page Settings
5. Cherche une section appelée :
   - **Environment** 
   - **Environment Variables**
   - **Env Vars**
   - **Variables**

## Méthode 2 : Via le menu du service

1. Clique sur ton service
2. En haut de la page, il y a des onglets :
   - **Overview**
   - **Logs**
   - **Events**
   - **Settings** ← Clique ici
3. Dans Settings, cherche **Environment**

## Méthode 3 : Si tu es dans le dashboard principal

1. Dans la liste de tes services
2. Clique sur les **3 points** (⋯) à droite de ton service
3. Cherche **Settings** ou **Configure**

## Méthode 4 : Recherche directe

1. Une fois dans ton service
2. Utilise `Cmd+F` (Mac) ou `Ctrl+F` (Windows) pour chercher
3. Tape : `environment` ou `env` ou `variable`
4. Ça devrait te montrer où c'est

## Si tu ne trouves toujours pas

### Vérifie que tu es au bon endroit :
- ✅ Tu es dans un **Web Service** (pas un Static Site)
- ✅ Tu es le propriétaire/admin du service
- ✅ Tu es connecté avec le bon compte

### Alternative : Créer un nouveau service

Si tu ne trouves vraiment pas, on peut :
1. Créer un nouveau service avec les variables dès le départ
2. Ou utiliser l'API Render pour les ajouter

## Capture d'écran de référence

Dans Render, les Environment Variables sont généralement :
- Dans **Settings** → Section **Environment**
- Ou dans **Settings** → Section **Environment Variables**
- Parfois dans un onglet séparé **Environment**

## Prochaine étape

Dis-moi :
1. Quel type de service c'est ? (Web Service, Static Site, etc.)
2. Quels onglets/menus tu vois dans ton service ?
3. Peux-tu me dire ce que tu vois dans le menu de gauche ?









