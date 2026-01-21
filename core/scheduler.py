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
- 16:00: Sync RV & Alertes (rendez-vous non confirmés)

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

        # 🔗 ORCHESTRATION: Déclencher le rapport Timeline automatiquement
        print("\n🔗 Chaînage: Génération automatique du Rapport Timeline...")
        try:
            task_generate_rapport_timeline()
            print("✅ Chaîne Gazelle → Timeline complétée avec succès\n")
            
            # Notifier le succès de la chaîne (optionnel, désactivé par défaut)
            # notifier.notify_chain_completion(
            #     chain_name="Gazelle → Timeline",
            #     tasks=[
            #         {'name': 'Sync Gazelle', 'status': 'success'},
            #         {'name': 'Rapport Timeline', 'status': 'success'}
            #     ]
            # )
        except Exception as timeline_error:
            print(f"⚠️ Erreur lors de la génération du rapport Timeline: {timeline_error}")
            # Notifier l'échec du rapport (mais le sync Gazelle a réussi)
            notifier.notify_sync_error(
                task_name='Rapport Timeline (auto après Gazelle)',
                error_message=str(timeline_error),
                send_slack=True,
                send_email=False
            )

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

        # 📧 NOTIFICATION: Envoyer alerte Slack pour erreur de sync
        notifier.notify_sync_error(
            task_name='Sync Gazelle Totale',
            error_message=error_msg,
            send_slack=True,
            send_email=False  # Email désactivé par défaut, Slack suffit
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


def task_sync_rv_and_alerts():
    """
    16:00 - Sync RV & Alertes

    Importation ciblée des rendez-vous et détection des RV non confirmés
    pour le lendemain. Envoie des alertes aux techniciens concernés.

    Exécution: Tous les jours à 16:00 (heure Montréal)
    """
    print("\n" + "="*70)
    print("📅 SYNC RV & ALERTES - Démarrage")
    print(f"   Heure: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*70)

    try:
        # 1. Sync appointments depuis Gazelle
        print("\n🔄 Étape 1/2: Synchronisation des appointments...")
        from modules.sync_gazelle.sync_to_supabase import GazelleToSupabaseSync

        syncer = GazelleToSupabaseSync()
        appointments_count = syncer.sync_appointments()
        print(f"✅ Appointments synchronisés: {appointments_count}")

        # 2. Vérifier et envoyer alertes pour RV non confirmés de demain
        print("\n📧 Étape 2/2: Vérification et envoi d'alertes...")
        from modules.alertes_rv.service import UnconfirmedAlertsService
        from core.supabase_storage import SupabaseStorage
        from modules.alertes_rv.checker import AppointmentChecker
        from modules.alertes_rv.email_sender import EmailSender

        storage = SupabaseStorage()
        checker = AppointmentChecker(storage)
        sender = EmailSender(method='sendgrid')
        service = UnconfirmedAlertsService(storage, checker, sender)

        # Date cible: demain
        target_date = (datetime.now() + timedelta(days=1)).date()

        # Envoyer alertes automatiquement
        result = service.send_alerts(
            target_date=target_date,
            technician_ids=None,  # Tous les techniciens avec RV non confirmés
            triggered_by='scheduler'
        )

        print(f"\n✅ Alertes envoyées:")
        print(f"   - Techniciens concernés: {result['total_technicians']}")
        print(f"   - RV non confirmés: {result['total_appointments']}")
        print(f"   - Emails envoyés: {result['emails_sent']}")

        print("\n" + "="*70)
        print("✅ SYNC RV & ALERTES - Terminé")
        print("="*70 + "\n")

    except Exception as e:
        print(f"\n❌ Erreur lors du sync RV & alertes: {e}")
        import traceback
        traceback.print_exc()
        raise


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

    # 16:00 - Sync RV & Alertes
    scheduler.add_job(
        task_sync_rv_and_alerts,
        trigger=CronTrigger(hour=16, minute=0, timezone='America/Montreal'),
        id='sync_rv_alerts',
        name='Sync RV & Alertes (16:00)',
        replace_existing=True,
        max_instances=1
    )
    print("   ✅ 16:00 - Sync RV & Alertes configurée")

    print("\n✅ Toutes les tâches planifiées sont configurées\n")
    print("ℹ️  Note: Le Rapport Timeline est généré automatiquement après Sync Gazelle\n")


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
    'task_sync_rv_and_alerts'
]
