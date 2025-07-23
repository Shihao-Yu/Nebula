from typing import Dict, Set, Optional
from fastapi import WebSocket
import asyncio
import json
from datetime import datetime
import structlog

from .schema.events import BaseEvent, ConnectionEvent, ErrorEvent

logger = structlog.get_logger(__name__)


class ConnectionManager:
    """Manages WebSocket connections and message routing"""
    
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.session_metadata: Dict[str, Dict] = {}
        self._lock = asyncio.Lock()
        
    async def connect(self, websocket: WebSocket, session_id: str, tenant_id: str):
        """Accept a new WebSocket connection"""
        await websocket.accept()
        
        async with self._lock:
            self.active_connections[session_id] = websocket
            self.session_metadata[session_id] = {
                "tenant_id": tenant_id,
                "connected_at": datetime.utcnow(),
                "last_activity": datetime.utcnow()
            }
            
        # Send connection confirmation
        await self.send_event(
            session_id,
            ConnectionEvent(
                status="connected",
                session_id=session_id
            )
        )
        
        logger.info("WebSocket connected", session_id=session_id, tenant_id=tenant_id)
        
    async def disconnect(self, session_id: str):
        """Disconnect a WebSocket connection"""
        async with self._lock:
            if session_id in self.active_connections:
                ws = self.active_connections.pop(session_id)
                self.session_metadata.pop(session_id, None)
                
                try:
                    await ws.close()
                except Exception as e:
                    logger.error("Error closing WebSocket", session_id=session_id, error=str(e))
                    
        logger.info("WebSocket disconnected", session_id=session_id)
        
    async def send_event(self, session_id: str, event: BaseEvent) -> bool:
        """Send an event to a specific session"""
        if session_id not in self.active_connections:
            logger.warning("Attempted to send to disconnected session", session_id=session_id)
            return False
            
        websocket = self.active_connections[session_id]
        
        try:
            await websocket.send_json(event.model_dump(mode="json"))
            
            # Update last activity
            if session_id in self.session_metadata:
                self.session_metadata[session_id]["last_activity"] = datetime.utcnow()
                
            return True
            
        except Exception as e:
            logger.error("Failed to send event", session_id=session_id, error=str(e))
            await self.disconnect(session_id)
            return False
            
    async def broadcast_to_tenant(self, tenant_id: str, event: BaseEvent):
        """Broadcast an event to all sessions of a tenant"""
        sessions = [
            session_id 
            for session_id, metadata in self.session_metadata.items()
            if metadata.get("tenant_id") == tenant_id
        ]
        
        tasks = [self.send_event(session_id, event) for session_id in sessions]
        await asyncio.gather(*tasks, return_exceptions=True)
        
    async def send_error(self, session_id: str, error_message: str, error_code: Optional[str] = None):
        """Send an error event to a session"""
        error_event = ErrorEvent(
            payload={"message": error_message},
            error_code=error_code,
            session_id=session_id
        )
        await self.send_event(session_id, error_event)
        
    def get_session_metadata(self, session_id: str) -> Optional[Dict]:
        """Get metadata for a session"""
        return self.session_metadata.get(session_id)
        
    def get_active_sessions(self, tenant_id: Optional[str] = None) -> Set[str]:
        """Get active session IDs, optionally filtered by tenant"""
        if tenant_id:
            return {
                session_id 
                for session_id, metadata in self.session_metadata.items()
                if metadata.get("tenant_id") == tenant_id
            }
        return set(self.active_connections.keys())
        
    async def health_check(self):
        """Periodic health check to clean up stale connections"""
        while True:
            try:
                current_time = datetime.utcnow()
                stale_sessions = []
                
                for session_id, metadata in self.session_metadata.items():
                    last_activity = metadata.get("last_activity")
                    if last_activity and (current_time - last_activity).seconds > 300:  # 5 minutes
                        stale_sessions.append(session_id)
                        
                for session_id in stale_sessions:
                    logger.warning("Disconnecting stale session", session_id=session_id)
                    await self.disconnect(session_id)
                    
            except Exception as e:
                logger.error("Health check error", error=str(e))
                
            await asyncio.sleep(60)  # Check every minute