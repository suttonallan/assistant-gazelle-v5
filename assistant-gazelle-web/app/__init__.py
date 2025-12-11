"""
Module Flask pour Assistant Gazelle Web
Initialise l'application Flask et enregistre les blueprints
"""

from flask import Flask
from flask_cors import CORS
import os
from pathlib import Path

# Importer les routes d'inventaire
from .inventory_routes import inventory_bp


def create_app():
    """Factory function pour créer l'application Flask"""
    app = Flask(__name__)
    
    # Configuration CORS
    CORS(app, resources={
        r"/api/*": {
            "origins": os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(","),
            "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            "allow_headers": ["Content-Type", "Authorization"]
        }
    })
    
    # Enregistrer les blueprints
    app.register_blueprint(inventory_bp)
    
    # Route de santé globale
    @app.route('/health', methods=['GET'])
    def health():
        return {'status': 'ok', 'service': 'assistant-gazelle-web'}, 200
    
    return app

