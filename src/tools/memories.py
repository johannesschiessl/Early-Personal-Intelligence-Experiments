import json
import os
from typing import Optional, Dict, List
from pathlib import Path

class Memory:
    def __init__(self):
        self.data_dir = Path("data")
        self.memories_file = self.data_dir / "memories.json"
        self._initialize_storage()

    def _initialize_storage(self) -> None:
        """Initialize the memories storage file if it doesn't exist"""
        if not self.data_dir.exists():
            self.data_dir.mkdir(parents=True)
        
        if not self.memories_file.exists():
            with open(self.memories_file, "w") as f:
                json.dump({}, f)

    def _load_memories(self) -> Dict:
        """Load all memories from storage"""
        with open(self.memories_file, "r") as f:
            return json.load(f)

    def _save_memories(self, memories: Dict) -> None:
        """Save memories to storage"""
        with open(self.memories_file, "w") as f:
            json.dump(memories, f, indent=2)

    def __call__(self, mode: str, memory_id: str, chat_id: int, content: Optional[str] = None) -> Dict:
        """
        Handle memory operations
        Args:
            mode: 'w' for write/update, 'd' for delete
            memory_id: Unique identifier for the memory (e.g., 'user_name_memory_type')
            chat_id: Telegram chat ID
            content: Memory content (required for write mode)
        """
        memories = self._load_memories()
        chat_id = str(chat_id)
        
        if chat_id not in memories:
            memories[chat_id] = {}

        if mode == "w":
            if not content:
                raise ValueError("Content is required for write mode")
            memories[chat_id][memory_id] = content
            self._save_memories(memories)
            return {"status": "success", "message": f"Memory {memory_id} saved"}
            
        elif mode == "d":
            if memory_id in memories[chat_id]:
                del memories[chat_id][memory_id]
                self._save_memories(memories)
                return {"status": "success", "message": f"Memory {memory_id} deleted"}
            return {"status": "error", "message": "Memory not found"}
            
        else:
            raise ValueError("Invalid mode. Use 'w' for write or 'd' for delete") 