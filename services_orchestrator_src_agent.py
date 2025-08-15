import asyncio
import os
from fast_agent_mcp.core.fastagent import FastAgent
import cognee
import docker
from playwright.async_api import async_playwright

# Configuração inicial
os.environ["LLM_API_KEY"] = os.getenv("LLM_API_KEY", "your-key")
os.environ["GPT_OSS_URL"] = "http://gpt-oss:8000/v1/chat/completions"
cognee.init(llm_api_key=os.getenv("LLM_API_KEY"), db_url="postgresql://user:pass@host/db")

fast = FastAgent("Orchestrator")

# Gerencia containers
docker_client = docker.from_env()

@fast.agent(
    name="orchestrator",
    instruction="Gerencie uma equipe de agentes, cada um em um container com um repositório. Ative o container correto por tarefa.",
    servers=["mcp_hub"],
    model="gpt-oss",  # Ou gemini-1.5-pro
    use_history=True,
    human_input=True,
    multimodal=True
)
async def orchestrate(query, repo_url=None, files=[]):
    # Ingest para memória
    await cognee.add(query + " " + " ".join(files))
    await cognee.cognify()

    # Ativar container para repositório
    workspace_id = f"repo-{hash(repo_url)}" if repo_url else "default"
    container = await start_container(workspace_id, repo_url)

    # Agente worker no container
    worker = FastAgent(f"Worker-{workspace_id}", servers=["mcp_hub"], model="gpt-oss")
    response = await worker.send(query, context=await cognee.search(query))

    # Parar container após uso (opcional, para economia)
    # docker_client.containers.get(container.id).stop()

    return response

async def start_container(workspace_id, repo_url):
    volume = f"gs://{os.getenv('GCS_BUCKET')}/repos/{workspace_id}:/workspace"
    try:
        container = docker_client.containers.get(workspace_id)
        if container.status != "running":
            container.start()
    except docker.errors.NotFound:
        container = docker_client.containers.run(
            "gcr.io/project/agent",
            name=workspace_id,
            volumes=[volume],
            environment={"REPO_URL": repo_url},
            detach=True
        )
    return container

# Tool para Web Nav
@fast.tool(
    name="browse_web",
    description="Navegue web em browser isolado",
    parameters={"url": str, "instructions": str}
)
async def browse_web(url, instructions):
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        await page.goto(url)
        content = await page.evaluate(instructions)
        await browser.close()
        return content

# Tool para MCP Attach
@fast.tool(
    name="attach_mcp_server",
    description="Anexe MCP server",
    parameters={"server_name": str}
)
async def attach_mcp(server_name):
    client = FastAgent(f"mcp-{server_name}", servers=[server_name])
    return await client.load_toolset()

if __name__ == "__main__":
    asyncio.run(orchestrate("Exemplo: navegue em site.com e extraia texto"))