import docker
import uuid
import tempfile
import os
from pathlib import Path
from typing import Dict, Union

class CodeExecutor:
    def __init__(self):
        self.client = docker.from_env()
        self.image_name = "python:3.9-slim"
        
        # Ensure the image exists
        try:
            self.client.images.get(self.image_name)
        except docker.errors.ImageNotFound:
            print(f"Pulling {self.image_name} image...")
            self.client.images.pull(self.image_name)

    def execute_code(self, code: str, timeout: int = 10) -> Dict[str, Union[bool, str]]:
        """
        Execute Python code in an isolated Docker container
        
        Args:
            code: Python code to execute
            timeout: Maximum execution time in seconds
            
        Returns:
            Dict containing success status, output or error message
        """
        # Create a temporary directory and file for the code
        with tempfile.TemporaryDirectory() as temp_dir:
            code_file = Path(temp_dir) / "code.py"
            code_file.write_text(code)
            
            container_name = f"code_executor_{uuid.uuid4().hex[:8]}"
            
            try:
                # Run the code in a container with resource limits
                container = self.client.containers.run(
                    self.image_name,
                    command=["python", "/code/code.py"],
                    name=container_name,
                    volumes={
                        str(temp_dir): {
                            'bind': '/code',
                            'mode': 'ro'  # Read-only mount
                        }
                    },
                    mem_limit="100m",  # 100MB memory limit
                    nano_cpus=1,  # 1 CPU
                    network_mode="none",  # No network access
                    detach=True,
                    remove=True
                )
                
                try:
                    # Wait for the container to finish with timeout
                    container.wait(timeout=timeout)
                    output = container.logs().decode('utf-8')
                    return {
                        "success": True,
                        "output": output
                    }
                    
                except docker.errors.NotFound:
                    return {
                        "success": False,
                        "error": "Container was removed before completion"
                    }
                except Exception as e:
                    return {
                        "success": False,
                        "error": f"Execution error: {str(e)}"
                    }
                finally:
                    try:
                        container.remove(force=True)
                    except:
                        pass
                        
            except Exception as e:
                return {
                    "success": False,
                    "error": f"Container creation error: {str(e)}"
                } 