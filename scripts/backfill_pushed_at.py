#!/usr/bin/env python3
"""
Backfill ponctuel — remplir `pushed_at` sur les fiches piano_service_records
qui n'en ont pas, pour qu'elles apparaissent en vert dans les vues VDI
pendant 7 jours après leur completion/validation.

Cible : fiches où
  - pushed_at IS NULL
  - status IN ('completed', 'validated')
  - COALESCE(validated_at, completed_at) >= now - 7 jours

Action : pushed_at = COALESCE(validated_at, completed_at). Le statut n'est
PAS modifié — on remplit seulement le timestamp pour que le visuel suive.

Usage:
    python3 scripts/backfill_pushed_at.py            # dry-run (par défaut)
    python3 scripts/backfill_pushed_at.py --write    # applique les changements
    python3 scripts/backfill_pushed_at.py --days 14  # fenêtre personnalisée
"""

import argparse
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / '.env')

import supabase


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--write', action='store_true',
                        help="Applique les changements. Sans ce flag, dry-run.")
    parser.add_argument('--days', type=int, default=7,
                        help="Fenêtre en jours (défaut: 7).")
    args = parser.parse_args()

    sb = supabase.create_client(
        os.getenv("SUPABASE_URL"),
        os.getenv("SUPABASE_SERVICE_ROLE_KEY"),
    )

    cutoff = (datetime.now(timezone.utc) - timedelta(days=args.days)).isoformat()
    print(f"Cutoff : {cutoff} (il y a {args.days} jours)")

    resp = (
        sb.table("piano_service_records")
        .select("id,piano_id,institution_slug,status,completed_at,validated_at,pushed_at")
        .is_("pushed_at", "null")
        .in_("status", ["completed", "validated"])
        .execute()
    )
    rows = resp.data or []

    candidates = []
    for r in rows:
        ref = r.get("validated_at") or r.get("completed_at")
        if not ref:
            continue
        if ref < cutoff:
            continue
        candidates.append((r, ref))

    print(f"\n{len(rows)} fiches sans pushed_at, dont {len(candidates)} dans la fenêtre {args.days} j.\n")

    if not candidates:
        print("Rien à faire.")
        return

    print(f"{'ID':<38} {'institution':<16} {'status':<11} {'pushed_at ←'}")
    print("-" * 90)
    for r, ref in candidates:
        print(f"{r['id']:<38} {r.get('institution_slug', ''):<16} {r['status']:<11} {ref}")

    if not args.write:
        print(f"\nDry-run. Pas d'écriture. Relancer avec --write pour appliquer ({len(candidates)} fiches).")
        return

    print(f"\nApplication de {len(candidates)} mises à jour...")
    updated = 0
    failed = 0
    for r, ref in candidates:
        try:
            sb.table("piano_service_records").update({
                "pushed_at": ref,
            }).eq("id", r["id"]).execute()
            updated += 1
        except Exception as e:
            failed += 1
            print(f"  ✗ {r['id']} : {e}")

    print(f"\n✅ {updated} fiches mises à jour. {failed} erreurs.")


if __name__ == "__main__":
    main()
