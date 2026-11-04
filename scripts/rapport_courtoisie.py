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
for titre, res in (("Brut", r["resume"]), ("Rattaché", r["resume_rattache"])):
    for m, s in sorted(res.items()):
        annees = " ; ".join(f"{a} : {v['revenus']}/{v['clients']}" for a, v in sorted(s["par_annee"].items()))
        note(f"{titre} — {m}", f"revenus : {s['revenus']}/{s['clients']} ({s['taux']} %) | dans les 12 mois : "
             f"{s['revenus_12']}/{s['eligibles_12']} ({s['taux_12']} %) | par année : {annees}")
sources = {}
for c in r["clients"]:
    if c["marchand"] == "Non précisé":
        cle = (c.get("preuve") or "aucun indice").split(" ")[0] + f" → {c['marchand_final']}"
        sources[cle] = sources.get(cle, 0) + 1
note("Rattachement des non précisés", sources)

SupabaseStorage(silent=True).save_system_setting("rapport_courtoisie", r)

try:
    from html import escape
    from core.email_notifier import get_email_notifier
    lignes = "".join(
        f"<tr><td>{c['marchand']}</td><td>{c['marchand_final']}</td><td>{escape(c['client'] or '')}</td>"
        f"<td>{c['date_courtoisie']}</td><td>{c['visites_payees_apres']}</td><td>{'oui' if c['revenu_12_mois'] else 'non'}</td>"
        f"<td>{c['derniere_visite'] or ''}</td><td>{escape(c.get('preuve') or '')}</td></tr>"
        for c in sorted(r["clients"], key=lambda c: (c["marchand_final"], c["date_courtoisie"])))
    resume = "".join(f"<li>{m} : {s['revenus']}/{s['clients']} ({s['taux']} %) ; dans les 12 mois : "
                     f"{s['revenus_12']}/{s['eligibles_12']} ({s['taux_12']} %)</li>"
                     for m, s in sorted(r["resume_rattache"].items()))
    html = (f"<p>Rétention après accord de courtoisie, après rattachement des marchands non précisés.</p><ul>{resume}</ul>"
            "<table border=1 cellpadding=4><tr><th>Marchand (facture)</th><th>Marchand retenu</th><th>Client</th>"
            "<th>Courtoisie</th><th>Visites payées après</th><th>Revenu en 12 mois</th><th>Dernière</th><th>Indice</th></tr>"
            f"{lignes}</table>")
    ok = get_email_notifier().send_email(["asutton@piano-tek.com"], "Rapport : courtoisies Nantel / Archambault (rattachées)", html)
    note("Courriel", "envoyé à asutton@" if ok else "non envoyé")
except Exception as e:
    note("Courriel", f"non envoyé : {e}")
