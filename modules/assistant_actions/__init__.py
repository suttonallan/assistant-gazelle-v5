"""
Actions exécutables par l'assistant chat (mutations Gazelle).

Architecture :
- intent_detector : reconnaît l'intention dans le texte du user
- estimate_actions : crée ou améliore une soumission Gazelle
- audit_log : logue chaque action dans assistant_actions_log
- rate_limiter : limite N actions / heure / user

Flow standard :
1. User → /chat/action/preview avec son texte
2. detect_intent → action_type + paramètres
3. rate_limiter.check → ok ou refusé
4. action.preview → retourne le plan + preview_token
5. User confirme → /chat/action/execute avec le token
6. action.execute → mutation Gazelle + audit log
"""
