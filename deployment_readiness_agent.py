#!/usr/bin/env python3
"""
Deployment Readiness Agent for ai2go Repository
Validates repository deployment readiness for production Docker/GCP environment
"""

import os
import re
import sys
import yaml
import json
import argparse
import subprocess
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, field, asdict


@dataclass
class ValidationResult:
    """Result of a validation check"""
    passed: bool
    message: str
    recommendations: List[str] = field(default_factory=list)
    severity: str = "ERROR"  # ERROR, WARNING, INFO


@dataclass
class ServiceConfig:
    """Configuration for a service"""
    name: str
    directory: Path
    dockerfile_expected: bool = True
    build_command: Optional[str] = None
    test_command: Optional[str] = None


class DeploymentReadinessAgent:
    """Agent to validate deployment readiness for production"""
    
    def __init__(self, repo_root: Path, json_output: bool = False, quiet: bool = False):
        self.repo_root = repo_root
        self.json_output = json_output
        self.quiet = quiet
        self.results: List[ValidationResult] = []
        
        # Define expected services based on AGENTS.md
        self.services = [
            ServiceConfig("fast-agent", repo_root / "fast-agent", build_command="uv sync", test_command="uv run pytest -q"),
            ServiceConfig("codemcp", repo_root / "codemcp", build_command="uv sync", test_command="uv run pytest -q"),
            ServiceConfig("genai-toolbox", repo_root / "genai-toolbox", build_command="go build ./...", test_command="go test ./..."),
            ServiceConfig("cognee", repo_root / "cognee"),
            ServiceConfig("LibreChat", repo_root / "LibreChat", build_command="npm ci", test_command="npm run test:client"),
            ServiceConfig("orchestrator", repo_root / "orchestrator", dockerfile_expected=False)  # Uses Dockerfile-orchestrator.txt
        ]
    
    def log_result(self, result: ValidationResult):
        """Log a validation result"""
        self.results.append(result)
    
    def check_localhost_violations(self) -> ValidationResult:
        """Check for localhost/mock/placeholder violations per AGENTS.md policy"""
        violations = []
        
        # Files to scan for violations
        scan_patterns = ["*.py", "*.js", "*.ts", "*.go", "*.yml", "*.yaml", "*.txt", "*.env*", "*.md"]
        forbidden_patterns = [
            r"localhost",
            r"127\.0\.0\.1",
            r"mock[^a-zA-Z]",  # mock as standalone word
            r"placeholder[^a-zA-Z]",  # placeholder as standalone word
            r"TODO.*mock",
            r"TODO.*placeholder"
        ]
        
        for pattern in scan_patterns:
            for file_path in self.repo_root.rglob(pattern):
                if file_path.is_file() and not str(file_path).startswith(str(self.repo_root / ".git")):
                    try:
                        content = file_path.read_text(encoding='utf-8', errors='ignore')
                        for line_num, line in enumerate(content.splitlines(), 1):
                            for forbidden_pattern in forbidden_patterns:
                                if re.search(forbidden_pattern, line, re.IGNORECASE):
                                    # Skip known exceptions (like this file and approved configurations)
                                    if "deployment_readiness_agent.py" in str(file_path):
                                        continue
                                    if "PROIBIDO LOCALHOST" in line:  # This is the error message itself
                                        continue
                                    if "# Não use localhost" in line:  # Documentation comments
                                        continue
                                    if "sem localhost" in line.lower():  # Documentation comments
                                        continue
                                    if "localhost no upstream" in line.lower():  # Documentation comments
                                        continue
                                    # Skip validation checks themselves (these are checking for localhost, not using it)
                                    if 'if "localhost"' in line or 'if "127.0.0.1"' in line:
                                        continue
                                    if '"localhost"' in line and 'in' in line:  # Checking for localhost
                                        continue
                                    if forbidden_pattern.lower() in ["placeholder"] and any(word in line.lower() for word in ["valor", "para", "segredo", "secret"]):
                                        continue  # Documentation about placeholders
                                    violations.append(f"{file_path}:{line_num}: {line.strip()}")
                    except Exception as e:
                        # Skip files that can't be read
                        continue
        
        if violations:
            return ValidationResult(
                passed=False,
                message=f"Found {len(violations)} localhost/mock/placeholder violations",
                recommendations=[
                    "Remove all localhost references and use service names in docker-compose",
                    "Replace mock implementations with real ones",
                    "Remove placeholder values and implement actual functionality",
                    "Violations found:",
                    *violations[:10],  # Show first 10 violations
                    *(["... and more"] if len(violations) > 10 else [])
                ],
                severity="ERROR"
            )
        
        return ValidationResult(
            passed=True,
            message="No localhost/mock/placeholder violations found",
            severity="INFO"
        )
    
    def check_dockerfiles(self) -> ValidationResult:
        """Check that all services have proper Dockerfiles"""
        missing_dockerfiles = []
        invalid_dockerfiles = []
        
        # Check main docker-compose referenced Dockerfiles
        dockerfile_mappings = {
            "orchestrator": "Dockerfile-orchestrator.txt",
            "agent": "Dockerfile-agent.txt", 
            "gpt-oss": "Dockerfile-gpt-oss.txt"
        }
        
        for service, dockerfile in dockerfile_mappings.items():
            dockerfile_path = self.repo_root / dockerfile
            if not dockerfile_path.exists():
                missing_dockerfiles.append(f"{service}: {dockerfile}")
            else:
                # Validate Dockerfile content
                try:
                    content = dockerfile_path.read_text()
                    if not content.strip():
                        invalid_dockerfiles.append(f"{dockerfile}: Empty file")
                    elif "FROM" not in content:
                        invalid_dockerfiles.append(f"{dockerfile}: Missing FROM instruction")
                except Exception as e:
                    invalid_dockerfiles.append(f"{dockerfile}: Cannot read - {e}")
        
        # Check service-specific Dockerfiles
        for service in self.services:
            if service.dockerfile_expected:
                service_dockerfile = service.directory / "Dockerfile"
                if not service_dockerfile.exists():
                    missing_dockerfiles.append(f"{service.name}: {service_dockerfile}")
        
        issues = []
        if missing_dockerfiles:
            issues.extend([f"Missing Dockerfiles: {', '.join(missing_dockerfiles)}"])
        if invalid_dockerfiles:
            issues.extend([f"Invalid Dockerfiles: {', '.join(invalid_dockerfiles)}"])
        
        if issues:
            return ValidationResult(
                passed=False,
                message="Dockerfile issues found",
                recommendations=[
                    "Create missing Dockerfiles for all services",
                    "Ensure all Dockerfiles have valid FROM instructions",
                    "Use multi-stage builds for optimization",
                    "Follow security best practices (non-root user, minimal base images)",
                    *issues
                ],
                severity="ERROR"
            )
        
        return ValidationResult(
            passed=True,
            message="All required Dockerfiles present and valid",
            severity="INFO"
        )
    
    def check_docker_compose(self) -> ValidationResult:
        """Check docker-compose.yml configuration"""
        compose_file = self.repo_root / "docker-compose.yml"
        
        if not compose_file.exists():
            return ValidationResult(
                passed=False,
                message="docker-compose.yml not found",
                recommendations=[
                    "Create docker-compose.yml for orchestrating all services",
                    "Include all required services: orchestrator, librechat, genai-toolbox, cognee-service"
                ],
                severity="ERROR"
            )
        
        try:
            with open(compose_file, 'r') as f:
                compose_config = yaml.safe_load(f)
            
            issues = []
            recommendations = []
            
            # Check services are defined
            services = compose_config.get('services', {})
            expected_services = ['orchestrator', 'librechat', 'genai-toolbox', 'cognee-service']
            missing_services = [svc for svc in expected_services if svc not in services]
            
            if missing_services:
                issues.append(f"Missing services: {missing_services}")
                recommendations.append(f"Add missing services to docker-compose.yml: {missing_services}")
            
            # Check for localhost references in docker-compose
            compose_content = compose_file.read_text()
            if "localhost" in compose_content.lower():
                issues.append("docker-compose.yml contains localhost references")
                recommendations.append("Replace localhost with service names in docker-compose.yml")
            
            # Check for proper networking
            if 'networks' not in compose_config:
                issues.append("No custom networks defined")
                recommendations.append("Define custom network for service communication")
            
            # Check for health checks
            services_without_healthcheck = []
            for svc_name, svc_config in services.items():
                if 'healthcheck' not in svc_config:
                    services_without_healthcheck.append(svc_name)
            
            if services_without_healthcheck:
                issues.append(f"Services without healthchecks: {services_without_healthcheck}")
                recommendations.append("Add healthcheck configuration to all services")
            
            if issues:
                return ValidationResult(
                    passed=False,
                    message=f"docker-compose.yml has {len(issues)} issues",
                    recommendations=recommendations + issues,
                    severity="WARNING"
                )
                
        except yaml.YAMLError as e:
            return ValidationResult(
                passed=False,
                message=f"docker-compose.yml is invalid YAML: {e}",
                recommendations=["Fix YAML syntax errors in docker-compose.yml"],
                severity="ERROR"
            )
        except Exception as e:
            return ValidationResult(
                passed=False,
                message=f"Cannot read docker-compose.yml: {e}",
                recommendations=["Ensure docker-compose.yml is readable"],
                severity="ERROR"
            )
        
        return ValidationResult(
            passed=True,
            message="docker-compose.yml is valid and well-configured",
            severity="INFO"
        )
    
    def check_environment_config(self) -> ValidationResult:
        """Check environment configuration"""
        env_example = self.repo_root / ".env.example"
        env_file = self.repo_root / ".env"
        
        issues = []
        recommendations = []
        
        if not env_example.exists():
            issues.append(".env.example not found")
            recommendations.append("Create .env.example with all required environment variables")
        
        if not env_file.exists():
            issues.append(".env not found")
            recommendations.append("Copy .env.example to .env and configure values")
        else:
            # Check for placeholder secrets
            try:
                env_content = env_file.read_text()
                if 'JWT_SECRET=""' in env_content:
                    issues.append("JWT_SECRET is empty")
                    recommendations.append("Generate secure JWT_SECRET using: openssl rand -hex 32")
                
                if 'JWT_REFRESH_SECRET=""' in env_content:
                    issues.append("JWT_REFRESH_SECRET is empty") 
                    recommendations.append("Generate secure JWT_REFRESH_SECRET using: openssl rand -hex 32")
                
                # Check for localhost in environment
                if "localhost" in env_content.lower():
                    issues.append(".env contains localhost references")
                    recommendations.append("Replace localhost with proper service URLs in .env")
                    
            except Exception as e:
                issues.append(f"Cannot read .env: {e}")
        
        if issues:
            return ValidationResult(
                passed=False,
                message=f"Environment configuration has {len(issues)} issues",
                recommendations=recommendations + issues,
                severity="ERROR"
            )
        
        return ValidationResult(
            passed=True,
            message="Environment configuration is properly set up",
            severity="INFO"
        )
    
    def check_service_structure(self) -> ValidationResult:
        """Check that all expected services have proper structure"""
        missing_services = []
        empty_services = []
        recommendations = []
        
        for service in self.services:
            if not service.directory.exists():
                missing_services.append(service.name)
            elif not any(service.directory.iterdir()):
                empty_services.append(service.name)
        
        if missing_services:
            recommendations.append(f"Create missing service directories: {missing_services}")
        
        if empty_services:
            recommendations.append(f"Implement missing services (currently empty): {empty_services}")
            recommendations.append("Each service should have its source code, Dockerfile, and configuration")
        
        issues = []
        if missing_services:
            issues.append(f"Missing service directories: {missing_services}")
        if empty_services:
            issues.append(f"Empty service directories: {empty_services}")
        
        if issues:
            return ValidationResult(
                passed=False,
                message="Service structure is incomplete",
                recommendations=recommendations + [
                    "Refer to AGENTS.md for expected service structure",
                    "Each service should be a complete, deployable microservice"
                ] + issues,
                severity="ERROR"
            )
        
        return ValidationResult(
            passed=True,
            message="All services have proper directory structure",
            severity="INFO"
        )
    
    def check_gcp_readiness(self) -> ValidationResult:
        """Check GCP deployment readiness"""
        issues = []
        recommendations = []
        
        # Check for GCP-specific configurations
        deploy_script = self.repo_root / "deploy.txt"
        if not deploy_script.exists():
            issues.append("No deploy.txt script found")
            recommendations.append("Create deploy.txt script for GCP deployment")
        else:
            try:
                deploy_content = deploy_script.read_text()
                
                # Check for GCP Cloud Run deployment
                if "gcloud run deploy" not in deploy_content:
                    issues.append("deploy.txt missing Cloud Run deployment commands")
                    recommendations.append("Add gcloud run deploy commands to deploy.txt")
                
                # Check for GCR push
                if "gcr.io" not in deploy_content and "docker push" not in deploy_content:
                    issues.append("deploy.txt missing container registry push")
                    recommendations.append("Add container registry push commands to deploy.txt")
                    
            except Exception as e:
                issues.append(f"Cannot read deploy.txt: {e}")
        
        # Check for proper ports (not localhost bound)
        compose_file = self.repo_root / "docker-compose.yml"
        if compose_file.exists():
            try:
                compose_content = compose_file.read_text()
                # Look for hardcoded localhost bindings
                if "127.0.0.1:" in compose_content:
                    issues.append("docker-compose.yml has localhost port bindings")
                    recommendations.append("Remove localhost IP bindings in docker-compose.yml")
            except Exception:
                pass
        
        # Check environment for GCP configurations
        env_file = self.repo_root / ".env"
        if env_file.exists():
            try:
                env_content = env_file.read_text()
                gcp_vars = ["PROJECT", "REGION", "GCS_BUCKET"]
                missing_gcp_vars = [var for var in gcp_vars 
                                   if f"{var}=" not in env_content and f"{var}_" not in env_content]
                
                if missing_gcp_vars:
                    issues.append(f"Missing GCP environment variables: {missing_gcp_vars}")
                    recommendations.append("Add GCP project configuration variables to .env")
                    
            except Exception:
                pass
        
        if issues:
            return ValidationResult(
                passed=False,
                message=f"GCP deployment readiness has {len(issues)} issues",
                recommendations=recommendations + [
                    "Ensure all services can run in GCP Cloud Run",
                    "Configure proper GCR/Artifact Registry for container images",
                    "Set up Cloud SQL for database if needed",
                    "Configure proper IAM permissions for deployment"
                ] + issues,
                severity="WARNING"
            )
        
        return ValidationResult(
            passed=True,
            message="GCP deployment configuration appears ready",
            severity="INFO"
        )
    
    def check_build_processes(self) -> ValidationResult:
        """Check that build processes are working"""
        issues = []
        recommendations = []
        
        # Check Makefile targets
        makefile = self.repo_root / "Makefile"
        if not makefile.exists():
            issues.append("Makefile not found")
            recommendations.append("Create Makefile with build, test, and deployment targets")
        else:
            try:
                makefile_content = makefile.read_text()
                expected_targets = ["bootstrap", "deps", "up", "test", "lint"]
                missing_targets = [target for target in expected_targets 
                                 if f"{target}:" not in makefile_content]
                
                if missing_targets:
                    issues.append(f"Makefile missing targets: {missing_targets}")
                    recommendations.append(f"Add missing Makefile targets: {missing_targets}")
                    
            except Exception as e:
                issues.append(f"Cannot read Makefile: {e}")
        
        # Try to validate docker-compose
        try:
            result = subprocess.run(
                ["docker", "compose", "config", "--quiet"],
                cwd=self.repo_root,
                capture_output=True,
                text=True,
                timeout=30
            )
            if result.returncode != 0:
                issues.append("docker-compose config validation failed")
                recommendations.append("Fix docker-compose.yml configuration errors")
        except subprocess.TimeoutExpired:
            issues.append("docker-compose config validation timed out")
        except FileNotFoundError:
            issues.append("docker or docker-compose not available")
            recommendations.append("Ensure Docker and Docker Compose are installed")
        except Exception as e:
            issues.append(f"Could not validate docker-compose: {e}")
        
        if issues:
            return ValidationResult(
                passed=False,
                message=f"Build process validation has {len(issues)} issues",
                recommendations=recommendations + issues,
                severity="WARNING"
            )
        
        return ValidationResult(
            passed=True,
            message="Build processes are properly configured",
            severity="INFO"
        )
    
    def run_all_checks(self) -> None:
        """Run all deployment readiness checks"""
        if not self.quiet:
            print("🚀 Running Deployment Readiness Validation for ai2go Repository")
            print("=" * 70)
        
        checks = [
            ("Service Structure", self.check_service_structure),
            ("Dockerfiles", self.check_dockerfiles),
            ("Docker Compose", self.check_docker_compose),
            ("Environment Config", self.check_environment_config),
            ("Localhost/Mock/Placeholder Policy", self.check_localhost_violations),
            ("Build Processes", self.check_build_processes),
            ("GCP Readiness", self.check_gcp_readiness)
        ]
        
        for check_name, check_func in checks:
            if not self.quiet:
                print(f"\n🔍 Checking {check_name}...")
            result = check_func()
            self.log_result(result)
            
            if not self.quiet:
                status_icon = "✅" if result.passed else ("⚠️" if result.severity == "WARNING" else "❌")
                print(f"{status_icon} {result.message}")
                
                if result.recommendations:
                    print("📋 Recommendations:")
                    for rec in result.recommendations:
                        print(f"   • {rec}")
    
    def generate_report(self) -> Dict:
        """Generate final deployment readiness report"""
        passed_checks = sum(1 for r in self.results if r.passed)
        total_checks = len(self.results)
        error_count = sum(1 for r in self.results if not r.passed and r.severity == "ERROR")
        warning_count = sum(1 for r in self.results if not r.passed and r.severity == "WARNING")
        
        deployment_ready = error_count == 0
        
        report = {
            "deployment_ready": deployment_ready,
            "passed_checks": passed_checks,
            "total_checks": total_checks,
            "error_count": error_count,
            "warning_count": warning_count,
            "results": [asdict(result) for result in self.results]
        }
        
        if self.json_output:
            print(json.dumps(report, indent=2))
            return report
        
        if not self.quiet:
            print("\n" + "=" * 70)
            print("📊 DEPLOYMENT READINESS SUMMARY")
            print("=" * 70)
            print(f"✅ Passed checks: {passed_checks}/{total_checks}")
            print(f"❌ Critical issues (ERRORS): {error_count}")
            print(f"⚠️ Warnings: {warning_count}")
            print()
            
            if deployment_ready:
                print("🎉 REPOSITORY IS DEPLOYMENT READY!")
                print("✨ All critical requirements are met for production deployment.")
            else:
                print("🚫 REPOSITORY IS NOT DEPLOYMENT READY")
                print("🔧 Critical issues must be resolved before production deployment:")
                
                for result in self.results:
                    if not result.passed and result.severity == "ERROR":
                        print(f"   ❌ {result.message}")
                        for rec in result.recommendations[:3]:  # Show top 3 recommendations
                            print(f"      • {rec}")
            
            if warning_count > 0:
                print("\n⚠️ Warnings (recommended to fix):")
                for result in self.results:
                    if not result.passed and result.severity == "WARNING":
                        print(f"   ⚠️ {result.message}")
            
            print("\n" + "=" * 70)
        
        return report


