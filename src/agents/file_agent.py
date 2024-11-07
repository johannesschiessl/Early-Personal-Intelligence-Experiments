import os
from pathlib import Path
from typing import List, Dict, Any
import shutil
import logging
from openai import OpenAI
import json

logging.basicConfig(
    filename='agent_calls.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

class FileAgent:
    def __init__(self, ai_directory: str):
        self.ai_directory = ai_directory
        self.user_directory = os.path.expanduser("~/")
        
        self.max_iterations = 10
        self.current_iteration = 0
        self.client = OpenAI()
        self.messages = []
        
        self._ensure_ai_directory()

    def _ensure_ai_directory(self) -> None:
        """Ensure the AI directory exists and is accessible"""
        try:
            Path(self.ai_directory).mkdir(parents=True, exist_ok=True)
        except Exception as e:
            logging.error(f"Failed to create AI directory: {str(e)}")
            raise RuntimeError(f"Cannot initialize AI directory: {str(e)}")

    @property
    def system_prompt(self) -> str:
        return """You are a File Agent with the capability to read files and copy them to a designated AI directory.
        Your primary responsibilities are:

        1. Safely read files from the system when given either:
           - A specific file path
           - A search query to find relevant files
           
        2. Copy found files to the AI directory for further processing
        
        # Important Guidelines
        - You can ONLY READ files. You cannot modify, delete, or write to original files
        - You must verify file existence before attempting operations
        - You should be cautious with sensitive directories (like /etc, /sys, /root)
        - You must use the return_to_assistant function when your task is complete
        - You have a maximum of 10 iterations before being forced to return
        
        # Process Flow
        1. Receive file path or search query (here you may need to do a few iterations to find the correct file, if a path given is not found, try searching for the file name. Try at least 3 iterations, before giving up and returning)
        2. Verify file existence/find matching files
        3. Read file contents
        4. Copy to AI directory if needed
        5. Return results to the assistant
        
        # Notes
        - Always validate paths before operations
        - Handle errors gracefully
        - Provide clear feedback about actions taken
        - Use return_to_assistant when task is complete

        # Tools
        - read_file: Read the contents of a file at the specified path
        - search_files: Search for files matching the query
        - copy_to_ai_directory: Copy a file to the AI directory (you need to provide the full path to the file, then it will be copied to the AI directory)
        - return_to_assistant: Return a message to the assistant and end the agent's execution
        
        You will be prompted with "What is your next action?" after each tool use.
        You must use the provided tools to accomplish your tasks.
        
        The user's home directory is {self.user_directory}"""

    @property
    def tools(self) -> List[Dict[str, Any]]:
        return [
            {
                "type": "function",
                "function": {
                    "name": "read_file",
                    "description": "Read the contents of a file at the specified path",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "file_path": {
                                "type": "string",
                                "description": "Absolute path to the file"
                            }
                        },
                        "required": ["file_path"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "search_files",
                    "description": "Search for files matching the query",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "Search query (filename or content)"
                            },
                            "directory": {
                                "type": "string",
                                "description": "Directory to start search from (default: current directory)"
                            }
                        },
                        "required": ["query"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "copy_to_ai_directory",
                    "description": "Copy a file to the AI directory",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "source_path": {
                                "type": "string",
                                "description": "Source file path to copy"
                            }
                        },
                        "required": ["source_path"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "return_to_assistant",
                    "description": "Return a message to the assistant and end the agent's execution",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "content": {
                                "type": "string",
                                "description": "Message to return to the assistant"
                            }
                        },
                        "required": ["content"]
                    }
                }
            }
        ]

    def process_task(self, task: str) -> Dict[str, Any]:
        """Process a task using the OpenAI API"""
        self.current_iteration = 0
        self.messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": task}
        ]
        
        while self.current_iteration < self.max_iterations:
            try:
                response = self.client.chat.completions.create(
                    model="gpt-4o",
                    messages=self.messages,
                    tools=self.tools,
                    tool_choice="auto"
                )
                
                response_message = response.choices[0].message
                tool_calls = response_message.tool_calls
                
                if tool_calls:
                    self.messages.append(response_message)
                    
                    for tool_call in tool_calls:
                        function_name = tool_call.function.name
                        arguments = json.loads(tool_call.function.arguments)
                        
                        if function_name == "return_to_assistant":
                            return {"status": "complete", "content": arguments["content"]}
                        
                        if hasattr(self, function_name):
                            function_response = getattr(self, function_name)(**arguments)
                        else:
                            function_response = {"error": f"Unknown function {function_name}"}
                            
                        self.messages.append({
                            "tool_call_id": tool_call.id,
                            "role": "tool",
                            "name": function_name,
                            "content": json.dumps(function_response)
                        })
                    
                    next_prompt = self.handle_response(response_message)
                    self.messages.append({"role": "user", "content": next_prompt})
                    
                else:
                    return {"status": "complete", "content": response_message.content}
                    
            except Exception as e:
                logging.error(f"Error in agent processing: {str(e)}")
                return {
                    "status": "error",
                    "content": f"An error occurred while processing the task: {str(e)}"
                }
                
        return {
            "status": "max_iterations",
            "content": "Maximum number of iterations reached without completing the task."
        }

    def handle_response(self, response: Dict[str, Any]) -> str:
        """Handle the response from the agent and track iterations"""
        self.current_iteration += 1
        
        if self.current_iteration >= self.max_iterations:
            return ("You have reached the maximum number of iterations. Please use the return_to_assistant "
                   "function to explain why you were unable to complete the task.")
            
        return "What is your next action?"

    def read_file(self, file_path: str) -> Dict[str, Any]:
        """Safely read a file and return its contents"""
        try:
            file_path = os.path.abspath(file_path)
            if not os.path.exists(file_path):
                return {"error": f"File not found: {file_path}"}
            
            if not os.path.isfile(file_path):
                return {"error": f"Path is not a file: {file_path}"}
                
            with open(file_path, 'r') as f:
                content = f.read()
            return {"content": content, "path": file_path}
            
        except Exception as e:
            logging.error(f"Error reading file {file_path}: {str(e)}")
            return {"error": f"Error reading file: {str(e)}"}

    def search_files(self, query: str, directory: str = None) -> Dict[str, Any]:
        """Search for files matching the query in user directory"""
        try:
            directory = directory or self.user_directory
            directory = os.path.abspath(directory)
            results = []
            skipped_dirs = set()
            
            def is_safe_directory(dir_path: str) -> bool:
                """Check if directory is safe to search"""
                unsafe_patterns = [
                    'AppData',
                    'Program Files',
                    'Windows',
                    '$Recycle.Bin',
                    'System Volume Information',
                    '.git'
                ]
                return not any(pattern in dir_path for pattern in unsafe_patterns)
            
            for root, dirs, files in os.walk(directory, topdown=True):
                dirs[:] = [d for d in dirs if is_safe_directory(os.path.join(root, d))]
                
                try:
                    for file in files:
                        if query.lower() in file.lower():
                            try:
                                file_path = os.path.join(root, file)
                                # Only include readable files
                                if os.access(file_path, os.R_OK):
                                    results.append({
                                        "path": file_path,
                                        "size": os.path.getsize(file_path),
                                        "modified": os.path.getmtime(file_path)
                                    })
                            except (PermissionError, OSError) as e:
                                continue
                except PermissionError:
                    skipped_dirs.add(root)
                    continue
                    
            return {
                "matches": results,
                "count": len(results),
                "skipped_directories": list(skipped_dirs),
                "base_directory": directory
            }
            
        except Exception as e:
            logging.error(f"Error searching files: {str(e)}")
            return {"error": f"Error searching files: {str(e)}"}

    def copy_to_ai_directory(self, source_path: str) -> Dict[str, Any]:
        """Copy a file to the AI directory"""
        try:
            source_path = os.path.abspath(source_path)
            if not os.path.exists(source_path):
                return {"error": f"Source file not found: {source_path}"}
                
            if not os.path.isfile(source_path):
                return {"error": f"Source path is not a file: {source_path}"}
                
            if not os.access(source_path, os.R_OK):
                return {"error": f"No read permission for file: {source_path}"}
                
            self._ensure_ai_directory()
                
            filename = os.path.basename(source_path)
            destination = os.path.join(self.ai_directory, filename)
            
            if not os.access(os.path.dirname(destination), os.W_OK):
                return {"error": f"No write permission in AI directory: {self.ai_directory}"}
            
            shutil.copy2(source_path, destination)
            return {
                "success": True,
                "source": source_path,
                "destination": destination,
                "file_size": os.path.getsize(destination)
            }
            
        except PermissionError as e:
            logging.error(f"Permission error copying file: {str(e)}")
            return {"error": f"Permission denied: {str(e)}"}
        except Exception as e:
            logging.error(f"Error copying file: {str(e)}")
            return {"error": f"Error copying file: {str(e)}"} 