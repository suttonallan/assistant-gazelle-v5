"""LECTURE SEULE — rétention des clients d'accords de courtoisie (Nantel vs Archambault).

Rien n'est écrit dans Gazelle. Les chiffres agrégés (sans noms) vont dans le journal public
du workflow ; la liste nominative va dans Supabase (system_settings « rapport_courtoisie »)
et par courriel à asutton@.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api.taches_routes import _calculer_courtoisie, _rapport_courtoisie  # noqa: E402
from core.supabase_storage import SupabaseStorage  # noqa: E402


def note(t, m):
    print(f"::notice title={t}::" + str(m).replace("%", "%25").replace("\n", "%0A"))


_calculer_courtoisie()
r = _rapport_courtoisie
if r.get("statut") != "termine":
    print("Erreur :", r.get("erreur"))
    sys.exit(1)

note("Factures lues", f"{r['factures_lues']} factures Gazelle ; factures au nom du marchand : {r['factures_au_nom_du_marchand']}")
for m, s in sorted(r["resume"].items()):
    annees = " ; ".join(f"{a} : {v['revenus']}/{v['clients']}" for a, v in sorted(s["par_annee"].items()))
    note(f"Courtoisie {m}", f"{s['revenus']}/{s['clients']} clients revenus au moins une fois ({s['taux']} %). Par année : {annees}")

SupabaseStorage(silent=True).save_system_setting("rapport_courtoisie", r)

try:
    from core.email_notifier import get_email_notifier
    lignes = "".join(
        f"<tr><td>{c['marchand']}</td><td>{c['client']}</td><td>{c['date_courtoisie']}</td>"
        f"<td>{c['visites_payees_apres']}</td><td>{c['derniere_visite'] or ''}</td></tr>"
        for c in r["clients"])
    resume = "".join(f"<li>{m} : {s['revenus']}/{s['clients']} ({s['taux']} %)</li>" for m, s in sorted(r["resume"].items()))
    html = (f"<p>Rétention après accord de courtoisie (au moins une visite payée ensuite).</p><ul>{resume}</ul>"
            "<table border=1 cellpadding=4><tr><th>Marchand</th><th>Client</th><th>Courtoisie</th>"
            f"<th>Visites payées après</th><th>Dernière</th></tr>{lignes}</table>")
    ok = get_email_notifier().send_email(["asutton@piano-tek.com"], "Rapport : clients des accords de courtoisie", html)
    note("Courriel", "envoyé à asutton@" if ok else "non envoyé")
except Exception as e:
    note("Courriel", f"non envoyé : {e}")
# relance 1793823837
