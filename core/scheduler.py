#!/usr/bin/env python3
"""
╔═══════════════════════════════════════════════════════════════════════════╗
║                     SCHEDULER CENTRALISÉ - ASSISTANT V5                    ║
║                   Tâches planifiées avec APScheduler                       ║
║                   + Orchestration & Notifications                          ║
╚═══════════════════════════════════════════════════════════════════════════╝

Gère toutes les tâches planifiées de l'application:
- 01:00: Sync Gazelle Totale → Rapport Timeline (chaînées automatiquement)
- 03:00: Backup SQL de la base de données
- 07:00-21:00 (toutes les heures): Sync Appointments - Détection des RV dernière minute
- 16:30: Sync Appointments - Capture les RV créés/modifiés dans la journée
- 16:00: URGENCE TECHNIQUE (J-1) - Alertes aux techniciens pour RV non confirmés
- 09:00: RELANCE LOUISE (J-7) - Relance pour RV créés il y a plus de 3 mois
- Toutes les 5 min: Traitement Late Assignment Queue (envoi emails)

Orchestration:
- Quand Sync Gazelle réussit → déclenche automatiquement Rapport Timeline
- Notifications Slack automatiques en cas d'erreur

Usage:
    from core.scheduler import get_scheduler, start_scheduler

    # Dans FastAPI startup
    start_scheduler()
"""

import os
import sys
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.events import EVENT_JOB_EXECUTED, EVENT_JOB_ERROR

# Ajouter le projet au path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()


# ============================================================
# SINGLETON SCHEDULER
# ============================================================

_scheduler: Optional[BackgroundScheduler] = None


def get_scheduler() -> BackgroundScheduler:
    """
    Retourne l'instance du scheduler (singleton).

    Returns:
        Instance APScheduler BackgroundScheduler
    """
    global _scheduler
    if _scheduler is None:
        _scheduler = BackgroundScheduler(timezone='America/Montreal')
        _scheduler.add_listener(_job_listener, EVENT_JOB_EXECUTED | EVENT_JOB_ERROR)
    return _scheduler


def _job_listener(event):
    """Listener pour logger l'exécution des jobs."""
    if event.exception:
        print(f"❌ Job {event.job_id} a échoué: {event.exception}")
    else:
        print(f"✅ Job {event.job_id} terminé avec succès")


# ============================================================
# HELPER POUR LOGGING
# ============================================================

def with_logging(task_name: str, task_label: str):
    """
    Decorator pour ajouter le logging automatique aux tâches.

    Args:
        task_name: Nom technique de la tâche
        task_label: Libellé affiché dans l'UI
    """
    def decorator(func):
        def wrapper(triggered_by='scheduler', user_email=None):
            from core.scheduler_logger import get_logger

            logger = get_logger()
            log_id = logger.start_task(
                task_name=task_name,
                task_label=task_label,
                triggered_by=triggered_by,
                triggered_by_user=user_email
            )

            try:
                # Exécuter la tâche
                result = func()

                # Logger le succès
                stats = result if isinstance(result, dict) else {}
                logger.complete_task(
                    log_id=log_id,
                    status='success',
                    message='Tâche terminée avec succès',
                    stats=stats
                )

                return result

            except Exception as e:
                # Logger l'erreur
                logger.complete_task(
                    log_id=log_id,
                    status='error',
                    message=str(e)
                )
                raise

        return wrapper
    return decorator


# ============================================================
# TÂCHES PLANIFIÉES
# ============================================================

