#!/usr/bin/env python3
"""
Gestion de l'authentification avec Supabase Auth.

Vérifie les tokens JWT et extrait les informations utilisateur.
"""

import os
import jwt
from typing import Optional, Dict, Any
from fastapi import Header, HTTPException, Depends
from jwt import PyJWTError


class AuthService:
    """Service d'authentification Supabase."""
    
    def __init__(self):
        self.supabase_jwt_secret = os.environ.get('SUPABASE_JWT_SECRET')
        if not self.supabase_jwt_secret:
            print("⚠️  SUPABASE_JWT_SECRET non configuré - l'auth sera désactivée")
    
    def verify_token(self, token: str) -> Dict[str, Any]:
        """
        Vérifie un token JWT Supabase et retourne les infos user.
        
        Args:
            token: Token JWT (sans le préfixe "Bearer ")
            
        Returns:
            Dict avec user_id, email, role, etc.
            
        Raises:
            HTTPException si token invalide
        """
        if not self.supabase_jwt_secret:
            # Mode dev sans auth
            return {
                "user_id": "dev-user",
                "email": "dev@localhost",
                "name": "Dev User",
                "role": "admin"
            }
        
        try:
            # Décoder le JWT avec la clé secrète Supabase
            payload = jwt.decode(
                token,
                self.supabase_jwt_secret,
                algorithms=["HS256"],
                audience="authenticated"
            )
            
            # Extraire les infos user
            user_id = payload.get("sub")
            email = payload.get("email")
            user_metadata = payload.get("user_metadata", {})
            
            return {
                "user_id": user_id,
                "email": email,
                "name": user_metadata.get("name", email.split("@")[0]),
                "role": user_metadata.get("role", "tech")
            }
            
        except PyJWTError as e:
            raise HTTPException(
                status_code=401,
                detail=f"Token invalide: {str(e)}"
            )
    
    def get_current_user(
        self,
        authorization: Optional[str] = Header(None)
    ) -> Dict[str, Any]:
        """
        Dependency pour FastAPI - récupère l'user depuis le header Authorization.
        
        Usage:
            @router.put("/pianos/{piano_id}")
            async def update_piano(
                piano_id: str,
                user: Dict = Depends(auth_service.get_current_user)
            ):
                # user contient user_id, email, name, role
                ...
        """
        if not authorization:
            # Mode dev sans auth
            if not self.supabase_jwt_secret:
                return {
                    "user_id": "dev-user",
                    "email": "dev@localhost",
                    "name": "Dev User",
                    "role": "admin"
                }
            raise HTTPException(
                status_code=401,
                detail="Authorization header manquant"
            )
        
        # Extraire le token (enlever "Bearer ")
        if not authorization.startswith("Bearer "):
            raise HTTPException(
                status_code=401,
                detail="Format Authorization invalide (attendu: 'Bearer TOKEN')"
            )
        
        token = authorization[7:]  # Enlever "Bearer "
        return self.verify_token(token)


# Instance globale
auth_service = AuthService()


# Dependency pour FastAPI
def get_current_user(
    authorization: Optional[str] = Header(None)
) -> Dict[str, Any]:
    """
    Dependency FastAPI pour récupérer l'utilisateur courant.
    
    Usage:
        @router.put("/pianos/{piano_id}")
        async def update_piano(
            piano_id: str,
            user: Dict = Depends(get_current_user)
        ):
            print(f"Modification par {user['name']} ({user['email']})")
            ...
    """
    return auth_service.get_current_user(authorization)







