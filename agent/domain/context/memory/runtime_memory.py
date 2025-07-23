from typing import Dict, List, Any, Optional
from datetime import datetime
import asyncio
from collections import defaultdict


class RuntimeMemory:
    """Manages runtime memory for active sessions"""
    
    def __init__(self):
        self.conversations: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        self.session_data: Dict[str, Dict[str, Any]] = {}
        self._lock = asyncio.Lock()
        
    async def add_to_conversation(self, session_id: str, message: Dict[str, Any]):
        """Add a message to conversation history"""
        
        async with self._lock:
            # Add timestamp if not present
            if "timestamp" not in message:
                message["timestamp"] = datetime.utcnow().isoformat()
                
            self.conversations[session_id].append(message)
            
            # Limit conversation history to 100 messages
            if len(self.conversations[session_id]) > 100:
                self.conversations[session_id] = self.conversations[session_id][-100:]
                
    async def get_conversation_history(self, session_id: str) -> List[Dict[str, Any]]:
        """Get conversation history for a session"""
        
        async with self._lock:
            return self.conversations.get(session_id, []).copy()
            
    async def set_session_data(self, session_id: str, key: str, value: Any):
        """Set session-specific data"""
        
        async with self._lock:
            if session_id not in self.session_data:
                self.session_data[session_id] = {}
            self.session_data[session_id][key] = value
            
    async def get_session_data(self, session_id: str, key: str) -> Optional[Any]:
        """Get session-specific data"""
        
        async with self._lock:
            if session_id in self.session_data:
                return self.session_data[session_id].get(key)
            return None
            
    async def clear_session(self, session_id: str):
        """Clear all data for a session"""
        
        async with self._lock:
            self.conversations.pop(session_id, None)
            self.session_data.pop(session_id, None)