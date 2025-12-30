#!/usr/bin/env python3
"""
Script d'introspection complète du schéma GraphQL Gazelle.

Ce script interroge l'API Gazelle pour extraire:
- Tous les types disponibles
- Tous les champs de chaque type
- Tous les arguments possibles
- La documentation inline

Résultat sauvegardé dans: GAZELLE_SCHEMA_REFERENCE.md
"""

import sys
import os
from datetime import datetime

# Ajouter le répertoire parent au PYTHONPATH
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.gazelle_api_client import GazelleAPIClient


def introspect_schema():
    """Introspection complète du schéma GraphQL."""

    client = GazelleAPIClient()

    # Requête d'introspection GraphQL standard
    introspection_query = """
    query IntrospectionQuery {
      __schema {
        queryType { name }
        mutationType { name }
        subscriptionType { name }
        types {
          ...FullType
        }
        directives {
          name
          description
          locations
          args {
            ...InputValue
          }
        }
      }
    }

    fragment FullType on __Type {
      kind
      name
      description
      fields(includeDeprecated: true) {
        name
        description
        args {
          ...InputValue
        }
        type {
          ...TypeRef
        }
        isDeprecated
        deprecationReason
      }
      inputFields {
        ...InputValue
      }
      interfaces {
        ...TypeRef
      }
      enumValues(includeDeprecated: true) {
        name
        description
        isDeprecated
        deprecationReason
      }
      possibleTypes {
        ...TypeRef
      }
    }

    fragment InputValue on __InputValue {
      name
      description
      type { ...TypeRef }
      defaultValue
    }

    fragment TypeRef on __Type {
      kind
      name
      ofType {
        kind
        name
        ofType {
          kind
          name
          ofType {
            kind
            name
            ofType {
              kind
              name
              ofType {
                kind
                name
                ofType {
                  kind
                  name
                  ofType {
                    kind
                    name
                  }
                }
              }
            }
          }
        }
      }
    }
    """

    print("🔍 Introspection du schéma GraphQL Gazelle...")
    print("=" * 80)

    try:
        result = client._execute_query(introspection_query)
        schema = result.get("data", {}).get("__schema", {})

        if not schema:
            print("❌ Erreur: Schéma vide retourné")
            return None

        print(f"✅ Schéma récupéré avec succès!")
        print(f"   Types: {len(schema.get('types', []))}")
        print(f"   Directives: {len(schema.get('directives', []))}")

        return schema

    except Exception as e:
        print(f"❌ Erreur lors de l'introspection: {e}")
        import traceback
        traceback.print_exc()
        return None


def format_type_ref(type_ref):
    """Formate une référence de type GraphQL de manière lisible."""
    if not type_ref:
        return "Unknown"

    kind = type_ref.get("kind")
    name = type_ref.get("name")
    of_type = type_ref.get("ofType")

    if kind == "NON_NULL":
        return f"{format_type_ref(of_type)}!"
    elif kind == "LIST":
        return f"[{format_type_ref(of_type)}]"
    else:
        return name or "Unknown"


