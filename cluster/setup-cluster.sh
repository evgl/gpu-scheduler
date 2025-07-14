#!/bin/bash
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print status
print_status() {
    if [ $1 -eq 0 ]; then
        echo -e "${GREEN}✓${NC} $2"
    else
        echo -e "${RED}✗${NC} $2"
        exit 1
    fi
}

print_info() {
    echo -e "${BLUE}ℹ${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

echo "=== GPU Scheduler Cluster Setup ==="

# Check prerequisites
print_info "Checking prerequisites..."

command -v kind >/dev/null 2>&1
print_status $? "KinD is installed"

command -v kubectl >/dev/null 2>&1
print_status $? "kubectl is installed"

command -v docker >/dev/null 2>&1
print_status $? "Docker is available"

# Check if Docker is running
docker info >/dev/null 2>&1
print_status $? "Docker is running"

# Create KinD cluster
print_info "Creating KinD cluster with GPU scheduler configuration..."

if kind get clusters | grep -q "gpu-scheduler-cluster"; then
    print_warning "Cluster 'gpu-scheduler-cluster' already exists. Deleting..."
    kind delete cluster --name gpu-scheduler-cluster
fi

kind create cluster --config kind-config.yaml
print_status $? "KinD cluster created"

# Wait for cluster to be ready
print_info "Waiting for cluster to be ready..."
kubectl wait --for=condition=Ready nodes --all --timeout=300s
print_status $? "All nodes are ready"

# Label nodes with correct names
print_info "Configuring node labels and names..."

# Get worker nodes and label them correctly
WORKER_NODES=($(kubectl get nodes --no-headers | grep -v control-plane | awk '{print $1}' | head -4))

for i in "${!WORKER_NODES[@]}"; do
    NODE_NAME="${WORKER_NODES[$i]}"
    TARGET_NAME="node$((i+1))"
    
    # Add node name label
    kubectl label node "$NODE_NAME" "gpu-node-name=$TARGET_NAME" --overwrite
    print_status $? "Labeled $NODE_NAME as $TARGET_NAME"
done

# Verify cluster setup
print_info "Verifying cluster configuration..."

# Check nodes
NODE_COUNT=$(kubectl get nodes --no-headers | wc -l)
if [ "$NODE_COUNT" -eq 5 ]; then
    print_status 0 "Cluster has 5 nodes (1 master + 4 workers)"
else
    print_status 1 "Expected 5 nodes, found $NODE_COUNT"
fi

# Check labels
LABELED_NODES=$(kubectl get nodes -l environment=gpu-enabled --no-headers | wc -l)
if [ "$LABELED_NODES" -eq 5 ]; then
    print_status 0 "All nodes have environment=gpu-enabled label"
else
    print_status 1 "Expected 5 labeled nodes, found $LABELED_NODES"
fi

# Display cluster info
print_info "Cluster Information:"
kubectl cluster-info
echo ""

print_info "Node Details:"
kubectl get nodes -o wide --show-labels
echo ""

print_info "Node Labels for GPU Scheduling:"
for i in {1..4}; do
    NODE_WITH_LABEL=$(kubectl get nodes -l "gpu-node-name=node$i" --no-headers -o custom-columns=NAME:.metadata.name | head -1)
    if [ -n "$NODE_WITH_LABEL" ]; then
        echo "  node$i -> $NODE_WITH_LABEL"
    fi
done

echo ""
print_info "Cluster setup complete! ✓"
print_info "Use 'kubectl get nodes' to view the cluster"
print_info "Use 'kind delete cluster --name gpu-scheduler-cluster' to clean up"