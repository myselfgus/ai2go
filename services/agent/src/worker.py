import asyncio
import os
import subprocess
import logging
from typing import Optional, Dict, Any, List
from pathlib import Path
from fast_agent_mcp.core.fastagent import FastAgent
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class WorkerSettings(BaseSettings):
    """Configuration settings for the worker"""
    workspace_id: str = Field(default="default", env="WORKSPACE_ID")
    repo_url: str = Field(default="", env="REPO_URL")
    llm_api_key: str = Field(default="your-key", env="LLM_API_KEY")
    gpt_oss_url: str = Field(default="http://gpt-oss:8000/v1/chat/completions", env="GPT_OSS_URL")
    workspace_path: Path = Field(default=Path("/workspace"), env="WORKSPACE_PATH")
    
    class Config:
        env_file = ".env"

class TaskRequest(BaseModel):
    """Request model for task execution"""
    query: str
    context: Optional[Dict[str, Any]] = None
    tools: List[str] = Field(default_factory=list)

class WorkerAgent:
    """Worker agent that executes tasks in isolated container environment"""
    
    def __init__(self):
        self.settings = WorkerSettings()
        self.setup_environment()
        self.fast_agent = FastAgent(f"Worker-{self.settings.workspace_id}")
        
    def setup_environment(self):
        """Configure environment variables"""
        os.environ["LLM_API_KEY"] = self.settings.llm_api_key
        os.environ["GPT_OSS_URL"] = self.settings.gpt_oss_url
        logger.info(f"Worker initialized for workspace: {self.settings.workspace_id}")

    async def initialize_workspace(self) -> bool:
        """Initialize workspace with repository and dependencies"""
        try:
            workspace_path = self.settings.workspace_path
            
            # Create workspace directory if it doesn't exist
            workspace_path.mkdir(parents=True, exist_ok=True)
            
            # Clone repository if URL provided and not already cloned
            if self.settings.repo_url and not (workspace_path / ".git").exists():
                logger.info(f"Cloning repository: {self.settings.repo_url}")
                result = subprocess.run([
                    "git", "clone", self.settings.repo_url, str(workspace_path)
                ], capture_output=True, text=True, timeout=300)
                
                if result.returncode != 0:
                    logger.error(f"Failed to clone repository: {result.stderr}")
                    return False
                    
                logger.info("Repository cloned successfully")
            
            # Change to workspace directory
            os.chdir(workspace_path)
            
            # Install Python dependencies if requirements.txt exists
            await self._install_dependencies()
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize workspace: {e}")
            return False

    async def _install_dependencies(self):
        """Install project dependencies"""
        workspace_path = self.settings.workspace_path
        
        # Install from requirements.txt
        requirements_file = workspace_path / "requirements.txt"
        if requirements_file.exists():
            logger.info("Installing Python dependencies from requirements.txt")
            try:
                result = subprocess.run([
                    "pip", "install", "-r", str(requirements_file)
                ], capture_output=True, text=True, timeout=600)
                
                if result.returncode == 0:
                    logger.info("Python dependencies installed successfully")
                else:
                    logger.warning(f"Failed to install some dependencies: {result.stderr}")
            except subprocess.TimeoutExpired:
                logger.warning("Dependency installation timed out")
        
        # Install from pyproject.toml
        pyproject_file = workspace_path / "pyproject.toml"
        if pyproject_file.exists():
            logger.info("Installing Python dependencies from pyproject.toml")
            try:
                result = subprocess.run([
                    "pip", "install", "-e", "."
                ], capture_output=True, text=True, timeout=600)
                
                if result.returncode == 0:
                    logger.info("Project installed successfully")
                else:
                    logger.warning(f"Failed to install project: {result.stderr}")
            except subprocess.TimeoutExpired:
                logger.warning("Project installation timed out")
        
        # Install from package.json (Node.js)
        package_json = workspace_path / "package.json"
        if package_json.exists():
            logger.info("Installing Node.js dependencies")
            try:
                result = subprocess.run([
                    "npm", "install"
                ], capture_output=True, text=True, timeout=600)
                
                if result.returncode == 0:
                    logger.info("Node.js dependencies installed successfully")
                else:
                    logger.warning(f"Failed to install Node.js dependencies: {result.stderr}")
            except subprocess.TimeoutExpired:
                logger.warning("Node.js dependency installation timed out")

    async def execute_task(self, task: TaskRequest) -> Dict[str, Any]:
        """Execute a task in the workspace"""
        try:
            logger.info(f"Executing task: {task.query}")
            
            # Initialize workspace if not already done
            if not await self.initialize_workspace():
                return {
                    "status": "error",
                    "error": "Failed to initialize workspace"
                }
            
            # Prepare context for the agent
            context = task.context or {}
            
            # Execute task using FastAgent
            response = await self.fast_agent.send(
                task.query, 
                context=context
            )
            
            logger.info("Task executed successfully")
            
            return {
                "status": "success",
                "response": response,
                "workspace_id": self.settings.workspace_id
            }
            
        except Exception as e:
            logger.error(f"Error executing task: {e}")
            return {
                "status": "error",
                "error": str(e)
            }

    async def run_command(self, command: str, timeout: int = 300) -> Dict[str, Any]:
        """Run a shell command in the workspace"""
        try:
            logger.info(f"Running command: {command}")
            
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=self.settings.workspace_path
            )
            
            return {
                "status": "success",
                "returncode": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr
            }
            
        except subprocess.TimeoutExpired:
            logger.error(f"Command timed out: {command}")
            return {
                "status": "error",
                "error": f"Command timed out after {timeout}s"
            }
        except Exception as e:
            logger.error(f"Error running command: {e}")
            return {
                "status": "error",
                "error": str(e)
            }

    async def list_files(self, path: str = ".") -> Dict[str, Any]:
        """List files in the workspace"""
        try:
            target_path = self.settings.workspace_path / path
            
            if not target_path.exists():
                return {
                    "status": "error",
                    "error": f"Path does not exist: {path}"
                }
            
            files = []
            if target_path.is_dir():
                for item in target_path.iterdir():
                    files.append({
                        "name": item.name,
                        "type": "directory" if item.is_dir() else "file",
                        "size": item.stat().st_size if item.is_file() else None
                    })
            else:
                files.append({
                    "name": target_path.name,
                    "type": "file",
                    "size": target_path.stat().st_size
                })
            
            return {
                "status": "success",
                "path": path,
                "files": files
            }
            
        except Exception as e:
            logger.error(f"Error listing files: {e}")
            return {
                "status": "error",
                "error": str(e)
            }

    async def read_file(self, file_path: str) -> Dict[str, Any]:
        """Read a file from the workspace"""
        try:
            target_path = self.settings.workspace_path / file_path
            
            if not target_path.exists() or not target_path.is_file():
                return {
                    "status": "error",
                    "error": f"File does not exist: {file_path}"
                }
            
            content = target_path.read_text(encoding="utf-8")
            
            return {
                "status": "success",
                "file_path": file_path,
                "content": content,
                "size": len(content)
            }
            
        except Exception as e:
            logger.error(f"Error reading file: {e}")
            return {
                "status": "error",
                "error": str(e)
            }

    async def write_file(self, file_path: str, content: str) -> Dict[str, Any]:
        """Write content to a file in the workspace"""
        try:
            target_path = self.settings.workspace_path / file_path
            
            # Create parent directories if they don't exist
            target_path.parent.mkdir(parents=True, exist_ok=True)
            
            target_path.write_text(content, encoding="utf-8")
            
            return {
                "status": "success",
                "file_path": file_path,
                "size": len(content)
            }
            
        except Exception as e:
            logger.error(f"Error writing file: {e}")
            return {
                "status": "error",
                "error": str(e)
            }

