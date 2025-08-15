#!/bin/bash
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}🚀 Deploying AI Agent System to Google Cloud${NC}"

# Check required environment variables
required_vars=("PROJECT_ID" "REGION" "GCS_BUCKET" "LLM_API_KEY")
for var in "${required_vars[@]}"; do
    if [ -z "${!var}" ]; then
        echo -e "${RED}❌ Error: $var environment variable is not set${NC}"
        exit 1
    fi
done

# Optional variables with defaults
DOCKER_USER=${DOCKER_USER:-""}
DOCKER_PASS=${DOCKER_PASS:-""}
SQL_INSTANCE=${SQL_INSTANCE:-""}

echo -e "${YELLOW}📋 Configuration:${NC}"
echo "  Project ID: $PROJECT_ID"
echo "  Region: $REGION"
echo "  GCS Bucket: $GCS_BUCKET"
echo "  Docker User: ${DOCKER_USER:-'Not set'}"

# Authenticate with Docker Hub if credentials provided
if [ -n "$DOCKER_USER" ] && [ -n "$DOCKER_PASS" ]; then
    echo -e "${YELLOW}🔐 Authenticating with Docker Hub...${NC}"
    echo "$DOCKER_PASS" | docker login -u "$DOCKER_USER" --password-stdin
fi

# Configure gcloud
echo -e "${YELLOW}⚙️  Configuring gcloud...${NC}"
gcloud config set project "$PROJECT_ID"
gcloud config set run/region "$REGION"

# Configure Docker for GCR
echo -e "${YELLOW}🔧 Configuring Docker for Google Container Registry...${NC}"
gcloud auth configure-docker gcr.io --quiet

# Build Docker images with multi-stage optimization
echo -e "${YELLOW}🏗️  Building Docker images...${NC}"

echo "  Building orchestrator..."
docker build -t "gcr.io/$PROJECT_ID/orchestrator" -f Dockerfile.orchestrator . --no-cache

echo "  Building agent..."
docker build -t "gcr.io/$PROJECT_ID/agent" -f Dockerfile.agent . --no-cache

echo "  Building GPT-OSS..."
docker build -t "gcr.io/$PROJECT_ID/gpt-oss" -f Dockerfile.gpt-oss . --no-cache

# Push images to GCR
echo -e "${YELLOW}⬆️  Pushing images to Google Container Registry...${NC}"
docker push "gcr.io/$PROJECT_ID/orchestrator"
docker push "gcr.io/$PROJECT_ID/agent"
docker push "gcr.io/$PROJECT_ID/gpt-oss"

# Create GCS bucket if it doesn't exist
echo -e "${YELLOW}🪣 Creating GCS bucket if needed...${NC}"
if ! gsutil ls -b "gs://$GCS_BUCKET" &>/dev/null; then
    gsutil mb -l "$REGION" "gs://$GCS_BUCKET"
    echo -e "${GREEN}✅ Created GCS bucket: $GCS_BUCKET${NC}"
else
    echo -e "${GREEN}✅ GCS bucket already exists: $GCS_BUCKET${NC}"
fi

# Deploy GPT-OSS service first
echo -e "${YELLOW}🤖 Deploying GPT-OSS service...${NC}"
gcloud run deploy gpt-oss \
  --image "gcr.io/$PROJECT_ID/gpt-oss" \
  --region "$REGION" \
  --platform managed \
  --allow-unauthenticated \
  --memory 4Gi \
  --cpu 2 \
  --timeout 3600 \
  --concurrency 10 \
  --max-instances 3 \
  --port 8000

# Get GPT-OSS service URL
GPT_OSS_URL=$(gcloud run services describe gpt-oss --region="$REGION" --format="value(status.url)")
echo -e "${GREEN}✅ GPT-OSS deployed at: $GPT_OSS_URL${NC}"

# Deploy orchestrator service
echo -e "${YELLOW}🎭 Deploying orchestrator service...${NC}"
deploy_cmd="gcloud run deploy orchestrator \
  --image gcr.io/$PROJECT_ID/orchestrator \
  --region $REGION \
  --platform managed \
  --allow-unauthenticated \
  --memory 2Gi \
  --cpu 1 \
  --timeout 900 \
  --concurrency 100 \
  --max-instances 10 \
  --port 8080 \
  --set-env-vars=\"GCS_BUCKET=$GCS_BUCKET,LLM_API_KEY=$LLM_API_KEY,PROJECT_ID=$PROJECT_ID,REGION=$REGION,GPT_OSS_URL=$GPT_OSS_URL/v1/chat/completions\""

