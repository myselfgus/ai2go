#!/usr/bin/env python3
"""
Test script for AI Agent System
Validates basic functionality of orchestrator and agent components
"""

import asyncio
import sys
import logging
from pathlib import Path

# Add services to path
sys.path.insert(0, str(Path(__file__).parent / "services" / "orchestrator" / "src"))
sys.path.insert(0, str(Path(__file__).parent / "services" / "agent" / "src"))

from agent import OrchestratorAgent, WorkspaceRequest
from worker import WorkerAgent, TaskRequest

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_orchestrator():
    """Test orchestrator initialization and basic functionality"""
    logger.info("🧪 Testing Orchestrator...")
    
    try:
        orchestrator = OrchestratorAgent()
        
        # Test workspace ID generation
        workspace_id = orchestrator._generate_workspace_id("https://github.com/test/repo")
        assert workspace_id.startswith("repo-"), f"Invalid workspace ID: {workspace_id}"
        
        # Test settings
        assert orchestrator.settings.project_id == "ai-agent-project"
        assert orchestrator.settings.region == "us-central1"
        
        logger.info("✅ Orchestrator tests passed")
        return True
        
    except Exception as e:
        logger.error(f"❌ Orchestrator test failed: {e}")
        return False

async def test_worker():
    """Test worker agent initialization and basic functionality"""
    logger.info("🧪 Testing Worker Agent...")
    
    try:
        worker = WorkerAgent()
        
        # Test settings
        assert worker.settings.workspace_id == "default"
        assert worker.settings.workspace_path == Path("/workspace")
        
        # Test task request model
        task = TaskRequest(query="Test query", context={"test": True})
        assert task.query == "Test query"
        assert task.context["test"] is True
        
        logger.info("✅ Worker Agent tests passed")
        return True
        
    except Exception as e:
        logger.error(f"❌ Worker Agent test failed: {e}")
        return False

async def test_file_operations():
    """Test file operations (using local filesystem)"""
    logger.info("🧪 Testing File Operations...")
    
    try:
        # Create temporary test file
        test_file = Path("/tmp/test_ai_agent.txt")
        test_content = "Hello from AI Agent System!"
        
        test_file.write_text(test_content)
        
        # Test reading
        read_content = test_file.read_text()
        assert read_content == test_content, "File content mismatch"
        
        # Cleanup
        test_file.unlink()
        
        logger.info("✅ File operations tests passed")
        return True
        
    except Exception as e:
        logger.error(f"❌ File operations test failed: {e}")
        return False

async def test_configuration():
    """Test configuration loading"""
    logger.info("🧪 Testing Configuration...")
    
    try:
        # Check if config files exist
        config_dir = Path(__file__).parent / "config"
        
        required_configs = [
            "gpt-oss-config.yaml",
            "mcp-hub.yaml"
        ]
        
        for config_file in required_configs:
            config_path = config_dir / config_file
            assert config_path.exists(), f"Missing config file: {config_file}"
            
        logger.info("✅ Configuration tests passed")
        return True
        
    except Exception as e:
        logger.error(f"❌ Configuration test failed: {e}")
        return False

async def test_docker_files():
    """Test Docker files existence and basic validation"""
    logger.info("🧪 Testing Docker Files...")
    
    try:
        base_dir = Path(__file__).parent
        
        docker_files = [
            "Dockerfile.orchestrator",
            "Dockerfile.agent", 
            "Dockerfile.gpt-oss",
            "docker-compose.yml"
        ]
        
        for docker_file in docker_files:
            docker_path = base_dir / docker_file
            assert docker_path.exists(), f"Missing Docker file: {docker_file}"
            
            # Basic content validation
            content = docker_path.read_text()
            if docker_file.startswith("Dockerfile"):
                assert "FROM" in content, f"Invalid Dockerfile: {docker_file}"
            elif docker_file == "docker-compose.yml":
                assert "version:" in content, f"Invalid docker-compose.yml"
                
        logger.info("✅ Docker files tests passed")
        return True
        
    except Exception as e:
        logger.error(f"❌ Docker files test failed: {e}")
        return False

async def main():
    """Run all tests"""
    logger.info("🚀 Starting AI Agent System Tests")
    
    tests = [
        test_configuration,
        test_docker_files,
        test_file_operations,
        test_orchestrator,
        test_worker,
    ]
    
    results = []
    for test in tests:
        try:
            result = await test()
            results.append(result)
        except Exception as e:
            logger.error(f"❌ Test {test.__name__} failed with exception: {e}")
            results.append(False)
    
    # Summary
    passed = sum(results)
    total = len(results)
    
    logger.info(f"📊 Test Results: {passed}/{total} passed")
    
    if passed == total:
        logger.info("🎉 All tests passed! System is ready.")
        return 0
    else:
        logger.error(f"❌ {total - passed} tests failed. Please check the logs.")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())