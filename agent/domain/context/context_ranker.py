from typing import Dict, List, Any
import asyncio
import re


class ContextRanker:
    """Ranks context elements by relevance to query"""
    
    def __init__(self):
        pass
        
    async def rank_tools(self, query: str, tools: List[Dict[str, Any]]) -> Dict[str, float]:
        """Rank tools by relevance to query"""
        
        scores = {}
        query_lower = query.lower()
        query_words = set(re.findall(r'\w+', query_lower))
        
        for tool in tools:
            tool_id = tool.get("id", "")
            description = tool.get("description", "").lower()
            name = tool.get("name", "").lower()
            
            # Simple keyword matching
            desc_words = set(re.findall(r'\w+', description))
            name_words = set(re.findall(r'\w+', name))
            
            # Calculate overlap
            desc_overlap = len(query_words.intersection(desc_words))
            name_overlap = len(query_words.intersection(name_words))
            
            # Weight name matches higher
            score = (name_overlap * 2 + desc_overlap) / len(query_words) if query_words else 0
            scores[tool_id] = min(score, 1.0)  # Cap at 1.0
            
        return scores
        
    async def calculate_relevance(self, query: str, content: str) -> float:
        """Calculate relevance score between query and content"""
        
        query_lower = query.lower()
        content_lower = content.lower()
        
        # Simple keyword overlap scoring
        query_words = set(re.findall(r'\w+', query_lower))
        content_words = set(re.findall(r'\w+', content_lower))
        
        if not query_words:
            return 0.0
            
        overlap = len(query_words.intersection(content_words))
        score = overlap / len(query_words)
        
        # Boost score if query appears as substring
        if query_lower in content_lower:
            score += 0.3
            
        return min(score, 1.0)  # Cap at 1.0