from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import Annotated, Dict, Any, Optional
import asyncio
import json
import uuid
from datetime import datetime
import structlog

from .connection_manager import ConnectionManager
from .schema.events import (
    UserMessage, EventType, ComponentType, 
    MarkdownEvent, ComponentEvent, ProgressData
)
from domain.orchestration.core.main_agent import AgentOrchestrator
from domain.context.context_manager import ContextManager
from infrastructure.security.jwt_validator import verify_token
from infrastructure.observability.logging import setup_logging

# Setup logging
setup_logging()
logger = structlog.get_logger(__name__)

app = FastAPI(title="Agent WebSocket Server")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global connection manager
connection_manager = ConnectionManager()

# Agent orchestrator (will be properly initialized later)
agent_orchestrator: Optional[AgentOrchestrator] = None
context_manager = ContextManager()


class TenantContext:
    """Tenant context for multi-tenancy support"""
    def __init__(self, tenant_id: str, permissions: Dict[str, Any]):
        self.tenant_id = tenant_id
        self.permissions = permissions


async def get_tenant_context(tenant_id: str, token: Optional[str] = None) -> TenantContext:
    """Validate tenant and return context"""
    # For now, mock implementation
    return TenantContext(
        tenant_id=tenant_id,
        permissions={"all": True}
    )


@app.on_event("startup")
async def startup_event():
    """Initialize the agent orchestrator and start background tasks"""
    global agent_orchestrator
    
    # Initialize agent orchestrator
    agent_orchestrator = AgentOrchestrator()
    
    # Start connection health check
    asyncio.create_task(connection_manager.health_check())
    
    logger.info("WebSocket server started")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    # Disconnect all active connections
    sessions = list(connection_manager.active_connections.keys())
    for session_id in sessions:
        await connection_manager.disconnect(session_id)
        
    logger.info("WebSocket server shutdown")


@app.websocket("/ws/agent/{tenant_id}/{session_id}")
async def agent_websocket(
    websocket: WebSocket,
    tenant_id: str,
    session_id: str,
):
    """Main WebSocket endpoint for agent interaction"""
    
    # Validate session ID format
    try:
        uuid.UUID(session_id)
    except ValueError:
        await websocket.close(code=1008, reason="Invalid session ID format")
        return
        
    # Get tenant context
    try:
        tenant_context = await get_tenant_context(tenant_id)
    except Exception as e:
        await websocket.close(code=1008, reason="Invalid tenant")
        return
        
    # Connect the WebSocket
    await connection_manager.connect(websocket, session_id, tenant_id)
    
    try:
        # Send initial progress event
        await connection_manager.send_event(
            session_id,
            ComponentEvent(
                payload={
                    "component": ComponentType.PROGRESS,
                    "data": ProgressData(status="Agent ready").model_dump()
                }
            )
        )
        
        # Main message loop
        while True:
            # Receive message from client
            data = await websocket.receive_json()
            
            # Parse the incoming event
            try:
                event_type = data.get("type")
                
                if event_type == EventType.USER_MESSAGE:
                    user_message = UserMessage(**data)
                    
                    # Process the user message
                    await process_user_message(
                        session_id=session_id,
                        tenant_context=tenant_context,
                        message=user_message
                    )
                    
                elif event_type == EventType.COMPONENT:
                    # Handle component interactions (form submits, etc)
                    await handle_component_interaction(
                        session_id=session_id,
                        tenant_context=tenant_context,
                        data=data
                    )
                    
            except Exception as e:
                logger.error("Error processing message", error=str(e), session_id=session_id)
                await connection_manager.send_error(
                    session_id,
                    f"Error processing message: {str(e)}"
                )
                
    except WebSocketDisconnect:
        logger.info("Client disconnected", session_id=session_id)
    except Exception as e:
        logger.error("WebSocket error", error=str(e), session_id=session_id)
    finally:
        await connection_manager.disconnect(session_id)


async def process_user_message(
    session_id: str, 
    tenant_context: TenantContext,
    message: UserMessage
):
    """Process a user message through the agent orchestrator"""
    
    try:
        # Send thinking indicator
        await connection_manager.send_event(
            session_id,
            ComponentEvent(
                payload={
                    "component": ComponentType.PROGRESS,
                    "data": ProgressData(status="Processing your request...").model_dump()
                }
            )
        )
        
        # Build context
        context = await context_manager.build_context(
            user_query=message.content,
            session_id=session_id
        )
        
        # Process through agent orchestrator
        # For now, mock response
        await asyncio.sleep(1)  # Simulate processing
        
        # Send mock response
        await connection_manager.send_event(
            session_id,
            MarkdownEvent(
                payload="I understand your request. Let me help you with that.\n\nThis is a mock response from the agent system."
            )
        )
        
        # Send completion indicator
        await connection_manager.send_event(
            session_id,
            ComponentEvent(
                payload={
                    "component": ComponentType.PROGRESS,
                    "data": ProgressData(status="_workflow_finish").model_dump()
                }
            )
        )
        
    except Exception as e:
        logger.error("Error in agent processing", error=str(e), session_id=session_id)
        await connection_manager.send_error(session_id, str(e))


async def handle_component_interaction(
    session_id: str,
    tenant_context: TenantContext,
    data: Dict[str, Any]
):
    """Handle UI component interactions"""
    
    component_type = data.get("payload", {}).get("component")
    
    if component_type == ComponentType.FORM_SUBMIT:
        # Handle form submission
        form_data = data.get("payload", {}).get("data", {})
        await process_form_submission(session_id, tenant_context, form_data)
        
    elif component_type == ComponentType.ASYNC_SELECT_QUERY:
        # Handle async select queries
        query_data = data.get("payload", {}).get("data", {})
        await process_async_select_query(session_id, tenant_context, query_data)


async def process_form_submission(
    session_id: str,
    tenant_context: TenantContext,
    form_data: Dict[str, Any]
):
    """Process form submission from UI"""
    
    form_id = form_data.get("form_id")
    values = form_data.get("values", {})
    
    logger.info("Form submitted", session_id=session_id, form_id=form_id)
    
    # Process the form data
    # For now, just acknowledge
    await connection_manager.send_event(
        session_id,
        MarkdownEvent(payload=f"Form '{form_id}' received with values: {values}")
    )


async def process_async_select_query(
    session_id: str,
    tenant_context: TenantContext,
    query_data: Dict[str, Any]
):
    """Process async select field queries"""
    
    field_key = query_data.get("field_key")
    query = query_data.get("query")
    
    # Mock response with sample data
    mock_options = [
        {"value": f"opt_{i}", "label": f"Option {i} for '{query}'"}
        for i in range(5)
    ]
    
    # Send response back
    # This would normally be sent through a specific response format
    await connection_manager.send_event(
        session_id,
        ComponentEvent(
            payload={
                "component": "async_select_response",
                "data": {
                    "field_key": field_key,
                    "options": mock_options
                }
            }
        )
    )


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "active_connections": len(connection_manager.active_connections),
        "timestamp": datetime.utcnow().isoformat()
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)