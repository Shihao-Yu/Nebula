from typing import Dict, Any, Optional
import asyncio
from datetime import datetime
import json


class StateManager:
    """Manages agent state across sessions"""
    
    def __init__(self):
        self.states: Dict[str, Dict[str, Any]] = {}
        self._lock = asyncio.Lock()
        
    async def get_current_state(self, session_id: str) -> Dict[str, Any]:
        """Get current state for a session"""
        
        async with self._lock:
            return self.states.get(session_id, {
                "session_id": session_id,
                "status": "idle",
                "created_at": datetime.utcnow().isoformat(),
                "last_updated": datetime.utcnow().isoformat()
            })
            
    async def update_state(self, session_id: str, updates: Dict[str, Any]):
        """Update state for a session"""
        
        async with self._lock:
            if session_id not in self.states:
                self.states[session_id] = {
                    "session_id": session_id,
                    "created_at": datetime.utcnow().isoformat()
                }
                
            self.states[session_id].update(updates)
            self.states[session_id]["last_updated"] = datetime.utcnow().isoformat()
            
    async def clear_state(self, session_id: str):
        """Clear state for a session"""
        
        async with self._lock:
            self.states.pop(session_id, None)
            
    async def get_all_active_sessions(self) -> Dict[str, Dict[str, Any]]:
        """Get all active session states"""
        
        async with self._lock:
            return self.states.copy()