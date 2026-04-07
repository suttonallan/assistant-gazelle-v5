#!/usr/bin/env python3
"""
API Routes pour les Briefings Intelligents - "Ma Journée" V4

Endpoints:
- GET /briefing/daily - Briefings narratifs du jour
- GET /briefing/client/{id} - Briefing détaillé d'un client
- POST /briefing/feedback - Sauvegarder une correction (Allan only)
- POST /briefing/follow-up/resolve - Marquer un follow-up résolu
- POST /briefing/warm-cache - Pré-charger le cache
- GET /briefing/search-clients - Recherche rapide de clients (autocomplete)
"""

import sys
from pathlib import Path
from datetime import datetime
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import List, Optional, Dict, Any

sys.path.insert(0, str(Path(__file__).parent.parent))

from modules.briefing.client_intelligence_service import (
    NarrativeBriefingService,
    save_feedback
)

router = APIRouter(prefix="/briefing", tags=["briefing"])


# ═══════════════════════════════════════════════════════════════════════
# MODÈLES
# ═══════════════════════════════════════════════════════════════════════

class FeedbackRequest(BaseModel):
    """Requête pour sauvegarder une note libre sur un client"""
    client_id: str
    note: str
    created_by: str = "asutton@piano-tek.com"


class AnalyzeFeedbackRequest(BaseModel):
    """Requête pour analyser un commentaire et suggérer des actions"""
    client_id: str
    client_name: str = ""
    note: str
    narrative: str = ""


class ApplyActionsRequest(BaseModel):
    """Requête pour appliquer les actions approuvées par Allan"""
    actions: List[Dict[str, Any]]
    created_by: str = "asutton@piano-tek.com"


class ResolveFollowUpRequest(BaseModel):
    """Requête pour marquer un follow-up comme résolu"""
    item_id: str
    resolved_by: Optional[str] = None
    resolution_note: Optional[str] = None


# ═══════════════════════════════════════════════════════════════════════
# ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════

@router.get("/health")
async def health_check():
    """Health check"""
    return {"status": "ok", "service": "briefing-v4"}


