#!/usr/bin/env python3
"""
Compile les appels du Call Center Gazelle (relances client par téléphone)
dans un Google Sheet dédié, pour que Louise/l'équipe puisse le consulter
sans repasser par Gazelle.

Gazelle log un appel comme une timeline entry SYSTEM_MESSAGE titrée
"Le statut du client a été changé à inactive..." avec la note du technicien
en description. Ce module lit les nouvelles entrées depuis le dernier sync
et les ajoute au Sheet.
"""
import re
from datetime import datetime, timezone

from core.supabase_storage import SupabaseStorage

SHEET_ID = "1d6kCDmDWaPlvUFNZq8C7crTfShv_qPMWGBPsiHx4lc4"
TAB_NAME = "Appels"
LAST_SYNC_SETTING_KEY = "call_center_sheet_last_sync"

TECH_DISPLAY_NAMES = {
    "usr_ofYggsCDt2JAVeNP": "Allan",
    "usr_HcCiFk7o0vZ9xAI0": "Nicolas",
    "usr_ReUSmIJmBF86ilY1": "Jean-Philippe",
    "usr_bbt59aCUqUaDWA8n": "Margot",
    "usr_tndhXmnT0iakT4HF": "Louise",
}


def sync_call_center_to_sheet() -> dict:
    """Ajoute au Sheet les appels du Call Center loggés depuis le dernier sync.
    Appelé par le cron (voir core/scheduler.py)."""
    import sys
    sys.path.insert(0, r"C:\PTM")
    sys.path.insert(0, r"C:\PTM\tools")
    from tools.gsheet import client as gsheet_client, append_rows

    storage = SupabaseStorage(silent=True)

    since = storage.get_system_setting(LAST_SYNC_SETTING_KEY)
    if not since:
        # Premier sync : couvre les 90 derniers jours (pas tout l'historique).
        from datetime import timedelta
        since = (datetime.now(timezone.utc) - timedelta(days=90)).isoformat()

    # Deux types de resultat suivis. Deux requetes separees plutot qu'un .or_()
    # combine : PostgREST interprete mal les parentheses litterales ("(était...)")
    # a l'interieur d'un filtre or_(), ce qui faisait silencieusement disparaitre
    # la moitie des conditions (verifie en direct le 2026-09-23).
    #
    # - "Client désactivé" : transition VERS inactive faite par une vraie personne
    #   (user_id present) -- signature fiable d'un appel qui n'a pas abouti.
    deactivations = storage.client.table('gazelle_timeline_entries').select(
        'title,description,occurred_at,client_id,user_id'
    ).eq('entry_type', 'SYSTEM_MESSAGE').ilike(
        'title', '%statut du client a été%inactive (était%'
    ).not_.is_('user_id', 'null').gt('occurred_at', since).execute().data or []

    # - "RV créé" : un prospect devient "new" parce qu'un rendez-vous vient d'etre
    #   cree pour lui. Ce message est TOUJOURS automatique cote Gazelle (pas de
    #   user_id), donc on ne peut pas prouver que CE rendez-vous vient d'un appel
    #   du Call Center precisement -- ca peut aussi venir d'une prise de contact
    #   par un autre canal. Affiche quand meme (demande par Allan) avec le
    #   technicien marque "(automatique)" pour rester honnete sur cette limite.
    new_appointments = storage.client.table('gazelle_timeline_entries').select(
        'title,description,occurred_at,client_id,user_id'
    ).eq('entry_type', 'SYSTEM_MESSAGE').ilike(
        'title', '%statut du client a été changé à new (était prospect)%'
    ).gt('occurred_at', since).execute().data or []

    rows = sorted(deactivations + new_appointments, key=lambda r: r.get('occurred_at') or '')

    if not rows:
        return {"success": True, "added": 0, "message": "Aucun nouvel appel depuis le dernier sync"}

    client_ids = list({r['client_id'] for r in rows if r.get('client_id')})
    clients_map, contacts_map = {}, {}
    if client_ids:
        cr = storage.client.table('gazelle_clients').select(
            'external_id,company_name'
        ).in_('external_id', client_ids).execute().data or []
        clients_map = {c['external_id']: c.get('company_name') for c in cr if c.get('company_name')}

        ctr = storage.client.table('gazelle_contacts').select(
            'client_external_id,first_name,last_name'
        ).in_('client_external_id', client_ids).eq('is_default', True).execute().data or []
        contacts_map = {
            c['client_external_id']: f"{c.get('first_name', '')} {c.get('last_name', '')}".strip()
            for c in ctr
        }

    sheet_rows = []
    latest_occurred_at = since
    for r in rows:
        occurred = r.get('occurred_at') or ''
        date_str, time_str = (occurred[:10], occurred[11:16]) if len(occurred) >= 16 else (occurred[:10], '')
        title = r.get('title') or ''
        is_deactivation = 'inactive (était' in title
        result_type = 'Client désactivé' if is_deactivation else 'RV créé'
        uid = r.get('user_id')
        tech = TECH_DISPLAY_NAMES.get(uid, uid) if uid else '(automatique)'
        cid = r.get('client_id')
        client_name = clients_map.get(cid) or contacts_map.get(cid) or '(client inconnu)'
        outcome = r.get('description') or ''
        sheet_rows.append([date_str, time_str, tech, client_name, result_type, outcome])
        if occurred > latest_occurred_at:
            latest_occurred_at = occurred

    svc = gsheet_client()
    append_rows(svc, SHEET_ID, f"{TAB_NAME}!A:F", sheet_rows)

    storage.save_system_setting(LAST_SYNC_SETTING_KEY, latest_occurred_at)

    return {"success": True, "added": len(sheet_rows), "up_to": latest_occurred_at}


if __name__ == "__main__":
    import json
    print(json.dumps(sync_call_center_to_sheet(), indent=2, ensure_ascii=False))