# Create worker instance
worker = WorkerAgent()

@worker.fast_agent.agent(
    name="worker",
    instruction="Execute tarefas em um repositório, instalando dependências e usando tools MCP quando necessário.",
    servers=["mcp_hub"],
    model="gpt-oss",
    use_history=True
)
async def execute_main_task(query: str, context: Optional[Dict[str, Any]] = None) -> str:
    """Main task execution endpoint"""
    task = TaskRequest(query=query, context=context)
    result = await worker.execute_task(task)
    return str(result)

@worker.fast_agent.tool(
    name="run_command",
    description="Execute shell command in workspace",
    parameters={"command": str, "timeout": int}
)
async def run_shell_command(command: str, timeout: int = 300) -> str:
    """Tool to run shell commands"""
    result = await worker.run_command(command, timeout)
    return str(result)

@worker.fast_agent.tool(
    name="list_files",
    description="List files in workspace directory",
    parameters={"path": str}
)
async def list_workspace_files(path: str = ".") -> str:
    """Tool to list files"""
    result = await worker.list_files(path)
    return str(result)

@worker.fast_agent.tool(
    name="read_file",
    description="Read file content from workspace",
    parameters={"file_path": str}
)
async def read_workspace_file(file_path: str) -> str:
    """Tool to read files"""
    result = await worker.read_file(file_path)
    return str(result)

@worker.fast_agent.tool(
    name="write_file",
    description="Write content to file in workspace",
    parameters={"file_path": str, "content": str}
)
async def write_workspace_file(file_path: str, content: str) -> str:
    """Tool to write files"""
    result = await worker.write_file(file_path, content)
    return str(result)

async def health_check() -> Dict[str, str]:
    """Health check endpoint"""
    try:
        workspace_path = worker.settings.workspace_path
        
        return {
            "status": "healthy",
            "workspace_id": worker.settings.workspace_id,
            "workspace_path": str(workspace_path),
            "workspace_exists": str(workspace_path.exists())
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e)
        }

if __name__ == "__main__":
    async def main():
        """Main entry point for worker"""
        logger.info("Starting AI Agent Worker")
        
        # Health check
        health = await health_check()
        logger.info(f"Health check: {health}")
        
        # Initialize workspace
        if await worker.initialize_workspace():
            logger.info("Workspace initialized successfully")
            
            # Example task execution
            example_task = TaskRequest(
                query="Listar arquivos no diretório atual e verificar se há um README"
            )
            
            result = await worker.execute_task(example_task)
            logger.info(f"Example task result: {result}")
        else:
            logger.error("Failed to initialize workspace")
    
    asyncio.run(main())