def generate_markdown_documentation(schema):
    """Génère la documentation Markdown du schéma."""

    lines = []

    # Header
    lines.append("# Schéma GraphQL Gazelle - Documentation Complète")
    lines.append("")
    lines.append(f"**Date de génération:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("")
    lines.append("---")
    lines.append("")

    # Table des matières
    lines.append("## Table des Matières")
    lines.append("")
    lines.append("1. [Vue d'ensemble](#vue-densemble)")
    lines.append("2. [Types Query](#types-query)")
    lines.append("3. [Types Mutation](#types-mutation)")
    lines.append("4. [Types Objets](#types-objets)")
    lines.append("5. [Types Input](#types-input)")
    lines.append("6. [Types Enum](#types-enum)")
    lines.append("")
    lines.append("---")
    lines.append("")

    # Vue d'ensemble
    lines.append("## Vue d'ensemble")
    lines.append("")
    query_type = schema.get("queryType", {}).get("name", "N/A")
    mutation_type = schema.get("mutationType", {}).get("name", "N/A")
    lines.append(f"- **Query Type:** `{query_type}`")
    lines.append(f"- **Mutation Type:** `{mutation_type}`")
    lines.append(f"- **Total Types:** {len(schema.get('types', []))}")
    lines.append("")
    lines.append("---")
    lines.append("")

    types_list = schema.get("types", [])

    # Séparer les types par catégorie
    query_types = []
    mutation_types = []
    object_types = []
    input_types = []
    enum_types = []

    for t in types_list:
        name = t.get("name", "")
        kind = t.get("kind", "")

        # Ignorer les types internes GraphQL
        if name.startswith("__"):
            continue

        if name == query_type:
            query_types.append(t)
        elif name == mutation_type:
            mutation_types.append(t)
        elif kind == "OBJECT":
            object_types.append(t)
        elif kind == "INPUT_OBJECT":
            input_types.append(t)
        elif kind == "ENUM":
            enum_types.append(t)

    # Types Query
    lines.append("## Types Query")
    lines.append("")
    if query_types:
        for t in query_types:
            lines.extend(format_type_details(t))
    else:
        lines.append("*Aucun type Query trouvé.*")
        lines.append("")

    # Types Mutation
    lines.append("## Types Mutation")
    lines.append("")
    if mutation_types:
        for t in mutation_types:
            lines.extend(format_type_details(t))
    else:
        lines.append("*Aucun type Mutation trouvé.*")
        lines.append("")

    # Types Objets
    lines.append("## Types Objets")
    lines.append("")
    lines.append(f"*{len(object_types)} types objets disponibles*")
    lines.append("")

    # Chercher spécifiquement les types importants
    important_types = ["PrivatePiano", "PrivateClient", "PrivateContact", "PrivateLocation", "PrivateAppointment"]

    for type_name in important_types:
        t = next((t for t in object_types if t.get("name") == type_name), None)
        if t:
            lines.extend(format_type_details(t))

    # Tous les autres types objets
    lines.append("### Autres Types Objets")
    lines.append("")
    for t in sorted(object_types, key=lambda x: x.get("name", "")):
        if t.get("name") not in important_types:
            lines.extend(format_type_details(t))

    # Types Input
    lines.append("## Types Input")
    lines.append("")
    for t in sorted(input_types, key=lambda x: x.get("name", "")):
        lines.extend(format_input_type_details(t))

    # Types Enum
    lines.append("## Types Enum")
    lines.append("")
    for t in sorted(enum_types, key=lambda x: x.get("name", "")):
        lines.extend(format_enum_type_details(t))

    return "\n".join(lines)


def format_type_details(type_obj):
    """Formate les détails d'un type objet."""
    lines = []

    name = type_obj.get("name", "Unknown")
    description = type_obj.get("description", "")
    fields = type_obj.get("fields", [])

    lines.append(f"### {name}")
    lines.append("")

    if description:
        lines.append(f"**Description:** {description}")
        lines.append("")

    if fields:
        lines.append("**Champs:**")
        lines.append("")
        lines.append("| Nom | Type | Arguments | Description |")
        lines.append("|-----|------|-----------|-------------|")

        for field in fields:
            field_name = field.get("name", "")
            field_type = format_type_ref(field.get("type"))
            field_desc = (field.get("description") or "").replace("\n", " ") or "-"
            args = field.get("args", [])

            if args:
                args_str = ", ".join([f"{a['name']}: {format_type_ref(a['type'])}" for a in args])
            else:
                args_str = "-"

            lines.append(f"| `{field_name}` | `{field_type}` | {args_str} | {field_desc} |")

        lines.append("")
    else:
        lines.append("*Aucun champ.*")
        lines.append("")

    lines.append("---")
    lines.append("")

    return lines


def format_input_type_details(type_obj):
    """Formate les détails d'un type Input."""
    lines = []

    name = type_obj.get("name", "Unknown")
    description = type_obj.get("description", "")
    input_fields = type_obj.get("inputFields", [])

    lines.append(f"### {name}")
    lines.append("")

    if description:
        lines.append(f"**Description:** {description}")
        lines.append("")

    if input_fields:
        lines.append("**Champs:**")
        lines.append("")
        lines.append("| Nom | Type | Défaut | Description |")
        lines.append("|-----|------|--------|-------------|")

        for field in input_fields:
            field_name = field.get("name", "")
            field_type = format_type_ref(field.get("type"))
            default_val = field.get("defaultValue", "-")
            field_desc = (field.get("description") or "").replace("\n", " ") or "-"

            lines.append(f"| `{field_name}` | `{field_type}` | {default_val} | {field_desc} |")

        lines.append("")

    lines.append("---")
    lines.append("")

    return lines


def format_enum_type_details(type_obj):
    """Formate les détails d'un type Enum."""
    lines = []

    name = type_obj.get("name", "Unknown")
    description = type_obj.get("description", "")
    enum_values = type_obj.get("enumValues", [])

    lines.append(f"### {name}")
    lines.append("")

    if description:
        lines.append(f"**Description:** {description}")
        lines.append("")

    if enum_values:
        lines.append("**Valeurs:**")
        lines.append("")
        for val in enum_values:
            val_name = val.get("name", "")
            val_desc = val.get("description", "")
            if val_desc:
                lines.append(f"- `{val_name}`: {val_desc}")
            else:
                lines.append(f"- `{val_name}`")

        lines.append("")

    lines.append("---")
    lines.append("")

    return lines


def main():
    """Point d'entrée principal."""

    # Introspection
    schema = introspect_schema()

    if not schema:
        print("\n❌ Impossible de générer la documentation sans schéma.")
        return 1

    # Génération de la documentation
    print("\n📝 Génération de la documentation Markdown...")
    markdown = generate_markdown_documentation(schema)

    # Sauvegarde
    output_file = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "GAZELLE_SCHEMA_REFERENCE.md"
    )

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(markdown)

    print(f"✅ Documentation sauvegardée dans: {output_file}")
    print(f"   Taille: {len(markdown)} caractères")

    return 0


if __name__ == "__main__":
    sys.exit(main())
