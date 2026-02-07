#!/bin/bash
set -e

echo "=================================="
echo "BeeAI Service Docker Setup Script"
echo "=================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if we're in the right directory
if [ ! -f "docker-compose.yml" ]; then
    echo -e "${RED}Error: docker-compose.yml not found!${NC}"
    echo "Please run this script from your beeai_service directory"
    exit 1
fi

echo -e "${YELLOW}Step 1: Checking prerequisites...${NC}"

# Check if docker is installed
if ! command -v docker &> /dev/null; then
    echo -e "${RED}Docker is not installed. Please install Docker first.${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Docker found${NC}"

# Check if docker-compose is installed
if ! command -v docker &> /dev/null; then
    echo -e "${RED}Docker Compose is not installed. Please install Docker Compose first.${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Docker Compose found${NC}"

# Check if Ollama is running
echo -e "${YELLOW}Step 2: Checking Ollama...${NC}"
if command -v ollama &> /dev/null; then
    echo -e "${GREEN}✓ Ollama CLI found${NC}"
    
    # Try to check if Ollama is running
    if curl -s http://localhost:11434/api/version > /dev/null 2>&1; then
        echo -e "${GREEN}✓ Ollama server is running${NC}"
        
        # Check if model exists
        if ollama list | grep -q "granite4:3b"; then
            echo -e "${GREEN}✓ Model granite4:3b is installed${NC}"
        else
            echo -e "${YELLOW}⚠ Model granite4:3b not found${NC}"
            echo "Run: ollama pull granite4:3b"
        fi
    else
        echo -e "${YELLOW}⚠ Ollama server not running${NC}"
        echo "Run: ollama serve"
    fi
else
    echo -e "${YELLOW}⚠ Ollama not found${NC}"
    echo "Install from: https://ollama.ai"
fi

echo ""
echo -e "${YELLOW}Step 3: Creating .env file...${NC}"
if [ ! -f ".env" ]; then
    cat > .env << 'EOF'
# BeeAI Service Configuration
BEEAI_WXO_PORT=8080
BEEAI_WXO_HOST=0.0.0.0
BEEAI_API_KEY=beeai-maintenance-key-2024
BEEAI_LLM_MODEL=ollama:granite4:3b
BEEAI_LOG_LEVEL=INFO
BEEAI_LOG_INTERMEDIATE_STEPS=false

# Ollama Configuration
OLLAMA_BASE_URL=http://host.docker.internal:11434
OLLAMA_NUM_CTX=8192
OLLAMA_TEMPERATURE=0.7
EOF
    echo -e "${GREEN}✓ Created .env file${NC}"
else
    echo -e "${YELLOW}⚠ .env file already exists, skipping${NC}"
fi

echo ""
echo -e "${YELLOW}Step 4: Cleaning up old containers...${NC}"
docker compose down -v 2>/dev/null || true
echo -e "${GREEN}✓ Cleaned up${NC}"

echo ""
echo -e "${YELLOW}Step 5: Removing old images...${NC}"
docker rmi beeai_service-beeai-service 2>/dev/null || echo "No old image to remove"

echo ""
echo -e "${YELLOW}Step 6: Building container...${NC}"
docker compose build --no-cache

echo ""
echo -e "${YELLOW}Step 7: Starting service...${NC}"
docker compose up -d

echo ""
echo -e "${YELLOW}Step 8: Waiting for service to be ready...${NC}"
sleep 5

# Check if service is running
if docker ps | grep -q beeai_maintenance_service; then
    echo -e "${GREEN}✓ Container is running${NC}"
    
    # Check health
    echo ""
    echo -e "${YELLOW}Checking health endpoint...${NC}"
    sleep 2
    
    HEALTH_CHECK=$(curl -s http://localhost:8080/health 2>/dev/null || echo "failed")
    
    if [ "$HEALTH_CHECK" != "failed" ]; then
        echo -e "${GREEN}✓ Service is healthy!${NC}"
        echo ""
        echo "Response: $HEALTH_CHECK"
    else
        echo -e "${YELLOW}⚠ Health check failed, checking logs...${NC}"
        echo ""
        docker compose logs --tail=20
    fi
else
    echo -e "${RED}✗ Container failed to start${NC}"
    echo ""
    echo "Checking logs:"
    docker compose logs --tail=30
    exit 1
fi

echo ""
echo -e "${GREEN}=================================="
echo "Setup Complete!"
echo "==================================${NC}"
echo ""
echo "Service is running at: http://localhost:8080"
echo "API Documentation: http://localhost:8080/docs"
echo ""
echo "View logs: docker compose logs -f"
echo "Stop service: docker compose down"
echo ""
echo -e "${YELLOW}Test the service with:${NC}"
echo 'curl http://localhost:8080/health'
echo ""