@router.post("/warm-cache", response_model=Dict[str, Any])
async def warm_cache():
    """
    Pré-charge le cache des briefings pour aujourd'hui et demain.
    Appelé automatiquement après chaque sync, ou manuellement.
    """
    try:
        from modules.briefing.briefing_cache import warm_briefing_cache_async
        stats = await warm_briefing_cache_async()
        return {
            "success": True,
            "message": "Cache pré-chargé",
            "stats": stats
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/daily", response_model=Dict[str, Any])
async def get_daily_briefings(
    technician_id: Optional[str] = Query(None, description="ID du technicien"),
    exclude_technician_id: Optional[str] = Query(None, description="Exclure ce technicien"),
    date: Optional[str] = Query(None, description="Date YYYY-MM-DD (défaut: aujourd'hui)"),
    skip_cache: bool = Query(False, description="Forcer le recalcul (ignorer le cache)")
):
    """
    Récupère les briefings narratifs pour les RV du jour.

    V4: Chaque briefing contient un paragraphe narratif généré par IA
    + des flags computés en Python (PLS, langue, piano).
    """
    target_date = date or datetime.now().strftime('%Y-%m-%d')

    try:
        briefings = None
        from_cache = False

        # Essayer le cache d'abord (sauf si skip_cache ou filtre technicien)
        if not skip_cache and not technician_id and not exclude_technician_id:
            try:
                from modules.briefing.briefing_cache import BriefingCache
                cache = BriefingCache()
                briefings = cache.get_cached_briefings(target_date)
                if briefings:
                    from_cache = True
                    print(f"⚡ Briefings servis depuis le cache ({len(briefings)})")
            except Exception as cache_err:
                print(f"⚠️ Cache non disponible: {cache_err}")

        # Fallback: générer à la demande (async!)
        if briefings is None:
            service = NarrativeBriefingService()
            briefings = await service.get_daily_briefings(
                technician_id=technician_id,
                exclude_technician_id=exclude_technician_id,
                target_date=target_date
            )

        # Filtrer par technicien si demandé (même avec cache)
        if from_cache and technician_id:
            briefings = [b for b in briefings
                        if b.get('appointment', {}).get('technician_id') == technician_id]
        elif from_cache and exclude_technician_id:
            briefings = [b for b in briefings
                        if b.get('appointment', {}).get('technician_id') != exclude_technician_id]

        return {
            "date": target_date,
            "technician_id": technician_id,
            "count": len(briefings),
            "from_cache": from_cache,
            "briefings": briefings,
        }

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/search-clients", response_model=Dict[str, Any])
async def search_clients(
    q: str = Query(..., min_length=2, description="Terme de recherche (min 2 caractères)"),
    limit: int = Query(10, ge=1, le=50, description="Nombre max de résultats")
):
    """
    Recherche rapide de clients par nom/compagnie.
    Utilisé par le panneau d'accès client (Louise).
    """
    try:
        from core.supabase_storage import SupabaseStorage
        import requests as http_requests

        storage = SupabaseStorage()
        headers = storage._get_headers()
        search_pattern = f"*{q.strip()}*"

        all_results = []
        seen_ids = set()

        for field in ['company_name', 'name', 'full_name']:
            try:
                url = (
                    f"{storage.api_url}/gazelle_clients"
                    f"?select=external_id,name,company_name,full_name,email,phone,city"
                    f"&{field}=ilike.{search_pattern}"
                    f"&limit={limit}"
                )
                resp = http_requests.get(url, headers=headers)
                if resp.status_code == 200:
                    for client in resp.json():
                        cid = client.get('external_id')
                        if cid and cid not in seen_ids:
                            all_results.append({
                                "client_id": cid,
                                "name": client.get('company_name') or client.get('full_name') or client.get('name') or '',
                                "phone": client.get('phone') or '',
                                "email": client.get('email') or '',
                                "city": client.get('city') or '',
                            })
                            seen_ids.add(cid)
            except Exception:
                pass

        return {
            "query": q,
            "count": len(all_results[:limit]),
            "results": all_results[:limit]
        }

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/client/{client_id}", response_model=Dict[str, Any])
async def get_client_briefing(client_id: str):
    """
    Génère un briefing narratif pour un client spécifique.
    """
    try:
        service = NarrativeBriefingService()
        briefing = await service.generate_single_briefing(client_id)

        if "error" in briefing:
            raise HTTPException(status_code=404, detail=briefing["error"])

        return briefing

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/feedback", response_model=Dict[str, Any])
async def list_feedback(
    client_id: Optional[str] = Query(None, description="Filtrer par client (None = tous)"),
    include_global: bool = Query(True, description="Inclure les règles globales")
):
    """
    Liste toutes les notes/corrections d'Allan.
    """
    try:
        from core.supabase_storage import SupabaseStorage
        import requests as http_requests

        storage = SupabaseStorage(silent=True)
        headers = storage._get_headers()

        url = f"{storage.api_url}/ai_training_feedback?is_active=eq.true&order=created_at.desc"
        if client_id:
            if include_global:
                url += f"&client_external_id=in.({client_id},__GLOBAL__)"
            else:
                url += f"&client_external_id=eq.{client_id}"

        resp = http_requests.get(url, headers=headers)
        if resp.status_code != 200:
            raise HTTPException(status_code=500, detail=f"Erreur Supabase: {resp.text}")

        data = resp.json()
        global_notes = [d for d in data if d.get('client_external_id') == '__GLOBAL__']
        client_notes = [d for d in data if d.get('client_external_id') != '__GLOBAL__']

        return {
            "count": len(data),
            "global_rules": [{
                "id": n["id"],
                "note": n.get("corrected_value", ""),
                "created_at": n.get("created_at", ""),
            } for n in global_notes],
            "client_notes": [{
                "id": n["id"],
                "client_id": n.get("client_external_id", ""),
                "note": n.get("corrected_value", ""),
                "created_at": n.get("created_at", ""),
            } for n in client_notes],
        }

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/feedback", response_model=Dict[str, Any])
async def submit_feedback(request: FeedbackRequest):
    """
    Sauvegarde une correction de briefing.
    ⚠️ SUPER-UTILISATEUR SEULEMENT (Allan)

    Pour une règle globale (tous les clients), envoyer client_id="__GLOBAL__"
    """
    if request.created_by != "asutton@piano-tek.com":
        raise HTTPException(
            status_code=403,
            detail="Seul asutton@piano-tek.com peut soumettre des corrections"
        )

    try:
        success = save_feedback(
            client_id=request.client_id,
            category='general',
            field_name='note_libre',
            original_value="",
            corrected_value=request.note,
            created_by=request.created_by
        )

        if success:
            return {
                "success": True,
                "message": "Note enregistrée",
                "client_id": request.client_id
            }
        else:
            raise HTTPException(status_code=500, detail="Erreur sauvegarde")

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/feedback/analyze", response_model=Dict[str, Any])
async def analyze_feedback(request: AnalyzeFeedbackRequest):
    """
    Analyse un commentaire d'Allan et suggère des actions concrètes.
    Retourne des suggestions client-spécifiques ET globales.
    """
    try:
        import os
        try:
            from anthropic import Anthropic
        except ImportError:
            raise HTTPException(status_code=500, detail="Anthropic SDK non disponible")

        api_key = os.getenv('ANTHROPIC_API_KEY')
        if not api_key:
            from core.supabase_storage import SupabaseStorage
            storage = SupabaseStorage(silent=True)
            try:
                settings = storage.get_data('system_settings', filters={'key': 'anthropic_api_key'})
                if settings and settings[0].get('value'):
                    api_key = settings[0]['value']
            except Exception:
                pass

        if not api_key:
            raise HTTPException(status_code=500, detail="Clé Anthropic non configurée")

        client = Anthropic(api_key=api_key)

        prompt = f"""Allan est le propriétaire de Piano Tek Musique, un service d'accordage et d'entretien de pianos à Montréal.
Il vient de lire le briefing quotidien généré par l'IA pour un technicien, et il a écrit ce commentaire pour corriger ou améliorer l'intelligence du système.

CLIENT CONCERNÉ: {request.client_name or request.client_id}
BRIEFING QUI A ÉTÉ GÉNÉRÉ: {request.narrative or '(non fourni)'}
COMMENTAIRE D'ALLAN: {request.note}

Analyse ce commentaire et propose des actions concrètes. Pour chaque action, indique:
- "scope": "client" (s'applique uniquement à ce client) ou "global" (s'applique à tous les futurs briefings de tous les clients)
- "note": la règle ou correction à enregistrer, formulée clairement pour que l'IA la comprenne aux prochaines générations
- "reason": explication courte de pourquoi cette action est pertinente

Retourne UNIQUEMENT ce JSON (pas de markdown):
{{
  "actions": [
    {{
      "scope": "client" ou "global",
      "note": "la règle à enregistrer",
      "reason": "pourquoi"
    }}
  ]
}}

IMPORTANT:
- Propose 1 à 3 actions maximum, seulement celles qui sont pertinentes
- Une action "client" corrige un fait spécifique à ce client
- Une action "global" améliore le comportement de l'IA pour TOUS les clients (ex: ne pas déduire X à partir de Y, toujours vérifier Z avant d'affirmer)
- Ne propose une action "global" QUE si le commentaire révèle un problème systémique, pas juste une erreur ponctuelle
- Formule les notes de façon actionable pour une IA qui génère des briefings"""

        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=500,
            temperature=0.1,
            messages=[{"role": "user", "content": prompt}],
        )

        import re, json
        raw = response.content[0].text.strip()
        if raw.startswith("```"):
            raw = re.sub(r'^```(?:json)?\s*', '', raw)
            raw = re.sub(r'\s*```$', '', raw)

        result = json.loads(raw)
        actions = result.get('actions', [])

        for action in actions:
            action['client_id'] = request.client_id if action.get('scope') == 'client' else '__GLOBAL__'
            action['client_name'] = request.client_name if action.get('scope') == 'client' else 'Tous les clients'

        return {
            "success": True,
            "original_note": request.note,
            "suggested_actions": actions,
        }

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/feedback/apply", response_model=Dict[str, Any])
async def apply_actions(request: ApplyActionsRequest):
    """
    Sauvegarde les actions approuvées par Allan (client-spécifiques et/ou globales).
    """
    if request.created_by != "asutton@piano-tek.com":
        raise HTTPException(status_code=403, detail="Réservé à Allan")

    saved = []
    errors = []
    for action in request.actions:
        client_id = action.get('client_id', '')
        note = action.get('note', '')
        if not client_id or not note:
            continue
        success = save_feedback(
            client_id=client_id,
            category='general',
            field_name='note_libre',
            original_value=action.get('reason', ''),
            corrected_value=note,
            created_by=request.created_by,
        )
        if success:
            saved.append({"client_id": client_id, "note": note})
        else:
            errors.append({"client_id": client_id, "note": note, "error": "Échec sauvegarde"})

    return {
        "success": len(errors) == 0,
        "saved": saved,
        "errors": errors,
        "message": f"{len(saved)} action(s) enregistrée(s)",
    }


