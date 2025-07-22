from langgraph import StateGraph, Command
from typing import TypedDict, Annotated, List
from langgraph.graph.message import add_messages

class EnterpriseAgentState(TypedDict):
    messages: Annotated[List[BaseMessage], add_messages]
    workflow_context: Dict[str, Any]
    user_session: Dict[str, str]
    execution_metadata: Dict[str, Any]
    pending_human_input: Optional[Dict[str, Any]]
    tool_results: List[Dict[str, Any]]
    agent_chain_trace: List[str]

# Multi-agent coordination graph
def create_enterprise_workflow():
    workflow = StateGraph(EnterpriseAgentState)
    
    # Specialized agents
    workflow.add_node("input_validator", input_validation_agent)
    workflow.add_node("task_planner", planning_agent)
    workflow.add_node("tool_executor", tool_execution_agent)
    workflow.add_node("human_reviewer", human_review_agent)
    workflow.add_node("result_synthesizer", synthesis_agent)
    
    # Dynamic routing with conditional edges
    workflow.add_conditional_edges(
        "task_planner",
        route_based_on_task_complexity,
        {
            "simple_execution": "tool_executor",
            "needs_human_approval": "human_reviewer",
            "complex_multi_step": "task_planner"  # Loop back for decomposition
        }
    )
    
    return workflow.compile(
        checkpointer=PostgresCheckpointer(),
        interrupt_before=["human_reviewer"]
    )