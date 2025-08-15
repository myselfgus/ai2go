import asyncio
import os
from fast_agent_mcp.core.fastagent import FastAgent
import subprocess

fast = FastAgent("Worker")

@fast.agent(
    name="worker",
    instruction="Execute tarefas em um repositório, instalando dependências e usando tools.",
    servers=["mcp_hub"],
    model="gpt-oss"
)
async def worker(query):
    # Instalar dependências
    if "requirements.txt" in os.listdir("/workspace"):
        subprocess.run(["pip", "install", "-r", "/workspace/requirements.txt"])

    # Executar query
    return await fast.worker.send(query)

if __name__ == "__main__":
    asyncio.run(worker("Exemplo task"))