@router.delete("/feedback/{feedback_id}", response_model=Dict[str, Any])
async def delete_feedback(feedback_id: str):
    """
    Désactive une note/correction (soft delete).
    """
    try:
        from core.supabase_storage import SupabaseStorage
        import requests as http_requests

        storage = SupabaseStorage(silent=True)
        headers = storage._get_headers()

        url = f"{storage.api_url}/ai_training_feedback?id=eq.{feedback_id}"
        resp = http_requests.patch(url, json={"is_active": False}, headers=headers)
        if resp.status_code in (200, 204):
            return {"success": True, "message": "Note désactivée"}
        else:
            raise HTTPException(status_code=500, detail=f"Erreur: {resp.text}")

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/admin/migrate", response_model=Dict[str, Any])
async def run_migration(request: Dict[str, Any]):
    """
    Exécute une migration SQL via la connexion directe PostgreSQL de Supabase.
    Temporaire — à retirer après usage.
    """
    secret = request.get("secret", "")
    sql = request.get("sql", "")

    if secret != "ptm-migrate-2026":
        raise HTTPException(status_code=403, detail="Accès refusé")
    if not sql.strip():
        raise HTTPException(status_code=400, detail="SQL vide")

    try:
        import os
        supabase_url = os.getenv('SUPABASE_URL', '')
        service_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY', '')

        if not service_key:
            raise HTTPException(status_code=500, detail="SERVICE_ROLE_KEY non disponible")

        from supabase import create_client
        client = create_client(supabase_url, service_key)

        # Execute each statement via Supabase's rpc
        statements = [s.strip() for s in sql.split(';') if s.strip() and not s.strip().startswith('--')]
        results = []

        for stmt in statements:
            try:
                res = client.rpc('exec_sql', {'sql_query': stmt}).execute()
                results.append({"sql": stmt[:100], "status": "ok"})
            except Exception as e:
                results.append({"sql": stmt[:100], "error": str(e)})

        return {"results": results, "note": "Si exec_sql n'existe pas, exécutez d'abord le bootstrap"}

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/admin/bootstrap-sql", response_model=Dict[str, Any])
async def bootstrap_sql_runner(request: Dict[str, Any]):
    """
    Crée la fonction exec_sql dans PostgreSQL via le endpoint Supabase pg-meta.
    """
    secret = request.get("secret", "")
    if secret != "ptm-migrate-2026":
        raise HTTPException(status_code=403, detail="Accès refusé")

    try:
        import os, requests as http_requests

        supabase_url = os.getenv('SUPABASE_URL', '')
        service_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY', '')

        if not service_key:
            raise HTTPException(status_code=500, detail="SERVICE_ROLE_KEY non disponible")

        # Supabase exposes a /pg endpoint for direct SQL (with service_role_key)
        headers = {
            "apikey": service_key,
            "Authorization": f"Bearer {service_key}",
            "Content-Type": "application/json",
            "x-connection-encrypted": "true",
        }

        create_fn_sql = """
        CREATE OR REPLACE FUNCTION exec_sql(sql_query text)
        RETURNS void
        LANGUAGE plpgsql
        SECURITY DEFINER
        AS $$
        BEGIN
            EXECUTE sql_query;
        END;
        $$;
        """

        # Try multiple Supabase SQL execution endpoints
        endpoints = [
            f"{supabase_url}/pg/query",
            f"{supabase_url}/rest/v1/rpc/exec_sql",
        ]

        for endpoint in endpoints:
            try:
                if 'rpc' in endpoint:
                    continue
                resp = http_requests.post(endpoint, headers=headers, json={"query": create_fn_sql})
                if resp.status_code in (200, 201, 204):
                    return {"success": True, "message": "Function exec_sql created", "endpoint": endpoint}
            except Exception:
                continue

        return {
            "success": False,
            "message": "Aucun endpoint SQL direct disponible. Allan doit exécuter ce SQL dans le dashboard Supabase",
            "sql_to_run": create_fn_sql.strip()
        }

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/introspect/{type_name}", response_model=Dict[str, Any])
async def introspect_gazelle_type(type_name: str):
    """
    Introspection temporaire — montre tous les champs disponibles sur un type Gazelle.
    Ex: /briefing/introspect/PrivateClient
    """
    try:
        from core.gazelle_api_client import GazelleAPIClient
        client = GazelleAPIClient()

        query = """
        query IntrospectType($typeName: String!) {
          __type(name: $typeName) {
            name
            kind
            description
            fields(includeDeprecated: true) {
              name
              description
              isDeprecated
              type {
                kind
                name
                ofType {
                  kind
                  name
                  ofType { kind, name, ofType { kind, name } }
                }
              }
            }
          }
        }
        """

        result = client._execute_query(query, variables={"typeName": type_name})
        type_info = result.get("data", {}).get("__type")

        if not type_info:
            raise HTTPException(status_code=404, detail=f"Type '{type_name}' non trouvé dans le schéma Gazelle")

        def format_type(t):
            if not t:
                return "?"
            kind = t.get("kind", "")
            name = t.get("name", "")
            of = t.get("ofType")
            if kind == "NON_NULL":
                return f"{format_type(of)}!"
            if kind == "LIST":
                return f"[{format_type(of)}]"
            return name or "?"

        fields = []
        for f in (type_info.get("fields") or []):
            fields.append({
                "name": f["name"],
                "type": format_type(f.get("type")),
                "description": f.get("description") or "",
                "deprecated": f.get("isDeprecated", False),
            })

        return {
            "type": type_info["name"],
            "kind": type_info.get("kind"),
            "description": type_info.get("description") or "",
            "field_count": len(fields),
            "fields": fields,
        }

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/admin/pda-compare", response_model=Dict[str, Any])
async def pda_compare(secret: str = Query("")):
    """Compare le matching PDA v5 (actuel) vs v6 (nouveau) sur toutes les demandes."""
    if secret != "ptm-migrate-2026":
        raise HTTPException(status_code=403, detail="Accès refusé")

    try:
        from core.supabase_storage import SupabaseStorage
        from modules.pda_v6_matcher import find_best_match, tech_name, REAL_TECHNICIAN_IDS
        from datetime import datetime, timedelta

        storage = SupabaseStorage(silent=True)
        PDA_CLIENT_ID = "cli_HbEwl9rN11pSuDEU"
        cutoff = (datetime.now() - timedelta(days=90)).strftime('%Y-%m-%d')

        # Charger demandes PDA
        all_requests = storage.client.table('place_des_arts_requests').select('*').order(
            'appointment_date', desc=True
        ).limit(100).execute().data or []

        # Charger RV Gazelle (client PDA + titre "Place des Arts")
        by_client = storage.client.table('gazelle_appointments').select('*').eq(
            'client_external_id', PDA_CLIENT_ID
        ).gte('appointment_date', cutoff).execute().data or []

        by_title = storage.client.table('gazelle_appointments').select('*').ilike(
            'title', '*Place des Arts*'
        ).gte('appointment_date', cutoff).execute().data or []

        seen = set()
        gazelle_apts = []
        for apt in by_client + by_title:
            eid = apt.get('external_id')
            if eid and eid not in seen:
                gazelle_apts.append(apt)
                seen.add(eid)

        apt_index = {a['external_id']: a for a in gazelle_apts if a.get('external_id')}

        # Comparer
        details = []
        agreements = 0
        divergences = []
        v6_only = []
        v5_only = []
        v5_matched = 0
        v6_matched = 0

        for req in all_requests:
            v5_apt_id = req.get('appointment_id')
            v5_apt = apt_index.get(v5_apt_id)
            v5_tech = req.get('technician_id')

            v6_match = find_best_match(req, gazelle_apts)
            v6_apt_id = v6_match.get('external_id') if v6_match else None
            v6_tech = v6_match.get('technicien') if v6_match else None
            v6_method = v6_match.get('_matched_by', 'direct') if v6_match else None

            if v5_apt_id: v5_matched += 1
            if v6_apt_id: v6_matched += 1

            same = v5_apt_id == v6_apt_id
            req_label = f"{str(req.get('appointment_date',''))[:10]} {req.get('for_who','')} ({req.get('room','')})"

            if same and v5_apt_id:
                agreements += 1
                verdict = "ACCORD"
            elif v6_apt_id and not v5_apt_id:
                v6_only.append(req_label)
                verdict = "V6 SEUL"
            elif v5_apt_id and not v6_apt_id:
                v5_only.append(req_label)
                verdict = "V5 SEUL"
            elif v5_apt_id and v6_apt_id and not same:
                v5_real = v5_tech in REAL_TECHNICIAN_IDS
                v6_real = v6_tech in REAL_TECHNICIAN_IDS
                better = "v6" if (v6_real and not v5_real) else "v5" if (v5_real and not v6_real) else "?"
                divergences.append({
                    "request": req_label,
                    "v5": f"{v5_apt.get('title','')[:35]} ({tech_name(v5_tech)})" if v5_apt else v5_apt_id,
                    "v6": f"{v6_match.get('title','')[:35]} ({tech_name(v6_tech)})",
                    "method": v6_method,
                    "better": better,
                })
                verdict = f"DIVERGE → {better}"
            else:
                verdict = "AUCUN"

            details.append({
                "date": str(req.get('appointment_date',''))[:10],
                "for_who": req.get('for_who',''),
                "room": req.get('room',''),
                "v5": f"{v5_apt.get('title','')[:30]} ({tech_name(v5_tech)})" if v5_apt else ("-" if not v5_apt_id else v5_apt_id[:15]),
                "v6": f"{v6_match.get('title','')[:30]} ({tech_name(v6_tech)})" if v6_match else "-",
                "verdict": verdict,
            })

        return {
            "summary": {
                "total": len(all_requests),
                "v5_matched": v5_matched,
                "v6_matched": v6_matched,
                "agreements": agreements,
                "divergences": len(divergences),
                "v6_better": len([d for d in divergences if d['better'] == 'v6']),
                "v5_better": len([d for d in divergences if d['better'] == 'v5']),
            },
            "divergences": divergences,
            "v6_only": v6_only,
            "v5_only": v5_only,
            "details": details,
        }

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/admin/backfill-all", response_model=Dict[str, Any])
async def backfill_all(request: Dict[str, Any]):
    """
    Backfill complet : appointments + timeline depuis 2017.
    Tourne en arrière-plan, retourne immédiatement.
    """
    secret = request.get("secret", "")
    if secret != "ptm-migrate-2026":
        raise HTTPException(status_code=403, detail="Accès refusé")

    import threading

    def _run_backfill():
        try:
            from modules.sync_gazelle.sync_to_supabase import GazelleToSupabaseSync

            sync = GazelleToSupabaseSync()

            # ── Phase 1 : Appointments depuis 2017 ──
            print("=" * 60)
            print("🔄 BACKFILL PHASE 1/2 : Appointments depuis 2017-01-01")
            print("=" * 60)
            try:
                appt_count = sync.sync_appointments(start_date_override='2017-01-01')
                print(f"✅ APPOINTMENTS: {appt_count} synchronisés")
            except Exception as e:
                import traceback
                print(f"❌ APPOINTMENTS ERREUR: {e}")
                traceback.print_exc()

            # ── Phase 2 : Timeline complète ──
            print("=" * 60)
            print("🔄 BACKFILL PHASE 2/2 : Timeline entries (tout l'historique)")
            print("=" * 60)
            try:
                from core.timezone_utils import parse_gazelle_datetime, format_for_supabase
                import requests as http_requests

                all_entries = sync.api_client.get_timeline_entries(since_date=None, limit=None)
                print(f"📥 {len(all_entries)} timeline entries récupérées de Gazelle")

                synced = 0
                errors = 0
                for i, entry_data in enumerate(all_entries):
                    try:
                        occurred_at_raw = entry_data.get('occurredAt')
                        occurred_at_utc = None
                        if occurred_at_raw:
                            dt_parsed = parse_gazelle_datetime(occurred_at_raw)
                            if dt_parsed:
                                occurred_at_utc = format_for_supabase(dt_parsed)

                        client_node = entry_data.get('client') or {}
                        piano_node = entry_data.get('piano') or {}
                        invoice_node = entry_data.get('invoice') or {}
                        estimate_node = entry_data.get('estimate') or {}
                        user_node = entry_data.get('user') or {}

                        record = {
                            'external_id': entry_data.get('id', ''),
                            'client_id': client_node.get('id') if isinstance(client_node, dict) else None,
                            'piano_id': piano_node.get('id') if isinstance(piano_node, dict) else None,
                            'invoice_id': invoice_node.get('id') if isinstance(invoice_node, dict) else None,
                            'estimate_id': estimate_node.get('id') if isinstance(estimate_node, dict) else None,
                            'user_id': user_node.get('id') if isinstance(user_node, dict) else None,
                            'entry_type': entry_data.get('type', ''),
                            'title': (entry_data.get('summary') or '')[:500],
                            'description': (entry_data.get('comment') or '')[:2000],
                            'occurred_at': occurred_at_utc,
                        }

                        url = f"{sync.storage.api_url}/gazelle_timeline_entries"
                        headers = sync.storage._get_headers()
                        headers['Prefer'] = 'resolution=merge-duplicates'
                        resp = http_requests.post(url, headers=headers, json=record)

                        if resp.status_code in (200, 201, 409):
                            synced += 1
                        else:
                            errors += 1
                    except Exception:
                        errors += 1

                    if (i + 1) % 500 == 0:
                        print(f"🔄 TIMELINE: {i + 1}/{len(all_entries)} ({synced} ok, {errors} err)")

                print(f"✅ TIMELINE: {synced} insérés, {errors} erreurs sur {len(all_entries)}")
            except Exception as e:
                import traceback
                print(f"❌ TIMELINE ERREUR: {e}")
                traceback.print_exc()

            print("=" * 60)
            print("✅ BACKFILL COMPLET TERMINÉ")
            print("=" * 60)

        except Exception as e:
            import traceback
            print(f"❌ BACKFILL ERREUR GLOBALE: {e}")
            traceback.print_exc()

    thread = threading.Thread(target=_run_backfill, daemon=True)
    thread.start()

    return {
        "success": True,
        "message": "Backfill complet lancé (appointments 2017+ et timeline complète). Voir les logs Render.",
    }


