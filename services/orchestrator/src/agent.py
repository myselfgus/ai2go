import asyncio
import os
import logging
from typing import Optional, List, Dict, Any
from fast_agent_mcp.core.fastagent import FastAgent
import cognee
import docker
from playwright.async_api import async_playwright
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class OrchestratorSettings(BaseSettings):
    """Configuration settings for the orchestrator"""
    llm_api_key: str = Field(default="your-key", env="LLM_API_KEY")
    gpt_oss_url: str = Field(default="http://gpt-oss:8000/v1/chat/completions", env="GPT_OSS_URL")
    db_url: str = Field(default="postgresql://user:pass@host/db", env="DATABASE_URL")
    gcs_bucket: str = Field(default="ai-agent-repos", env="GCS_BUCKET")
    project_id: str = Field(default="ai-agent-project", env="PROJECT_ID")
    region: str = Field(default="us-central1", env="REGION")
    
    class Config:
        env_file = ".env"

class WorkspaceRequest(BaseModel):
    """Request model for workspace operations"""
    query: str
    repo_url: Optional[str] = None
    files: List[str] = Field(default_factory=list)
    workspace_id: Optional[str] = None

class OrchestratorAgent:
    """Main orchestrator that manages agent containers"""
    
    def __init__(self):
        self.settings = OrchestratorSettings()
        self.setup_environment()
        self.docker_client = docker.from_env()
        self.fast_agent = FastAgent("Orchestrator")
        
    def setup_environment(self):
        """Configure environment variables and initialize cognee"""
        os.environ["LLM_API_KEY"] = self.settings.llm_api_key
        os.environ["GPT_OSS_URL"] = self.settings.gpt_oss_url
        
        try:
            cognee.init(
                llm_api_key=self.settings.llm_api_key, 
                db_url=self.settings.db_url
            )
            logger.info("Cognee initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize cognee: {e}")

    async def orchestrate(self, request: WorkspaceRequest) -> Dict[str, Any]:
        """Main orchestration method"""
        try:
            logger.info(f"Processing request: {request.query}")
            
            # Ingest query and files into memory
            content = request.query + " " + " ".join(request.files)
            await cognee.add(content)
            await cognee.cognify()
            
            # Determine workspace ID
            workspace_id = request.workspace_id or self._generate_workspace_id(request.repo_url)
            
            # Start or get existing container
            container = await self.start_container(workspace_id, request.repo_url)
            
            # Create worker agent
            worker = FastAgent(
                f"Worker-{workspace_id}", 
                servers=["mcp_hub"], 
                model="gpt-oss"
            )
            
            # Get context from memory
            context = await cognee.search(request.query)
            
            # Send task to worker
            response = await worker.send(request.query, context=context)
            
            logger.info(f"Task completed for workspace {workspace_id}")
            
            return {
                "status": "success",
                "workspace_id": workspace_id,
                "response": response,
                "container_id": container.id
            }
            
        except Exception as e:
            logger.error(f"Error in orchestration: {e}")
            return {
                "status": "error",
                "error": str(e)
            }

    def _generate_workspace_id(self, repo_url: Optional[str]) -> str:
        """Generate workspace ID based on repository URL"""
        if repo_url:
            return f"repo-{abs(hash(repo_url)) % 10000}"
        return "default"

    async def start_container(self, workspace_id: str, repo_url: Optional[str]):
        """Start or get existing container for workspace"""
        try:
            # Try to get existing container
            container = self.docker_client.containers.get(workspace_id)
            if container.status != "running":
                container.start()
                logger.info(f"Started existing container {workspace_id}")
        except docker.errors.NotFound:
            # Create new container
            logger.info(f"Creating new container {workspace_id}")
            
            # Configure volume for GCS
            volume_config = f"gs://{self.settings.gcs_bucket}/repos/{workspace_id}:/workspace"
            
            container = self.docker_client.containers.run(
                f"gcr.io/{self.settings.project_id}/agent",
                name=workspace_id,
                volumes=[volume_config],
                environment={
                    "REPO_URL": repo_url or "",
                    "WORKSPACE_ID": workspace_id,
                    "LLM_API_KEY": self.settings.llm_api_key,
                    "GPT_OSS_URL": self.settings.gpt_oss_url
                },
                detach=True,
                ports={'8081/tcp': None},  # Random host port
                restart_policy={"Name": "unless-stopped"}
            )
            logger.info(f"Created container {workspace_id} with ID {container.id}")
            
        return container

    async def stop_container(self, workspace_id: str) -> bool:
        """Stop container for workspace"""
        try:
            container = self.docker_client.containers.get(workspace_id)
            container.stop()
            logger.info(f"Stopped container {workspace_id}")
            return True
        except docker.errors.NotFound:
            logger.warning(f"Container {workspace_id} not found")
            return False
        except Exception as e:
            logger.error(f"Error stopping container {workspace_id}: {e}")
            return False

    async def list_containers(self) -> List[Dict[str, Any]]:
        """List all managed containers"""
        containers = []
        for container in self.docker_client.containers.list(all=True):
            if container.name.startswith("repo-") or container.name == "default":
                containers.append({
                    "name": container.name,
                    "id": container.id,
                    "status": container.status,
                    "image": container.image.tags[0] if container.image.tags else "unknown"
                })
        return containers

