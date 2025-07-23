from typing import Dict, List, Any, Optional
import structlog
from datetime import datetime

from domain.models.agent_state import ExecutionContext
from .memory.runtime_memory import RuntimeMemory
from .memory.vector_memory_store import VectorMemoryStore
from .memory.cache_memory_store import CacheMemoryStore
from .state.state_manager import StateManager
from .context_ranker import ContextRanker
from .context_retriver import ContextRetriever
from domain.tool.tool_registry import ToolRegistry

logger = structlog.get_logger(__name__)


class ContextManager:
    """Assembles context from multiple sources for agent execution"""
    
    def __init__(self):
        self.runtime_memory = RuntimeMemory()
        self.vector_store = VectorMemoryStore()
        self.cache_store = CacheMemoryStore()
        self.state_manager = StateManager()
        self.context_ranker = ContextRanker()
        self.context_retriever = ContextRetriever()
        self.tool_registry = ToolRegistry()
        
    async def build_context(self, user_query: str, session_id: str) -> ExecutionContext:
        """Build comprehensive execution context from multiple sources"""
        
        logger.info("Building context", session_id=session_id)
        
        # Gather context from multiple sources
        conversation_context = await self.get_conversation_context(session_id)
        user_context = await self.get_user_context(session_id)
        relevant_tools = await self.discover_relevant_tools(user_query)
        state_context = await self.state_manager.get_current_state(session_id)
        
        # Retrieve relevant memories
        relevant_memories = await self._retrieve_relevant_memories(user_query, session_id)
        
        # Calculate relevance scores
        relevance_scores = await self.calculate_relevance_scores(
            query=user_query,
            tools=relevant_tools,
            memories=relevant_memories
        )
        
        # Build execution context
        context = ExecutionContext(
            query=user_query,
            session_id=session_id,
            conversation_history=conversation_context,
            user_profile=user_context,
            available_tools=relevant_tools,
            relevance_scores=relevance_scores,
            metadata={
                "state": state_context,
                "memories": relevant_memories,
                "timestamp": datetime.utcnow().isoformat()
            }
        )
        
        # Cache the context
        await self.cache_store.set(f"context_{session_id}", context.model_dump())
        
        return context
        
    async def get_conversation_context(self, session_id: str) -> List[Dict[str, Any]]:
        """Get conversation history for the session"""
        
        # Get from runtime memory
        conversation = await self.runtime_memory.get_conversation_history(session_id)
        
        # Limit to last 20 messages for context window
        return conversation[-20:] if len(conversation) > 20 else conversation
        
    async def get_user_context(self, session_id: str) -> Dict[str, Any]:
        """Get user profile and preferences"""
        
        # Check cache first
        cached_profile = await self.cache_store.get(f"user_profile_{session_id}")
        if cached_profile:
            return cached_profile
            
        # Mock user profile - in real implementation would fetch from database
        user_profile = {
            "session_id": session_id,
            "preferences": {
                "response_style": "concise",
                "expertise_level": "intermediate"
            },
            "permissions": {
                "can_access_tools": True,
                "requires_approval": False
            }
        }
        
        # Cache the profile
        await self.cache_store.set(f"user_profile_{session_id}", user_profile, ttl=3600)
        
        return user_profile
        
    async def discover_relevant_tools(self, user_query: str) -> List[str]:
        """Discover tools relevant to the user query"""
        
        # Get all available tools
        all_tools = await self.tool_registry.get_available_tools()
        
        # Use context ranker to find relevant tools
        tool_scores = await self.context_ranker.rank_tools(user_query, all_tools)
        
        # Return top relevant tools (threshold > 0.5)
        relevant_tools = [
            tool_id for tool_id, score in tool_scores.items() 
            if score > 0.5
        ]
        
        logger.info("Discovered relevant tools", 
                   query=user_query[:50], 
                   tools=relevant_tools)
        
        return relevant_tools
        
    async def _retrieve_relevant_memories(self, query: str, session_id: str) -> List[Dict[str, Any]]:
        """Retrieve relevant memories from vector store"""
        
        # Search in vector store
        memories = await self.vector_store.search(
            query=query,
            session_id=session_id,
            limit=5
        )
        
        return memories
        
    async def calculate_relevance_scores(
        self, 
        query: str, 
        tools: List[str], 
        memories: List[Dict[str, Any]]
    ) -> Dict[str, float]:
        """Calculate relevance scores for context elements"""
        
        scores = {}
        
        # Score tools
        for tool in tools:
            tool_info = await self.tool_registry.get_tool_info(tool)
            if tool_info:
                score = await self.context_ranker.calculate_relevance(
                    query, 
                    tool_info.get("description", "")
                )
                scores[f"tool_{tool}"] = score
                
        # Score memories
        for idx, memory in enumerate(memories):
            score = memory.get("score", 0.0)  # Vector search score
            scores[f"memory_{idx}"] = score
            
        return scores
        
    async def update_context(self, session_id: str, updates: Dict[str, Any]):
        """Update context with new information"""
        
        # Update runtime memory
        await self.runtime_memory.add_to_conversation(session_id, updates)
        
        # Update state if needed
        if "state_update" in updates:
            await self.state_manager.update_state(session_id, updates["state_update"])
            
        # Store in vector memory if significant
        if updates.get("store_in_memory", False):
            await self.vector_store.add(
                session_id=session_id,
                content=updates.get("content", ""),
                metadata=updates.get("metadata", {})
            )
            
    async def get_context_summary(self, session_id: str) -> Dict[str, Any]:
        """Get a summary of the current context"""
        
        # Get cached context
        cached_context = await self.cache_store.get(f"context_{session_id}")
        
        if cached_context:
            return {
                "session_id": session_id,
                "has_conversation": len(cached_context.get("conversation_history", [])) > 0,
                "available_tools": len(cached_context.get("available_tools", [])),
                "memory_count": len(cached_context.get("metadata", {}).get("memories", [])),
                "last_updated": cached_context.get("metadata", {}).get("timestamp")
            }
        
        return {
            "session_id": session_id,
            "status": "no_context"
        }
        
    async def clear_session_context(self, session_id: str):
        """Clear all context for a session"""
        
        logger.info("Clearing session context", session_id=session_id)
        
        # Clear from all stores
        await self.runtime_memory.clear_session(session_id)
        await self.cache_store.delete(f"context_{session_id}")
        await self.cache_store.delete(f"user_profile_{session_id}")
        await self.state_manager.clear_state(session_id)