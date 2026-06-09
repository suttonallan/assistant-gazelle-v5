#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Recherche client intelligente (langage naturel) pour l'assistant.

Permet a Louise (et l'equipe) de retrouver un client par criteres flous, en
cherchant a travers TOUS les champs texte ou l'info peut vivre :
  - fiche client : prenom/nom/compagnie, ville, notes perso et de preference
  - timeline du client (beaucoup d'infos n'existent QUE la, ex. "va demenager a
    Saint-Hilaire")
  - notes de pianos (ex. "Ancienne mecanique - Restaure par ...")

Principe (aligne sur le plan de fiabilite Ma Journee) : on rend la PROVENANCE.
Chaque correspondance affiche d'ou elle vient (note / timeline + date / piano).

Deux passes :
  1) DECOUVERTE : une requete par terme (avec limite) -> liste de clients candidats.
  2) RECOMPTE EXACT : pour les candidats, on relit leurs donnees scopees par client
     (sans troncature) et on recompte TOUS les termes. Indispensable car un terme
     commun (ex. "demenagement") est tronque par la limite en passe 1 et ferait
     disparaitre le bon client.
"""
import json
import re
from collections import defaultdict

import requests

_EMAIL_TYPES = ("CONTACT_EMAIL_AUTOMATED,CONTACT_EMAIL_MANUAL,CONTACT_SMS_AUTOMATED,"
                "CONTACT_SMS_MANUAL,SCHEDULED_MESSAGE_EMAIL,SCHEDULED_MESSAGE_SMS,CONTACT_EMAIL")

_STOPWORDS = {
    "client", "cliente", "clients", "contact", "cherche", "chercher", "trouve",
    "trouver", "recherche", "rechercher", "le", "la", "les", "un", "une", "des",
    "de", "du", "qui", "que", "quoi", "quel", "quelle", "on", "nous", "vous",
    "est", "elle", "il", "ils", "pour", "avec", "dans", "sur", "son", "sa", "ses",
    "notre", "nos", "votre", "vos", "au", "aux", "et", "ou", "mais", "donc",
    "ce", "cette", "ces", "avons", "avez", "ont", "fait", "faite", "quelque",
    "part", "habitait", "habite", "va", "vont", "ete",
}

_NORMALIZE = [
    (re.compile(r"saint[- ]?hilaire|st[- ]?hilaire", re.I), "hilaire"),
    (re.compile(r"restaur\w*", re.I), "restaur"),
    (re.compile(r"d[ée]m[ée]nag\w*", re.I), "nag"),
]


def _normalize_term(term: str) -> str:
    for pat, repl in _NORMALIZE:
        if pat.search(term or ""):
            return repl
    return term


def _sanitize(term: str) -> str:
    # ilike : '*' = joker ; ',' '(' ')' '%' cassent la liste or=. On nettoie.
    return re.sub(r"[,*()%]", " ", term or "").strip()


def _fallback_terms(query: str) -> list:
    words = re.split(r"[^0-9A-Za-zÀ-ÿ\-]+", (query or "").lower())
    seen, res = set(), []
    for w in words:
        w = w.strip("-")
        if len(w) < 4 or w in _STOPWORDS:
            continue
        nt = _normalize_term(w)
        if nt and nt not in seen:
            seen.add(nt)
            res.append(nt)
    return res[:6]


def extract_terms(query: str, anthropic=None) -> list:
    """Extrait les criteres distinctifs. Claude si dispo, sinon tokenisation."""
    if anthropic:
        try:
            sys_prompt = (
                "Tu extrais d'une question les CRITERES de recherche distinctifs pour retrouver "
                "un client d'un atelier de pianos : lieux, types de travaux, marques/modeles de "
                "piano, noms, mots-cles rares. Ignore les mots vides et generiques (client, "
                "cliente, cherche, trouve, on, qui...). Donne des RACINES en sous-chaine quand "
                "utile (ex. 'restaur' pour restaure/restauration ; 'hilaire' pour Saint-Hilaire). "
                'Reponds UNIQUEMENT en JSON : {"termes": ["...", "..."]} (max 6).'
            )
            resp = anthropic.messages.create(
                model="claude-haiku-4-5-20251001", max_tokens=150,
                system=sys_prompt, messages=[{"role": "user", "content": query}],
            )
            raw = resp.content[0].text.strip()
            m = re.search(r"\{.*\}", raw, re.DOTALL)
            if m:
                terms = [_sanitize(_normalize_term(str(t))) for t in (json.loads(m.group(0)).get("termes") or [])]
                terms = [t for t in dict.fromkeys(terms) if len(t) >= 3]
                if terms:
                    return terms[:6]
        except Exception:
            pass
    return [t for t in _fallback_terms(query) if len(_sanitize(t)) >= 3]


def _snippet(text: str, term: str, width: int = 55) -> str:
    if not text:
        return ""
    i = text.lower().find(term.lower())
    if i < 0:
        return re.sub(r"\s+", " ", text)[:width].strip()
    start, end = max(0, i - 20), min(len(text), i + len(term) + width)
    snip = re.sub(r"\s+", " ", text[start:end]).strip()
    return ("..." if start > 0 else "") + snip + ("..." if end < len(text) else "")


def search_clients_intelligent(storage, query: str, anthropic=None, limit: int = 8) -> str:
    if not query or not query.strip():
        return "Aucun critere de recherche fourni."
    terms = [t for t in (extract_terms(query, anthropic) or []) if len(_sanitize(t)) >= 3]
    if not terms:
        return f"Je n'ai pas pu degager de critere clair de « {query} »."

    headers, api = storage._get_headers(), storage.api_url

    def get(url):
        try:
            r = requests.get(url, headers=headers, timeout=20)
            return r.json() if r.status_code == 200 else []
        except Exception:
            return []

    # ----- Passe 1 : decouverte des candidats (1 requete par terme) -----
    cand_terms = defaultdict(set)  # client_id -> set(terms) (approx, peut etre tronque)
    for term in terms:
        t = _sanitize(term)
        p = f"*{t}*"
        for c in get(f"{api}/gazelle_clients?or=(first_name.ilike.{p},last_name.ilike.{p},"
                     f"company_name.ilike.{p},personal_notes.ilike.{p},preference_notes.ilike.{p},"
                     f"city.ilike.{p})&select=external_id&limit=150"):
            cand_terms[c["external_id"]].add(term)
        for row in get(f"{api}/gazelle_timeline_entries?or=(title.ilike.{p},description.ilike.{p})"
                       f"&entry_type=not.in.({_EMAIL_TYPES})&select=client_id&order=occurred_at.desc&limit=150"):
            if row.get("client_id"):
                cand_terms[row["client_id"]].add(term)
        for pn in get(f"{api}/gazelle_pianos?or=(notes.ilike.{p},model.ilike.{p},make.ilike.{p},"
                      f"location.ilike.{p})&select=client_external_id&limit=150"):
            if pn.get("client_external_id"):
                cand_terms[pn["client_external_id"]].add(term)

    if not cand_terms:
        return f"Aucun client ne correspond a « {query} »."

    # Selection des candidats a recompter exactement. Un terme commun (nag,
    # restaur) est tronque en passe 1 -> un client peut n'y matcher qu'un terme
    # RARE (lieu, marque). On inclut donc TOUT client matchant un terme-signal
    # (peu de clients) + tout client a >=2 termes, puis on borne par rarete approx.
    counts = {t: sum(1 for s in cand_terms.values() if t in s) for t in terms}
    approx_w = {t: 1.0 / max(1, counts[t]) for t in terms}
    signal = {t for t, n in counts.items() if n <= 100}
    cand = [cid for cid, ts in cand_terms.items() if len(ts) >= 2 or (ts & signal)]
    cand.sort(key=lambda cid: sum(approx_w[t] for t in cand_terms[cid]), reverse=True)
    cand = cand[:150]
    ids = ",".join(cand)

    # ----- Passe 2 : recompte EXACT, scope par client (sans troncature) -----
    clients_by = {c["external_id"]: c for c in get(
        f"{api}/gazelle_clients?external_id=in.({ids})&select=external_id,first_name,last_name,"
        f"company_name,city,personal_notes,preference_notes")}
    # On ne tire que les entrees QUI matchent un terme (scopees aux candidats) :
    # petit ensemble, jamais tronque par la limite (sinon une vieille entree
    # pertinente, ex. "demenager a Saint-Hilaire" de 2024, tombe sous la recence).
    term_or = ",".join(f"title.ilike.*{_sanitize(t)}*,description.ilike.*{_sanitize(t)}*" for t in terms)
    tl = get(f"{api}/gazelle_timeline_entries?client_id=in.({ids})&or=({term_or})"
             f"&entry_type=not.in.({_EMAIL_TYPES})"
             f"&select=client_id,occurred_at,title,description&order=occurred_at.desc&limit=6000")
    pianos = get(f"{api}/gazelle_pianos?client_external_id=in.({ids})"
                 f"&select=client_external_id,make,model,notes,location")

    exact = {cid: {"terms": set(), "hits": []} for cid in cand}
    low_terms = [(term, _sanitize(term).lower()) for term in terms]

    def scan(cid, text, source, date=None):
        if cid not in exact or not text:
            return
        tl_ = text.lower()
        for term, lt in low_terms:
            if lt in tl_:
                exact[cid]["terms"].add(term)
                snip = _snippet(text, _sanitize(term), date and 45 or 55)
                exact[cid]["hits"].append((source, snip, date))

    for cid, c in clients_by.items():
        for fld in ("personal_notes", "preference_notes", "city"):
            scan(cid, c.get(fld), "note")
    for row in tl:
        scan(row.get("client_id"), row.get("description") or row.get("title") or "",
             "timeline", str(row.get("occurred_at"))[:10])
    for pn in pianos:
        scan(pn.get("client_external_id"),
             pn.get("notes") or pn.get("location") or f"{pn.get('make', '')} {pn.get('model', '')}", "piano")

    # Classement par rarete (exacte) ; un terme rare (lieu, marque) pese plus.
    tc = defaultdict(set)
    for cid, e in exact.items():
        for t in e["terms"]:
            tc[t].add(cid)
    w = {t: 1.0 / max(1, len(c)) for t, c in tc.items()}
    distinctive = {t for t, c in tc.items() if len(c) <= max(8, len(cand) // 3)}

    final = [cid for cid in cand if exact[cid]["terms"]
             and (len(exact[cid]["terms"]) >= 2 or any(t in distinctive for t in exact[cid]["terms"]))]
    final.sort(key=lambda cid: (sum(w[t] for t in exact[cid]["terms"]), len(exact[cid]["terms"])), reverse=True)
    final = final[:limit]
    if not final:
        return f"Aucun client ne correspond clairement a « {query} »."

    def name_of(c):
        c = c or {}
        return (c.get("company_name")
                or " ".join(x for x in [c.get("first_name"), c.get("last_name")] if x) or "(sans nom)")

    lines = [f"{len(final)} client(s) correspondent a « {query} » :", ""]
    for i, cid in enumerate(final, 1):
        c = clients_by.get(cid) or {}
        city = c.get("city") or ""
        lines.append(f"{i}. {name_of(c)} ({cid})" + (f" - {city}" if city else ""))
        lines.append(f"   Criteres : {', '.join(sorted(exact[cid]['terms']))}")
        seen = set()
        for source, snip, date in exact[cid]["hits"]:
            if not snip or snip in seen:
                continue
            seen.add(snip)
            label = {"note": "Note", "piano": "Piano",
                     "timeline": f"Timeline {date}" if date else "Timeline"}[source]
            lines.append(f"   - {label} : « {snip} »")
            if len(seen) >= 3:
                break
        lines.append("")
    return "\n".join(lines).strip()
