#!/usr/bin/env python3
"""
Explorer la structure de la mutation updatePiano.

Date: 2026-01-01
"""

import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.gazelle_api_client import GazelleAPIClient


def explore_updatePiano():
    """Explore la mutation updatePiano."""
    client = GazelleAPIClient()

    print(f"\n{'='*70}")
    print(f"🔍 EXPLORATION: Mutation updatePiano")
    print(f"{'='*70}\n")

    # Introspection query pour updatePiano
    query = """
    query {
        __type(name: "Mutation") {
            fields(includeDeprecated: false) {
                name
                args {
                    name
                    type {
                        name
                        kind
                        ofType {
                            name
                            kind
                        }
                    }
                }
                type {
                    name
                    kind
                }
            }
        }
    }
    """

    try:
        result = client._execute_query(query)
        mutation_type = result.get("data", {}).get("__type", {})
        fields = mutation_type.get("fields", [])

        # Trouver updatePiano
        update_piano = None
        for field in fields:
            if field.get("name") == "updatePiano":
                update_piano = field
                break

        if not update_piano:
            print("❌ Mutation updatePiano non trouvée")
            return

        print("✅ Mutation updatePiano trouvée\n")
        print(f"{'='*70}")
        print("ARGUMENTS")
        print(f"{'='*70}\n")

        args = update_piano.get("args", [])
        for arg in args:
            arg_name = arg.get("name")
            arg_type = arg.get("type", {})
            type_name = arg_type.get("name") or arg_type.get("ofType", {}).get("name")
            print(f"  • {arg_name}: {type_name}")

        print(f"\n{'='*70}")
        print("TYPE DE RETOUR")
        print(f"{'='*70}\n")

        return_type = update_piano.get("type", {})
        return_type_name = return_type.get("name")
        print(f"  {return_type_name}")

        # Explorer le type de retour UpdatePianoPayload
        print(f"\n{'='*70}")
        print(f"STRUCTURE DE {return_type_name}")
        print(f"{'='*70}\n")

        payload_query = f"""
        query {{
            __type(name: "{return_type_name}") {{
                fields {{
                    name
                    type {{
                        name
                        kind
                        ofType {{
                            name
                        }}
                    }}
                }}
            }}
        }}
        """

        payload_result = client._execute_query(payload_query)
        payload_type = payload_result.get("data", {}).get("__type", {})
        payload_fields = payload_type.get("fields", [])

        for field in payload_fields:
            field_name = field.get("name")
            field_type = field.get("type", {})
            type_name = field_type.get("name") or field_type.get("ofType", {}).get("name")
            print(f"  • {field_name}: {type_name}")

        # Explorer PrivatePianoInput
        print(f"\n{'='*70}")
        print(f"STRUCTURE DE PrivatePianoInput")
        print(f"{'='*70}\n")

        input_query = """
        query {
            __type(name: "PrivatePianoInput") {
                inputFields {
                    name
                    type {
                        name
                        kind
                        ofType {
                            name
                        }
                    }
                }
            }
        }
        """

        input_result = client._execute_query(input_query)
        input_type = input_result.get("data", {}).get("__type", {})
        input_fields = input_type.get("inputFields", [])

        # Chercher manualLastService
        manual_last_service_found = False
        for field in input_fields:
            field_name = field.get("name")
            if "last" in field_name.lower() or "service" in field_name.lower():
                field_type = field.get("type", {})
                type_name = field_type.get("name") or field_type.get("ofType", {}).get("name")
                marker = "⭐" if "manual" in field_name.lower() else " "
                print(f"  {marker} {field_name}: {type_name}")

                if "manual" in field_name.lower():
                    manual_last_service_found = True

        if not manual_last_service_found:
            print("\n❌ manualLastService non trouvé dans PrivatePianoInput")

        print()

    except Exception as e:
        print(f"\n❌ Erreur: {e}")
        import traceback
        traceback.print_exc()


def main():
    explore_updatePiano()


if __name__ == '__main__':
    main()