@router.post("/admin/flag", response_model=Dict[str, Any])
async def set_feature_flag(request: Dict[str, Any]):
    """Active ou désactive un feature flag."""
    if request.get("secret") != "ptm-migrate-2026":
        raise HTTPException(status_code=403, detail="Accès refusé")

    flag = request.get("flag", "")
    enabled = request.get("enabled", False)
    if not flag:
        raise HTTPException(status_code=400, detail="flag requis")

    try:
        from core.supabase_storage import SupabaseStorage
        import requests as http_requests

        storage = SupabaseStorage(silent=True)
        key = f"flag_{flag}"
        value = "true" if enabled else "false"

        url = f"{storage.api_url}/system_settings"
        headers = storage._get_headers()
        headers["Prefer"] = "resolution=merge-duplicates"
        resp = http_requests.post(url, headers=headers, json={"key": key, "value": value})

        if resp.status_code in (200, 201):
            # Vider le cache des flags
            from core.feature_flags import _refresh_cache
            _refresh_cache()
            return {"success": True, "flag": flag, "enabled": enabled}
        else:
            raise HTTPException(status_code=500, detail=f"Erreur Supabase: {resp.text}")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/admin/pda-scan", response_model=Dict[str, Any])
async def pda_scan_now(request: Dict[str, Any]):
    """Lance un scan PDA/OSM immédiat (test)."""
    if request.get("secret") != "ptm-migrate-2026":
        raise HTTPException(status_code=403, detail="Accès refusé")
    try:
        from modules.pda_auto_scanner import scan_and_watch
        return scan_and_watch()
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/admin/backfill-invoices", response_model=Dict[str, Any])
async def backfill_invoices(request: Dict[str, Any]):
    """Backfill complet des factures depuis Gazelle. Tâche de fond."""
    if request.get("secret") != "ptm-migrate-2026":
        raise HTTPException(status_code=403, detail="Accès refusé")

    import threading

    def _run():
        try:
            from core.gazelle_api_client import GazelleAPIClient
            from core.supabase_storage import SupabaseStorage
            import requests as http_requests

            api = GazelleAPIClient()
            storage = SupabaseStorage()
            headers = storage._get_headers()
            headers["Prefer"] = "resolution=merge-duplicates"

            print("🔄 BACKFILL FACTURES: Récupération depuis Gazelle...")
            invoices = api.get_invoices(limit=None)
            print(f"📥 {len(invoices)} factures récupérées")

            synced = 0
            items_synced = 0
            errors = 0

            for inv in invoices:
                try:
                    client_node = inv.get("client") or {}
                    created_at = inv.get("createdAt") or ""
                    due_on = inv.get("dueOn") or ""
                    # Montants en cents dans Gazelle → convertir en dollars
                    sub_total = inv.get("subTotal")
                    total = inv.get("total")
                    if isinstance(sub_total, int) and sub_total > 1000:
                        sub_total = sub_total / 100
                    if isinstance(total, int) and total > 1000:
                        total = total / 100

                    record = {
                        "external_id": inv.get("id", ""),
                        "client_id": client_node.get("id", "") if isinstance(client_node, dict) else "",
                        "invoice_number": str(inv.get("number", "")),
                        "invoice_date": str(created_at)[:10] or None,
                        "status": inv.get("status", ""),
                        "sub_total": sub_total,
                        "total": total,
                        "notes": (inv.get("notes") or "")[:2000],
                        "due_on": str(due_on)[:10] or None,
                    }

                    resp = http_requests.post(
                        f"{storage.api_url}/gazelle_invoices",
                        headers=headers, json=record
                    )
                    if resp.status_code in (200, 201, 409):
                        synced += 1
                    else:
                        errors += 1

                    # Invoice items
                    items = inv.get("allInvoiceItems", {}).get("nodes", [])
                    for item in items:
                        item_record = {
                            "external_id": item.get("id", ""),
                            "invoice_external_id": inv.get("id", ""),
                            "description": (item.get("description") or "")[:2000],
                            "item_type": item.get("type", ""),
                            "quantity": item.get("quantity"),
                            "amount": item.get("amount"),
                            "sub_total": item.get("subTotal"),
                            "tax_total": item.get("taxTotal"),
                            "total": item.get("total"),
                            "billable": item.get("billable", True),
                            "taxable": item.get("taxable", True),
                            "sequence_number": item.get("sequenceNumber"),
                        }
                        item_resp = http_requests.post(
                            f"{storage.api_url}/gazelle_invoice_items",
                            headers=headers, json=item_record
                        )
                        if item_resp.status_code in (200, 201, 409):
                            items_synced += 1

                except Exception as e:
                    errors += 1
                    if errors <= 3:
                        print(f"❌ Erreur facture {inv.get('id','')}: {e}")

                if (synced + errors) % 100 == 0:
                    print(f"🔄 FACTURES: {synced}/{len(invoices)} ({items_synced} lignes)")

            print(f"✅ BACKFILL FACTURES TERMINÉ: {synced} factures, {items_synced} lignes, {errors} erreurs")

        except Exception as e:
            import traceback
            print(f"❌ BACKFILL FACTURES ERREUR: {e}")
            traceback.print_exc()

    thread = threading.Thread(target=_run, daemon=True)
    thread.start()
    return {"success": True, "message": "Backfill factures lancé en arrière-plan"}


