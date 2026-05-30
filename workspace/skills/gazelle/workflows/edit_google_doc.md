# Modifier un Google Doc — workflow obligatoire

**IMPORTANT : NE JAMAIS utiliser les outils MCP google-drive pour éditer des Google Docs.**
Les outils MCP (`updateGoogleDoc`, `findAndReplaceInDoc`, `editTableCell`, `insertText`)
utilisent l'API Google Docs qui N'EST PAS activée sur le projet GCP du service account.

## Méthode obligatoire : Drive API export/re-upload

Le service account a le scope `drive` (pas `documents`). On utilise le Drive API
pour exporter le doc en HTML, modifier le HTML en Python, et re-uploader.

### Pattern Python

```python
import json, tempfile
from core.supabase_storage import SupabaseStorage
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaInMemoryUpload

# Auth via Supabase (credentials stockées dans system_settings)
s = SupabaseStorage(silent=True)
r = s.client.table('system_settings').select('value').eq('key', 'GOOGLE_SHEETS_JSON').execute()
creds = r.data[0]['value']
tmp = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
json.dump(creds, tmp); tmp.close()

credentials = service_account.Credentials.from_service_account_file(
    tmp.name,
    scopes=['https://www.googleapis.com/auth/drive'],
    subject='asutton@piano-tek.com'
)
service = build('drive', 'v3', credentials=credentials)

DOC_ID = 'xxxxx'

# 1. Export en HTML
html_bytes = service.files().export(fileId=DOC_ID, mimeType='text/html').execute()
html = html_bytes.decode('utf-8')

# 2. Modifier le HTML (remplacements, insertions de lignes de tableau, etc.)
# ATTENTION : les accents sont en entités HTML (&agrave; &eacute; etc.)
html = html.replace('ancien texte', 'nouveau texte')

# 3. Re-upload (supportsAllDrives=True pour les shared drives)
media = MediaInMemoryUpload(html.encode('utf-8'), mimetype='text/html')
service.files().update(fileId=DOC_ID, media_body=media, supportsAllDrives=True).execute()
```

### Points critiques

- **Toujours sauvegarder le HTML original** avant modification (fichier backup local)
- **supportsAllDrives=True** obligatoire pour les docs dans des shared drives
- **Entités HTML** : `à` = `&agrave;`, `é` = `&eacute;`, `È` = `&Eacute;`, etc.
- **Tableaux** : les lignes sont des `<tr>...</tr>`, copier le style d'une ligne existante
- **Export text/plain** pour vérifier le résultat sans HTML (lecture seule)
- Les liens deviennent des redirections Google (`google.com/url?q=...`) après re-upload — c'est normal

### Historique du problème (2026-04-30)

Le 28 avril, le doc QRS PNOmation a été créé et édité avec ce pattern Drive API.
Le 30 avril, Claude Code a tenté d'utiliser les outils MCP google-drive à la place,
ce qui a échoué pendant 45 minutes. Le MCP utilise l'API Docs (projet 1027601768584)
qui n'est pas activée. La méthode Drive API fonctionne et a toujours fonctionné.
