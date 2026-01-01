#!/usr/bin/env python3
"""
Script pour mapper les IDs Supabase (usr_xxx) vers les noms de techniciens.
Met à jour inventaire_techniciens avec les vrais noms.
"""

import sys
import os
from pathlib import Path
from dotenv import load_dotenv

# Charger .env
env_path = Path(__file__).parent.parent / '.env'
if env_path.exists():
    load_dotenv(env_path)

# Changer vers le répertoire du projet
script_dir = os.path.dirname(os.path.abspath(__file__))
project_dir = os.path.dirname(script_dir)
os.chdir(project_dir)

sys.path.insert(0, project_dir)

from core.supabase_storage import SupabaseStorage
from core.reference_manager import get_reference_manager
import requests

# Forcer le flush immédiat
sys.stdout.reconfigure(line_buffering=True) if hasattr(sys.stdout, 'reconfigure') else None

# Charger le mapping depuis la référence
ref_manager = get_reference_manager()
ref_manager.ensure_reference_consulted("mapping_techniciens")

# Récupérer le mapping depuis la référence
MAPPING_TECHNICIENS = {
    "usr_ofYggsCDt2JAVeNP": ref_manager.get_technicien_name("usr_ofYggsCDt2JAVeNP") or "Allan",
    "usr_HcCiFk7o0vZ9xAI0": ref_manager.get_technicien_name("usr_HcCiFk7o0vZ9xAI0") or "Nicolas",
    "usr_ReUSmIJmBF86ilY1": ref_manager.get_technicien_name("usr_ReUSmIJmBF86ilY1") or "Jean-Philippe",
}

print("🔄 Mapping des techniciens (correction inversion)...", flush=True)
print()

def mapper_techniciens():
    """Met à jour les noms de techniciens dans inventaire_techniciens."""
    try:
        storage = SupabaseStorage()
        
        # Récupérer tous les enregistrements
        tous = storage.get_data("inventaire_techniciens", filters={})
        
        print(f"📊 Total d'enregistrements: {len(tous)}", flush=True)
        
        if not tous:
            print("✅ Aucune donnée à mapper", flush=True)
            return
        
        # Grouper par technicien_id
        techniciens_uniques = set(item.get("technicien") for item in tous)
        print(f"📋 Techniciens uniques trouvés: {len(techniciens_uniques)}", flush=True)
        for tech_id in techniciens_uniques:
            print(f"   - {tech_id}", flush=True)
        
        print()
        print("🔄 Mise à jour en cours...", flush=True)
        
        mis_a_jour = 0
        non_mappes = 0
        
        for item in tous:
            technicien_id = item.get("technicien")
            technicien_nom = MAPPING_TECHNICIENS.get(technicien_id)
            
            if not technicien_nom:
                non_mappes += 1
                print(f"  ⚠️  ID non mappé: {technicien_id}", flush=True)
                continue
            
            # Mettre à jour avec le nom
            item_id = item.get("id")
            url = f"{storage.api_url}/inventaire_techniciens?id=eq.{item_id}"
            headers = storage._get_headers()
            
            data_update = {
                "technicien": technicien_nom
            }
            
            response = requests.patch(url, headers=headers, json=data_update)
            
            if response.status_code in [200, 204]:
                mis_a_jour += 1
                if mis_a_jour % 10 == 0:
                    print(f"  ✅ {mis_a_jour} mis à jour...", flush=True)
            else:
                try:
                    error = response.json().get('message', response.text)
                    print(f"  ❌ Erreur pour {item.get('code_produit')}: {error}", flush=True)
                except:
                    print(f"  ❌ Erreur {response.status_code}: {response.text}", flush=True)
        
        print()
        print("📊 Résultat:", flush=True)
        print(f"   ✅ Mis à jour: {mis_a_jour}", flush=True)
        print(f"   ⚠️  Non mappés: {non_mappes}", flush=True)
        
        # Mettre à jour la référence après succès
        if mis_a_jour > 0:
            ref_manager.update_after_success("technicien_mapping", MAPPING_TECHNICIENS)
            print("✅ Référence mise à jour automatiquement", flush=True)
        
        if non_mappes > 0:
            print()
            print("💡 Pour mapper les IDs restants, ajoutez-les dans docs/REFERENCE_COMPLETE.md", flush=True)
        
    except Exception as e:
        print(f"\n❌ Erreur fatale: {e}", flush=True)
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    mapper_techniciens()


