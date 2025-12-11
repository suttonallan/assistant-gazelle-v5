#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Point d'entrée pour lancer l'application Flask
Piano Technique Montréal - Version Web (Render/Supabase)
"""

import os
from dotenv import load_dotenv
from app import create_app

# Charger les variables d'environnement
load_dotenv()

# Créer l'application
app = create_app()

if __name__ == '__main__':
    # Configuration du port (Render utilise PORT, sinon 5000)
    port = int(os.getenv('PORT', 5000))
    host = os.getenv('HOST', '0.0.0.0')
    debug = os.getenv('DEBUG', 'false').lower() == 'true'
    
    print(f"🚀 Démarrage Assistant Gazelle Web sur {host}:{port}")
    print(f"📊 Mode debug: {debug}")
    
    app.run(host=host, port=port, debug=debug)

