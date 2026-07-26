# 🌡️ Système d'alertes d'humidité PTM — Documentation

> **But du document** : expliquer honnêtement comment fonctionne le système d'alertes d'humidité, en distinguant le **bot LOCAL** (dépendant du PC d'Allan) du **code CLOUD** (dans le repo `assistant-gazelle-v5`), afin que l'équipe puisse décider en connaissance de cause de le **réécrire dans le nuage**, le **retirer**, ou le **laisser tel quel**.
>
> ⚠️ Document de constat en lecture seule. Aucun code n'a été modifié.
>
> **Dernière mise à jour :** 2026-07-26

---

## 1. Résumé en 3 lignes

- Le système surveille les **notes de service des techniciens** pour repérer les mauvaises pratiques qui exposent les pianos à l'humidité : **housse retirée**, **PLS / Dampp-Chaser débranché**, réservoir vide, humidité anormale.
- Quand un problème **non résolu** est détecté, il **notifie** (Slack + courriel à Nicolas) pour qu'on aille corriger avant que le piano souffre.
- Il existe aujourd'hui **deux implémentations en parallèle** qui font presque la même chose : un **bot local sur le PC d'Allan** et un **scanner dans le nuage** (repo v5). Le bot local est le dernier « cordon » qui rattache une tâche opérationnelle au PC physique.

---

## 2. Deux systèmes en parallèle

| | 🖥️ **Bot LOCAL (PC)** | ☁️ **Code CLOUD (repo v5)** |
|---|---|---|
| **Fichier principal** | `C:\Allan Python projets\humidity_alerts\humidity_alert_system.py` | `modules/alerts/humidity_scanner.py` (classe `HumidityScanner`) |
| **Où ça tourne** | PC d'Allan (`PIANOTEK`), Windows Task Scheduler | GitHub Actions (runner Ubuntu) + Render |
| **Source de données** | **SQL Server local** `PIANOTEK\SQLEXPRESS`, base `PianoTek`, table `TimelineEntries` (type `SERVICE_ENTRY_MANUAL`) | **Supabase** PostgreSQL, table `gazelle_timeline_entries` |
| **Clients surveillés** | **TOUS** (`config.json` → `monitoring.clients = []` = pas de filtre) ⚠️ | **Seulement institutionnels** : Vincent d'Indy, Place des Arts, Orford (filtre en dur) |
| **Détection IA** | OpenAI `gpt-4o-mini` (clé `OPENAI_API_KEY`) | Anthropic `claude-haiku-4-5` (clé `ANTHROPIC_API_KEY`) ⚠️ voir §5 |
| **Anti-doublon** | Fichier local `alerts_history.json` (liste des `EntryId` déjà traités) | Table Supabase `humidity_alerts_history` |
| **Stockage des alertes** | Table SQL locale `MaintenanceAlerts` + rapport Google Sheet | Tables Supabase `humidity_alerts` / `humidity_alerts_active` |
| **Notifications Slack** | Webhooks : **Louise** + **Nicolas** (Allan et Jean-Philippe = URL placeholder, inactives) | Via `NotificationService` → Louise + Nicolas |
| **Notification courriel** | Oui — courriel HTML à `nlessard@piano-tek.com` (via `core.email_notifier` de v5, token Gmail Supabase) | Oui — courriel à `nlessard@piano-tek.com` (même `EmailNotifier`) |
| **Affichage tableau de bord** | ❌ Aucun | ✅ Carte « Alertes humidité » dans `DashboardHome.jsx` (conditionnelle) |
| **Planification** | Windows Task **« PianoTek - Mise a jour quotidienne »**, tous les jours **03:00**, via `C:\Genosa\Working\update.bat` | GitHub Actions `humidity_alerts_scanner.yml`, tous les jours **14:00 UTC = 9:00 Montréal** |
| **Dernière exécution constatée** | `2026-06-27` (voir `alerts_history.json`) | (déclenchée par GitHub, indépendante du PC) |

---

## 3. Ce qui est PC-only (le cordon) 🔌

Ce qui **s'arrête si le PC d'Allan est éteint** :

1. **Le pipeline d'alimentation de la base locale** — `C:\Genosa\Working\update.bat` → `Import_daily_update.py` (+ `Clients.py`, `pianos.py`, `timeline.py`) qui va chercher les données Gazelle (GraphQL) et remplit **SQL Server `PIANOTEK\SQLEXPRESS`**. **Unique au local** : rien dans le nuage n'alimente ce SQL Server.
2. **Le bot local `humidity_alert_system.py`** lui-même, lancé en 4ᵉ étape de `update.bat`. **Partiellement dupliqué** dans le nuage (voir §5), mais avec des différences (tous les clients vs institutionnels seulement, OpenAI vs Claude).
3. **La table SQL locale `MaintenanceAlerts`** et **le rapport Google Sheet** (`maintenance_alerts_report.py`) générés par le bot local. **Unique au local** — le nuage écrit plutôt dans Supabase et dans une carte de tableau de bord.
4. **Le fichier d'anti-doublon `alerts_history.json`** (état local). **Unique au local** (le nuage a son équivalent Supabase `humidity_alerts_history`).

Ce qui **NE dépend PAS du PC** (déjà couvert dans le nuage) :

- Le scan quotidien des institutions (Vincent d'Indy, Place des Arts, Orford) via **GitHub Actions** — tourne sur les serveurs GitHub, indépendant du PC.
- Les notifications Slack/courriel de la version cloud passent par Supabase + Resend/Gmail, sans PC.

➡️ **En clair** : couper le PC arrête (a) la mise à jour du SQL Server local et (b) la surveillance **de tous les clients non-institutionnels**. La surveillance des **3 institutions** continue via le nuage.

---

## 4. Fonctionnement détaillé du bot local

Fichier : `C:\Allan Python projets\humidity_alerts\humidity_alert_system.py`

### Entrées
- **Requête SQL** sur `TimelineEntries` (jointures `Pianos`, `Users`, `Clients`), filtrée sur `EntryType = 'SERVICE_ENTRY_MANUAL'` et les **`days_back` derniers jours** (`config.json` → `monitoring.days_back = 1`).
- Champs récupérés : date, description/titre, client, marque/modèle/n° de série du piano, local, technicien, notes générales, `EntryId`.

### Logique de détection (`analyze_services`)
Pour chaque entrée pas déjà dans l'historique :
1. **Étape 1 — mots-clés** (`detect_issue`) sur la description ET les notes générales. Deux familles dans `config.json` :
   - `housse` : « housse enlevée/retirée », « cover removed/off », « sans housse », « no cover »…
   - `alimentation` : « débranché », « pls débranché », « unplugged », « déconnecté », « pas branché »…
2. **Étape 2 — IA (fallback)** (`analyze_with_ai`) : si aucun mot-clé, appel OpenAI `gpt-4o-mini` (JSON, seuil `confidence > 0.6`). Détecte `housse` / `alimentation`.
3. **Détection de résolution** : pour chaque problème trouvé, cherche un mot-clé de `resolution_keywords` (ex. « rebranché », « replacée », « plugged back »). Une entrée peut donc être marquée **résolue**.

### Sorties (ordre du `main()`)
1. **Insertion dans `MaintenanceAlerts`** (SQL local) — **toutes** les alertes (résolues + non résolues). `RecipientEmail` mis en dur à `jgonzalo@emvi.qc.ca`, `CreatedBy = "Scanner Auto (<technicien>)"`.
2. **Rapport Google Sheet** régénéré (`maintenance_alerts_report.py`) s'il y a eu insertion.
3. **Notifications — SEULEMENT les non résolues** :
   - **Slack** (`send_slack_notification`) : POST vers chaque webhook de `config.json`. Actifs : **Louise** et **Nicolas**. Message groupé par local, icônes 🔌 (alimentation) / 🛡️ (housse) / ✅ (résolu).
   - **Courriel HTML** à `nlessard@piano-tek.com` (`send_email_to_nicolas`) via `core.email_notifier` du repo v5 (le bot local **importe du code v5** et charge le `.env` de `C:\PTM\assistant-gazelle-v5`).
4. **Mise à jour de `alerts_history.json`** : ajoute les `EntryId` traités + `last_run`.

### Config / seuils (`config.json`, sans secrets)
- `database.server = PIANOTEK\SQLEXPRESS`, `database.name = PianoTek`
- `monitoring.days_back = 1`, `monitoring.clients = []` (**tous les clients** — la liste UQAM / Pierre-Péladeau / Vincent-d'Indy / Place des Arts du README n'est **pas** appliquée)
- `slack.webhooks` : Louise ✅, Nicolas ✅, Allan (placeholder), Jean-Philippe (placeholder) → **[webhooks Slack configurés, non reproduits ici]**
- `alert_keywords` / `resolution_keywords` : familles `housse` et `alimentation` (voir ci-dessus)
- Secrets (`OPENAI_API_KEY`, tokens Supabase/Gmail) : chargés depuis des `.env`, **non présents dans ce document**.

---

## 5. Chevauchement / doublons

Le nuage **reproduit déjà l'essentiel** du bot local, mais **pas à 100 %** et avec de la **dette technique**.

### Ce que le cloud couvre (identique)
- Même logique de détection (mots-clés `housse` / `alimentation`, + `reservoir` et `environnement` en plus côté cloud) portée dans `modules/alerts/humidity_scanner.py` (`detect_issue`, `analyze_with_ai`).
- Même anti-doublon (table `humidity_alerts_history`), même principe « notifier seulement les non résolues ».
- Mêmes destinataires : Slack (Louise + Nicolas) + courriel à `nlessard@piano-tek.com`.
- **En plus** : carte de tableau de bord front-end, stockage Supabase, filtre « mesure normale » (ex. `21C, 39%` ignoré).

### Ce que seul le bot local fait
- Surveille **tous les clients** (le cloud se limite à **Vincent d'Indy, Place des Arts, Orford**).
- Écrit dans la table SQL locale **`MaintenanceAlerts`** et génère le **rapport Google Sheet**.
- Alimente le **SQL Server local** (via le pipeline Genosa) — dont dépendent aussi les autres rapports Excel/Timeline du PC.

### ⚠️ Incohérences / dette repérées dans le code cloud (à connaître avant de décider)
1. **Trois scanners cloud coexistent** : `HumidityScanner` (utilisé par GitHub Actions ✅), `HumidityScannerSafe` (utilisé par l'endpoint manuel `POST /scan`), et les fonctions de `core/humidity_alert_detector.py` (patterns regex `dampp_chaser`, `high/low_humidity`… **apparemment câblées à rien**). Plus un port `modules/humidity-alerts/humidity_alert_system_MAC.py`.
2. **Job Render cassé** : `api/humidity_alerts_routes.py` (`_run_daily_scan`, cron 16h) importe `from modules.alerts.humidity_scanner import HumidityAlertScanner` — **cette classe n'existe pas** (le fichier définit `HumidityScanner`). Ce job planifié lève donc une `ImportError` à l'exécution. Le scan cloud qui **fonctionne réellement** est celui de **GitHub Actions** (9h Montréal).
3. **IA effectivement désactivée dans le nuage** : `humidity_scanner.py` → `analyze_with_ai` exige `ANTHROPIC_API_KEY`, mais le workflow `humidity_alerts_scanner.yml` ne fournit que `OPENAI_API_KEY`. Le scan cloud tourne donc **en mots-clés seulement** (pas de fallback IA). Le bot local, lui, a bien son IA OpenAI.
4. **Le scheduler principal `core/scheduler.py` ne contient AUCUN job d'humidité** — la planification cloud repose uniquement sur GitHub Actions.

➡️ **Conclusion §5** : ~80 % du bot local est déjà dupliqué dans le nuage, mais la version cloud (a) ne couvre que 3 institutions, (b) n'écrit pas dans `MaintenanceAlerts`/Google Sheet, (c) tourne sans IA, et (d) traîne du code mort/cassé.

---

## 6. Les 3 options d'avenir

### (a) 🗑️ Retirer le bot local
**Effort : très faible (~30 min).** Désactiver la tâche Windows / retirer l'étape humidité de `update.bat`.
**Ce qu'on perd exactement :**
- La surveillance humidité des **clients non-institutionnels** (le cloud ne couvre que Vincent d'Indy, PDA, Orford).
- La table `MaintenanceAlerts` (SQL local) et le **rapport Google Sheet** associé.
- Le fallback **IA OpenAI** (le cloud n'a pas d'IA active).

⚠️ Attention : `update.bat` sert **aussi** à alimenter le SQL Server local pour d'autres rapports. Retirer *seulement* l'étape humidité (étape 4) n'arrête pas le pipeline ; retirer *tout* le PC est une décision plus large.

### (b) ☁️ Réécrire proprement dans le nuage
**Effort : faible à moyen (½ à 1 journée).** L'infrastructure existe déjà. À faire :
1. **Élargir le périmètre** : enlever le filtre institutionnel dans `humidity_scanner.py` (ou le rendre configurable) si on veut couvrir tous les clients comme le local.
2. **Réactiver l'IA** : ajouter `ANTHROPIC_API_KEY` (ou basculer sur OpenAI) dans les secrets du workflow GitHub Actions.
3. **Nettoyer la dette** : supprimer le job Render cassé (`HumidityAlertScanner`), choisir **un seul** scanner, retirer le port MAC et `humidity_alert_detector.py` s'ils sont morts.
4. (Optionnel) Remplacer le rapport Google Sheet par la carte tableau de bord déjà existante.

→ Aucune dépendance PC ; tout tourne sur GitHub Actions + Supabase + Resend/Gmail.

### (c) 🤝 Laisser tel quel
**Effort : nul.** **Risque : le cordon PC demeure.** Si le PC est éteint / en panne : plus de mise à jour du SQL local et plus de surveillance des clients non-institutionnels. C'est exactement la dépendance qu'Allan veut éliminer.

### Recommandation
Allan indique que la fonctionnalité **« n'est pas vraiment appréciée / pas importante »**. Dans ce cas, **option (a) — retirer le bot local** est le choix le plus rapide et cohérent, **à condition d'accepter** que seules les 3 institutions restent surveillées (par le nuage).

**Nuance de protection piano** : les institutions (Steinway/Yamaha de concert à Vincent d'Indy, Place des Arts, Orford) sont les pianos où un PLS débranché coûte le plus cher — et ils restent couverts par le nuage. Le vrai « trou » créé par le retrait, ce sont les clients privés/commerciaux, où l'enjeu humidité est généralement moindre. Si un jour on juge cette couverture utile, l'**option (b)** est peu coûteuse car 80 % existe déjà.

---

## 7. Verdict (une ligne)

**Couper le cordon = ~30 min pour retirer le bot local (option a), en gardant la couverture des 3 institutions déjà assurée par GitHub Actions ; si on tient à couvrir tous les clients, ~½–1 journée pour finir/nettoyer la version cloud (option b). Vu le peu de valeur perçue, retirer le bot local est la voie recommandée.**

---

*Sources : `C:\Allan Python projets\humidity_alerts\*` (bot local), `C:\Genosa\Working\update.bat` + `Import_daily_update.py` (pipeline d'alimentation SQL), `modules/alerts/humidity_scanner.py`, `modules/alerts/humidity_scanner_safe.py`, `core/humidity_alert_detector.py`, `api/humidity_alerts_routes.py`, `core/scheduler.py`, `.github/workflows/humidity_alerts_scanner.yml`. Aucun secret (webhooks, clés API) reproduit.*
