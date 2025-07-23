"""
JWT Validation Module - Mock implementation for development
"""

from typing import Dict, Optional, Any
import structlog

logger = structlog.get_logger(__name__)


async def verify_token(token: Optional[str]) -> Dict[str, Any]:
    """
    Mock JWT token verification
    
    Args:
        token: JWT token to verify
        
    Returns:
        User information if valid
        
    Raises:
        ValueError: If token is invalid
    """
    
    if not token:
        raise ValueError("No token provided")
        
    # Mock validation - in production, this would verify against JWKS
    logger.info("Mock token validation", token_prefix=token[:10] if len(token) > 10 else token)
    
    # Return mock user data
    return {
        "sub": "mock-user-123",
        "email": "user@example.com",
        "name": "Mock User",
        "roles": ["user", "admin"],
        "tenant_id": "mock-tenant"
    }


class JWTValidator:
    """Mock JWT Validator for development"""
    
    def __init__(self):
        self.validated = False
        
    async def validate_token_async(self, token: str) -> bool:
        """Mock async token validation"""
        
        if not token:
            return False
            
        # Mock validation
        self.validated = True
        return True
        
    def get_user(self) -> Optional[Dict[str, Any]]:
        """Get user information from validated token"""
        
        if not self.validated:
            return None
            
        return {
            "upn": "mock.user@example.com",
            "name": "Mock User",
            "email": "mock.user@example.com",
            "groups": ["users", "admins"],
            "claims": {},
            "is_azure": False
        }