# Setup FastAgent tools
orchestrator = OrchestratorAgent()

@orchestrator.fast_agent.agent(
    name="orchestrator",
    instruction="Gerencie uma equipe de agentes, cada um em um container com um repositório. Ative o container correto por tarefa.",
    servers=["mcp_hub"],
    model="gpt-oss",
    use_history=True,
    human_input=True,
    multimodal=True
)
async def orchestrate_main(query: str, repo_url: Optional[str] = None, files: List[str] = None) -> str:
    """Main orchestration endpoint"""
    if files is None:
        files = []
    
    request = WorkspaceRequest(
        query=query,
        repo_url=repo_url,
        files=files
    )
    
    result = await orchestrator.orchestrate(request)
    return str(result)

@orchestrator.fast_agent.tool(
    name="browse_web",
    description="Navegue web em browser isolado",
    parameters={"url": str, "instructions": str}
)
async def browse_web(url: str, instructions: str) -> str:
    """Web browsing tool with isolated Playwright instance"""
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            await page.goto(url)
            
            # Execute instructions as JavaScript
            content = await page.evaluate(instructions)
            await browser.close()
            
            return str(content)
    except Exception as e:
        logger.error(f"Error browsing web: {e}")
        return f"Error: {e}"

@orchestrator.fast_agent.tool(
    name="attach_mcp_server",
    description="Anexe MCP server",
    parameters={"server_name": str}
)
async def attach_mcp(server_name: str) -> Dict[str, Any]:
    """Attach MCP server and load toolset"""
    try:
        client = FastAgent(f"mcp-{server_name}", servers=[server_name])
        toolset = await client.load_toolset()
        logger.info(f"Attached MCP server: {server_name}")
        return {"status": "success", "server": server_name, "tools": toolset}
    except Exception as e:
        logger.error(f"Error attaching MCP server {server_name}: {e}")
        return {"status": "error", "error": str(e)}

@orchestrator.fast_agent.tool(
    name="manage_containers",
    description="Gerencie containers (list, stop, start)",
    parameters={"action": str, "workspace_id": str}
)
async def manage_containers(action: str, workspace_id: str = "") -> Dict[str, Any]:
    """Container management tool"""
    try:
        if action == "list":
            containers = await orchestrator.list_containers()
            return {"status": "success", "containers": containers}
        elif action == "stop" and workspace_id:
            success = await orchestrator.stop_container(workspace_id)
            return {"status": "success" if success else "error", "workspace_id": workspace_id}
        else:
            return {"status": "error", "error": "Invalid action or missing workspace_id"}
    except Exception as e:
        logger.error(f"Error managing containers: {e}")
        return {"status": "error", "error": str(e)}

async def health_check() -> Dict[str, str]:
    """Health check endpoint"""
    try:
        # Check Docker connection
        orchestrator.docker_client.ping()
        
        # Check cognee connection
        await cognee.search("health")
        
        return {"status": "healthy", "timestamp": str(asyncio.get_event_loop().time())}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}

if __name__ == "__main__":
    async def main():
        """Main entry point"""
        logger.info("Starting AI Agent Orchestrator")
        
        # Health check
        health = await health_check()
        logger.info(f"Health check: {health}")
        
        # Example orchestration
        example_request = WorkspaceRequest(
            query="Exemplo: navegue em github.com e extraia informações sobre repositórios populares",
            repo_url="https://github.com/example/repo"
        )
        
        result = await orchestrator.orchestrate(example_request)
        logger.info(f"Example result: {result}")
    
    asyncio.run(main())