"""
Routes Flask pour la gestion de l'inventaire
Piano Technique Montréal - Version Web (Render/Supabase)

Endpoints:
- GET /api/inventory/check-stock - Vérifier les stocks bas
- GET /api/inventory/export - Exporter les données (admin)
- GET /api/inventory/alerts - Obtenir toutes les alertes
"""

from flask import Blueprint, jsonify, request, send_file
from functools import wraps
import sys
from pathlib import Path

# Ajouter le répertoire parent au path
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.inventory_checker import (
    check_low_stock,
    check_zero_stock,
    generate_alerts
)
from scripts.export_inventory_data import (
    export_products,
    export_inventory,
    export_product_display
)

# Créer le blueprint
inventory_bp = Blueprint('inventory', __name__)


def require_auth(permission='read_client'):
    """
    Décorateur pour l'authentification (à adapter selon votre système d'auth)
    Pour l'instant, simple vérification basique
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # TODO: Implémenter la vérification d'authentification réelle
            # Pour l'instant, on accepte toutes les requêtes
            # auth_header = request.headers.get('Authorization')
            # if not auth_header or not verify_token(auth_header):
            #     return jsonify({'error': 'Unauthorized'}), 401
            return f(*args, **kwargs)
        return decorated_function
    return decorator


@inventory_bp.route('/api/inventory/check-stock', methods=['GET'])
@require_auth('read_client')
def check_stock():
    """
    Vérifie les stocks bas et retourne les alertes
    
    Query params:
    - technician_id (optionnel): Filtrer par technicien
    """
    try:
        technician_id = request.args.get('technician_id', None)
        alerts = generate_alerts(technician_id=technician_id)
        return jsonify({
            'success': True,
            'data': alerts
        }), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@inventory_bp.route('/api/inventory/alerts', methods=['GET'])
@require_auth('read_client')
def get_alerts():
    """
    Retourne toutes les alertes de stock (stocks bas + ruptures)
    
    Query params:
    - technician_id (optionnel): Filtrer par technicien
    - type (optionnel): 'low' (stocks bas), 'zero' (ruptures), ou 'all' (défaut)
    """
    try:
        technician_id = request.args.get('technician_id', None)
        alert_type = request.args.get('type', 'all').lower()
        
        result = {}
        
        if alert_type in ('all', 'low'):
            result['low_stock'] = check_low_stock(technician_id)
        
        if alert_type in ('all', 'zero'):
            result['zero_stock'] = check_zero_stock(technician_id)
        
        if alert_type == 'all':
            result['summary'] = {
                'total_low_stock': len(result.get('low_stock', [])),
                'total_zero_stock': len(result.get('zero_stock', [])),
                'total_alerts': len(result.get('low_stock', [])) + len(result.get('zero_stock', []))
            }
        
        return jsonify({
            'success': True,
            'data': result
        }), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@inventory_bp.route('/api/inventory/export', methods=['GET'])
@require_auth('admin')
def export_inventory_data():
    """
    Exporte les données d'inventaire en CSV/JSON (admin uniquement)
    
    Query params:
    - format: 'csv' ou 'json' (défaut: 'json')
    - table: 'products', 'inventory', 'product_display', ou 'all' (défaut)
    """
    try:
        export_format = request.args.get('format', 'json').lower()
        table = request.args.get('table', 'all').lower()
        
        # Créer le répertoire d'export
        from pathlib import Path
        output_dir = Path("data/export_inventory")
        output_dir.mkdir(parents=True, exist_ok=True)
        
        results = {}
        
        if table in ('all', 'products'):
            count = export_products(output_dir)
            results['products'] = count
        
        if table in ('all', 'inventory'):
            count = export_inventory(output_dir)
            results['inventory'] = count
        
        if table in ('all', 'product_display'):
            count = export_product_display(output_dir)
            results['product_display'] = count
        
        # Retourner les fichiers ou un lien
        if export_format == 'json':
            # Retourner les données JSON directement
            data = {}
            for table_name in results.keys():
                json_path = output_dir / f'{table_name}.json'
                if json_path.exists():
                    import json
                    with open(json_path, 'r', encoding='utf-8') as f:
                        data[table_name] = json.load(f)
            
            return jsonify({
                'success': True,
                'data': data,
                'summary': results
            }), 200
        else:
            # Retourner les fichiers CSV (ou un lien de téléchargement)
            # Pour l'instant, on retourne juste les chemins
            files = {}
            for table_name in results.keys():
                csv_path = output_dir / f'{table_name}.csv'
                if csv_path.exists():
                    files[table_name] = str(csv_path.relative_to(Path.cwd()))
            
            return jsonify({
                'success': True,
                'files': files,
                'summary': results,
                'message': 'Fichiers CSV créés. Utilisez /api/inventory/download/<table> pour télécharger.'
            }), 200
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@inventory_bp.route('/api/inventory/download/<table>', methods=['GET'])
@require_auth('admin')
def download_export(table):
    """
    Télécharge un fichier CSV exporté
    
    Args:
        table: 'products', 'inventory', ou 'product_display'
    """
    try:
        from pathlib import Path
        output_dir = Path("data/export_inventory")
        csv_path = output_dir / f'{table}.csv'
        
        if not csv_path.exists():
            return jsonify({
                'success': False,
                'error': f'Fichier {table}.csv non trouvé. Exécutez d\'abord /api/inventory/export'
            }), 404
        
        return send_file(
            str(csv_path),
            mimetype='text/csv',
            as_attachment=True,
            download_name=f'{table}.csv'
        )
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@inventory_bp.route('/api/inventory/health', methods=['GET'])
def health_check():
    """Vérification de santé de l'API inventaire"""
    try:
        from scripts.inventory_checker import get_db_connection
        conn = get_db_connection()
        conn.close()
        return jsonify({
            'success': True,
            'status': 'healthy',
            'message': 'Connexion à la base de données OK'
        }), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'status': 'unhealthy',
            'error': str(e)
        }), 500

