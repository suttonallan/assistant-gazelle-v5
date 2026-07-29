#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests anti-amalgame du parser Place des Arts.

Règle métier (Allan) : une demande = date + heure précise + local + piano,
assignée à un technicien. Deux lignes identiques sur ces axes = LA MÊME demande.

Ces tests VÉRIFIENT (pas de supposition) :
  1. canonical_time : normalisation 24h (6am, 7pm, 19h, avant 9h...)
  2. normalize_room : « JD » = « TJD » (Théâtre Jean-Duceppe)
  3. dédup de bout en bout : le motif Isaiah (19h en double) → 1 seule ligne
  4. non-régression : format naturel Annie Jenkins → 1 demande
"""

import sys
from modules.place_des_arts.services.email_parser import (
    canonical_time, normalize_room, parse_email_text,
)

ok = True

def check(label, got, expected):
    global ok
    passed = got == expected
    ok = ok and passed
    print(f"  [{'OK ' if passed else 'FAIL'}] {label}: {got!r}" +
          ("" if passed else f"  (attendu {expected!r})"))

print("=== 1. canonical_time (heure 24h) ===")
check("6am",            canonical_time("6am"),        "06:00")
check("7pm",            canonical_time("7pm"),        "19:00")
check("19h",            canonical_time("19h"),        "19:00")
check("14h30",          canonical_time("14h30"),      "14:30")
check("a 14h",          canonical_time("à 14h"),      "14:00")
check("avant 9h",       canonical_time("avant 9h"),   "09:00")
check("Avant 9",        canonical_time("Avant 9"),    "09:00")
check("entre 8h et 9h", canonical_time("entre 8h et 9h"), "08:00")
check("vide",           canonical_time(""),           None)
check("7pm == 19h",     canonical_time("7pm") == canonical_time("19h"), True)

print("=== 2. normalize_room (JD == TJD) ===")
check("JD",  normalize_room("JD"),  "TJD")
check("TJD", normalize_room("TJD"), "TJD")
check("JD == TJD", normalize_room("JD") == normalize_room("TJD"), True)

print("=== 3. Dédup bout-en-bout : motif Isaiah (19h en double) ===")
# Chaque service préfixé de sa date (déclenche le découpage en blocs).
# La demande de 19h est écrite DEUX fois : « 7pm / JD » et « 19h / TJD ».
email_isaiah = """Bonjour,

3 juillet
TJD
Isaiah Collier FIJM
440
Steinway B
19h

3 juillet
JD
Isaiah Collier FIJM
440
Steinway B
7pm

Isabelle
"""
res = parse_email_text(email_isaiah)
# Aucune paire (date, heure24, salle, piano) identique ne doit subsister.
keys = [(str(r.get('date'))[:10], r.get('time_24h'),
         normalize_room(r.get('room') or ''), (r.get('piano') or '').lower().strip())
        for r in res]
print(f"  demandes retournées: {len(res)} | clés: {keys}")
check("pas de doublon (clés uniques)", len(keys), len(set(keys)))
check("les deux 19h ont fusionné", sum(1 for k in keys if k[1] == '19:00') <= 1, True)

print("=== 4. Non-régression : format naturel Annie Jenkins ===")
annie = """Est-ce possible pour vous de faire un accord du Steinway 9' D - New York
à 442 de la Salle D le 20 janvier entre 8h00 et 9h00?
Merci de me confirmer si c'est possible.
ANNIE JENKINS
"""
ra = parse_email_text(annie)
check("1 seule demande", len(ra), 1)

print()
print("✅ TOUS LES TESTS PASSENT" if ok else "❌ DES TESTS ÉCHOUENT")
sys.exit(0 if ok else 1)
