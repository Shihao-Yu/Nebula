from typing import Dict, Any, Optional, List, Callable
import asyncio
import structlog
from datetime import datetime

from application.websocket.connection_manager import ConnectionManager
from application.websocket.schema.events import (
    MarkdownEvent, ComponentEvent, ProgressData, 
    ComponentType, EventType, FormData, FormField
)
from domain.models.agent_state import AgentStatus, HumanInteractionRequest

logger = structlog.get_logger(__name__)


class StreamingHandler:
    """Handles real-time streaming of agent events to WebSocket clients"""
    
    def __init__(self, connection_manager: Optional[ConnectionManager] = None):
        self.connection_manager = connection_manager or ConnectionManager()
        self.event_handlers: Dict[str, List[Callable]] = {}
        self.streaming_sessions: Dict[str, Dict[str, Any]] = {}
        
    async def handle_update(self, session_id: str, update: Dict[str, Any]):
        """Handle workflow state updates and stream to client"""
        
        # Extract relevant information from the update
        for node_id, node_data in update.items():
            await self._process_node_update(session_id, node_id, node_data)
            
    async def _process_node_update(self, session_id: str, node_id: str, node_data: Dict[str, Any]):
        """Process updates from specific workflow nodes"""
        
        logger.debug("Processing node update", session_id=session_id, node_id=node_id)
        
        # Handle different node types
        if node_id == "input_validator":
            await self._handle_input_validation(session_id, node_data)
        elif node_id == "task_planner":
            await self._handle_task_planning(session_id, node_data)
        elif node_id == "tool_executor":
            await self._handle_tool_execution(session_id, node_data)
        elif node_id == "human_reviewer":
            await self._handle_human_review(session_id, node_data)
        elif node_id == "result_synthesizer":
            await self._handle_synthesis(session_id, node_data)
        elif node_id == "error_handler":
            await self._handle_error(session_id, node_data)
            
    async def _handle_input_validation(self, session_id: str, data: Dict[str, Any]):
        """Handle input validation updates"""
        
        # Send progress update
        await self.send_progress(
            session_id,
            "Validating your input...",
            step_index=1,
            total_steps=5
        )
        
    async def _handle_task_planning(self, session_id: str, data: Dict[str, Any]):
        """Handle task planning updates"""
        
        agent_state = data.get("agent_state")
        if agent_state and agent_state.current_task:
            task = agent_state.current_task
            await self.send_progress(
                session_id,
                f"Planning: {task.name}",
                step_index=2,
                total_steps=5
            )
            
    async def _handle_tool_execution(self, session_id: str, data: Dict[str, Any]):
        """Handle tool execution updates"""
        
        tool_results = data.get("tool_results", [])
        if tool_results:
            last_result = tool_results[-1]
            await self.send_progress(
                session_id,
                f"Executing: {last_result.get('tool', 'tool')}",
                step_index=3,
                total_steps=5
            )
            
    async def _handle_human_review(self, session_id: str, data: Dict[str, Any]):
        """Handle human review requests"""
        
        pending_input = data.get("pending_human_input")
        if pending_input and isinstance(pending_input, HumanInteractionRequest):
            await self._send_human_interaction_form(session_id, pending_input)
            
    async def _handle_synthesis(self, session_id: str, data: Dict[str, Any]):
        """Handle result synthesis"""
        
        await self.send_progress(
            session_id,
            "Synthesizing results...",
            step_index=4,
            total_steps=5
        )
        
        # Extract the final message
        messages = data.get("messages", [])
        if messages:
            last_message = messages[-1]
            if hasattr(last_message, "content"):
                await self.send_markdown(session_id, last_message.content)
                
        # Send completion
        await self.send_workflow_complete(session_id)
        
    async def _handle_error(self, session_id: str, data: Dict[str, Any]):
        """Handle error updates"""
        
        error = data.get("error")
        if error:
            await self.connection_manager.send_error(session_id, str(error))
            
    async def _send_human_interaction_form(self, session_id: str, request: HumanInteractionRequest):
        """Send human interaction form to client"""
        
        # Convert request to form data
        fields = []
        
        if request.form_schema:
            # Use provided schema
            for field_key, field_config in request.form_schema.items():
                fields.append(FormField(
                    key=field_key,
                    type=field_config.get("type", "text"),
                    label=field_config.get("label", field_key),
                    required=field_config.get("required", False),
                    placeholder=field_config.get("placeholder"),
                    options=field_config.get("options"),
                    default_value=field_config.get("default")
                ))
        else:
            # Create default approval form
            fields = [
                FormField(
                    key="action",
                    type="select",
                    label="Action",
                    required=True,
                    options=[
                        {"value": "approve", "label": "Approve"},
                        {"value": "reject", "label": "Reject"},
                        {"value": "modify", "label": "Modify"}
                    ]
                ),
                FormField(
                    key="comments",
                    type="textarea",
                    label="Comments",
                    required=False,
                    placeholder="Optional comments..."
                )
            ]
            
        form_data = FormData(
            id=request.id,
            title=request.title,
            fields=fields
        )
        
        # Send form component
        await self.connection_manager.send_event(
            session_id,
            ComponentEvent(
                payload={
                    "component": ComponentType.UI_INTERACTION,
                    "data": form_data.model_dump()
                }
            )
        )
        
    async def send_progress(
        self, 
        session_id: str, 
        status: str, 
        step_index: Optional[int] = None,
        total_steps: Optional[int] = None
    ):
        """Send progress update to client"""
        
        progress_data = ProgressData(
            status=status,
            step_index=step_index,
            total_steps=total_steps
        )
        
        await self.connection_manager.send_event(
            session_id,
            ComponentEvent(
                payload={
                    "component": ComponentType.PROGRESS,
                    "data": progress_data.model_dump()
                }
            )
        )
        
    async def send_markdown(self, session_id: str, content: str):
        """Send markdown content to client"""
        
        await self.connection_manager.send_event(
            session_id,
            MarkdownEvent(payload=content)
        )
        
    async def send_workflow_complete(self, session_id: str):
        """Send workflow completion signal"""
        
        await self.send_progress(session_id, "_workflow_finish")
        
    async def stream_token(self, session_id: str, token: str):
        """Stream a single token (for LLM streaming)"""
        
        # Get or create streaming buffer
        if session_id not in self.streaming_sessions:
            self.streaming_sessions[session_id] = {
                "buffer": "",
                "last_send": datetime.utcnow()
            }
            
        session_data = self.streaming_sessions[session_id]
        session_data["buffer"] += token
        
        # Send buffered content every 100ms or 50 chars
        now = datetime.utcnow()
        time_diff = (now - session_data["last_send"]).total_seconds()
        
        if time_diff > 0.1 or len(session_data["buffer"]) > 50:
            await self.send_markdown(session_id, session_data["buffer"])
            session_data["buffer"] = ""
            session_data["last_send"] = now
            
    async def flush_stream(self, session_id: str):
        """Flush any remaining buffered content"""
        
        if session_id in self.streaming_sessions:
            session_data = self.streaming_sessions[session_id]
            if session_data["buffer"]:
                await self.send_markdown(session_id, session_data["buffer"])
                session_data["buffer"] = ""
            del self.streaming_sessions[session_id]
            
    def register_event_handler(self, event_type: str, handler: Callable):
        """Register a custom event handler"""
        
        if event_type not in self.event_handlers:
            self.event_handlers[event_type] = []
        self.event_handlers[event_type].append(handler)
        
    async def emit_custom_event(self, session_id: str, event_type: str, data: Any):
        """Emit a custom event to registered handlers"""
        
        if event_type in self.event_handlers:
            for handler in self.event_handlers[event_type]:
                try:
                    await handler(session_id, data)
                except Exception as e:
                    logger.error("Error in event handler", 
                               event_type=event_type, 
                               error=str(e))