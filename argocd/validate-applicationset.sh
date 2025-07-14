#!/bin/bash
set -e

echo "=== GPU Scheduler ApplicationSet Validation ==="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
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

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

print_info() {
    echo -e "ℹ $1"
}

# Check if kubectl is available
command -v kubectl >/dev/null 2>&1
print_status $? "kubectl command available"

# Check if cluster is accessible
kubectl cluster-info >/dev/null 2>&1
print_status $? "Kubernetes cluster accessible"

# Validate YAML files
print_info "Validating YAML syntax..."

for file in *.yaml; do
    if [ -f "$file" ]; then
        kubectl --dry-run=client apply -f "$file" >/dev/null 2>&1
        print_status $? "YAML syntax valid: $file"
    fi
done

# Check for ArgoCD CRDs
print_info "Checking ArgoCD CRDs..."

kubectl get crd applications.argoproj.io >/dev/null 2>&1
if [ $? -eq 0 ]; then
    print_status 0 "ArgoCD Application CRD exists"
else
    print_warning "ArgoCD Application CRD not found - ArgoCD may not be installed"
fi

kubectl get crd applicationsets.argoproj.io >/dev/null 2>&1
if [ $? -eq 0 ]; then
    print_status 0 "ArgoCD ApplicationSet CRD exists"
else
    print_warning "ArgoCD ApplicationSet CRD not found - ApplicationSet controller may not be installed"
fi

kubectl get crd appprojects.argoproj.io >/dev/null 2>&1
if [ $? -eq 0 ]; then
    print_status 0 "ArgoCD AppProject CRD exists"
else
    print_warning "ArgoCD AppProject CRD not found - ArgoCD may not be installed"
fi

# Check ArgoCD namespace
kubectl get namespace argocd >/dev/null 2>&1
if [ $? -eq 0 ]; then
    print_status 0 "ArgoCD namespace exists"
else
    print_warning "ArgoCD namespace not found - you may need to create it or install ArgoCD"
fi

# Validate ApplicationSet generator
print_info "Validating ApplicationSet configuration..."

# Check if required labels exist on any clusters
CLUSTERS_WITH_LABEL=$(kubectl get nodes -l environment=gpu-enabled --no-headers 2>/dev/null | wc -l)
if [ "$CLUSTERS_WITH_LABEL" -gt 0 ]; then
    print_status 0 "Found $CLUSTERS_WITH_LABEL nodes with environment=gpu-enabled label"
else
    print_warning "No nodes found with 'environment=gpu-enabled' label. ApplicationSet may not generate applications."
    print_info "To add label: kubectl label node <node-name> environment=gpu-enabled"
fi

# Check if Helm charts exist
print_info "Checking for Helm charts..."

if [ -d "../gpu-scheduler-chart" ]; then
    print_status 0 "GPU scheduler Helm chart found"
else
    print_warning "GPU scheduler Helm chart not found at ../gpu-scheduler-chart"
fi

if [ -d "../gpu-scheduler-check-chart" ]; then
    print_status 0 "GPU scheduler check Helm chart found"
else
    print_warning "GPU scheduler check Helm chart not found at ../gpu-scheduler-check-chart"
fi

# Validate Helm charts if helm is available
if command -v helm >/dev/null 2>&1; then
    print_info "Validating Helm charts..."
    
    if [ -d "../gpu-scheduler-chart" ]; then
        helm lint ../gpu-scheduler-chart >/dev/null 2>&1
        print_status $? "GPU scheduler Helm chart lint"
    fi
    
    if [ -d "../gpu-scheduler-check-chart" ]; then
        helm lint ../gpu-scheduler-check-chart >/dev/null 2>&1
        print_status $? "GPU scheduler check Helm chart lint"
    fi
else
    print_warning "Helm not found - skipping chart validation"
fi

echo ""
print_info "Validation complete!"
print_info "To deploy:"
print_info "1. Update repoURL in ApplicationSet files to your Git repository"
print_info "2. kubectl apply -f gpu-scheduler-project.yaml"
print_info "3. kubectl apply -f gpu-scheduler-complete-applicationset.yaml"
print_info "4. Monitor with: kubectl get applications -n argocd"