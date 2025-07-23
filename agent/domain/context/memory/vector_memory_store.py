from typing import Dict, List, Any, Optional
import asyncio
from datetime import datetime


class VectorMemoryStore:
    """Mock vector memory store for semantic search"""
    
    def __init__(self):
        self.memories: Dict[str, List[Dict[str, Any]]] = {}
        self._lock = asyncio.Lock()
        
    async def add(self, session_id: str, content: str, metadata: Dict[str, Any] = None) -> str:
        """Add content to vector store"""
        
        async with self._lock:
            if session_id not in self.memories:
                self.memories[session_id] = []
                
            memory_id = f"{session_id}_{len(self.memories[session_id])}"
            
            memory = {
                "id": memory_id,
                "content": content,
                "metadata": metadata or {},
                "timestamp": datetime.utcnow().isoformat(),
                "embedding": self._mock_embedding(content)  # Mock embedding
            }
            
            self.memories[session_id].append(memory)
            
            # Limit to 1000 memories per session
            if len(self.memories[session_id]) > 1000:
                self.memories[session_id] = self.memories[session_id][-1000:]
                
            return memory_id
            
    async def search(self, query: str, session_id: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Search for relevant memories"""
        
        async with self._lock:
            if session_id not in self.memories:
                return []
                
            # Mock semantic search - just return recent memories with mock scores
            memories = self.memories[session_id][-limit:]
            
            # Add mock relevance scores
            results = []
            for i, memory in enumerate(memories):
                result = memory.copy()
                result["score"] = 0.9 - (i * 0.1)  # Mock declining relevance
                results.append(result)
                
            return results
            
    def _mock_embedding(self, text: str) -> List[float]:
        """Generate mock embedding vector"""
        # Simple hash-based mock embedding
        hash_val = hash(text.lower())
        return [(hash_val >> i) & 1 for i in range(384)]  # 384-dim mock embedding