# Deployment Readiness Agent

## Overview

The Deployment Readiness Agent is an automated validation tool that ensures the ai2go repository is ready for production deployment on Docker/GCP. It performs comprehensive checks to identify issues that would prevent successful deployment and provides clear, actionable guidance.

## Features

- **Service Structure Validation**: Ensures all expected services have proper directory structure and content
- **Dockerfile Verification**: Validates that all services have production-ready Dockerfiles
- **Docker Compose Validation**: Checks docker-compose.yml configuration for deployment readiness
- **Environment Configuration**: Validates environment variables and secrets management
- **Localhost/Mock/Placeholder Policy Enforcement**: Ensures compliance with repository policies (PROIBIDO LOCALHOST, PROIBIDO MOCK, PROIBIDO PLACEHOLDER)
- **Build Process Validation**: Verifies build processes work correctly
- **GCP Deployment Readiness**: Checks for GCP-specific deployment configurations

## Usage

### Command Line

```bash
# Run deployment readiness check
python3 deployment_readiness_agent.py

# Or use the Makefile
make check-deploy
```

### CI/CD Integration

The agent returns appropriate exit codes:
- `0`: Repository is deployment ready
- `1`: Critical issues found, deployment not ready
- `130`: Interrupted by user
- Other: Unexpected errors

## Validation Checks

### 1. Service Structure
- Verifies all expected services exist: `fast-agent`, `codemcp`, `genai-toolbox`, `cognee`, `LibreChat`, `orchestrator`
- Ensures service directories contain actual implementation code
- Validates service structure follows repository guidelines

### 2. Dockerfiles
- Checks for existence of Dockerfiles for all services
- Validates Dockerfile syntax and structure
- Ensures production-ready configurations

### 3. Docker Compose
- Validates `docker-compose.yml` syntax
- Checks for proper service definitions
- Verifies network configurations
- Ensures health checks are configured

### 4. Environment Configuration
- Validates `.env` and `.env.example` files
- Checks for proper secrets management (JWT_SECRET, etc.)
- Ensures no localhost references in environment

### 5. Localhost/Mock/Placeholder Policy
- Scans all code files for policy violations
- Identifies localhost references (forbidden in production)
- Detects mock implementations that need real replacements
- Finds placeholder values that need actual implementation

### 6. Build Processes
- Validates Makefile targets exist and work
- Tests docker-compose configuration
- Ensures build tools are available

### 7. GCP Readiness
- Checks for GCP deployment scripts
- Validates Cloud Run configurations
- Ensures proper container registry setup
- Verifies GCP environment variables

## Repository Policies Enforced

### PROIBIDO LOCALHOST
- No localhost references in configuration files
- No 127.0.0.1 IP addresses in service URLs
- Use Docker service names for inter-service communication

### PROIBIDO MOCK
- No mock implementations in production code
- All services must have real implementations

### PROIBIDO PLACEHOLDER
- No placeholder values in configuration
- All secrets and API keys must be properly configured

## Expected Service Structure

Based on `AGENTS.md`, the following services are expected:

1. **fast-agent/**: Orchestrator and agents (Python with uv)
2. **codemcp/**: MCP for files/code (Python with uv)  
3. **genai-toolbox/**: MCP for databases (Go)
4. **cognee/**: Memory/knowledge graph (Python)
5. **LibreChat/**: Web UI (Node.js)
6. **orchestrator/**: Main orchestrator service (Python)

## Common Issues and Solutions

### Service Directories Empty
**Issue**: Service directories exist but are empty  
**Solution**: Implement the actual services according to `AGENTS.md` specifications

### Missing Dockerfiles
**Issue**: Services lack Dockerfiles  
**Solution**: Create production-ready Dockerfiles for each service following best practices

### Localhost References
**Issue**: Configuration contains localhost URLs  
**Solution**: Replace with Docker service names (e.g., `http://orchestrator:8000`)

### Environment Secrets
**Issue**: JWT secrets are empty or placeholder  
**Solution**: Generate secure secrets using `openssl rand -hex 32`

### GCP Configuration
**Issue**: Missing GCP deployment variables  
**Solution**: Add PROJECT, REGION, GCS_BUCKET to `.env`

## Integration with Repository Workflow

The deployment readiness agent integrates with existing repository tools:

- **Makefile**: Use `make check-deploy` for quick validation
- **CI/CD**: Include in deployment pipelines to prevent broken deployments
- **Development**: Run before commits to ensure deployment readiness

## Exit Codes

- `0`: All checks passed, repository is deployment ready
- `1`: Critical issues found, deployment blocked
- `130`: Process interrupted by user (Ctrl+C)
- Other: Unexpected errors occurred

## Output Interpretation

### ✅ Passed Checks
- Requirements are met
- No action needed

### ⚠️ Warnings
- Issues that should be fixed but don't block deployment
- Recommended improvements

### ❌ Critical Issues
- Must be fixed before deployment
- Will cause deployment failures

## Future Enhancements

- JSON output mode for programmatic processing
- Integration with specific GCP deployment tools
- Security scanning capabilities
- Performance optimization checks
- Automated fix suggestions