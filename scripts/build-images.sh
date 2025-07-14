#!/bin/bash
set -e

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}Building GPU Scheduler Docker Images${NC}"

# Get version
VERSION=$(cat VERSION)
echo "Building version: $VERSION"

# Build GPU Scheduler image
echo -e "${GREEN}Building GPU Scheduler image...${NC}"
cd gpu-scheduler
docker build -t gpu-scheduler:latest .
docker build -t gpu-scheduler:$VERSION .
cd ..

# Build GPU Scheduler Check image  
echo -e "${GREEN}Building GPU Scheduler Check image...${NC}"
cd gpu-scheduler-check
docker build -t gpu-scheduler-check:latest .
docker build -t gpu-scheduler-check:$VERSION .
cd ..

echo -e "${GREEN}✓ All images built successfully${NC}"

# List built images
echo -e "${BLUE}Built images:${NC}"
docker images | grep -E "(gpu-scheduler|gpu-scheduler-check)"