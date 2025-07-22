# Dynamic Tool Registry (ToolFactory)
from typing import Protocol
from abc import abstractmethod

class ToolInterface(Protocol):
    name: str
    description: str
    parameters_schema: Dict[str, Any]
    required_permissions: List[str]
    execution_timeout: int
    
    @abstractmethod
    async def execute(self, parameters: Dict[str, Any], context: ExecutionContext) -> ToolResult:
        pass
    
    @abstractmethod  
    def validate_parameters(self, parameters: Dict[str, Any]) -> bool:
        pass

class DynamicToolRegistry:
    def __init__(self):
        self.tools: Dict[str, ToolInterface] = {}
        self.tool_categories: Dict[str, List[str]] = {}
        self.security_policies: Dict[str, SecurityPolicy] = {}
    
    def register_tool(self, tool: ToolInterface, category: str = "general"):
        # Validate tool implementation
        self._validate_tool_interface(tool)
        
        # Register tool
        self.tools[tool.name] = tool
        
        if category not in self.tool_categories:
            self.tool_categories[category] = []
        self.tool_categories[category].append(tool.name)
        
        # Set security policy
        self.security_policies[tool.name] = SecurityPolicy(
            required_permissions=tool.required_permissions,
            execution_timeout=tool.execution_timeout,
            sandbox_requirements=self._determine_sandbox_requirements(tool)
        )
    
    async def discover_tools_for_task(self, task_description: str, user_context: UserContext) -> List[ToolInterface]:
        # Use LLM to analyze task and suggest tools
        relevant_tools = await self._semantic_tool_discovery(task_description)
        
        # Filter by user permissions
        authorized_tools = [
            tool for tool in relevant_tools
            if self._check_tool_authorization(tool, user_context)
        ]
        
        return authorized_tools