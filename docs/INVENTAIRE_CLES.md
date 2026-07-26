# 🔐 Inventaire des secrets — où ils vivent, parité nuage, actions

> **But** : cartographier chaque secret/clé/token du système PTM — **où il vit**, s'il est
> **déjà dans le nuage** (indépendant du PC), et quelle **action** reste. Pour un futur
> « tout nuage » sans le PC d'Allan, chaque secret utilisé par du code nuage DOIT exister
> dans un coffre nuage (GitHub Secrets, Render, ou Supabase `system_settings`).
>
> ⚠️ **Règle absolue (constitution)** : un secret ne va **JAMAIS** dans git. Ce document ne
> contient que des **noms** de secrets, jamais leurs valeurs.
>
> **Dernière mise à jour :** 2026-07-26

---

## Les 4 coffres (+ 1 risque legacy)

| Coffre | Rôle | Voir les valeurs ? |
|---|---|---|
| **GitHub Secrets** | Secrets des workflows GitHub Actions (chiffrés) | Non (chiffrés) — noms visibles dans `.github/workflows/` |
| **Render** (env vars) | Backend `assistant-gazelle-v5-api` | Dashboard Render seulement |
| **Supabase `system_settings`** | Tokens runtime (OAuth, clés partagées) | Table Supabase (service role) |
| **`.env` local** | Copie de travail pour dev + tâches locales (gitignoré) | Fichier local |
| 🔴 **Code legacy local** | Secrets **codés en dur** dans C:\Genosa, bot humidité | Dans le code (à retirer) |

---

## Inventaire par secret

| Secret | Utilisé par | Vit dans | Parité nuage | Action |
|---|---|---|---|---|
| `SUPABASE_URL` / `SUPABASE_SERVICE_ROLE_KEY` | tout | GitHub Secrets + Render + .env | ✅ nuage | — |
| `SUPABASE_DB_PASSWORD` | connexion DB directe | .env | ⚠️ à vérifier dans Render | vérifier Render |
| `GAZELLE_CLIENT_ID` / `GAZELLE_CLIENT_SECRET` | sync Gazelle | GitHub Secrets ; tokens dans `system_settings` (`gazelle_oauth_token`) | ✅ nuage | rotation (voir legacy) |
| `OPENAI_API_KEY` | humidité (workflow) | GitHub Secrets | ✅ nuage | — |
| `ANTHROPIC_API_KEY` | scan IA / assistant | .env | ⚠️ à vérifier dans Render | vérifier Render |
| `RESEND_API_KEY` | courriel (fallback, **inactif**) | GitHub Secrets | ✅ nuage | — |
| `GOOGLE_SERVICE_ACCOUNT_JSON` / `GOOGLE_SHEETS_JSON` | Google Sheets/Drive | GitHub Secrets + `system_settings` | ✅ nuage | — |
| `GMAIL_TOKEN_JSON` / `gmail_oauth_token` | envoi Gmail (principal) | `system_settings` | ✅ nuage | — |
| `google_maps_api_key` | distances | `system_settings` | ✅ nuage | — |
| `CLICKUP_API_TOKEN` / `FRONT_API_TOKEN` | intégrations | `system_settings` | ✅ nuage | — |
| `PLANE_API_KEY` | `place_des_arts/email_processor.py` (nuage) | .env | ⚠️ à vérifier dans Render | vérifier Render |
| `ZOOM_SECRET_TOKEN` | `api/main.py`, `core/zoom_sms.py` (nuage) | .env | ⚠️ à vérifier dans Render | vérifier Render |
| `BRIEFING_SLACK_WEBHOOK_ALLAN` + webhooks Slack | briefings/alertes | GitHub Secrets / .env | ✅ (Allan) / ⚠️ autres à confirmer | vérifier Render |

---

## Le seul angle mort : Render

Je (Claude) **ne peux pas voir les variables d'env de Render** depuis le code. Mais le
backend tourne 24/7 en prod → il **a forcément** les secrets dont son code a besoin. La
vérification définitive de parité (est-ce que Render a bien Anthropic / Plane / Zoom /
DB password ?) se fait en **30 s dans le dashboard Render** : Settings → Environment.

**À vérifier dans Render (4)** : `ANTHROPIC_API_KEY`, `PLANE_API_KEY`, `ZOOM_SECRET_TOKEN`,
`SUPABASE_DB_PASSWORD`. Si présents → parité complète, `.env` = simple copie locale.

---

## 🔴 Le vrai risque PC-only : secrets en dur dans le code legacy

Ces secrets sont **écrits en clair dans du code** sur le PC (pas dans un coffre) :
- `C:\Genosa\Working\Import_daily_update.py` — **Gazelle Client ID + Secret** en dur.
- Bot humidité (`C:\Allan Python projets\humidity_alerts\...`) — **clé OpenAI** en dur.

Ils alimentent le **système local qu'on décommissionne** (SQL Server, bot humidité). Donc
l'action n'est **pas** de les migrer, mais :
1. **Décommissionner** le système local (voir `transferabilite-plan.md`).
2. **Rotation** de ces secrets ensuite (les régénérer côté Gazelle/OpenAI), pour que les
   copies en clair qui traînent deviennent inutiles.

---

## Où ajouter un nouveau secret (pour la relève)

| Cas | Où le mettre |
|---|---|
| Utilisé par un workflow GitHub Actions | **GitHub Secrets** (repo → Settings → Secrets) |
| Utilisé par le backend Render | **Render** → Settings → Environment |
| Token runtime partagé (OAuth, clé lue par le code à l'exécution) | **Supabase `system_settings`** |
| Environnement de dev nuage (Claude Code on the web) | **Environment variables** de l'environnement |
| **Jamais** | ❌ dans git / dans le code |

Lié : `transferabilite-plan.md` (Zone C — comptes & clés), `reference-github-auth`.
