"""PTM Google Sheets helper — direct edit via Sheets API.

Usage:
    from tools.gsheet import client, get_sheet, list_tabs, add_tab, update_range, read_range
    svc = client()
    list_tabs(svc, SHEET_ID)
    add_tab(svc, SHEET_ID, 'Mon nouvel onglet')
    update_range(svc, SHEET_ID, 'Mon nouvel onglet!A1:B2', [['x','y'],['1','2']])

CLI:
    python tools/gsheet.py list <sheet_id>
    python tools/gsheet.py add-tab <sheet_id> <title>
    python tools/gsheet.py read <sheet_id> <range>
    python tools/gsheet.py update <sheet_id> <range> <json_2d_array>

Auth: service account via Supabase system_settings.GOOGLE_SHEETS_JSON,
domain-wide delegation as asutton@piano-tek.com.
Required scopes on the delegation: drive + spreadsheets.
"""
import sys, json, tempfile, os

# Force UTF-8 on stdout for Windows consoles (emojis in tab names)
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

# Make assistant-gazelle-v5 importable so we can use SupabaseStorage
_GZ = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'assistant-gazelle-v5')
if _GZ not in sys.path:
    sys.path.insert(0, _GZ)

from core.supabase_storage import SupabaseStorage
from google.oauth2 import service_account
from googleapiclient.discovery import build

SCOPES = [
    'https://www.googleapis.com/auth/drive',
    'https://www.googleapis.com/auth/spreadsheets',
]

_creds_cache = None


def _credentials():
    global _creds_cache
    if _creds_cache is not None:
        return _creds_cache
    s = SupabaseStorage(silent=True)
    r = s.client.table('system_settings').select('value').eq('key', 'GOOGLE_SHEETS_JSON').execute()
    creds_json = r.data[0]['value']
    tmp = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
    json.dump(creds_json, tmp)
    tmp.close()
    _creds_cache = service_account.Credentials.from_service_account_file(
        tmp.name, scopes=SCOPES, subject='asutton@piano-tek.com'
    )
    return _creds_cache


def client():
    """Return a Sheets API v4 service."""
    return build('sheets', 'v4', credentials=_credentials())


def drive_client():
    """Return a Drive API v3 service (for shared-drive-aware ops)."""
    return build('drive', 'v3', credentials=_credentials())


def get_sheet(svc, sheet_id):
    return svc.spreadsheets().get(spreadsheetId=sheet_id).execute()


def list_tabs(svc, sheet_id):
    meta = svc.spreadsheets().get(
        spreadsheetId=sheet_id, fields='properties.title,sheets.properties'
    ).execute()
    return [(s['properties']['title'], s['properties']['sheetId']) for s in meta.get('sheets', [])]


def add_tab(svc, sheet_id, title):
    body = {'requests': [{'addSheet': {'properties': {'title': title}}}]}
    return svc.spreadsheets().batchUpdate(spreadsheetId=sheet_id, body=body).execute()


def delete_tab(svc, sheet_id, tab_id):
    body = {'requests': [{'deleteSheet': {'sheetId': tab_id}}]}
    return svc.spreadsheets().batchUpdate(spreadsheetId=sheet_id, body=body).execute()


def read_range(svc, sheet_id, a1_range):
    return svc.spreadsheets().values().get(spreadsheetId=sheet_id, range=a1_range).execute().get('values', [])


def update_range(svc, sheet_id, a1_range, values, value_input_option='USER_ENTERED'):
    """value_input_option: USER_ENTERED (formulas evaluated) or RAW."""
    return svc.spreadsheets().values().update(
        spreadsheetId=sheet_id, range=a1_range,
        valueInputOption=value_input_option,
        body={'values': values},
    ).execute()


def append_rows(svc, sheet_id, a1_range, values, value_input_option='USER_ENTERED'):
    return svc.spreadsheets().values().append(
        spreadsheetId=sheet_id, range=a1_range,
        valueInputOption=value_input_option,
        body={'values': values},
    ).execute()


def batch_update(svc, sheet_id, requests):
    """Pass-through to Sheets API batchUpdate. `requests` is a list of dicts,
    each one a Sheets API Request (see https://developers.google.com/sheets/api/reference/rest/v4/spreadsheets/request).
    Use this for formatting, merging, conditional formats, frozen rows, etc."""
    return svc.spreadsheets().batchUpdate(
        spreadsheetId=sheet_id, body={'requests': requests}
    ).execute()


# CLI
def _main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 1
    cmd, sheet_id = argv[0], argv[1]
    svc = client()
    if cmd == 'list':
        for title, tid in list_tabs(svc, sheet_id):
            print(f"  {title}\t(id={tid})")
    elif cmd == 'add-tab':
        title = argv[2]
        add_tab(svc, sheet_id, title)
        print(f"Tab '{title}' added.")
    elif cmd == 'read':
        a1 = argv[2]
        rows = read_range(svc, sheet_id, a1)
        for r in rows:
            print('\t'.join(str(c) for c in r))
    elif cmd == 'update':
        a1 = argv[2]
        data = json.loads(argv[3])
        update_range(svc, sheet_id, a1, data)
        print(f"Updated {a1}.")
    else:
        print(f"Unknown command: {cmd}")
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(_main(sys.argv[1:]))
