"""Ajoute l'onglet '📄 Contrat' au sheet Orford 2026 en 5e position avec formules et formatage complet."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.stdout.reconfigure(encoding='utf-8') if sys.platform == 'win32' else None

from gsheet import client, list_tabs

SHEET_ID = '1Bc_MCpbZVBizv0hdAys9-xBvtp_txZMkPAr0AJIBHu8'
TAB_TITLE = '📄 Contrat'

# Couleurs (Sheets API utilise 0-1)
def rgb(hexstr):
    h = hexstr.lstrip('#')
    return {'red': int(h[0:2],16)/255, 'green': int(h[2:4],16)/255, 'blue': int(h[4:6],16)/255}

NAVY = rgb('#1F3A5F')
LIGHT_BLUE = rgb('#D9E2F3')
YELLOW = rgb('#FFF2CC')
GREY_NOTE = rgb('#999999')
GREY_SOFT = rgb('#666666')
WHITE = rgb('#FFFFFF')

svc = client()

# 1. Localiser la position d'insertion (juste après '💰 Sommaire contrat')
tabs = list_tabs(svc, SHEET_ID)
print("Onglets actuels:", [t for t,_ in tabs])
existing_titles = [t for t,_ in tabs]
if TAB_TITLE in existing_titles:
    print(f"⚠️ L'onglet '{TAB_TITLE}' existe déjà. Abandon pour ne rien écraser.")
    sys.exit(0)

# Index où insérer (juste après Sommaire contrat)
insert_index = None
for i, (title, _) in enumerate(tabs):
    if title == '💰 Sommaire contrat':
        insert_index = i + 1
        break
if insert_index is None:
    print("❌ Onglet '💰 Sommaire contrat' introuvable.")
    sys.exit(1)
print(f"Insertion à l'index {insert_index} (5e position)")

# 2. addSheet
add_resp = svc.spreadsheets().batchUpdate(
    spreadsheetId=SHEET_ID,
    body={'requests': [{
        'addSheet': {
            'properties': {
                'title': TAB_TITLE,
                'index': insert_index,
                'gridProperties': {
                    'rowCount': 100,
                    'columnCount': 4,
                    'hideGridlines': True,
                },
            }
        }
    }]}
).execute()
new_sheet_id = add_resp['replies'][0]['addSheet']['properties']['sheetId']
print(f"✅ Onglet créé, sheetId={new_sheet_id}")

# 3. Écriture des valeurs (USER_ENTERED pour évaluer les formules)
values_data = [
    # (range, [[values]])
    (f"'{TAB_TITLE}'!A1", [["CONTRAT D'ENGAGEMENT — SAISON 2026"]]),
    (f"'{TAB_TITLE}'!B3", [["📌 Document généré automatiquement à partir du calendrier et des paramètres. Pour modifier un montant ou une date, change les valeurs dans les onglets ⚙️ Paramètres ou 📅 Calendrier — tout se met à jour ici. Pour imprimer/exporter en PDF : Fichier → Imprimer (cocher \"masquer la colonne C\" si tu veux la version sans notes internes)."]]),
    (f"'{TAB_TITLE}'!A5", [["ENTRE"]]),
    (f"'{TAB_TITLE}'!B6", [["ORFORD MUSIQUE, personne morale ayant son siège social au 3165, chemin du Parc, Orford (Québec) J1X 7A2, représentée par Wonny Song, Directeur,"]]),
    (f"'{TAB_TITLE}'!B7", [["ci-après désigné « ORFORD MUSIQUE »"]]),
    (f"'{TAB_TITLE}'!A9", [["ET"]]),
    (f"'{TAB_TITLE}'!B10", [["PIANO TECHNIQUE MONTRÉAL, entreprise de services d'accord et d'entretien de pianos, représentée par Nicolas Lessard, RPT, et Allan Sutton,"]]),
    (f"'{TAB_TITLE}'!B11", [["ci-après désigné « l'ACCORDEUR »"]]),
    (f"'{TAB_TITLE}'!B13", [["LES PARTIES CONVIENNENT DE CE QUI SUIT :"]]),
    (f"'{TAB_TITLE}'!A15", [["ARTICLE 1"]]),
    (f"'{TAB_TITLE}'!B15", [["OBJET DU CONTRAT"]]),
    (f"'{TAB_TITLE}'!B16", [["L'ACCORDEUR s'engage à fournir les services d'accord, d'entretien et de préparation des pianos de concert et des pianos de l'Académie d'ORFORD MUSIQUE pour la saison 2026."]]),
    (f"'{TAB_TITLE}'!A18", [["ARTICLE 2"]]),
    (f"'{TAB_TITLE}'!B18", [["CONDITIONS FINANCIÈRES"]]),
    (f"'{TAB_TITLE}'!B19", [["2.1  Le cachet est fixé selon les types de service :"]]),
    (f"'{TAB_TITLE}'!B21", [["=\" • Préparation pré-festival : \"&TEXT('💰 Sommaire contrat'!D6,\"#,##0\")&\" $ pour deux journées de travail avec quatre techniciens.\""]]),
    (f"'{TAB_TITLE}'!C21", [["Réf. 2024 : 3 000 $ | Réf. 2025 : inclus dans les 24,5 jours à 630 $/jour"]]),
    (f"'{TAB_TITLE}'!B22", [["=\" • Les accords de l'Annexe A seront faits pour un total de \"&TEXT('💰 Sommaire contrat'!D7+'💰 Sommaire contrat'!D8,\"#,##0\")&\" $ (\"&TEXT('💰 Sommaire contrat'!B7+'💰 Sommaire contrat'!B8,\"#,##0.0\")&\" journées-tech à \"&TEXT(TARIF_JOUR,\"#,##0.00\")&\" $/jour).\""]]),
    (f"'{TAB_TITLE}'!C22", [["Réf. 2024 : 10 200 $ (20 jours) | Réf. 2025 : 15 435 $ (24,5 jours à 630 $/jour)"]]),
    (f"'{TAB_TITLE}'!B23", [["=\" • Accord de piano à queue supplémentaire (non prévu au calendrier initial) : \"&TEXT(TARIF_ACCORD_SUPP,\"#,##0.00\")&\" $ + tx.\""]]),
    (f"'{TAB_TITLE}'!C23", [["Réf. 2024 : 125 $ | Réf. 2025 : 175 $ + tx"]]),
    (f"'{TAB_TITLE}'!B24", [["=\" • Frais de déplacement : \"&TEXT('💰 Sommaire contrat'!B10,\"#,##0\")&\" déplacements à \"&TEXT(TARIF_DEPLACEMENT,\"#,##0.00\")&\" $ = \"&TEXT('💰 Sommaire contrat'!D10,\"#,##0.00\")&\" $.\""]]),
    (f"'{TAB_TITLE}'!C24", [["Réf. 2024 : inclus | Réf. 2025 : 10 dépl. à 173,95 $ = 1 739,50 $"]]),
    (f"'{TAB_TITLE}'!B26", [["2.2  L'ACCORDEUR va facturer les travaux effectués selon les tarifs au point 2.1 en trois (3) versements échelonnés sur la saison."]]),
    (f"'{TAB_TITLE}'!C26", [["Réf. 2025 : 3 paiements de 4 949 $ + tx les 29 mai, 10 juillet et 7 août"]]),
    (f"'{TAB_TITLE}'!B28", [["=\"2.3  Rabais institutionnel : \"&TEXT(-'💰 Sommaire contrat'!D12,\"#,##0\")&\" $ (\"&TEXT(RABAIS_PCT,\"0.0%\")&\" du sous-total des services), accordé en échange de la visibilité prévue à l'article 4.\""]]),
    (f"'{TAB_TITLE}'!C28", [["Réf. 2024 : ~5 000 $ (visibilité) | Réf. 2025 : 2 327,50 $ (95 $/jour)"]]),
    (f"'{TAB_TITLE}'!B30", [["=\"TOTAL : \"&TEXT('💰 Sommaire contrat'!D13,\"#,##0\")&\" $ + TX (= \"&TEXT('💰 Sommaire contrat'!D15,\"#,##0\")&\" $ taxes incluses).\""]]),
    (f"'{TAB_TITLE}'!C30", [["Réf. 2024 : 12 000 $ | Réf. 2025 : 14 847 $ + tx"]]),
    (f"'{TAB_TITLE}'!B32", [["2.4  Les frais d'hébergement et les frais repas à la cafétéria d'ORFORD MUSIQUE du 12 juin au 15 août 2026 seront assumés par ORFORD MUSIQUE, à l'exception des journées de préparation pré-festival. Tous autres frais (bar, restaurant, services) sont à la charge de l'ACCORDEUR et payés immédiatement par lui."]]),
    (f"'{TAB_TITLE}'!C32", [["Dates à ajuster manuellement si Festival change de bornes"]]),
    (f"'{TAB_TITLE}'!B34", [["2.5  L'ACCORDEUR qui désire être accompagné lors de son séjour devra en faire la demande formelle auprès d'ORFORD MUSIQUE au moins 45 jours avant l'arrivée. L'hébergement sera offert selon la disponibilité et sera sujet à la tarification en vigueur durant le séjour. Pour les repas, la tarification (taxes incluses) sera communiquée par ORFORD MUSIQUE."]]),
    (f"'{TAB_TITLE}'!B36", [["2.6  ORFORD MUSIQUE exige la pleine révélation, à la signature du contrat, de toute allergie ou handicap physique de l'ACCORDEUR ou de ses invités qui pourrait susciter une attention particulière. ORFORD MUSIQUE ne pourra être tenue responsable de toute situation résultant d'un manque d'information."]]),
    (f"'{TAB_TITLE}'!A38", [["ARTICLE 3"]]),
    (f"'{TAB_TITLE}'!B38", [["CONDITIONS RELATIVES À L'ENGAGEMENT"]]),
    (f"'{TAB_TITLE}'!B39", [["3.1  ORFORD MUSIQUE s'engage à transmettre à l'ACCORDEUR, 7 jours à l'avance, les pianos à accorder selon le calendrier de l'offre de service (Annexe A)."]]),
    (f"'{TAB_TITLE}'!B41", [["3.2  ORFORD MUSIQUE se réserve le droit de diminuer le nombre d'accords selon ses besoins."]]),
    (f"'{TAB_TITLE}'!B43", [["=\"3.3  L'ACCORDEUR se déplace pour un minimum de \"&TEXT(TARIF_JOUR,\"#,##0.00\")&\" $ par jour.\""]]),
    (f"'{TAB_TITLE}'!C43", [["Réf. 2024 : 600 $ | Réf. 2025 : 630 $"]]),
    (f"'{TAB_TITLE}'!B45", [["3.4  L'ajout d'accords par ORFORD MUSIQUE doit être accepté préalablement par l'ACCORDEUR."]]),
    (f"'{TAB_TITLE}'!B47", [["3.5  Un adjoint d'expérience est autorisé par ORFORD MUSIQUE. Ce dernier sera rémunéré par l'ACCORDEUR."]]),
    (f"'{TAB_TITLE}'!A49", [["ARTICLE 4"]]),
    (f"'{TAB_TITLE}'!B49", [["ÉCHANGE DE VISIBILITÉ"]]),
    (f"'{TAB_TITLE}'!B50", [["=\"La valeur du rabais institutionnel accordé est de \"&TEXT(-'💰 Sommaire contrat'!D12,\"#,##0\")&\" $.\""]]),
    (f"'{TAB_TITLE}'!C50", [["Réf. 2024 : 5 000 $ | Réf. 2025 : 2 327,50 $"]]),
    (f"'{TAB_TITLE}'!B52", [["En échange, ORFORD MUSIQUE offre la visibilité suivante à l'ACCORDEUR :"]]),
    (f"'{TAB_TITLE}'!B53", [["    • Piano Technique Montréal sera remercié dans le dépliant ;"]]),
    (f"'{TAB_TITLE}'!B54", [["    • Piano Technique Montréal sera nommé au début de chaque concert en voix hors champ ;"]]),
    (f"'{TAB_TITLE}'!B55", [["    • Piano Technique Montréal sera nommé dans les programmes de concerts du Festival."]]),
    (f"'{TAB_TITLE}'!B57", [["L'ACCORDEUR affichera le logo d'ORFORD MUSIQUE sur son site web."]]),
    (f"'{TAB_TITLE}'!A59", [["ARTICLE 5"]]),
    (f"'{TAB_TITLE}'!B59", [["RÉSILIATION"]]),
    (f"'{TAB_TITLE}'!B60", [["5.1  Le présent contrat est résilié :"]]),
    (f"'{TAB_TITLE}'!B61", [["a)  À la demande d'ORFORD MUSIQUE, pour un motif sérieux, à la réception par l'ACCORDEUR d'un avis à cet effet. ORFORD MUSIQUE assume les frais engagés par l'ACCORDEUR avant la date de réception de l'avis ainsi qu'une rémunération proportionnelle à celle prévue à la clause 2."]]),
    (f"'{TAB_TITLE}'!B63", [["b)  À la demande de l'ACCORDEUR, pour un motif sérieux, à la réception par ORFORD MUSIQUE d'un avis à cet effet mentionnant les motifs de la résiliation. L'ACCORDEUR est tenu de restituer les avances reçues en excédent des sommes gagnées."]]),
    (f"'{TAB_TITLE}'!B65", [["c)  Lorsque les obligations qui font l'objet des présentes ne peuvent être exécutées en raison d'une force majeure ou lorsqu'un événement prévu par une disposition législative d'ordre public prévoyant la résiliation du contrat survient."]]),
    (f"'{TAB_TITLE}'!B67", [["5.2  Toute procédure légale pouvant être intentée en vertu de ce contrat devra l'être exclusivement dans le district judiciaire de Saint-François, Québec, Canada."]]),
    (f"'{TAB_TITLE}'!A69", [["ARTICLE 6"]]),
    (f"'{TAB_TITLE}'!B69", [["SIGNATURES"]]),
    (f"'{TAB_TITLE}'!B70", [["Une copie du présent contrat doit être retournée à ORFORD MUSIQUE à l'adresse suivante : scusson@orford.mu"]]),
    (f"'{TAB_TITLE}'!B72", [["Pour ORFORD MUSIQUE :"]]),
    (f"'{TAB_TITLE}'!B73", [["Signature : ____________________________________   Date : ___________________"]]),
    (f"'{TAB_TITLE}'!B74", [["Nom : Wonny Song, Directeur"]]),
    (f"'{TAB_TITLE}'!B76", [["Pour l'ACCORDEUR (Piano Technique Montréal) :"]]),
    (f"'{TAB_TITLE}'!B77", [["Signature : ____________________________________   Date : ___________________"]]),
    (f"'{TAB_TITLE}'!B78", [["Nom : Nicolas Lessard, RPT"]]),
    (f"'{TAB_TITLE}'!A80", [["ANNEXE A"]]),
    (f"'{TAB_TITLE}'!B80", [["CALENDRIER DES ACCORDS — SAISON 2026"]]),
    (f"'{TAB_TITLE}'!B81", [["Le détail complet du calendrier est dans l'onglet 📅 Calendrier de ce même document. Pour la version imprimée du contrat, exporter cet onglet en PDF (Fichier → Télécharger → PDF) et joindre les pages au présent contrat."]]),
    (f"'{TAB_TITLE}'!C81", [["L'Annexe A se met à jour en temps réel via l'onglet Calendrier"]]),
    (f"'{TAB_TITLE}'!B83", [["Pianos de concert disponibles :"]]),
    (f"'{TAB_TITLE}'!B84", [["    • Steinway D (SC-2)"]]),
    (f"'{TAB_TITLE}'!B85", [["    • Yamaha CFIII S6045000 (SC-1)"]]),
    (f"'{TAB_TITLE}'!B86", [["    • Shigeru Kawai (SC-3, acquis en 2023)"]]),
    (f"'{TAB_TITLE}'!B87", [["    • + 3 pianos supplémentaires pour le concert d'ouverture du 13 juin (modèles à confirmer)"]]),
    (f"'{TAB_TITLE}'!B89", [["Catégories de pianos de l'Académie :"]]),
    (f"'{TAB_TITLE}'!B90", [["    • Catégorie A : pianos à queue pour les classes de maîtres de piano"]]),
    (f"'{TAB_TITLE}'!B91", [["    • Catégorie B : pianos à queue pour les classes de maîtres autres que piano"]]),
    (f"'{TAB_TITLE}'!B92", [["    • Catégorie C : pianos à queue pour les pianistes accompagnateurs"]]),
    (f"'{TAB_TITLE}'!B93", [["    • Catégorie D : piano à queue billetterie et pianos droits"]]),
]

# Convertir en batchUpdate
data_batch = [{'range': r, 'values': v} for r, v in values_data]
svc.spreadsheets().values().batchUpdate(
    spreadsheetId=SHEET_ID,
    body={
        'valueInputOption': 'USER_ENTERED',
        'data': data_batch,
    }
).execute()
print(f"✅ {len(data_batch)} cellules écrites")

# 4. Formatage via batchUpdate
sid = new_sheet_id

def cell_format(start_row, end_row, start_col, end_col, fields, format_dict):
    """RepeatCell helper. Rows/cols 0-indexed, end exclusive."""
    return {
        'repeatCell': {
            'range': {
                'sheetId': sid,
                'startRowIndex': start_row, 'endRowIndex': end_row,
                'startColumnIndex': start_col, 'endColumnIndex': end_col,
            },
            'cell': {'userEnteredFormat': format_dict},
            'fields': fields,
        }
    }

def row_height(row_idx, height):
    return {
        'updateDimensionProperties': {
            'range': {
                'sheetId': sid, 'dimension': 'ROWS',
                'startIndex': row_idx, 'endIndex': row_idx + 1,
            },
            'properties': {'pixelSize': height},
            'fields': 'pixelSize',
        }
    }

def col_width(col_idx, width):
    return {
        'updateDimensionProperties': {
            'range': {
                'sheetId': sid, 'dimension': 'COLUMNS',
                'startIndex': col_idx, 'endIndex': col_idx + 1,
            },
            'properties': {'pixelSize': width},
            'fields': 'pixelSize',
        }
    }

requests = []

# Largeurs colonnes (A=120, B=640, C=260 — équivalent xlsx 16/90/35 chars)
requests += [col_width(0, 120), col_width(1, 640), col_width(2, 260)]

# Police par défaut Arial 11 sur tout le sheet
requests.append(cell_format(
    0, 100, 0, 4,
    'userEnteredFormat(textFormat,verticalAlignment)',
    {
        'textFormat': {'fontFamily': 'Arial', 'fontSize': 11},
        'verticalAlignment': 'TOP',
    },
))

# Wrap par défaut sur colonne B
requests.append(cell_format(
    0, 100, 1, 2,
    'userEnteredFormat.wrapStrategy',
    {'wrapStrategy': 'WRAP'},
))

# Fusion A1:C1
requests.append({
    'mergeCells': {
        'range': {'sheetId': sid, 'startRowIndex': 0, 'endRowIndex': 1, 'startColumnIndex': 0, 'endColumnIndex': 3},
        'mergeType': 'MERGE_ALL',
    }
})

# A1 (titre principal) : Arial 18 gras navy, hauteur 28
requests.append(cell_format(
    0, 1, 0, 3,
    'userEnteredFormat(textFormat,horizontalAlignment,verticalAlignment)',
    {
        'textFormat': {'fontFamily': 'Arial', 'fontSize': 18, 'bold': True, 'foregroundColor': NAVY},
        'horizontalAlignment': 'CENTER',
        'verticalAlignment': 'MIDDLE',
    },
))
requests.append(row_height(0, 28))

# B3 (bandeau jaune) : Arial 10 italique #666666, fond jaune, bordures, wrap, hauteur 70
requests.append(cell_format(
    2, 3, 1, 2,
    'userEnteredFormat(textFormat,backgroundColor,borders,wrapStrategy,verticalAlignment)',
    {
        'textFormat': {'fontFamily': 'Arial', 'fontSize': 10, 'italic': True, 'foregroundColor': GREY_SOFT},
        'backgroundColor': YELLOW,
        'borders': {
            'top': {'style': 'SOLID', 'color': NAVY},
            'bottom': {'style': 'SOLID', 'color': NAVY},
            'left': {'style': 'SOLID', 'color': NAVY},
            'right': {'style': 'SOLID', 'color': NAVY},
        },
        'wrapStrategy': 'WRAP',
        'verticalAlignment': 'MIDDLE',
    },
))
requests.append(row_height(2, 70))

# A5, A9 (ENTRE / ET) — Gras navy
for r in (4, 8):  # 0-indexed
    requests.append(cell_format(
        r, r+1, 0, 1,
        'userEnteredFormat.textFormat',
        {'textFormat': {'fontFamily': 'Arial', 'fontSize': 11, 'bold': True, 'foregroundColor': NAVY}},
    ))

# B6, B10 (descriptions parties) — wrap, hauteur 30
for r in (5, 9):
    requests.append(row_height(r, 30))

# B13 (LES PARTIES CONVIENNENT) — gras
requests.append(cell_format(
    12, 13, 1, 2,
    'userEnteredFormat.textFormat',
    {'textFormat': {'fontFamily': 'Arial', 'fontSize': 11, 'bold': True}},
))

# Articles : barre fond #D9E2F3 gras navy + titre gras
# ARTICLE 1 (row 14), 2 (17), 3 (37), 4 (48), 5 (58), 6 (68), ANNEXE A (79)
article_rows = [14, 17, 37, 48, 58, 68, 79]
for r in article_rows:
    # Bandeau A:C fond + ARTICLE bold navy
    requests.append(cell_format(
        r, r+1, 0, 3,
        'userEnteredFormat(backgroundColor,textFormat)',
        {
            'backgroundColor': LIGHT_BLUE,
            'textFormat': {'fontFamily': 'Arial', 'fontSize': 11, 'bold': True, 'foregroundColor': NAVY},
        },
    ))

# B16 (objet contrat) — wrap, hauteur 32
requests.append(row_height(15, 32))

# B19 (2.1 cachet) — gras
requests.append(cell_format(
    18, 19, 1, 2, 'userEnteredFormat.textFormat',
    {'textFormat': {'fontFamily': 'Arial', 'fontSize': 11, 'bold': True}},
))

# Hauteurs des points 2.1 (rows 20-23) et 2.2 (row 25)
for r, h in [(20, 30), (21, 32), (25, 32)]:
    requests.append(row_height(r, h))

# B28 (2.3 rabais) — gras + hauteur 36
requests.append(cell_format(
    27, 28, 1, 2, 'userEnteredFormat.textFormat',
    {'textFormat': {'fontFamily': 'Arial', 'fontSize': 11, 'bold': True}},
))
requests.append(row_height(27, 36))

# B30 (TOTAL) — Arial 12 gras navy, hauteur 26
requests.append(cell_format(
    29, 30, 1, 2, 'userEnteredFormat.textFormat',
    {'textFormat': {'fontFamily': 'Arial', 'fontSize': 12, 'bold': True, 'foregroundColor': NAVY}},
))
requests.append(row_height(29, 26))

# B32, B34, B36 (2.4, 2.5, 2.6) — hauteur 60
for r in (31, 33, 35):
    requests.append(row_height(r, 60))

# B39 (3.1) — hauteur 32
requests.append(row_height(38, 32))

# B60 (5.1 Le contrat est résilié) — gras
requests.append(cell_format(
    59, 60, 1, 2, 'userEnteredFormat.textFormat',
    {'textFormat': {'fontFamily': 'Arial', 'fontSize': 11, 'bold': True}},
))

# B61, B63, B65 (a, b, c) hauteurs 60/50/50
for r, h in [(60, 60), (62, 50), (64, 50)]:
    requests.append(row_height(r, h))

# B67 (5.2) hauteur 36
requests.append(row_height(66, 36))

# B70 (adresse retour) hauteur 24
requests.append(row_height(69, 24))

# B72, B76 (Pour ORFORD / Pour ACCORDEUR) — gras
for r in (71, 75):
    requests.append(cell_format(
        r, r+1, 1, 2, 'userEnteredFormat.textFormat',
        {'textFormat': {'fontFamily': 'Arial', 'fontSize': 11, 'bold': True}},
    ))

# B81 (Annexe A intro) hauteur 60
requests.append(row_height(80, 60))

# B83, B89 (Pianos / Catégories) — gras
for r in (82, 88):
    requests.append(cell_format(
        r, r+1, 1, 2, 'userEnteredFormat.textFormat',
        {'textFormat': {'fontFamily': 'Arial', 'fontSize': 11, 'bold': True}},
    ))

# Colonne C (notes internes) : Arial 9 italique #999999 sur toute la colonne
requests.append(cell_format(
    0, 100, 2, 3,
    'userEnteredFormat.textFormat',
    {'textFormat': {'fontFamily': 'Arial', 'fontSize': 9, 'italic': True, 'foregroundColor': GREY_NOTE}},
))

# Article titles in B (B15, B18, B38, B49, B59, B69, B80) — gras
for r in [14, 17, 37, 48, 58, 68, 79]:
    requests.append(cell_format(
        r, r+1, 1, 2, 'userEnteredFormat.textFormat',
        {'textFormat': {'fontFamily': 'Arial', 'fontSize': 11, 'bold': True}},
    ))
# Mais pour les bandeaux article (col A:C), on a déjà mis bold navy. La col B ARTICLE titre doit rester bold mais pas navy (titre sujet).
# Retravaillons: les bandeaux A:C des article rows ont fond bleu pâle + bold navy.
# Le contenu du titre en B reste lisible — on peut laisser bold navy aussi (cohérent) ou bold noir.
# La spec dit "B15: OBJET DU CONTRAT, Gras" sans préciser navy → on met bold simple, pas navy.
# Override col B des articles pour bold noir (pas navy) :
for r in [14, 17, 37, 48, 58, 68, 79]:
    requests.append(cell_format(
        r, r+1, 1, 2, 'userEnteredFormat.textFormat',
        {'textFormat': {'fontFamily': 'Arial', 'fontSize': 11, 'bold': True, 'foregroundColor': rgb('#000000')}},
    ))
# Et A des article rows : gras navy (pas écraser)
for r in [14, 17, 37, 48, 58, 68, 79]:
    requests.append(cell_format(
        r, r+1, 0, 1, 'userEnteredFormat.textFormat',
        {'textFormat': {'fontFamily': 'Arial', 'fontSize': 11, 'bold': True, 'foregroundColor': NAVY}},
    ))

# Exécuter le batch
print(f"Envoi de {len(requests)} requêtes de formatage...")
svc.spreadsheets().batchUpdate(
    spreadsheetId=SHEET_ID,
    body={'requests': requests},
).execute()
print("✅ Formatage appliqué")

# Vérification finale
tabs_after = list_tabs(svc, SHEET_ID)
print("\nOnglets finaux:")
for i, (t, _) in enumerate(tabs_after):
    marker = " ← NOUVEAU" if t == TAB_TITLE else ""
    print(f"  {i+1}. {t}{marker}")
