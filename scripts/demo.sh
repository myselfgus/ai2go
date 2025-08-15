#!/bin/bash

# AI Agent System Demo Script
# This script demonstrates the key features of the Docker optimization architecture

set -e

echo "🎭 AI Agent System - Docker Optimization Architecture Demo"
echo "========================================================"
echo ""

# Check if Docker is available
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed or not available"
    exit 1
fi

echo "🐳 Docker is available"
echo ""

# Show system structure
echo "📁 System Structure:"
echo "==================="
tree -L 3 -I '__pycache__|*.pyc|.git' . || ls -la
echo ""

# Show configuration examples
echo "⚙️  Configuration Examples:"
echo "=========================="
echo ""
echo "🔧 Environment Configuration (.env.example):"
echo "----------------------------------------------"
head -10 .env.example
echo ""

echo "🤖 GPT-OSS Configuration:"
echo "-------------------------"
head -15 config/gpt-oss-config.yaml
echo ""

echo "🔌 MCP Hub Configuration:"
echo "------------------------"
head -20 config/mcp-hub.yaml
echo ""

# Show Docker Compose services
echo "🐳 Docker Services Available:"
echo "============================="
grep -A 2 "^  [a-z].*:$" docker-compose.yml | head -20
echo ""

# Show key features of each service
echo "🎯 Key System Components:"
echo "========================="
echo ""

echo "🎭 ORCHESTRATOR (services/orchestrator/src/agent.py):"
echo "- Manages container-based agents"
echo "- Integrates with cognee for memory"
echo "- Coordinates MCP tools"
echo "- Handles workspace routing"
echo ""

echo "🤖 AGENT WORKER (services/agent/src/worker.py):"
echo "- Runs in isolated containers"
echo "- Manages repository cloning"
echo "- Handles dependency installation"
echo "- Executes tasks with file operations"
echo ""

echo "🧠 GPT-OSS SERVICE (Dockerfile.gpt-oss):"
echo "- Self-hosted AI model via vLLM"
echo "- OpenAI-compatible API"
echo "- Cost-effective alternative"
echo "- Local deployment option"
echo ""

# Show usage examples
echo "🚀 Usage Examples:"
echo "=================="
echo ""

echo "1️⃣ Local Development:"
echo "--------------------"
echo "docker-compose up -d"
echo "curl -X POST http://localhost:8080/orchestrate \\"
echo "  -H 'Content-Type: application/json' \\"
echo "  -d '{\"query\": \"Analyze repository structure\", \"repo_url\": \"https://github.com/example/repo\"}'"
echo ""

echo "2️⃣ Cloud Deployment:"
echo "--------------------"
echo "export PROJECT_ID=\"your-gcp-project\""
echo "export REGION=\"us-central1\""
echo "export GCS_BUCKET=\"your-bucket\""
echo "export LLM_API_KEY=\"your-key\""
echo "./scripts/deploy.sh"
echo ""

echo "3️⃣ Container Management:"
echo "-----------------------"
echo "# List active containers"
echo "curl http://localhost:8080/containers"
echo ""
echo "# Stop specific workspace"
echo "curl -X POST http://localhost:8080/manage \\"
echo "  -H 'Content-Type: application/json' \\"
echo "  -d '{\"action\": \"stop\", \"workspace_id\": \"repo-12345\"}'"
echo ""

# Show cost optimization features
echo "💰 Cost Optimization Features:"
echo "=============================="
echo "✅ GPT-OSS self-hosting (~$0.02/hour vs $0.01/1K tokens)"
echo "✅ Container reuse (no repeated cloning)"
echo "✅ Multi-stage Docker builds (smaller images)"
echo "✅ Distroless base images (security + size)"
echo "✅ Resource limits per container"
echo "✅ Auto-scaling and suspension"
echo ""

# Show architecture benefits
echo "🏗️  Architecture Benefits:"
echo "=========================="
echo "🔒 Isolation: Each repository in separate container"
echo "🔄 Persistence: Containers persist to avoid re-setup"
echo "📈 Scalability: Dynamic container activation"
echo "🛠️  Flexibility: MCP tools for enhanced capabilities"
echo "☁️  Cloud Native: Optimized for Google Cloud Run"
echo "🐳 Portability: Works with Docker Desktop locally"
echo ""

# Show next steps
echo "🎯 Next Steps:"
echo "=============="
echo "1. Copy .env.example to .env and configure"
echo "2. Run 'docker-compose up -d' for local testing"
echo "3. Use './scripts/deploy.sh' for Cloud Run deployment"
echo "4. Test with the provided API examples"
echo "5. Add your repositories to the system"
echo ""

echo "✨ AI Agent System is ready for use!"
echo ""
echo "📚 For more information, see README.md"
echo "🐛 For issues, check the troubleshooting section"
echo "🚀 Happy coding with your AI agent team!"