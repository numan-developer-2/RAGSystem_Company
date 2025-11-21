"""
Authentication and Role-Based Access Control
"""
from typing import Optional, Dict
from fastapi import HTTPException, Header, Depends
from enum import Enum
import secrets
import hashlib
from datetime import datetime, timedelta


class UserRole(str, Enum):
    ADMIN = "admin"
    USER = "user"
    VIEWER = "viewer"


class AuthManager:
    """Manage authentication and authorization"""
    
    def __init__(self):
        # In production, use database
        self.api_keys = {
            # Format: "api_key": {"user_id": "...", "role": "...", "name": "..."}
            self._hash_key("admin_key_123"): {
                "user_id": "admin_1",
                "role": UserRole.ADMIN,
                "name": "Admin User",
                "created_at": datetime.now().isoformat()
            },
            self._hash_key("user_key_456"): {
                "user_id": "user_1",
                "role": UserRole.USER,
                "name": "Regular User",
                "created_at": datetime.now().isoformat()
            }
        }
    
    def _hash_key(self, key: str) -> str:
        """Hash API key for storage"""
        return hashlib.sha256(key.encode()).hexdigest()
    
    def verify_api_key(self, api_key: str) -> Optional[Dict]:
        """Verify API key and return user info"""
        hashed = self._hash_key(api_key)
        return self.api_keys.get(hashed)
    
    def generate_api_key(self, user_id: str, role: UserRole, name: str) -> str:
        """Generate new API key"""
        key = secrets.token_urlsafe(32)
        hashed = self._hash_key(key)
        
        self.api_keys[hashed] = {
            "user_id": user_id,
            "role": role,
            "name": name,
            "created_at": datetime.now().isoformat()
        }
        
        return key
    
    def check_permission(self, user_info: Dict, required_role: UserRole) -> bool:
        """Check if user has required role"""
        user_role = user_info.get("role")
        
        # Admin has all permissions
        if user_role == UserRole.ADMIN:
            return True
        
        # Check specific role
        if required_role == UserRole.USER:
            return user_role in [UserRole.USER, UserRole.ADMIN]
        
        if required_role == UserRole.VIEWER:
            return user_role in [UserRole.VIEWER, UserRole.USER, UserRole.ADMIN]
        
        return False


# Global auth manager
auth_manager = AuthManager()


# Dependency for FastAPI
async def get_current_user(
    x_api_key: Optional[str] = Header(None, alias="X-API-Key")
) -> Dict:
    """FastAPI dependency to get current user from API key"""
    if not x_api_key:
        raise HTTPException(
            status_code=401,
            detail="Missing API key. Please provide X-API-Key header."
        )
    
    user_info = auth_manager.verify_api_key(x_api_key)
    if not user_info:
        raise HTTPException(
            status_code=401,
            detail="Invalid API key"
        )
    
    return user_info


async def require_admin(current_user: Dict = Depends(get_current_user)) -> Dict:
    """Require admin role"""
    if not auth_manager.check_permission(current_user, UserRole.ADMIN):
        raise HTTPException(
            status_code=403,
            detail="Admin access required"
        )
    return current_user


async def require_user(current_user: Dict = Depends(get_current_user)) -> Dict:
    """Require user role or higher"""
    if not auth_manager.check_permission(current_user, UserRole.USER):
        raise HTTPException(
            status_code=403,
            detail="User access required"
        )
    return current_user