@router.get("/admin/test-invoices", response_model=Dict[str, Any])
async def test_invoices(secret: str = Query("")):
    """Test: combien de factures dans Gazelle vs Supabase."""
    if secret != "ptm-migrate-2026":
        raise HTTPException(status_code=403, detail="Accès refusé")
    try:
        from core.supabase_storage import SupabaseStorage
        storage = SupabaseStorage(silent=True)
        sb_result = storage.client.table("gazelle_invoices").select("id", count="exact").limit(1).execute()
        sb_count = sb_result.count if hasattr(sb_result, 'count') and sb_result.count else 0

        gazelle_error = None
        sample = {}
        gazelle_count = 0
        try:
            from core.gazelle_api_client import GazelleAPIClient
            api = GazelleAPIClient()
            invoices = api.get_invoices(limit=3)
            gazelle_count = len(invoices)
            sample = invoices[0] if invoices else {}
        except Exception as e:
            gazelle_error = str(e)

        return {
            "supabase_count": sb_count,
            "gazelle_sample_count": gazelle_count,
            "gazelle_error": gazelle_error,
            "sample_keys": list(sample.keys())[:10] if sample else [],
            "sample_client_id": sample.get("clientId", ""),
            "sample_number": sample.get("number", ""),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/admin/search-invoices", response_model=Dict[str, Any])
async def search_invoices(
    secret: str = Query(""),
    q: str = Query(""),
    client_id: str = Query(""),
    date_from: str = Query(""),
    date_to: str = Query(""),
    total_max: float = Query(None),
    limit: int = Query(20),
):
    """Recherche dans les factures et lignes de facture."""
    if secret != "ptm-migrate-2026":
        raise HTTPException(status_code=403, detail="Accès refusé")
    try:
        from core.supabase_storage import SupabaseStorage
        storage = SupabaseStorage(silent=True)

        # Recherche dans les factures
        query = storage.client.table("gazelle_invoices").select("*")

        if client_id:
            query = query.eq("client_id", client_id)
        if date_from:
            query = query.gte("invoice_date", date_from)
        if date_to:
            query = query.lte("invoice_date", date_to)
        if total_max is not None:
            query = query.lte("total", total_max)
        if q:
            query = query.ilike("notes", f"*{q}*")

        result = query.order("invoice_date", desc=True).limit(limit).execute()

        entries = []
        for inv in (result.data or []):
            entries.append({
                "invoice_number": inv.get("invoice_number", ""),
                "invoice_date": inv.get("invoice_date", ""),
                "client_id": inv.get("client_id", ""),
                "total": inv.get("total"),
                "sub_total": inv.get("sub_total"),
                "status": inv.get("status", ""),
                "notes": (inv.get("notes") or "")[:200],
            })

        return {"query": q, "count": len(entries), "entries": entries}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/admin/search-timeline", response_model=Dict[str, Any])
async def search_timeline(
    secret: str = Query(""),
    q: str = Query(""),
    date: str = Query(""),
    date_from: str = Query(""),
    date_to: str = Query(""),
    client_id: str = Query(""),
    limit: int = Query(50),
):
    """Recherche dans la timeline. Supporte texte, date exacte, plage de dates, client."""
    if secret != "ptm-migrate-2026":
        raise HTTPException(status_code=403, detail="Accès refusé")
    if not q and not date and not date_from and not client_id:
        raise HTTPException(status_code=400, detail="Au moins un filtre requis (q, date, date_from, client_id)")
    try:
        from core.supabase_storage import SupabaseStorage
        storage = SupabaseStorage(silent=True)
        query = storage.client.table('gazelle_timeline_entries').select(
            'client_id,occurred_at,entry_type,title,description,user_id'
        )

        if q:
            query = query.ilike('description', f'*{q}*')
        if date:
            query = query.gte('occurred_at', f'{date}T00:00:00').lt('occurred_at', f'{date}T23:59:59')
        if date_from:
            query = query.gte('occurred_at', f'{date_from}T00:00:00')
        if date_to:
            query = query.lt('occurred_at', f'{date_to}T23:59:59')
        if client_id:
            query = query.eq('client_id', client_id)

        result = query.order('occurred_at', desc=True).limit(limit).execute()

        entries = []
        for e in (result.data or []):
            entries.append({
                "client_id": e.get("client_id", ""),
                "date": (e.get("occurred_at") or "")[:10],
                "type": e.get("entry_type", ""),
                "title": (e.get("title") or "")[:100],
                "description": (e.get("description") or "")[:300],
                "user_id": e.get("user_id", ""),
            })
        return {"query": q, "date": date, "count": len(entries), "entries": entries}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/admin/pda-stats", response_model=Dict[str, Any])
async def pda_appointment_stats(secret: str = Query(""), since: str = Query("2025-08-01")):
    """Statistiques des RV Place des Arts par jour/heure depuis une date."""
    if secret != "ptm-migrate-2026":
        raise HTTPException(status_code=403, detail="Accès refusé")
    try:
        from core.supabase_storage import SupabaseStorage
        from collections import defaultdict
        from datetime import datetime as dt
        import re

        storage = SupabaseStorage(silent=True)
        PDA_CLIENT_ID = "cli_HbEwl9rN11pSuDEU"

        result = storage.client.table('gazelle_appointments').select(
            'appointment_date,appointment_time,title,technicien,status'
        ).eq('client_external_id', PDA_CLIENT_ID).gte(
            'appointment_date', since
        ).order('appointment_date').execute()

        appointments = result.data or []

        day_names = ['Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi', 'Samedi', 'Dimanche']
        by_day = defaultdict(int)
        by_hour = defaultdict(int)
        by_day_hour = defaultdict(int)
        all_entries = []

        for apt in appointments:
            date_str = (apt.get('appointment_date') or '')[:10]
            time_str = apt.get('appointment_time') or ''
            if not date_str or len(date_str) < 10:
                continue

            d = dt.strptime(date_str, '%Y-%m-%d')
            day = day_names[d.weekday()]
            by_day[day] += 1

            hour = None
            if time_str:
                try:
                    hour = int(time_str.split(':')[0])
                    h_label = f"{hour:02d}h"
                    by_hour[h_label] += 1
                    by_day_hour[f"{day} {h_label}"] += 1
                except:
                    pass

            all_entries.append({
                "date": date_str,
                "day": day,
                "time": time_str[:5] if time_str else "",
                "title": apt.get('title', ''),
                "technician": apt.get('technicien', ''),
            })

        total = len(all_entries)
        top_combos = sorted(by_day_hour.items(), key=lambda x: -x[1])[:15]

        return {
            "total": total,
            "since": since,
            "by_day": {d: by_day.get(d, 0) for d in day_names},
            "by_hour": dict(sorted(by_hour.items())),
            "top_combos": [{"slot": k, "count": v} for k, v in top_combos],
            "appointments": all_entries,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/admin/timeline-stats", response_model=Dict[str, Any])
async def timeline_stats(secret: str = Query("")):
    """Nombre d'entrées timeline par année dans Supabase."""
    if secret != "ptm-migrate-2026":
        raise HTTPException(status_code=403, detail="Accès refusé")
    try:
        from core.supabase_storage import SupabaseStorage
        storage = SupabaseStorage(silent=True)
        stats = {}
        total = 0
        for year in range(2016, 2027):
            result = storage.client.table('gazelle_timeline_entries').select(
                'id', count='exact'
            ).gte('occurred_at', f'{year}-01-01').lt(
                'occurred_at', f'{year + 1}-01-01'
            ).limit(1).execute()
            count = result.count if hasattr(result, 'count') and result.count else 0
            stats[str(year)] = count
            total += count
        return {"total": total, "by_year": stats, "target": 282669}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/follow-up/resolve", response_model=Dict[str, Any])
async def resolve_follow_up(request: ResolveFollowUpRequest):
    """
    Marque un follow-up comme résolu.
    """
    try:
        service = NarrativeBriefingService()
        success = service.resolve_follow_up(
            item_id=request.item_id,
            resolved_by=request.resolved_by,
            resolution_note=request.resolution_note,
        )

        if success:
            return {
                "success": True,
                "message": "Suivi marqué comme résolu",
                "item_id": request.item_id,
            }
        else:
            raise HTTPException(status_code=500, detail="Erreur résolution")

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
