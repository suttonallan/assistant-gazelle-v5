# PTM - Piano Tek Musique

## Protocole de session

**Au demarrage de chaque session, TOUJOURS lire ces fichiers avant de commencer quoi que ce soit :**
1. `C:\PTM\progress.md` — ou on en est
2. `C:\PTM\todo.md` — quoi faire ensuite
3. `C:\PTM\decisions.md` — decisions prises, ne pas les remettre en question sauf demande explicite
4. La section **« Sous-projets PTM »** plus bas dans ce fichier — vue d'ensemble des projets actifs avec leur statut

**Si Allan dit « ouvre `xxx-plan.md` »** → c'est sa façon de dire « on travaille sur ce sous-projet maintenant ». Lis le plan file en entier, focus dessus, ignore les autres sous-projets sauf si Allan demande. L'en-tête de chaque plan file contient `Statut`, `Dernière mise à jour`, `Prochain pas` et `Bloqué par` — c'est ta source de vérité pour reprendre instantanément.

**A la fin de chaque session, TOUJOURS mettre a jour :**
1. `C:\PTM\progress.md` — ajouter ce qui a ete accompli aujourd'hui
2. `C:\PTM\todo.md` — mettre a jour les priorites, cocher ce qui est fait
3. `C:\PTM\decisions.md` — ajouter toute nouvelle decision technique prise pendant la session
4. **Si on a travaille sur un sous-projet** : mettre a jour son `xxx-plan.md` (champs `Statut`, `Dernière mise à jour`, `Prochain pas`, `Bloqué par`) ET mettre a jour la section « Sous-projets PTM » de ce fichier si le statut a change

## Sous-projets PTM

Allan travaille en parallele sur plusieurs initiatives. Chaque sous-projet a son propre plan file a la racine de C:\PTM. La discipline : **un sous-projet = un plan file = une discussion focalisee** (mais Allan peut switcher entre conversations Claude Code en pointant vers un autre plan file).

| Sous-projet | Plan file | Statut | Prochain pas |
|---|---|---|---|
| Refonte soumissions Gazelle | `soumissions-plan.md` | 🟢 actif | Phase 3 — digest 8h info@ pour soumissions sans relance + tag `relance-faite` |
| Digest fiches d'accord à pousser | `digest-accords-plan.md` | 🟢 actif | Live dry-run puis commit + push pour activer le cron 17h + livrer la simplification workflow (retrait bouton Terminé + Nettoyer anciens + fix filtre Tout valider) |
| Amélioration checklists bundles | `bundles-checklists-plan.md` | 🟡 en attente | Session collaborative avec Nicolas pour valider les actions par défaut |
| Analytics des soumissions | `soumissions-analytics-plan.md` | 🟡 en attente | Attendre que la phase 3 du sous-projet soumissions soit déployée et adoptée 2 semaines |
| Marketing autonome | `marketing-plan.md` | 🟢 actif | Veille quotidienne + newsletter Mailchimp + blog + rappels hebdo |
| AEC Saint-Laurent | _(drive partagé)_ | 🟢 actif | Entrevue chargé de cours réglage — 3 docs préparés dans drive AEC |
| QRS PNOmation | _(drive partagé)_ | 🟢 actif | Soumission Yamaha C5 — 3 options Touch/NV/OT, contact Lori chez QRS |
| Compagnon d'entreprise | `compagnon-entreprise-plan.md` | 🟢 actif | Phase 0 — Inventaire des connaissances PTM + architecture du Cerveau |
| Connexion QuickBooks Online | `quickbooks-plan.md` | 🟡 en attente | Phase 0 — Allan crée l'app sur developer.intuit.com (credentials sandbox + prod + Realm ID) |
| Refonte status pianos (3 systèmes co-existants) | `refonte-status-pianos-plan.md` | 🟡 en attente | Phase 0 — audit complet des lecteurs/écrivains de `vincent_dindy_piano_updates.status` |
| Adoption ClickUp par l'équipe | `adoption-clickup-plan.md` | 🟢 actif | Phase 0 — inviter Margot+Louise, préparer 3-5 tâches concrètes par personne, vues personnalisées |

**Convention de statut :** 🟢 actif · 🟡 en pause / en attente · ✅ complété · ❌ abandonné

