from typing import Dict, List, Any, Optional
import asyncio
from datetime import datetime


class ToolRegistry:
    """Registry for managing available tools"""
    
    def __init__(self):
        self.tools: Dict[str, Dict[str, Any]] = {}
        self.tool_categories: Dict[str, List[str]] = {}
        self._initialize_mock_tools()
        
    def _initialize_mock_tools(self):
        """Initialize with mock tools"""
        
        mock_tools = [
            {
                "id": "search_web",
                "name": "Web Search",
                "description": "Search the web for information",
                "category": "search",
                "parameters": {
                    "query": {"type": "string", "required": True},
                    "limit": {"type": "integer", "default": 10}
                }
            },
            {
                "id": "send_email",
                "name": "Send Email",
                "description": "Send an email to specified recipients",
                "category": "communication",
                "parameters": {
                    "to": {"type": "string", "required": True},
                    "subject": {"type": "string", "required": True},
                    "body": {"type": "string", "required": True}
                }
            },
            {
                "id": "create_document",
                "name": "Create Document",
                "description": "Create a new document",
                "category": "productivity",
                "parameters": {
                    "title": {"type": "string", "required": True},
                    "content": {"type": "string", "required": True},
                    "format": {"type": "string", "default": "markdown"}
                }
            },
            {
                "id": "analyze_data",
                "name": "Analyze Data",
                "description": "Analyze and visualize data",
                "category": "analytics",
                "parameters": {
                    "data_source": {"type": "string", "required": True},
                    "analysis_type": {"type": "string", "required": True}
                }
            }
        ]
        
        for tool in mock_tools:
            self.register_tool(tool)
            
    def register_tool(self, tool_config: Dict[str, Any]):
        """Register a new tool"""
        
        tool_id = tool_config["id"]
        category = tool_config.get("category", "general")
        
        self.tools[tool_id] = tool_config
        
        if category not in self.tool_categories:
            self.tool_categories[category] = []
        self.tool_categories[category].append(tool_id)
        
    async def get_available_tools(self) -> List[Dict[str, Any]]:
        """Get all available tools"""
        
        return list(self.tools.values())
        
    async def get_tool_info(self, tool_id: str) -> Optional[Dict[str, Any]]:
        """Get information about a specific tool"""
        
        return self.tools.get(tool_id)
        
    async def get_tools_by_category(self, category: str) -> List[Dict[str, Any]]:
        """Get tools by category"""
        
        tool_ids = self.tool_categories.get(category, [])
        return [self.tools[tool_id] for tool_id in tool_ids if tool_id in self.tools]
        
    async def search_tools(self, query: str) -> List[Dict[str, Any]]:
        """Search tools by name or description"""
        
        query_lower = query.lower()
        matching_tools = []
        
        for tool in self.tools.values():
            name = tool.get("name", "").lower()
            description = tool.get("description", "").lower()
            
            if query_lower in name or query_lower in description:
                matching_tools.append(tool)
                
        return matching_tools