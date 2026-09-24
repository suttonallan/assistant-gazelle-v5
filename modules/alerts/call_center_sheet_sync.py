#!/usr/bin/env python3
"""
Compile les appels du Call Center Gazelle (relances client par téléphone)
dans un Google Sheet dédié, pour que Louise/l'équipe puisse le consulter
sans repasser par Gazelle.

Gazelle log un appel comme une timeline entry SYSTEM_MESSAGE titrée
"Le statut du client a été changé à inactive..." avec la note du technicien
en description. Ce module lit les nouvelles entrées depuis le dernier sync
et les ajoute au Sheet.

Deux types de résultat :
- "Client désactivé" : signal direct et prouvable (un humain a désactivé le
  client, avec une note "Autre -- ...").
- "RV créé (pendant l'appel)" : le client a accepté un rendez-vous plutôt que
  d'être désactivé. Gazelle n'attache aucune preuve directe reliant un
  "Rendez-vous créé" à un appel précis (un "RV créé" isolé a été essayé et
  retiré le 2026-09-23 pour cette raison -- un cas réel testé était une
  réservation en ligne du client, sans rapport avec un appel). La méthode
  retenue : ne compter un "RV créé" que s'il tombe dans une FENÊTRE DE SESSION
  du même technicien -- un intervalle de temps ancré par au moins une vraie
  désactivation ce jour-là, avec un écart max de 15 min entre deux actions
  consécutives pour rester dans la même session. Un "RV créé" isolé, loin de
  tout appel logué, n'est jamais inclus.
"""
from datetime import datetime, timedelta, timezone

from core.supabase_storage import SupabaseStorage

SHEET_ID = "1d6kCDmDWaPlvUFNZq8C7crTfShv_qPMWGBPsiHx4lc4"
TAB_NAME = "Appels"
LAST_SYNC_SETTING_KEY = "call_center_sheet_last_sync"

# Ecart max entre deux actions consecutives pour rester dans la meme session
# d'appels, et marge ajoutee de part et d'autre de la fenetre resultante.
SESSION_GAP = timedelta(minutes=15)
SESSION_BUFFER = timedelta(minutes=5)

TECH_DISPLAY_NAMES = {
    "usr_ofYggsCDt2JAVeNP": "Allan",
    "usr_HcCiFk7o0vZ9xAI0": "Nicolas",
    "usr_ReUSmIJmBF86ilY1": "Jean-Philippe",
    "usr_bbt59aCUqUaDWA8n": "Margot",
    "usr_tndhXmnT0iakT4HF": "Louise",
}


def _parse(occurred_at: str) -> datetime:
    return datetime.fromisoformat(occurred_at.replace('Z', '+00:00'))


def _build_session_windows(deactivations: list) -> dict:
    """Regroupe les désactivations par technicien en fenêtres de session
    (clusters d'actions rapprochées dans le temps), avec une marge de part
    et d'autre. Retourne {user_id: [(start, end), ...]}."""
    by_tech = {}
    for r in deactivations:
        uid = r.get('user_id')
        if not uid:
            continue
        by_tech.setdefault(uid, []).append(_parse(r['occurred_at']))

    windows = {}
    for uid, times in by_tech.items():
        times.sort()
        sessions = []
        session_start = session_end = times[0]
        for t in times[1:]:
            if t - session_end <= SESSION_GAP:
                session_end = t
            else:
                sessions.append((session_start, session_end))
                session_start = session_end = t
        sessions.append((session_start, session_end))
        windows[uid] = [(s - SESSION_BUFFER, e + SESSION_BUFFER) for s, e in sessions]
    return windows


def _falls_in_session(uid: str, when: datetime, windows: dict) -> bool:
    for start, end in windows.get(uid, []):
        if start <= when <= end:
            return True
    return False


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
        since = (datetime.now(timezone.utc) - timedelta(days=90)).isoformat()

    deactivations = storage.client.table('gazelle_timeline_entries').select(
        'title,description,occurred_at,client_id,user_id'
    ).eq('entry_type', 'SYSTEM_MESSAGE').ilike(
        'title', '%statut du client a été%inactive (était%'
    ).not_.is_('user_id', 'null').gt('occurred_at', since).execute().data or []

    appointments_created = storage.client.table('gazelle_timeline_entries').select(
        'title,description,occurred_at,client_id,user_id'
    ).eq('entry_type', 'SYSTEM_MESSAGE').ilike(
        'title', '%Rendez-vous%créé%'
    ).not_.is_('user_id', 'null').gt('occurred_at', since).execute().data or []

    session_windows = _build_session_windows(deactivations)
    matched_appointments = [
        r for r in appointments_created
        if _falls_in_session(r.get('user_id'), _parse(r['occurred_at']), session_windows)
    ]

    rows = deactivations + matched_appointments
    if not rows:
        return {"success": True, "added": 0, "message": "Aucun nouvel appel depuis le dernier sync"}
    rows.sort(key=lambda r: r['occurred_at'])

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
        is_deactivation = 'inactive (était' in (r.get('title') or '')
        result_type = 'Client désactivé' if is_deactivation else 'RV créé (pendant l\'appel)'
        uid = r.get('user_id')
        tech = TECH_DISPLAY_NAMES.get(uid, uid)
        cid = r.get('client_id')
        client_name = clients_map.get(cid) or contacts_map.get(cid) or '(client inconnu)'
        outcome = r.get('description') or r.get('title') or ''
        sheet_rows.append([date_str, time_str, tech, client_name, result_type, outcome])
        if occurred > latest_occurred_at:
            latest_occurred_at = occurred

    svc = gsheet_client()
    append_rows(svc, SHEET_ID, f"{TAB_NAME}!A:F", sheet_rows)

    storage.save_system_setting(LAST_SYNC_SETTING_KEY, latest_occurred_at)

    return {
        "success": True,
        "added": len(sheet_rows),
        "deactivations": len(deactivations),
        "appointments_matched": len(matched_appointments),
        "up_to": latest_occurred_at,
    }


if __name__ == "__main__":
    import json
    print(json.dumps(sync_call_center_to_sheet(), indent=2, ensure_ascii=False))
