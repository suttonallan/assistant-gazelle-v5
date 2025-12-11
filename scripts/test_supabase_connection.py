#!/usr/bin/env python3
"""
Script de test pour vérifier la connexion Supabase.

À exécuter sur Cursor PC pour vérifier que les credentials sont bien configurés.
"""

import os
import sys
from pathlib import Path

# Ajouter le répertoire parent au path
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    print("⚠️  python-dotenv non installé, utilisation des variables d'environnement système")
    print("   Installez avec: pip install python-dotenv")

try:
    from core.supabase_storage import SupabaseStorage
except ImportError as e:
    print(f"❌ Erreur d'import: {e}")
    print("   Vérifiez que vous êtes dans le bon répertoire")
    sys.exit(1)


def test_credentials():
    """Teste que les credentials sont présents."""
    print("=" * 60)
    print("Test de Connexion Supabase")
    print("=" * 60)
    
    # Vérifier les variables d'environnement
    print("\n1️⃣  Vérification des variables d'environnement...")
    supabase_url = os.environ.get('SUPABASE_URL')
    supabase_key = os.environ.get('SUPABASE_KEY')
    
    if not supabase_url:
        print("   ❌ SUPABASE_URL manquant")
        print("   → Ajoutez SUPABASE_URL dans .env ou variables d'environnement")
        return False
    else:
        print(f"   ✅ SUPABASE_URL: {supabase_url[:30]}...")
    
    if not supabase_key:
        print("   ❌ SUPABASE_KEY manquant")
        print("   → Ajoutez SUPABASE_KEY dans .env ou variables d'environnement")
        return False
    else:
        print(f"   ✅ SUPABASE_KEY: {supabase_key[:30]}...")
    
    # Tester la connexion
    print("\n2️⃣  Test de connexion à Supabase...")
    try:
        storage = SupabaseStorage()
        print("   ✅ Connexion Supabase réussie!")
        
        # Tester une requête simple
        print("\n3️⃣  Test de requête (lecture produits_catalogue)...")
        produits = storage.get_data("produits_catalogue", limit=1)
        print(f"   ✅ Requête réussie! ({len(produits) if produits else 0} produit(s) trouvé(s))")
        
        print("\n" + "=" * 60)
        print("✅ Tous les tests réussis!")
        print("=" * 60)
        print("\n🎯 Vous pouvez maintenant exécuter:")
        print("   python scripts/import_gazelle_product_display.py --dry-run")
        
        return True
        
    except ValueError as e:
        print(f"   ❌ Erreur de configuration: {e}")
        return False
    except Exception as e:
        print(f"   ❌ Erreur de connexion: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_credentials()
    sys.exit(0 if success else 1)
