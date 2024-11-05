import json
import os
from typing import Dict, List
from datetime import datetime

class MemoryManager:
    def __init__(self, file_path: str = "memories.json"):
        self.file_path = file_path
        self.memories = self._load_memories()

    def _load_memories(self) -> Dict:
        if os.path.exists(self.file_path):
            with open(self.file_path, 'r') as f:
                return json.load(f)
        return {}

    def _save_memories(self):
        with open(self.file_path, 'w') as f:
            json.dump(self.memories, f, indent=2)

    def add_memory(self, memory_id: str, content: str) -> Dict:
        """
        Add a new memory with a custom ID and timestamp
        
        Args:
            memory_id: Custom identifier for the memory (e.g. 'john_likes_coffee')
            content: The content of the memory
            
        Returns:
            Dict containing the memory details
        """
        if memory_id in self.memories:
            return {"error": f"Memory with ID {memory_id} already exists"}
            
        timestamp = datetime.now().isoformat()
        memory_data = {
            "content": content,
            "timestamp": timestamp
        }
        
        self.memories[memory_id] = memory_data
        self._save_memories()
        
        return {
            "id": memory_id,
            "content": content,
            "timestamp": timestamp
        }

    def get_all_memories(self) -> str:
        """Get all memories formatted as a string"""
        if not self.memories:
            return "No memories stored."
        
        memory_strings = []
        for memory_id, memory_data in self.memories.items():
            memory_strings.append(
                f"{memory_id}: {memory_data['content']} (Added: {memory_data['timestamp']})"
            )
        return "\n".join(memory_strings)