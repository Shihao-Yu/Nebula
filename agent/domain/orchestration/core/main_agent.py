from typing import TypedDict, Annotated, List, Dict, Any, Optional, Literal
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
try:
    from langgraph.checkpoint.postgres import PostgresSaver
    POSTGRES_AVAILABLE = True
except ImportError:
    PostgresSaver = None
    POSTGRES_AVAILABLE = False
from langgraph.prebuilt import ToolNode
import structlog
from datetime import datetime

from domain.models.agent_state import (
    AgentState, AgentStatus, Task, TaskStatus, 
    ExecutionContext, HumanInteractionRequest
)
from domain.streaming.streaming_handler import StreamingHandler
from domain.orchestration.subagent.base_subagent import BaseSubAgent

logger = structlog.get_logger(__name__)


class WorkflowState(TypedDict):
    """State for the workflow graph"""
    messages: Annotated[List[BaseMessage], add_messages]
    agent_state: AgentState
    workflow_context: Dict[str, Any]
    user_session: Dict[str, str]
    execution_metadata: Dict[str, Any]
    pending_human_input: Optional[HumanInteractionRequest]
    tool_results: List[Dict[str, Any]]
    agent_chain_trace: List[str]
    current_agent: str
    next_action: Optional[str]
    error: Optional[str]


