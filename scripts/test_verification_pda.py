"""Vérification hors ligne de la contre-vérification PdA (aucun accès réseau).
Usage : python3 scripts/test_verification_pda.py"""
import sys
from datetime import date
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from modules.place_des_arts.services import verification_source as vs

COURRIEL = """> > Bonjour,
> > Il y a 2 ajouts d'accords pour l'Adisq (les demandes pour le 8 nov vous avez déjà) :
> > 6-Nov
> > WP
> > Adisq
> > 440
> > Steinway 7'
> > Avant 8h
> > 7-Nov
> > WP
> > Adisq
> > 440
> > Steinway 9' D NY
> > Avant 8h
> > Merci de confirmer
> > Isabelle
**De :** Isabelle Clairoux
> 8-Nov WP Adisq 440 Steinway 7' Avant 11h
"""
lignes, ctx = vs.analyser(COURRIEL, date(2026, 10, 28))
assert [l['date'] for l in lignes] == ['2026-11-06', '2026-11-07'], lignes
bonne = {'id': 'a', 'appointment_date': '2026-11-06', 'room': 'WP', 'for_who': 'Adisq',
         'piano': "Steinway 7'", 'diapason': '440', 'time': 'Avant 8h'}
c = vs.comparer(bonne, vs.choisir_ligne(bonne, lignes, ctx), ctx)
assert all(x['statut'] == 'ok' for x in c.values()), c
mauvaise = dict(bonne, id='b', piano="Steinway 9' D NY")
c = vs.comparer(mauvaise, vs.choisir_ligne(mauvaise, lignes, ctx), ctx)
assert c['piano']['statut'] == 'ecart', c
date_fausse = dict(bonne, id='c', appointment_date='2026-11-09')
assert vs.choisir_ligne(date_fausse, lignes, ctx) is None
assert [len(x) for x in vs.associer(lignes, [bonne], ctx)] == [1, 0]
assert vs._statut_champ('piano', 'Steinway B', {'texte': "TM Steinway D 9'"}) is False
assert vs._statut_champ('piano', "Steinway 9' D NY", {'texte': "Salle D Steinway 9' D - New York"}) is True
print("OK — contre-vérification PdA")
