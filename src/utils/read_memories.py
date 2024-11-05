import json
from pathlib import Path
from typing import Dict

def read_memories(chat_id: int) -> Dict:
    """Read all memories for a specific chat_id"""
    memories_file = Path("data/memories.json")
    
    if not memories_file.exists():
        return {}
        
    with open(memories_file, "r") as f:
        memories = json.load(f)
        
    return memories.get(str(chat_id), {}) 