"""
Orchestrateur : reçoit une demande chat, route vers la bonne action.

Flow :
1. detect_intent → identifie create / improve / unknown
2. rate_limiter.check → bloque si quota dépassé
3. preview_create_estimate ou preview_improve_estimate
4. log_action(status='preview', preview_token=...)
5. retourne le preview + token

L'utilisateur appelle ensuite /chat/action/execute avec le token pour confirmer.
"""
from typing import Dict

from .intent_detector import detect_intent
from .estimate_actions import preview_create_estimate, preview_improve_estimate
from .audit_log import log_action, generate_preview_token
from .rate_limiter import check_rate_limit


def dispatch_chat_action(text: str, user_id: str, user_role: str = 'technicien') -> Dict:
    """
    Point d'entrée principal. Retourne un dict :
        {
            'recognized': bool,
            'action_type': str | None,
            'preview': dict | None,
            'preview_token': str | None,
            'message': str,
        }
    """
    intent = detect_intent(text)

    # 1. Intention non reconnue
    if intent['intent'] == 'unknown':
        log_action(
            user_id=user_id,
            user_role=user_role,
            action_type='unknown',
            intent_text=text,
            status='rejected',
            error_message='intent unknown',
        )
        return {
            'recognized': False,
            'message': (
                "Je n'ai pas reconnu d'action sur soumission dans ta demande. "
                "Exemples : « fais-moi une soumission marteaux + cordes basses pour Mme Joly » "
                "ou « améliore la soumission #11929 »."
            ),
        }

    # 2. Rate limit (sur l'execute, pas sur la preview)
    # On vérifie l'historique des executes pour anticiper
    ok, msg = check_rate_limit(user_id, 'estimate.execute')
    if not ok:
        log_action(
            user_id=user_id,
            user_role=user_role,
            action_type='estimate.preview',
            intent_text=text,
            status='rejected',
            error_message=msg,
        )
        return {'recognized': True, 'message': msg}

    # 3. Construire le preview selon l'intent
    if intent['intent'] == 'create':
        result = preview_create_estimate(intent)
        action_type = 'estimate.create'
    elif intent['intent'] == 'improve':
        result = preview_improve_estimate(intent)
        action_type = 'estimate.improve'
    else:
        return {'recognized': False, 'message': 'Intent non géré'}

    if not result.get('ok'):
        log_action(
            user_id=user_id,
            user_role=user_role,
            action_type=f'{action_type}.preview',
            intent_text=text,
            status='rejected',
            error_message=result.get('message', 'preview failed'),
        )
        return {'recognized': True, 'action_type': action_type, 'message': result['message']}

    # 4. Log la preview avec un token
    token = generate_preview_token()
    log_action(
        user_id=user_id,
        user_role=user_role,
        action_type=f'{action_type}.preview',
        intent_text=text,
        target_resource=str(intent.get('estimate_number')) if intent.get('estimate_number') else None,
        payload=result.get('preview'),
        status='preview',
        preview_token=token,
    )

    return {
        'recognized': True,
        'action_type': action_type,
        'preview': result['preview'],
        'preview_token': token,
        'message': result['message'],
    }
