from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from datetime import datetime


class BaseSubAgent(ABC):
    """Base class for specialized sub-agents"""
    
    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description
        self.created_at = datetime.utcnow()
        self.last_active = datetime.utcnow()
        
    @abstractmethod
    async def process(self, input_data: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Process input and return result"""
        pass
        
    @abstractmethod
    async def validate_input(self, input_data: Dict[str, Any]) -> bool:
        """Validate input data"""
        pass
        
    def update_activity(self):
        """Update last activity timestamp"""
        self.last_active = datetime.utcnow()
        
    def get_info(self) -> Dict[str, Any]:
        """Get agent information"""
        return {
            "name": self.name,
            "description": self.description,
            "created_at": self.created_at.isoformat(),
            "last_active": self.last_active.isoformat()
        }