# Add SQL instance if provided
if [ -n "$SQL_INSTANCE" ]; then
    deploy_cmd="$deploy_cmd --set-cloudsql-instances=$SQL_INSTANCE"
fi

# Add Cloud Storage volume
deploy_cmd="$deploy_cmd --add-volume=name=repos,type=cloud-storage,bucket=$GCS_BUCKET --add-volume-mount=volume=repos,mount-path=/mnt/repos"

eval $deploy_cmd

# Get orchestrator service URL
ORCHESTRATOR_URL=$(gcloud run services describe orchestrator --region="$REGION" --format="value(status.url)")
echo -e "${GREEN}✅ Orchestrator deployed at: $ORCHESTRATOR_URL${NC}"

# Deploy a sample agent container (this will be managed by orchestrator)
echo -e "${YELLOW}🤖 Pre-warming agent image...${NC}"
gcloud run deploy agent-template \
  --image "gcr.io/$PROJECT_ID/agent" \
  --region "$REGION" \
  --platform managed \
  --no-allow-unauthenticated \
  --memory 1Gi \
  --cpu 1 \
  --timeout 600 \
  --concurrency 1 \
  --max-instances 5 \
  --port 8081 \
  --set-env-vars="LLM_API_KEY=$LLM_API_KEY,GPT_OSS_URL=$GPT_OSS_URL/v1/chat/completions" \
  --add-volume=name=workspace,type=cloud-storage,bucket="$GCS_BUCKET" \
  --add-volume-mount=volume=workspace,mount-path=/workspace

# Create IAM policy for orchestrator to manage containers
echo -e "${YELLOW}🔐 Setting up IAM permissions...${NC}"
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
  --member="serviceAccount:$(gcloud run services describe orchestrator --region="$REGION" --format="value(spec.template.spec.serviceAccountName)")" \
  --role="roles/run.developer" || true

gcloud projects add-iam-policy-binding "$PROJECT_ID" \
  --member="serviceAccount:$(gcloud run services describe orchestrator --region="$REGION" --format="value(spec.template.spec.serviceAccountName)")" \
  --role="roles/storage.admin" || true

# Create example environment file
echo -e "${YELLOW}📝 Creating example environment file...${NC}"
cat > .env.example << EOF
# Required Configuration
PROJECT_ID=$PROJECT_ID
REGION=$REGION
GCS_BUCKET=$GCS_BUCKET
LLM_API_KEY=your-llm-api-key-here

# Service URLs (auto-generated during deployment)
ORCHESTRATOR_URL=$ORCHESTRATOR_URL
GPT_OSS_URL=$GPT_OSS_URL

# Optional Configuration
DOCKER_USER=your-docker-username
DOCKER_PASS=your-docker-password
SQL_INSTANCE=your-cloudsql-instance

# Database Configuration
DATABASE_URL=postgresql://user:pass@host/db

# LibreChat Configuration (if using)
BACKEND_URL=$ORCHESTRATOR_URL
EOF

echo -e "${GREEN}🎉 Deployment completed successfully!${NC}"
echo -e "${YELLOW}📊 Service Summary:${NC}"
echo "  🤖 GPT-OSS Service: $GPT_OSS_URL"
echo "  🎭 Orchestrator Service: $ORCHESTRATOR_URL"
echo "  🪣 GCS Bucket: gs://$GCS_BUCKET"
echo ""
echo -e "${YELLOW}🧪 Test your deployment:${NC}"
echo "  curl -X POST $ORCHESTRATOR_URL/orchestrate \\"
echo "    -H 'Content-Type: application/json' \\"
echo "    -d '{\"query\": \"List files in current directory\", \"repo_url\": \"https://github.com/example/repo\"}'"
echo ""
echo -e "${YELLOW}📝 Configuration saved to .env.example${NC}"
echo -e "${GREEN}✨ Your AI Agent System is ready to use!${NC}"