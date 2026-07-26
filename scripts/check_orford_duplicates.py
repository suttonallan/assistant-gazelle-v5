#!/usr/bin/env python3
"""
Détection de doublons dans les fiches de service Orford (piano_service_records).

Lecture seule — n'écrit rien. Signale trois types de doublons :

  1. Fiches actives multiples pour un même piano
     (invariant "une seule fiche active par piano" violé — status draft/completed/validated).
  2. Même piano poussé plusieurs fois le même jour (America/Montreal)
     — vrais doublons masqués par la déduplication de l'historique (service_records.py:662).
  3. Même piano présent dans plusieurs fiches validées en attente de push
     (doublons imminents au prochain push groupé).

Usage :
    python3 scripts/check_orford_duplicates.py
    python3 scripts/check_orford_duplicates.py --institution orford --days 120
"""

import argparse
import os
import sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

try:
    from dotenv import load_dotenv
    load_dotenv(PROJECT_ROOT / '.env')
except ImportError:
    pass  # python-dotenv absent : on lira les variables d'environnement directement

import supabase

try:
    from core.timezone_utils import MONTREAL_TZ
except Exception:  # fallback si l'import échoue
    try:
        from zoneinfo import ZoneInfo
        MONTREAL_TZ = ZoneInfo("America/Montreal")
    except Exception:
        MONTREAL_TZ = timezone.utc

TABLE = "piano_service_records"
ACTIVE_STATUSES = ["draft", "completed", "validated"]


def _montreal_day(iso_str):
    """Convertit un ISO-8601 (UTC de Gazelle) en date YYYY-MM-DD America/Montreal."""
    if not iso_str:
        return None
    try:
        s = iso_str.replace("Z", "+00:00")
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(MONTREAL_TZ).strftime("%Y-%m-%d")
    except Exception:
        return iso_str[:10]  # dégradé : tronque brutalement


def _short(txt, n=60):
    txt = (txt or "").strip().replace("\n", " ")
    return (txt[:n] + "…") if len(txt) > n else txt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--institution", default="orford",
                        help="Slug institution (défaut: orford).")
    parser.add_argument("--days", type=int, default=120,
                        help="Fenêtre pour les fiches poussées, en jours (défaut: 120).")
    args = parser.parse_args()

    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY")
    if not url or not key:
        print("❌ SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY manquants dans .env")
        sys.exit(1)

    sb = supabase.create_client(url, key)
    inst = args.institution
    print(f"🔎 Analyse des doublons pour « {inst} »\n")

    # ------------------------------------------------------------------
    # 1. Fiches actives multiples par piano (invariant "une seule active")
    # ------------------------------------------------------------------
    active = (
        sb.table(TABLE)
        .select("id,piano_id,status,travail,updated_at,technician_email")
        .eq("institution_slug", inst)
        .in_("status", ACTIVE_STATUSES)
        .order("updated_at", desc=True)
        .execute()
    ).data or []

    by_piano_active = defaultdict(list)
    for r in active:
        by_piano_active[r["piano_id"]].append(r)

    dup_active = {pid: recs for pid, recs in by_piano_active.items() if len(recs) > 1}

    print("=" * 70)
    print("1) FICHES ACTIVES MULTIPLES PAR PIANO (invariant violé)")
    print("=" * 70)
    if not dup_active:
        print("✅ Aucun piano avec plus d'une fiche active.\n")
    else:
        print(f"⚠️  {len(dup_active)} piano(s) avec plusieurs fiches actives :\n")
        for pid, recs in dup_active.items():
            print(f"  🎹 {pid} — {len(recs)} fiches :")
            for r in recs:
                print(f"      · {r['id']}  [{r['status']:<9}]  maj={_montreal_day(r.get('updated_at'))}"
                      f"  « {_short(r.get('travail'))} »")
            print()

    # ------------------------------------------------------------------
    # 2. Même piano poussé plusieurs fois le même jour (Montréal)
    # ------------------------------------------------------------------
    cutoff = (datetime.now(timezone.utc) - timedelta(days=args.days)).isoformat()
    pushed = (
        sb.table(TABLE)
        .select("id,piano_id,status,travail,pushed_at,completed_at,gazelle_event_id")
        .eq("institution_slug", inst)
        .eq("status", "pushed")
        .gte("pushed_at", cutoff)
        .order("pushed_at", desc=True)
        .execute()
    ).data or []

    by_piano_day = defaultdict(list)
    for r in pushed:
        day = _montreal_day(r.get("pushed_at") or r.get("completed_at"))
        by_piano_day[(r["piano_id"], day)].append(r)

    dup_day = {k: recs for k, recs in by_piano_day.items() if len(recs) > 1}

    print("=" * 70)
    print(f"2) MÊME PIANO POUSSÉ PLUSIEURS FOIS LE MÊME JOUR (fenêtre {args.days}j)")
    print("=" * 70)
    if not dup_day:
        print("✅ Aucun doublon piano+jour dans les fiches poussées.\n")
    else:
        print(f"⚠️  {len(dup_day)} couple(s) piano/jour en double :\n")
        for (pid, day), recs in sorted(dup_day.items(), key=lambda x: x[0][1] or "", reverse=True):
            events = {r.get("gazelle_event_id") for r in recs}
            same_event = " (même événement Gazelle)" if len(events) == 1 else " (événements DIFFÉRENTS)"
            print(f"  🎹 {pid} — {day} — {len(recs)} fiches{same_event} :")
            for r in recs:
                print(f"      · {r['id']}  event={r.get('gazelle_event_id')}"
                      f"  « {_short(r.get('travail'))} »")
            print()

    # ------------------------------------------------------------------
    # 3. Même piano dans plusieurs fiches VALIDÉES (doublons imminents)
    # ------------------------------------------------------------------
    validated = [r for r in active if r["status"] == "validated"]
    by_piano_val = defaultdict(list)
    for r in validated:
        by_piano_val[r["piano_id"]].append(r)
    dup_val = {pid: recs for pid, recs in by_piano_val.items() if len(recs) > 1}

    print("=" * 70)
    print("3) MÊME PIANO DANS PLUSIEURS FICHES VALIDÉES (doublons au prochain push)")
    print("=" * 70)
    if not dup_val:
        print("✅ Aucun piano validé en double.\n")
    else:
        print(f"⚠️  {len(dup_val)} piano(s) validé(s) en double :\n")
        for pid, recs in dup_val.items():
            print(f"  🎹 {pid} — {len(recs)} fiches validées :")
            for r in recs:
                print(f"      · {r['id']}  « {_short(r.get('travail'))} »")
            print()

    # ------------------------------------------------------------------
    # Résumé
    # ------------------------------------------------------------------
    print("=" * 70)
    print("RÉSUMÉ")
    print("=" * 70)
    print(f"  Fiches actives lues            : {len(active)}")
    print(f"  Fiches poussées lues ({args.days}j)   : {len(pushed)}")
    print(f"  ⚠️  Pianos à fiches actives multiples : {len(dup_active)}")
    print(f"  ⚠️  Couples piano/jour poussés en double : {len(dup_day)}")
    print(f"  ⚠️  Pianos validés en double           : {len(dup_val)}")
    total = len(dup_active) + len(dup_day) + len(dup_val)
    print(f"\n{'✅ Aucun doublon détecté.' if total == 0 else f'⚠️  {total} anomalie(s) de doublon à examiner.'}")


if __name__ == "__main__":
    main()
