from typing import Dict, Any, Optional, List, Literal, Union
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum


class EventType(str, Enum):
    """WebSocket event types"""
    MARKDOWN = "markdown"
    COMPONENT = "component"
    ERROR = "error"
    CONNECTION = "connection"
    USER_MESSAGE = "user_message"


class ComponentType(str, Enum):
    """UI component types"""
    PROGRESS = "progress"
    UI_INTERACTION = "ui_interaction"
    FORM_SUBMIT = "form_submit"
    ASYNC_SELECT_QUERY = "async_select_query"


class BaseEvent(BaseModel):
    """Base event model for all WebSocket messages"""
    type: EventType
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    session_id: Optional[str] = None


class MarkdownEvent(BaseEvent):
    """Markdown content event for chat messages"""
    type: Literal[EventType.MARKDOWN] = EventType.MARKDOWN
    payload: str
    
    
class ProgressData(BaseModel):
    """Progress component data"""
    status: str
    step_index: Optional[int] = None
    total_steps: Optional[int] = None
    

class FormField(BaseModel):
    """Form field definition"""
    type: Literal["text", "select", "number", "date", "textarea", "checkbox"]
    key: str
    label: str
    required: bool = False
    placeholder: Optional[str] = None
    validation: Optional[List[Dict[str, Any]]] = None
    options: Optional[List[Dict[str, str]]] = None  # For select fields
    async_config: Optional[Dict[str, Any]] = None  # For async select
    default_value: Optional[Any] = None


class FormData(BaseModel):
    """Form component data"""
    id: str
    title: str
    fields: List[FormField]
    submit_label: str = "Submit"
    cancel_label: str = "Cancel"


class ComponentPayload(BaseModel):
    """Component event payload"""
    component: ComponentType
    data: Union[ProgressData, FormData, Dict[str, Any]]


class ComponentEvent(BaseEvent):
    """Component event for UI interactions"""
    type: Literal[EventType.COMPONENT] = EventType.COMPONENT
    payload: ComponentPayload


class ErrorEvent(BaseEvent):
    """Error event"""
    type: Literal[EventType.ERROR] = EventType.ERROR
    payload: Dict[str, Any]
    error_code: Optional[str] = None
    
    
class ConnectionEvent(BaseEvent):
    """Connection status event"""
    type: Literal[EventType.CONNECTION] = EventType.CONNECTION
    status: Literal["connected", "disconnected", "reconnecting"]
    

class UserMessage(BaseEvent):
    """User message event"""
    type: Literal[EventType.USER_MESSAGE] = EventType.USER_MESSAGE
    content: str
    attachments: Optional[List[Dict[str, Any]]] = None
    metadata: Optional[Dict[str, Any]] = None


class FormSubmitData(BaseModel):
    """Form submission data"""
    form_id: str
    values: Dict[str, Any]
    

class FormSubmitEvent(BaseEvent):
    """Form submission event from UI"""
    type: Literal[EventType.COMPONENT] = EventType.COMPONENT
    payload: ComponentPayload
    
    @classmethod
    def create(cls, form_id: str, values: Dict[str, Any], session_id: Optional[str] = None):
        """Create a form submit event"""
        return cls(
            payload=ComponentPayload(
                component=ComponentType.FORM_SUBMIT,
                data={"form_id": form_id, "values": values}
            ),
            session_id=session_id
        )


class AsyncSelectQuery(BaseModel):
    """Async select query data"""
    field_key: str
    query: str
    page: int = 1
    page_size: int = 20
    

class AsyncSelectEvent(BaseEvent):
    """Async select query event"""
    type: Literal[EventType.COMPONENT] = EventType.COMPONENT
    payload: ComponentPayload
    
    @classmethod
    def create(cls, field_key: str, query: str, page: int = 1, session_id: Optional[str] = None):
        """Create an async select query event"""
        return cls(
            payload=ComponentPayload(
                component=ComponentType.ASYNC_SELECT_QUERY,
                data=AsyncSelectQuery(
                    field_key=field_key,
                    query=query,
                    page=page
                ).model_dump()
            ),
            session_id=session_id
        )