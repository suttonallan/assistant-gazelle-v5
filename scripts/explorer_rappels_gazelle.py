#!/usr/bin/env python3
"""Lecture seule : préparer les rappels personnalisés (phrase insérée dans les gabarits du cycle de vie).

Répond à quatre questions, sans rien écrire dans Gazelle :
1. Quels champs personnalisés existent sur la fiche client, et lesquels sont déjà utilisés (et par combien de fiches) ?
2. Quels cycles de vie existent (identifiants, langue), et quels codes de fusion leurs gabarits utilisent déjà ?
3. Les gabarits utilisent-ils déjà un champ personnalisé autre que custom2 ?
4. Que sait-on lire des soumissions (champs disponibles, nombre de soumissions récentes) ?
N'affiche que des noms de champs, des compteurs et des identifiants techniques (aucune donnée personnelle).
"""
import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from dotenv import load_dotenv; load_dotenv()
from core.gazelle_api_client import GazelleAPIClient

api = GazelleAPIClient()


def q(t, v=None):
    r = api._execute_query(t, v or {})
    if r.get("errors"):
        print(f"::warning title=Erreur::{str(r['errors'])[:800]}")
    return r.get("data") or {}


def note(t, m):
    print(f"::notice title={t}::" + str(m)[:3500].replace("%", "%25").replace("\r", "").replace("\n", "%0A"))


def champs_du_type(nom):
    t = q('query($n:String!){ __type(name:$n){ fields { name type { kind name ofType { kind name } } } } }', {"n": nom})
    return (t.get("__type") or {}).get("fields") or []


# 1. Champs personnalisés de la fiche client
cl = champs_du_type("PrivateClient")
perso = [f["name"] for f in cl if re.match(r"(?i)custom", f["name"])]
note("1a. Champs personnalisés client", perso or "aucun champ custom* trouvé")
racine = [f["name"] for f in champs_du_type("Query") if re.search(r"(?i)custom|setting|estimate|lifecycle|template", f["name"])]
note("1b. Requêtes utiles disponibles", racine)

scalaires = [f["name"] for f in cl if f["name"] in perso and (f["type"]["kind"] == "SCALAR" or (f["type"].get("ofType") or {}).get("kind") == "SCALAR")]
if scalaires:
    remplis, total, apres = Counter(), 0, None
    while True:
        d = q('query($a:String){ allClients(first:100, after:$a){ nodes { %s } pageInfo { hasNextPage endCursor } } }' % " ".join(scalaires), {"a": apres})
        bloc = d.get("allClients") or {}
        for n in bloc.get("nodes") or []:
            total += 1
            for c in scalaires:
                if (n.get(c) or "").strip():
                    remplis[c] += 1
        info = bloc.get("pageInfo") or {}
        if not info.get("hasNextPage"):
            break
        apres = info.get("endCursor")
    note("1c. Fiches où chaque champ est rempli", f"{total} fiches au total ; " + ", ".join(f"{c} : {remplis[c]}" for c in scalaires))

# 2-3. Cycles de vie et codes de fusion
MSG = "id kind state reminderKind recurringSubject recurringMessage firstSubject firstMessage specialSubject specialMessage"
cycles = (q("{ allLifecycles(first: 50) { nodes { id name lifecycleMessages { %s } } } }" % MSG).get("allLifecycles") or {}).get("nodes") or []
codes_globaux = Counter()
lignes = []
for c in cycles:
    codes = Counter()
    for m in c.get("lifecycleMessages") or []:
        for k in ("recurringSubject", "recurringMessage", "firstSubject", "firstMessage", "specialSubject", "specialMessage"):
            for code in re.findall(r"\{\{\s*([^}]+?)\s*\}\}", m.get(k) or ""):
                codes[code] += 1
    codes_globaux.update(codes)
    nb = len(c.get("lifecycleMessages") or [])
    kinds = Counter(f"{m['reminderKind']}/{m['state']}" for m in c.get("lifecycleMessages") or [])
    lignes.append(f"{c['id']} « {c['name']} » : {nb} messages ({dict(kinds)}) ; champs perso utilisés : {sorted(k for k in codes if 'custom' in k.lower()) or 'aucun'}")
note("2a. Cycles de vie", "\n".join(lignes))
note("2b. Codes de fusion déjà utilisés (tous cycles)", ", ".join(f"{k} ×{v}" for k, v in codes_globaux.most_common()))

# Quelle langue pour chaque cycle : regarder la locale des clients qui y sont inscrits
langues = {}
apres = None
while True:
    d = q('query($a:String){ allClients(first:100, after:$a){ nodes { status lifecycle { id } %s } pageInfo { hasNextPage endCursor } } }'
          % ("locale" if any(f["name"] == "locale" for f in cl) else ""), {"a": apres})
    bloc = d.get("allClients") or {}
    for n in bloc.get("nodes") or []:
        lc = (n.get("lifecycle") or {}).get("id") or "aucun"
        langues.setdefault(lc, Counter())[n.get("locale") or "?"] += 1
    info = bloc.get("pageInfo") or {}
    if not info.get("hasNextPage"):
        break
    apres = info.get("endCursor")
note("2c. Langue des clients inscrits à chaque cycle", "\n".join(f"{k} : {dict(v)}" for k, v in langues.items()))

# 4. Soumissions
est = champs_du_type("PrivateEstimate")
note("4a. Champs d'une soumission", [f["name"] for f in est])
if est:
    noms = {f["name"] for f in est}
    sel = " ".join(x for x in ("createdAt", "estimatedOn", "expiresOn", "isArchived", "archived", "status") if x in noms)
    d = q("{ allEstimates(first: 100) { totalCount nodes { %s } } }" % (sel or "id"))
    bloc = d.get("allEstimates") or {}
    nodes = bloc.get("nodes") or []
    resume = {"total": bloc.get("totalCount")}
    for k in ("status", "isArchived", "archived"):
        if k in sel:
            resume[k] = dict(Counter(str(n.get(k)) for n in nodes))
    note("4b. Soumissions (100 premières)", resume)
