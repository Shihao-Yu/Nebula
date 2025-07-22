# Assembles context from multiple sources
class ContextManager:
    async def build_context(self, user_query: str, session_id: str) -> ExecutionContext:
        # Gather context from multiple sources
        conversation_context = await self.get_conversation_context(session_id)
        user_context = await self.get_user_context(session_id)
        relevant_tools = await self.discover_relevant_tools(user_query)
        
        return ExecutionContext(
            query=user_query,
            conversation_history=conversation_context,
            user_profile=user_context,
            available_tools=relevant_tools,
            relevance_scores=self.calculate_relevance_scores()
        )