def main():
    """Main function to run deployment readiness checks"""
    parser = argparse.ArgumentParser(
        description="Deployment Readiness Agent for ai2go Repository",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 deployment_readiness_agent.py              # Run with normal output
  python3 deployment_readiness_agent.py --json       # JSON output for CI/CD
  python3 deployment_readiness_agent.py --quiet      # Minimal output
  make check-deploy                                   # Via Makefile
        """
    )
    parser.add_argument(
        "--json", 
        action="store_true", 
        help="Output results in JSON format for CI/CD integration"
    )
    parser.add_argument(
        "--quiet", 
        action="store_true", 
        help="Suppress progress output, only show final result"
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path(__file__).parent,
        help="Path to repository root (default: script directory)"
    )
    
    args = parser.parse_args()
    
    agent = DeploymentReadinessAgent(
        repo_root=args.repo_root,
        json_output=args.json,
        quiet=args.quiet
    )
    
    try:
        agent.run_all_checks()
        report = agent.generate_report()
        
        # Exit with error code if not deployment ready
        sys.exit(0 if report["deployment_ready"] else 1)
        
    except KeyboardInterrupt:
        if not args.quiet:
            print("\n\n🛑 Deployment readiness check interrupted by user")
        sys.exit(130)
    except Exception as e:
        if not args.quiet:
            print(f"\n\n💥 Unexpected error during deployment readiness check: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()