def task_sync_gazelle_totale(triggered_by='scheduler', user_email=None):
    """
    01:00 - Sync Gazelle Totale

    Synchronise toutes les données depuis l'API Gazelle vers Supabase:
    - Clients
    - Contacts
    - Pianos
    - Timeline entries
    - Appointments

    Si succès, déclenche automatiquement la génération du rapport Timeline.

    Exécution: Tous les jours à 01:00 (heure Montréal)
    """
    from core.scheduler_logger import get_logger
    from core.notification_service import get_notification_service

    logger = get_logger()
    notifier = get_notification_service()
    
    log_id = logger.start_task(
        task_name='sync_gazelle',
        task_label='Sync Gazelle Totale',
        triggered_by=triggered_by,
        triggered_by_user=user_email
    )

    print("\n" + "="*70)
    print("🔄 SYNC GAZELLE TOTALE - Démarrage")
    print(f"   Heure: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*70)

    try:
        from modules.sync_gazelle.sync_to_supabase import GazelleToSupabaseSync

        syncer = GazelleToSupabaseSync()

        # Sync clients
        clients_count = syncer.sync_clients()
        print(f"✅ Clients synchronisés: {clients_count}")

        # Sync contacts
        contacts_count = syncer.sync_contacts()
        print(f"✅ Contacts synchronisés: {contacts_count}")

        # Sync pianos
        pianos_count = syncer.sync_pianos()
        print(f"✅ Pianos synchronisés: {pianos_count}")

        # Sync timeline - Utilise smart_import avec filtre anti-bruit (7 derniers jours)
        # Remplacé sync_timeline() par smart_import pour éviter le bruit (Mailchimp, emails)
        from scripts.smart_import_all_data import SmartImport
        
        # Calculer date de cutoff (7 jours en arrière, format ISO UTC)
        # datetime et timedelta sont déjà importés en haut du fichier
        cutoff_date = datetime.now() - timedelta(days=7)
        since_date_iso = cutoff_date.strftime('%Y-%m-%dT%H:%M:%SZ')
        
        print(f"📊 Timeline: Utilisation smart_import avec filtre anti-bruit (7 jours)")
        smart_importer = SmartImport(dry_run=False, delay=0.3)  # Délai réduit pour sync quotidienne
        timeline_result = smart_importer.import_timeline(since_date=since_date_iso)
        timeline_count = timeline_result.get('imported', 0)
        print(f"✅ Timeline entries synchronisées: {timeline_count} (sur {timeline_result.get('valuable', 0)} de haute valeur)")

        # Sync appointments
        appointments_count = syncer.sync_appointments()
        print(f"✅ Appointments synchronisés: {appointments_count}")

        print("\n" + "="*70)
        print("✅ SYNC GAZELLE TOTALE - Terminé")
        print("="*70 + "\n")

        stats = {
            'clients': clients_count,
            'contacts': contacts_count,
            'pianos': pianos_count,
            'timeline': timeline_count,
            'appointments': appointments_count
        }

        # Logger le succès
        logger.complete_task(
            log_id=log_id,
            status='success',
            message='Synchronisation complète réussie',
            stats=stats
        )

        # Rapport Timeline généré par GitHub Actions (full_gazelle_sync.yml)
        # pas par le scheduler Render — évite les doublons et les sheets vidés
        print("ℹ️  Rapport Timeline sera généré par GitHub Actions (pas ici)")

        return stats

    except Exception as e:
        print(f"\n❌ Erreur lors du sync Gazelle: {e}")
        import traceback
        traceback.print_exc()

        error_msg = str(e)

        # Logger l'erreur
        logger.complete_task(
            log_id=log_id,
            status='error',
            message=error_msg
        )

        # 📧 NOTIFICATION: Envoyer alerte Slack + Email (Allan) pour erreur de sync
        notifier.notify_sync_error(
            task_name='Sync Gazelle Totale',
            error_message=error_msg,
            send_slack=True,
            send_email=True  # Email à Allan pour erreurs critiques
        )

        raise


def task_generate_rapport_timeline():
    """
    02:00 - Génération Rapport Timeline Google Sheets

    Génère le rapport Timeline dans Google Sheets avec 4 onglets:
    - UQAM
    - Vincent d'Indy
    - Place des Arts
    - Alertes Maintenance

    Exécution: Tous les jours à 02:00 (heure Montréal)
    """
    print("\n" + "="*70)
    print("📊 RAPPORT TIMELINE - Démarrage")
    print(f"   Heure: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*70)

    try:
        from modules.reports.service_reports import run_reports

        # Générer le rapport (mode replace)
        result = run_reports(append=False)

        print("\n" + "="*70)
        print("✅ RAPPORT TIMELINE - Terminé")
        print("="*70)

        for tab, count in result.items():
            print(f"   {tab}: {count} lignes")

        print("\n🔗 Rapport disponible:")
        print("   https://docs.google.com/spreadsheets/d/1ZZsMrIT0BEwHKQ6-BKGzFoXR3k99zCEzixp0tsRKUj8")
        print()

    except Exception as e:
        print(f"\n❌ Erreur lors de la génération du rapport: {e}")
        import traceback
        traceback.print_exc()
        raise


def task_scan_pda_emails():
    """
    Scan automatique des emails PDA/OSM.

    Vérifie les emails de @placedesarts.com, @operademontreal.com, @osm.ca.
    Parse et importe automatiquement les nouvelles demandes.
    Notifie dans Front quand une demande est importée.

    Contrôlé par feature flag 'pda_auto_scanner'.
    """
    from core.feature_flags import is_enabled
    if not is_enabled('pda_auto_scanner'):
        return

    print("\n📧 SCAN PDA/OSM — Recherche de nouvelles demandes...")
    try:
        from modules.pda_auto_scanner import scan_and_watch
        result = scan_and_watch()
        print(f"✅ Scan terminé: {result['scanned']} vérifiés, {result['imported']} importés, {result['skipped']} déjà traités")
        if result['errors']:
            for err in result['errors']:
                print(f"   ⚠️ {err}")
    except Exception as e:
        print(f"❌ Erreur scan PDA: {e}")
        import traceback
        traceback.print_exc()


def task_backup_database():
    """
    03:00 - Backup SQL

    Crée une sauvegarde de la base de données SQLite.
    Garde les 10 derniers backups.

    Exécution: Tous les jours à 03:00 (heure Montréal)
    """
    print("\n" + "="*70)
    print("💾 BACKUP DATABASE - Démarrage")
    print(f"   Heure: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*70)

    try:
        from scripts.backup_db import backup_database

        backup_database()

        print("\n" + "="*70)
        print("✅ BACKUP DATABASE - Terminé")
        print("="*70 + "\n")

    except Exception as e:
        print(f"\n❌ Erreur lors du backup: {e}")
        import traceback
        traceback.print_exc()
        raise


def task_urgence_technique_j1():
    """
    URGENCE TECHNIQUE (J-1) : La veille à 16h, si un RV n'est pas 'Confirmed',
    envoie une alerte au technicien concerné (Nicolas, Allan ou JP).

    Exécution: Tous les jours à 16:00 (heure Montréal)
    """
    print("\n" + "="*70)
    print("🚨 URGENCE TECHNIQUE (J-1) - Démarrage")
    print(f"   Heure: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*70)

    try:
        from modules.alertes_rv.service import UnconfirmedAlertsService
        from core.supabase_storage import SupabaseStorage
        from modules.alertes_rv.checker import AppointmentChecker
        from modules.alertes_rv.email_sender import EmailSender

        storage = SupabaseStorage()
        checker = AppointmentChecker(storage)
        sender = EmailSender(method='resend')
        service = UnconfirmedAlertsService(storage, checker, sender)

        # Date cible: demain
        target_date = (datetime.now() + timedelta(days=1)).date()

        # Envoyer alertes automatiquement aux techniciens
        result = service.send_alerts(
            target_date=target_date,
            technician_ids=None,  # Tous les techniciens avec RV non confirmés
            triggered_by='scheduler_urgence_j1'
        )

        print(f"\n✅ Alertes URGENCE TECHNIQUE envoyées:")
        print(f"   - Emails envoyés: {result.get('sent_count', 0)}")
        if result.get('technicians'):
            for tech in result['technicians']:
                print(f"   - {tech['name']}: {tech['appointment_count']} RV non confirmé(s)")

        print("\n" + "="*70)
        print("✅ URGENCE TECHNIQUE (J-1) - Terminé")
        print("="*70 + "\n")

    except Exception as e:
        print(f"\n❌ Erreur lors de l'envoi des alertes URGENCE TECHNIQUE: {e}")
        import traceback
        traceback.print_exc()
        raise


def task_relance_louise_j7():
    """
    RELANCE LOUISE (J-7) : 7 jours avant un RV, si celui-ci a été créé il y a plus de 3 mois,
    envoie une alerte à Louise (info@piano-tek.com).

    Exécution: Tous les jours à 09:00 (heure Montréal)
    """
    print("\n" + "="*70)
    print("📧 RELANCE LOUISE (J-7) - Démarrage")
    print(f"   Heure: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*70)

    try:
        from modules.alertes_rv.service import UnconfirmedAlertsService
        from core.supabase_storage import SupabaseStorage
        from modules.alertes_rv.checker import AppointmentChecker
        from modules.alertes_rv.email_sender import EmailSender

        storage = SupabaseStorage()
        checker = AppointmentChecker(storage)
        sender = EmailSender(method='resend')
        service = UnconfirmedAlertsService(storage, checker, sender)

        # Vérifier les RV dans 7 jours créés il y a plus de 3 mois
        result = service.check_relance_louise()

        if result.get('success'):
            print(f"\n✅ Relance LOUISE envoyée:")
            print(f"   - RV concernés: {result.get('count', 0)}")
            print(f"   - Date cible: {result.get('target_date')}")
        else:
            print(f"\n⚠️ {result.get('message', 'Erreur inconnue')}")

        print("\n" + "="*70)
        print("✅ RELANCE LOUISE (J-7) - Terminé")
        print("="*70 + "\n")

    except Exception as e:
        print(f"\n❌ Erreur lors de l'envoi de la relance LOUISE: {e}")
        import traceback
        traceback.print_exc()
        raise


def task_follow_up_digest():
    """
    Digest quotidien 8h des soumissions actives sans relance (tag relance-faite).
    Fenetre 7-90 jours. Envoi a info@piano-tek.com.
    """
    try:
        print("\n" + "=" * 70)
        print("TACHE : Follow-up Digest (8h)")
        print("=" * 70)
        from modules.briefing.follow_up_digest import run_follow_up_digest
        import asyncio
        result = asyncio.run(run_follow_up_digest())
        print(f"Resultat : {result}")
    except Exception as exc:
        import traceback
        print(f"Erreur follow_up_digest : {exc}")
        traceback.print_exc()


def task_critical_estimate_digest():
    """
    Envoie le digest quotidien à Louise des RV à venir avec soumissions
    critiques non confirmées. Scanne les 7 prochains jours, déduplique sur
    7 jours glissants, envoie via Resend.
    """
    try:
        print("\n" + "=" * 70)
        print("📋 TÂCHE : Critical Estimate Digest (7h)")
        print("=" * 70)
        from modules.briefing.critical_estimate_digest import run_critical_estimate_digest
        import asyncio
        result = asyncio.run(run_critical_estimate_digest())
        print(f"📊 Résultat : {result}")
    except Exception as exc:
        import traceback
        print(f"❌ Erreur critical_estimate_digest : {exc}")
        traceback.print_exc()


def task_push_digest():
    """
    Digest quotidien 17h (lun-ven) des fiches d'accord validees pas encore
    poussees vers Gazelle. Destinataire info@, escalation Allan en CC apres
    3 jours sans push. Aucun email si zero fiche en attente.
    """
    try:
        print("\n" + "=" * 70)
        print("TACHE : Push Digest (17h)")
        print("=" * 70)
        from modules.briefing.push_digest import run_push_digest
        import asyncio
        result = asyncio.run(run_push_digest())
        print(f"Resultat : {result}")
    except Exception as exc:
        import traceback
        print(f"Erreur push_digest : {exc}")
        traceback.print_exc()


def task_process_late_assignment_queue():
    """
    Traite la file d'attente des alertes d'assignation tardive.

    Envoie les emails aux techniciens pour les RV assignés < 24h avant.
    Exécuté toutes les 5 minutes et à 07:05.
    """
    try:
        print("\n" + "="*70)
        print("📧 TRAITEMENT LATE ASSIGNMENT QUEUE")
        print("="*70)

        from modules.late_assignment.late_assignment_notifier import LateAssignmentNotifier

        notifier = LateAssignmentNotifier()
        result = notifier.process_queue()

        print(f"   Traité: {result.get('processed', 0)}, Envoyé: {result.get('sent', 0)}, Échec: {result.get('failed', 0)}")
        print("="*70 + "\n")

        return result

    except Exception as e:
        print(f"\n❌ Erreur traitement late assignment queue: {e}")
        import traceback
        traceback.print_exc()
        raise


def task_sync_appointments_only(triggered_by='scheduler', user_email=None):
    """
    16:30 - Sync Appointments uniquement
    
    Synchronise uniquement les rendez-vous pour capturer ceux créés/modifiés
    dans la journée (jusqu'à 16:30).
    
    Utile pour voir les rendez-vous ajoutés après la sync matinale (01:00).
    """
    from core.scheduler_logger import get_logger
    from modules.sync_gazelle.sync_to_supabase import GazelleToSupabaseSync

    logger = get_logger()
    log_id = logger.start_task(
        task_name='sync_appointments_1630',
        task_label='Sync Appointments (16:30)',
        triggered_by=triggered_by,
        triggered_by_user=user_email
    )

    try:
        print("\n" + "="*70)
        print("📅 SYNC APPOINTMENTS (16:30)")
        print("="*70)

        # Mode incrémental (7 derniers jours) pour performance
        syncer = GazelleToSupabaseSync(incremental_mode=True)

        # Sync appointments uniquement
        appointments_count = syncer.sync_appointments()
        print(f"✅ Appointments synchronisés: {appointments_count}")

        # Lier les demandes PDA/OSM aux RV Gazelle automatiquement
        # Sans ça, place_des_arts_requests.technician_id reste à "À attribuer"
        # jusqu'à ce que quelqu'un clique le bouton Synchroniser dans le dashboard
        pda_sync_count = 0
        try:
            from modules.place_des_arts.services.gazelle_sync import GazelleSyncService
            pda_service = GazelleSyncService()
            pda_result = pda_service.sync_requests_with_gazelle(dry_run=False)
            pda_sync_count = pda_result.get('updated', 0)
            print(f"✅ Demandes PDA/OSM synchronisées avec Gazelle: {pda_sync_count}")
        except Exception as pda_exc:
            print(f"⚠️  Sync PDA/OSM échouée (non bloquant): {pda_exc}")

        print("\n" + "="*70)
        print("✅ SYNC APPOINTMENTS - Terminé")
        print("="*70 + "\n")

        stats = {
            'appointments': appointments_count,
            'pda_sync': pda_sync_count
        }

        # Logger le succès
        logger.complete_task(
            log_id=log_id,
            status='success',
            message=f'{appointments_count} rendez-vous synchronisés',
            stats=stats
        )

        return stats

    except Exception as e:
        print(f"\n❌ Erreur lors de la sync appointments (16:30): {e}")
        import traceback
        traceback.print_exc()
        
        # Logger l'erreur
        logger.complete_task(
            log_id=log_id,
            status='error',
            message=str(e),
            stats={}
        )
        raise


def task_scan_pda_emails():
    """
    Scan Gmail pour les nouvelles demandes PDA.

    Lit la boîte info@piano-tek.com, parse les emails de
    @placedesarts.com et @operademontreal.com, crée les demandes
    automatiquement et envoie un récapitulatif par email.

    Exécuté toutes les heures (heures ouvrables).
    """
    try:
        print("\n" + "=" * 70)
        print("📬 SCAN GMAIL - DEMANDES PDA")
        print("=" * 70)

        from modules.place_des_arts.services.email_processor import get_email_processor

        processor = get_email_processor()
        result = processor.run_scan()

        print(f"   Emails trouvés: {result.get('emails_found', 0)}")
        print(f"   Emails traités: {result.get('emails_processed', 0)}")
        print(f"   Demandes créées: {result.get('requests_created', 0)}")
        print(f"   Confirmations: {result.get('confirmations_sent', 0)}")

        if result.get('errors'):
            for err in result['errors']:
                print(f"   ⚠️ {err}")

        print("=" * 70 + "\n")
        return result

    except Exception as e:
        print(f"\n❌ Erreur scan PDA emails: {e}")
        import traceback
        traceback.print_exc()
        raise


# ============================================================
# RAPPEL VALIDATION FICHES DE SERVICE (17h)
# ============================================================

def task_rappel_validation():
    """
    Envoie un rappel à Nicolas s'il y a des fiches de service
    complétées en attente de validation.
    """
    print("\n" + "="*60)
    print("📧 RAPPEL VALIDATION FICHES DE SERVICE")
    print("="*60)

    try:
        import os
        from supabase import create_client
        from core.email_notifier import EmailNotifier

        sb_url = os.getenv("SUPABASE_URL")
        sb_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        if not sb_url or not sb_key:
            print("⚠️ Config Supabase manquante, rappel annulé")
            return

        sb = create_client(sb_url, sb_key)

        # Chercher fiches completed (en attente de validation)
        response = (
            sb.table("piano_service_records")
            .select("piano_id,institution_slug,completed_at,completed_by,technician_email,travail")
            .eq("status", "completed")
            .order("completed_at", desc=True)
            .execute()
        )

        records = response.data or []
        if not records:
            print("✅ Aucune fiche en attente de validation")
            return

        # Grouper par institution
        by_institution = {}
        for r in records:
            inst = r.get("institution_slug", "?")
            by_institution.setdefault(inst, []).append(r)

        # Construire l'email
        lines = []
        for inst, recs in by_institution.items():
            lines.append(f"<h3>{inst} — {len(recs)} piano(s)</h3>")
            lines.append("<ul>")
            for r in recs[:10]:  # Max 10 par institution
                tech = r.get("completed_by") or r.get("technician_email") or "?"
                travail_preview = (r.get("travail") or "")[:60]
                lines.append(f"<li><b>{r['piano_id']}</b> — {tech}: {travail_preview}</li>")
            if len(recs) > 10:
                lines.append(f"<li>... et {len(recs) - 10} autre(s)</li>")
            lines.append("</ul>")

        html_content = f"""
        <h2>📋 Fiches de service à valider</h2>
        <p>{len(records)} fiche(s) complétée(s) par les techniciens aujourd'hui, en attente de validation.</p>
        {"".join(lines)}
        <hr>
        <p style="color: #666; font-size: 12px;">Rappel automatique — Assistant Gazelle V5</p>
        """

        notifier = EmailNotifier()
        if notifier.client:
            nicolas_email = os.getenv('EMAIL_NICOLAS', 'nlessard@piano-tek.com')
            info_email = os.getenv('EMAIL_INFO', 'info@piano-tek.com')
            notifier.send_email(
                to_emails=[nicolas_email, info_email],
                subject=f"📋 {len(records)} fiche(s) de service à valider",
                html_content=html_content
            )
            print(f"✅ Rappel envoyé à {nicolas_email} et {info_email}: {len(records)} fiche(s)")
        else:
            print("⚠️ Email notifier non configuré")

    except Exception as e:
        print(f"❌ Erreur rappel validation: {e}")
        import traceback
        traceback.print_exc()


# ============================================================
# CONFIGURATION DU SCHEDULER
# ============================================================

def configure_jobs(scheduler: BackgroundScheduler):
    """
    Configure toutes les tâches planifiées.

    Args:
        scheduler: Instance du scheduler APScheduler
    """
    print("\n📅 Configuration des tâches planifiées...")

    # 01:00 - Sync Gazelle Totale → Timeline (chaînées)
    scheduler.add_job(
        task_sync_gazelle_totale,
        trigger=CronTrigger(hour=1, minute=0, timezone='America/Montreal'),
        id='sync_gazelle_totale',
        name='Sync Gazelle → Timeline (01:00)',
        replace_existing=True,
        max_instances=1
    )
    print("   ✅ 01:00 - Sync Gazelle → Timeline (chaînées)")

    # 03:00 - Backup Database
    scheduler.add_job(
        task_backup_database,
        trigger=CronTrigger(hour=3, minute=0, timezone='America/Montreal'),
        id='backup_database',
        name='Backup SQL (03:00)',
        replace_existing=True,
        max_instances=1
    )
    print("   ✅ 03:00 - Backup SQL configurée")

    # 16:00 - URGENCE TECHNIQUE (J-1)
    scheduler.add_job(
        task_urgence_technique_j1,
        trigger=CronTrigger(hour=16, minute=0, timezone='America/Montreal'),
        id='urgence_technique_j1',
        name='URGENCE TECHNIQUE (J-1) - 16:00',
        replace_existing=True,
        max_instances=1
    )
    print("   ✅ 16:00 - URGENCE TECHNIQUE (J-1) configurée")

    # 07:00 - Digest quotidien des soumissions critiques à Louise
    scheduler.add_job(
        task_critical_estimate_digest,
        trigger=CronTrigger(hour=7, minute=0, timezone='America/Montreal'),
        id='critical_estimate_digest',
        name='Digest soumissions critiques Louise (07:00)',
        replace_existing=True,
        max_instances=1
    )
    print("   ✅ 07:00 - Digest soumissions critiques (Louise) configurée")

    # 08:00 - Digest quotidien des soumissions sans relance à info@
    scheduler.add_job(
        task_follow_up_digest,
        trigger=CronTrigger(hour=8, minute=0, timezone='America/Montreal'),
        id='follow_up_digest',
        name='Digest suivi soumissions info@ (08:00)',
        replace_existing=True,
        max_instances=1
    )
    print("   ✅ 08:00 - Digest suivi soumissions (info@) configurée")

    # 17:00 - Digest fiches d'accord validees a pousser (lun-ven)
    scheduler.add_job(
        task_push_digest,
        trigger=CronTrigger(
            day_of_week='mon-fri',
            hour=17, minute=0,
            timezone='America/Montreal',
        ),
        id='push_digest',
        name='Digest fiches d\'accord a pousser info@ (17:00 lun-ven)',
        replace_existing=True,
        max_instances=1
    )
    print("   ✅ 17:00 - Digest fiches d'accord a pousser (info@, lun-ven) configurée")

    # 07:05 - Traitement file d'attente Late Assignment (alertes mises en attente pendant la nuit)
    scheduler.add_job(
        task_process_late_assignment_queue,
        trigger=CronTrigger(hour=7, minute=5, timezone='America/Montreal'),
        id='late_assignment_morning',
        name='Traitement Late Assignment (07:05)',
        replace_existing=True,
        max_instances=1
    )
    print("   ✅ 07:05 - Traitement Late Assignment (matin) configurée")

    # Toutes les 5 minutes - Traitement file d'attente Late Assignment (buffer 5 min)
    scheduler.add_job(
        task_process_late_assignment_queue,
        trigger=CronTrigger(minute='*/5', timezone='America/Montreal'),
        id='late_assignment_frequent',
        name='Traitement Late Assignment (toutes les 5 min)',
        replace_existing=True,
        max_instances=1
    )
    print("   ✅ Toutes les 5 min - Traitement Late Assignment configurée")

    # 09:00 - RELANCE LOUISE (J-7)
    scheduler.add_job(
        task_relance_louise_j7,
        trigger=CronTrigger(hour=9, minute=0, timezone='America/Montreal'),
        id='relance_louise_j7',
        name='RELANCE LOUISE (J-7) - 09:00',
        replace_existing=True,
        max_instances=1
    )
    print("   ✅ 09:00 - RELANCE LOUISE (J-7) configurée")

    # 16:30 - Sync Appointments (pour capturer les RV créés dans la journée)
    scheduler.add_job(
        task_sync_appointments_only,
        trigger=CronTrigger(hour=16, minute=30, timezone='America/Montreal'),
        id='sync_appointments_1630',
        name='Sync Appointments (16:30)',
        replace_existing=True,
        max_instances=1
    )
    print("   ✅ 16:30 - Sync Appointments configurée")

    # Toutes les heures (heures ouvrables 7h-21h) - Sync Appointments pour détecter les RV dernière minute
    scheduler.add_job(
        task_sync_appointments_only,
        trigger=CronTrigger(hour='7-21', minute=0, timezone='America/Montreal'),
        id='sync_appointments_hourly',
        name='Sync Appointments (horaire 7h-21h)',
        replace_existing=True,
        max_instances=1
    )
    print("   ✅ Toutes les heures (7h-21h) - Sync Appointments configurée")

    # Toutes les heures (heures ouvrables 8h-18h) - Scan Gmail pour demandes PDA
    scheduler.add_job(
        task_scan_pda_emails,
        trigger=CronTrigger(hour='8-18', minute=30, timezone='America/Montreal'),
        id='scan_pda_emails_hourly',
        name='Scan Gmail PDA (horaire 8h30-18h30)',
        replace_existing=True,
        max_instances=1
    )
    print("   ✅ Toutes les heures (8h30-18h30) - Scan Gmail PDA configurée")

    # 17:00 - Rappel validation fiches de service
    scheduler.add_job(
        task_rappel_validation,
        trigger=CronTrigger(hour=17, minute=0, timezone='America/Montreal'),
        id='rappel_validation',
        name='Rappel validation fiches de service',
        replace_existing=True,
        max_instances=1
    )
    print("   ✅ 17:00 - Rappel validation fiches de service configuré")

    print("\n✅ Toutes les tâches planifiées sont configurées\n")
    print("ℹ️  Note: Le Rapport Timeline est généré par GitHub Actions (full_gazelle_sync.yml), pas par le scheduler Render\n")


def start_scheduler():
    """
    Démarre le scheduler avec toutes les tâches configurées.
    À appeler dans le startup event de FastAPI.
    """
    scheduler = get_scheduler()

    if not scheduler.running:
        configure_jobs(scheduler)
        scheduler.start()
        print("🚀 Scheduler démarré avec succès\n")

        # Afficher les prochaines exécutions
        print("📅 Prochaines exécutions:")
        for job in scheduler.get_jobs():
            next_run = job.next_run_time
            print(f"   - {job.name}: {next_run.strftime('%Y-%m-%d %H:%M:%S')}")
        print()
    else:
        print("⚠️  Scheduler déjà en cours d'exécution")


def stop_scheduler():
    """
    Arrête le scheduler proprement.
    À appeler dans le shutdown event de FastAPI.
    """
    scheduler = get_scheduler()

    if scheduler.running:
        scheduler.shutdown(wait=False)
        print("🛑 Scheduler arrêté")
    else:
        print("⚠️  Scheduler n'était pas en cours d'exécution")


# ============================================================
# EXPORTS
# ============================================================

__all__ = [
    'get_scheduler',
    'start_scheduler',
    'stop_scheduler',
    'task_sync_gazelle_totale',
    'task_generate_rapport_timeline',
    'task_backup_database',
    'task_sync_appointments_only',
    'task_process_late_assignment_queue',
    'task_urgence_technique_j1',
    'task_relance_louise_j7'
]
