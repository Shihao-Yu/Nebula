from typing import Dict, Any, List, Optional, Annotated
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum
from langchain.schema import BaseMessage


class AgentStatus(str, Enum):
    """Agent execution status"""
    IDLE = "idle"
    THINKING = "thinking"
    EXECUTING = "executing"
    WAITING_HUMAN_INPUT = "waiting_human_input"
    COMPLETED = "completed"
    FAILED = "failed"


class TaskPriority(str, Enum):
    """Task priority levels"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class TaskStatus(str, Enum):
    """Task execution status"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    BLOCKED = "blocked"
    COMPLETED = "completed"
    FAILED = "failed"


class Task(BaseModel):
    """Represents a task in the agent workflow"""
    id: str = Field(description="Unique task identifier")
    name: str = Field(description="Task name")
    description: Optional[str] = Field(None, description="Task description")
    priority: TaskPriority = Field(default=TaskPriority.MEDIUM)
    status: TaskStatus = Field(default=TaskStatus.PENDING)
    dependencies: List[str] = Field(default_factory=list, description="Task IDs this task depends on")
    assigned_agent: Optional[str] = Field(None, description="Agent assigned to this task")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    result: Optional[Dict[str, Any]] = Field(None, description="Task execution result")


class ExecutionContext(BaseModel):
    """Context for agent execution"""
    query: str = Field(description="User query or request")
    session_id: str = Field(description="Session identifier")
    tenant_id: Optional[str] = Field(None, description="Tenant identifier")
    conversation_history: List[Dict[str, Any]] = Field(default_factory=list)
    user_profile: Dict[str, Any] = Field(default_factory=dict)
    available_tools: List[str] = Field(default_factory=list)
    relevance_scores: Dict[str, float] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    

class AgentMemory(BaseModel):
    """Agent memory storage"""
    short_term: List[Dict[str, Any]] = Field(default_factory=list, description="Recent interactions")
    long_term: List[Dict[str, Any]] = Field(default_factory=list, description="Persistent knowledge")
    working_memory: Dict[str, Any] = Field(default_factory=dict, description="Current task context")
    

class AgentState(BaseModel):
    """Complete agent state"""
    session_id: str
    status: AgentStatus = Field(default=AgentStatus.IDLE)
    current_task: Optional[Task] = None
    task_queue: List[Task] = Field(default_factory=list)
    completed_tasks: List[Task] = Field(default_factory=list)
    memory: AgentMemory = Field(default_factory=AgentMemory)
    context: Optional[ExecutionContext] = None
    tool_results: List[Dict[str, Any]] = Field(default_factory=list)
    agent_chain_trace: List[str] = Field(default_factory=list)
    error_log: List[Dict[str, Any]] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_activity: datetime = Field(default_factory=datetime.utcnow)
    
    def add_task(self, task: Task):
        """Add a task to the queue"""
        self.task_queue.append(task)
        self.task_queue.sort(key=lambda t: t.priority.value)
        
    def get_next_task(self) -> Optional[Task]:
        """Get next available task"""
        for task in self.task_queue:
            if task.status == TaskStatus.PENDING:
                # Check if dependencies are completed
                deps_completed = all(
                    any(t.id == dep_id and t.status == TaskStatus.COMPLETED 
                        for t in self.completed_tasks)
                    for dep_id in task.dependencies
                )
                if deps_completed:
                    return task
        return None
        
    def update_status(self, status: AgentStatus):
        """Update agent status"""
        self.status = status
        self.last_activity = datetime.utcnow()
        
    def add_to_memory(self, memory_type: str, data: Dict[str, Any]):
        """Add data to agent memory"""
        if memory_type == "short_term":
            self.memory.short_term.append({
                "timestamp": datetime.utcnow(),
                "data": data
            })
            # Keep only last 100 items
            if len(self.memory.short_term) > 100:
                self.memory.short_term = self.memory.short_term[-100:]
        elif memory_type == "long_term":
            self.memory.long_term.append({
                "timestamp": datetime.utcnow(),
                "data": data
            })
        elif memory_type == "working":
            self.memory.working_memory.update(data)
            
    def log_error(self, error: str, context: Optional[Dict[str, Any]] = None):
        """Log an error"""
        self.error_log.append({
            "timestamp": datetime.utcnow(),
            "error": error,
            "context": context or {}
        })
        
    def get_state_summary(self) -> Dict[str, Any]:
        """Get a summary of the current state"""
        return {
            "session_id": self.session_id,
            "status": self.status.value,
            "current_task": self.current_task.name if self.current_task else None,
            "pending_tasks": len([t for t in self.task_queue if t.status == TaskStatus.PENDING]),
            "completed_tasks": len(self.completed_tasks),
            "errors": len(self.error_log),
            "last_activity": self.last_activity.isoformat()
        }


class HumanInteractionRequest(BaseModel):
    """Request for human interaction"""
    id: str = Field(description="Unique request identifier")
    type: str = Field(description="Type of interaction (approval, input, review)")
    title: str = Field(description="Title of the request")
    description: str = Field(description="Detailed description")
    data: Dict[str, Any] = Field(default_factory=dict, description="Associated data")
    options: Optional[List[str]] = Field(None, description="Available options for selection")
    form_schema: Optional[Dict[str, Any]] = Field(None, description="Form schema for complex inputs")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = Field(None, description="Expiration time for the request")
    

class HumanInteractionResponse(BaseModel):
    """Response from human interaction"""
    request_id: str
    action: str = Field(description="Action taken (approve, reject, submit)")
    data: Dict[str, Any] = Field(default_factory=dict)
    responded_at: datetime = Field(default_factory=datetime.utcnow)
    responder_id: Optional[str] = None