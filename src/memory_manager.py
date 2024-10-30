import json
import os
from typing import Dict, List
import uuid

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

    def add_memory(self, content: str) -> str:
        memory_id = str(uuid.uuid4())
        self.memories[memory_id] = content
        self._save_memories()
        return memory_id

    def get_all_memories(self) -> str:
        if not self.memories:
            return "No memories stored."
        return "\n".join([f"{k}: {v}" for k, v in self.memories.items()])