class AgentOrchestrator:
    """Main agent orchestrator using LangGraph"""
    
    def __init__(self, checkpoint_url: Optional[str] = None):
        self.checkpoint_url = checkpoint_url
        self.workflow = self._create_workflow()
        self.streaming_handler = StreamingHandler()
        self.subagents: Dict[str, BaseSubAgent] = {}
        
    def _create_workflow(self) -> StateGraph:
        """Create the multi-agent workflow graph"""
        
        # Initialize the graph
        workflow = StateGraph(WorkflowState)
        
        # Add nodes for each agent
        workflow.add_node("input_validator", self.input_validation_node)
        workflow.add_node("task_planner", self.task_planning_node)
        workflow.add_node("tool_executor", self.tool_execution_node)
        workflow.add_node("human_reviewer", self.human_review_node)
        workflow.add_node("result_synthesizer", self.synthesis_node)
        workflow.add_node("error_handler", self.error_handler_node)
        
        # Set entry point
        workflow.set_entry_point("input_validator")
        
        # Add edges
        workflow.add_edge("input_validator", "task_planner")
        
        # Conditional routing from task planner
        workflow.add_conditional_edges(
            "task_planner",
            self.route_based_on_task_complexity,
            {
                "simple_execution": "tool_executor",
                "needs_human_approval": "human_reviewer",
                "complex_multi_step": "task_planner",
                "synthesis": "result_synthesizer",
                "error": "error_handler"
            }
        )
        
        # From tool executor
        workflow.add_conditional_edges(
            "tool_executor",
            self.check_tool_result,
            {
                "success": "task_planner",
                "needs_human_review": "human_reviewer",
                "error": "error_handler"
            }
        )
        
        # From human reviewer
        workflow.add_conditional_edges(
            "human_reviewer",
            self.process_human_response,
            {
                "approved": "tool_executor",
                "rejected": "task_planner",
                "modified": "task_planner"
            }
        )
        
        # From result synthesizer
        workflow.add_edge("result_synthesizer", END)
        
        # From error handler
        workflow.add_conditional_edges(
            "error_handler",
            self.handle_error_recovery,
            {
                "retry": "task_planner",
                "fail": END
            }
        )
        
        # Compile with checkpointer if provided and available
        if self.checkpoint_url and POSTGRES_AVAILABLE:
            checkpointer = PostgresSaver.from_conn_string(self.checkpoint_url)
            return workflow.compile(
                checkpointer=checkpointer,
                interrupt_before=["human_reviewer"]
            )
        else:
            return workflow.compile(interrupt_before=["human_reviewer"])
            
    async def input_validation_node(self, state: WorkflowState) -> Dict[str, Any]:
        """Validate and sanitize user input"""
        logger.info("Validating input", session_id=state["agent_state"].session_id)
        
        # Update agent status
        state["agent_state"].update_status(AgentStatus.THINKING)
        state["agent_chain_trace"].append("input_validator")
        
        # Extract last user message
        last_message = state["messages"][-1]
        
        # Validate message
        if not isinstance(last_message, HumanMessage):
            state["error"] = "Invalid message type"
            return state
            
        # Basic content validation
        content = last_message.content
        if not content or len(content.strip()) == 0:
            state["error"] = "Empty message content"
            return state
            
        # Add validation result to trace
        state["execution_metadata"]["input_validated"] = True
        state["execution_metadata"]["input_length"] = len(content)
        
        return state
        
    async def task_planning_node(self, state: WorkflowState) -> Dict[str, Any]:
        """Plan tasks based on user input"""
        logger.info("Planning tasks", session_id=state["agent_state"].session_id)
        
        state["agent_chain_trace"].append("task_planner")
        agent_state = state["agent_state"]
        
        # Check if we have pending tasks
        next_task = agent_state.get_next_task()
        
        if next_task:
            # Continue with existing task
            agent_state.current_task = next_task
            next_task.status = TaskStatus.IN_PROGRESS
            state["next_action"] = self._determine_task_action(next_task)
        else:
            # Create new tasks based on user input
            last_message = state["messages"][-1]
            tasks = self._create_tasks_from_input(last_message.content)
            
            for task in tasks:
                agent_state.add_task(task)
                
            # Get first task
            next_task = agent_state.get_next_task()
            if next_task:
                agent_state.current_task = next_task
                next_task.status = TaskStatus.IN_PROGRESS
                state["next_action"] = self._determine_task_action(next_task)
            else:
                # No tasks to execute, go to synthesis
                state["next_action"] = "synthesis"
                
        return state
        
    async def tool_execution_node(self, state: WorkflowState) -> Dict[str, Any]:
        """Execute tools for the current task"""
        logger.info("Executing tools", session_id=state["agent_state"].session_id)
        
        state["agent_chain_trace"].append("tool_executor")
        agent_state = state["agent_state"]
        
        if not agent_state.current_task:
            state["error"] = "No current task to execute"
            return state
            
        # Mock tool execution
        tool_result = {
            "task_id": agent_state.current_task.id,
            "tool": "mock_tool",
            "result": f"Executed task: {agent_state.current_task.name}",
            "timestamp": datetime.utcnow().isoformat()
        }
        
        state["tool_results"].append(tool_result)
        agent_state.current_task.result = tool_result
        
        return state
        
    async def human_review_node(self, state: WorkflowState) -> Dict[str, Any]:
        """Handle human-in-the-loop interactions"""
        logger.info("Requesting human review", session_id=state["agent_state"].session_id)
        
        state["agent_chain_trace"].append("human_reviewer")
        
        # Create human interaction request
        request = HumanInteractionRequest(
            id=f"req_{datetime.utcnow().timestamp()}",
            type="approval",
            title="Review Required",
            description="Please review and approve the following action",
            data={
                "task": state["agent_state"].current_task.model_dump() if state["agent_state"].current_task else {},
                "context": state["workflow_context"]
            }
        )
        
        state["pending_human_input"] = request
        state["agent_state"].update_status(AgentStatus.WAITING_HUMAN_INPUT)
        
        return state
        
    async def synthesis_node(self, state: WorkflowState) -> Dict[str, Any]:
        """Synthesize results and generate response"""
        logger.info("Synthesizing results", session_id=state["agent_state"].session_id)
        
        state["agent_chain_trace"].append("result_synthesizer")
        agent_state = state["agent_state"]
        
        # Compile results from completed tasks
        results = []
        for task in agent_state.completed_tasks:
            if task.result:
                results.append(task.result)
                
        # Generate response message
        response = self._generate_response(results, state["tool_results"])
        
        # Add AI message to conversation
        state["messages"].append(AIMessage(content=response))
        
        # Update status
        agent_state.update_status(AgentStatus.COMPLETED)
        
        # Move current task to completed
        if agent_state.current_task:
            agent_state.current_task.status = TaskStatus.COMPLETED
            agent_state.completed_tasks.append(agent_state.current_task)
            agent_state.current_task = None
            
        return state
        
    async def error_handler_node(self, state: WorkflowState) -> Dict[str, Any]:
        """Handle errors in the workflow"""
        logger.error("Handling error", error=state.get("error"), session_id=state["agent_state"].session_id)
        
        state["agent_chain_trace"].append("error_handler")
        
        # Log error
        state["agent_state"].log_error(
            state.get("error", "Unknown error"),
            {"trace": state["agent_chain_trace"]}
        )
        
        # Determine recovery strategy
        error_count = len(state["agent_state"].error_log)
        if error_count < 3:
            state["next_action"] = "retry"
        else:
            state["next_action"] = "fail"
            state["agent_state"].update_status(AgentStatus.FAILED)
            
        return state
        
    def route_based_on_task_complexity(self, state: WorkflowState) -> Literal["simple_execution", "needs_human_approval", "complex_multi_step", "synthesis", "error"]:
        """Route based on task complexity"""
        
        if state.get("error"):
            return "error"
            
        next_action = state.get("next_action", "simple_execution")
        
        if next_action == "synthesis":
            return "synthesis"
        elif next_action == "human_approval":
            return "needs_human_approval"
        elif next_action == "complex":
            return "complex_multi_step"
        else:
            return "simple_execution"
            
    def check_tool_result(self, state: WorkflowState) -> Literal["success", "needs_human_review", "error"]:
        """Check tool execution result"""
        
        if state.get("error"):
            return "error"
            
        # Check if tool result needs human review
        last_result = state["tool_results"][-1] if state["tool_results"] else None
        
        if last_result and last_result.get("needs_review"):
            return "needs_human_review"
            
        return "success"
        
    def process_human_response(self, state: WorkflowState) -> Literal["approved", "rejected", "modified"]:
        """Process human review response"""
        
        # In real implementation, this would check actual human response
        # For now, mock approval
        return "approved"
        
    def handle_error_recovery(self, state: WorkflowState) -> Literal["retry", "fail"]:
        """Determine error recovery strategy"""
        
        return state.get("next_action", "fail")
        
    def _create_tasks_from_input(self, user_input: str) -> List[Task]:
        """Create tasks from user input"""
        
        # Mock task creation
        # In real implementation, this would use NLP to understand intent
        task = Task(
            id=f"task_{datetime.utcnow().timestamp()}",
            name="Process user request",
            description=f"Handle: {user_input[:100]}..."
        )
        
        return [task]
        
    def _determine_task_action(self, task: Task) -> str:
        """Determine action needed for a task"""
        
        # Mock logic - in real implementation would analyze task
        if "approval" in task.name.lower():
            return "human_approval"
        elif task.dependencies:
            return "complex"
        else:
            return "simple_execution"
            
    def _generate_response(self, task_results: List[Dict], tool_results: List[Dict]) -> str:
        """Generate final response from results"""
        
        # Mock response generation
        return f"I've completed your request. Processed {len(task_results)} tasks with {len(tool_results)} tool executions."
        
    async def process_message(self, session_id: str, message: str, context: ExecutionContext) -> None:
        """Process a message through the workflow"""
        
        # Initialize agent state
        agent_state = AgentState(session_id=session_id, context=context)
        
        # Create initial workflow state
        initial_state: WorkflowState = {
            "messages": [HumanMessage(content=message)],
            "agent_state": agent_state,
            "workflow_context": context.metadata,
            "user_session": {"session_id": session_id},
            "execution_metadata": {},
            "pending_human_input": None,
            "tool_results": [],
            "agent_chain_trace": [],
            "current_agent": "input_validator",
            "next_action": None,
            "error": None
        }
        
        # Stream execution through the workflow
        async for chunk in self.workflow.astream(initial_state):
            # Handle streaming updates
            await self.streaming_handler.handle_update(session_id, chunk)