**Quand un nouveau sous-projet émerge** : créer un fichier `nom-du-projet-plan.md` à la racine de `C:\PTM\` avec l'en-tête standardisé (Statut/Créé/Dernière maj/Prochain pas/Bloqué par), puis ajouter une ligne dans le tableau ci-dessus. Quand il est complété : le marquer ✅, ne pas le supprimer du tableau (garde l'historique des projets accomplis visible).

## Contexte
PTM (Piano Tek Musique) est un projet d'entreprise de vente/location de pianos avec une stack technologique moderne. Proprietaire : Allan Sutton (suttonallan@gmail.com).

## Repos et architecture

| Repo | Role | Stack |
|------|------|-------|
| `assistant-gazelle-v5` | Assistant IA client (chatbot) | Node.js / OpenAI |
| `assistant-v6` | Nouvelle version de l'assistant | En developpement |
| `ptm-chat` | Interface chat frontend | React / Next.js |
| `ptm-chat-api` | API backend du chat | Node.js / Express |
| `piano-tek-ai` | IA et logique metier piano | Python / AI |
| `ptm-quiz` | Quiz interactif pour clients | Web app |

## Conventions de travail
- **Langue** : Code et commits en anglais, communication avec Allan en francais
- **Git** : Commit messages descriptifs, push sur main sauf branche specifique demandee
- **Autonomie** : Travailler en autonomie maximale, prendre des decisions techniques, demander confirmation uniquement pour les changements majeurs d'architecture
- **Tests** : Tester localement avant push quand possible
- **Style** : Code propre, pas de commentaires inutiles, DRY
- **Fichiers de suivi** : Ne jamais supprimer d'entrees dans progress.md ou decisions.md, seulement ajouter

## Structure locale
```
C:\PTM\
├── CLAUDE.md          <- ce fichier (contexte permanent)
├── progress.md        <- journal de travail
├── decisions.md       <- decisions techniques
├── todo.md            <- taches prioritaires
├── assistant-gazelle-v5/
├── assistant-v6/
├── ptm-chat/
├── ptm-chat-api/
├── piano-tek-ai/
└── ptm-quiz/
```

## Commandes utiles
- `gh repo list suttonallan` - Lister les repos
- `gh auth status` - Verifier l'auth GitHub

## Editer un Google Sheet PTM
**TOUJOURS** utiliser `C:\PTM\tools\gsheet.py` (service account, edition directe via API Sheets).
JAMAIS le MCP google-drive (token OAuth perime), jamais via xlsx intermediaire.
Voir memory `reference_gsheet_helper.md` pour le pattern complet.

## Editer un Google Doc PTM
Voir `.claude/skills/gazelle/workflows/edit_google_doc.md` (export HTML / re-upload via Drive API).
JAMAIS le MCP google-drive pour les Docs.

## Infrastructure / Watchdog

Garde le serveur `claude remote-control` en vie 24/7 pour l'acces iPhone aux agents.

**Architecture v2 (2026-05-30) — Scheduled Task + Python/psutil :**
- `C:\PTM\watchdog\watchdog.py` — script one-shot Python (psutil, pas de WMI)
- `C:\PTM\watchdog\test-kill.ps1` — test detache (kill + verifier relance)
- Tache planifiee Windows : `PTM-RemoteControlWatchdog` (toutes les 2 min, sous sutto en S4U)
- Keepalive reseau : HEAD vers api.anthropic.com toutes les 5 min (garde NAT/routeur chaud)
- Power/registre : `monitor/standby/disk/hibernate-timeout` AC+DC a 0, `HKLM\...\Policies\System\InactivityTimeoutSecs` = 0

**Pourquoi v2 :** WMI/CIM est casse sur cette machine (OutOfMemoryException depuis mai 2026). `Get-CimInstance` echoue systematiquement. La v2 utilise `psutil` pour detecter les process (lit le PEB directement, zero dependance WMI). Tourne sous le compte utilisateur via Scheduled Task (pas un service SYSTEM).

**Comment le watchdog spawn :** quand claude.exe remote-control est absent, lance
`powershell -NoExit -Command "cd C:\PTM; claude remote-control --spawn worktree --capacity 32"`.
Cooldown anti-flapping : pas de respawn si dernier respawn < 5 min (raison : chaque spawn cree une nouvelle environment cote Anthropic = nouveau suffix iPhone, on ne veut pas spammer).

**Verifier que ca tourne :**
```powershell
schtasks /Query /TN "PTM-RemoteControlWatchdog"
Get-Content C:\PTM\watchdog\watchdog.log -Tail 20
python -c "import psutil; [print(f'PID={p.pid} CMD={p.cmdline()}') for p in psutil.process_iter(['pid','name','cmdline']) if p.info['name'] and 'claude' in p.info['name'].lower()]"
```

**Retester la relance auto :**
```powershell
Start-Process powershell -ArgumentList "-ExecutionPolicy","Bypass","-WindowStyle","Hidden","-File","C:\PTM\watchdog\test-kill.ps1"
# Attendre ~4 min puis :
Get-Content C:\PTM\watchdog\test-result.log
```

**Anciens fichiers archives (ne pas supprimer) :**
- `C:\PTM\watchdog\watchdog.ps1.bak` — ancien watchdog PowerShell one-shot (v1, WMI)
- `C:\PTM\watchdog\watchdog_service.py` — tentative service Windows (abandonnee, SYSTEM ne peut pas spawner dans la session user)
- `C:\PTM\watchdog\install-watchdog.ps1` — ancien installateur Scheduled Task (v1)
- `C:\PTM\scripts\claude-remote-watchdog.ps1.bak` — ancien watchdog boucle infinie via Startup
- `C:\PTM\scripts\claude-remote-watchdog.vbs.bak` — ancien lanceur invisible
- `...\Startup\claude-remote-control.bat.bak` — ancien declencheur Startup (desactive)

**Limitation connue v2 :** detecte la presence du process, pas sa sante (un process hung passe inapercu). Si l'iPhone reste sans reponse alors que le process tourne, killer manuellement et laisser le watchdog respawn.
