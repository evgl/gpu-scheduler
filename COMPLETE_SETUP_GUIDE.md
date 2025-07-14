# GPU Scheduler - Complete Setup Guide

This comprehensive guide will take you from zero to a fully working GPU scheduler system with automatic CUDA_VISIBLE_DEVICES injection. Follow these steps to see the complete solution in action.

## 📋 Table of Contents

1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Step 1: Local Cluster Setup](#step-1-local-cluster-setup)
4. [Step 2: Build Container Images](#step-2-build-container-images)
5. [Step 3: Deploy GPU Scheduler with Webhook](#step-3-deploy-gpu-scheduler-with-webhook)
6. [Step 4: Deploy Test Service and Verify GPU Scheduling](#step-4-deploy-test-service-and-verify-gpu-scheduling)
7. [Step 5: Generate Required Task Outputs](#step-5-generate-required-task-outputs)
8. [Step 6: ArgoCD Deployment](#step-6-argocd-deployment)
9. [Troubleshooting](#troubleshooting)

## Overview

**What You'll Build:**
- Custom Kubernetes scheduler that places pods on specific nodes
- Mutating admission webhook that automatically injects CUDA_VISIBLE_DEVICES
- Complete test environment to validate GPU scheduling

**Expected Results:**
- Pods automatically scheduled to designated nodes
- CUDA_VISIBLE_DEVICES environment variable set based on annotations
- Working GPU scheduling system ready for production

**Image Registry:**
This guide uses GitLab Container Registry (`registry.gitlab.com/evgenii19/gpu-scheduler/`) for container images. For local development, you can build images locally and load them into KinD (see Step 2).

## Prerequisites

### Required Software
```bash
# Check if you have these installed
docker --version          # Docker 20.10+
kubectl version --client  # kubectl 1.19+
helm version              # Helm 3.x
kind version              # KinD 0.11+

# Install missing tools if needed:
# Docker: https://docs.docker.com/get-docker/
# kubectl: https://kubernetes.io/docs/tasks/tools/
# Helm: https://helm.sh/docs/intro/install/
# KinD: https://kind.sigs.k8s.io/docs/user/quick-start/#installation
```

### Repository Setup
```bash
# Clone or navigate to the repository
cd /path/to/gpu-scheduler-project

# Verify repository structure
ls -la
# Should see: gpu-scheduler/, charts/, cluster/, docs/, etc.
```

## Step 1: Local Cluster Setup

### 1.1 Create KinD Cluster
```bash
# Navigate to cluster directory
cd cluster

# Create 5-node cluster (1 control-plane + 4 workers)
kind create cluster --config kind-config.yaml --name gpu-scheduler-cluster

# Verify cluster is running
kubectl cluster-info --context kind-gpu-scheduler-cluster
```

### 1.2 Configure Node Labels
```bash
# Label worker nodes with logical GPU node names
kubectl label node gpu-scheduler-cluster-worker gpu-node-name=node1
kubectl label node gpu-scheduler-cluster-worker2 gpu-node-name=node2
kubectl label node gpu-scheduler-cluster-worker3 gpu-node-name=node3
kubectl label node gpu-scheduler-cluster-worker4 gpu-node-name=node4

# Verify labels
kubectl get nodes --show-labels | grep gpu-node-name
```

### 1.3 Create Namespaces
```bash
# Create required namespaces
kubectl create namespace gpu-scheduler-system
kubectl create namespace gpu-scheduler-tests

# Verify namespaces
kubectl get namespaces | grep gpu-scheduler
```

## Step 2: Build Container Images

**Note**: For production deployment, images are built via GitLab CI and stored in the GitLab Container Registry at `registry.gitlab.com/evgenii19/gpu-scheduler/`. The steps below are for local development only.

### 2.1 Build GPU Scheduler Image
```bash
# Navigate to gpu-scheduler directory
cd ../gpu-scheduler

# Build the image
docker build -t gpu-scheduler:latest .

# Verify image built successfully
docker images | grep gpu-scheduler
```

### 2.2 Build Test Service Image
```bash
# Navigate to test service directory
cd ../gpu-scheduler-check

# Build the test image
docker build -t gpu-scheduler-check:latest .

# Verify image built successfully
docker images | grep gpu-scheduler-check
```

### 2.3 Load Images into KinD Cluster

**Note**: This step is **only required for local KinD development**. When using GitLab CI-built images, Kubernetes will automatically pull images from the GitLab Container Registry.

```bash
# Load images into KinD cluster (LOCAL DEVELOPMENT ONLY)
kind load docker-image gpu-scheduler:latest --name gpu-scheduler-cluster
kind load docker-image gpu-scheduler-check:latest --name gpu-scheduler-cluster

# Verify images are available in cluster
docker exec -it gpu-scheduler-cluster-control-plane crictl images | grep gpu-scheduler
```

**✅ Expected Result:**
```
gpu-scheduler        latest    abc123def456    2 minutes ago    300MB
gpu-scheduler-check  latest    def456abc123    1 minute ago     250MB
```

**For Production with GitLab CI + ArgoCD:**
- Images are automatically built and pushed to: `registry.gitlab.com/evgenii19/gpu-scheduler/`
- ArgoCD pulls images automatically from the registry
- No manual loading required

## Step 3: Deploy GPU Scheduler with Webhook

### 3.1 Generate TLS Certificates
```bash
# Navigate to scheduler directory
cd ../gpu-scheduler

# Generate TLS certificates for webhook
./generate-webhook-certs.sh

# Create TLS secret in Kubernetes
kubectl apply -f certs/webhook-tls-secret.yaml

# Verify secret was created
kubectl get secret gpu-scheduler-webhook-tls -n gpu-scheduler-system
```

### 3.2 Get CA Bundle for Webhook Configuration
```bash
# Extract CA bundle for webhook configuration
CA_BUNDLE=$(cat certs/ca.crt | base64 -w 0)
echo "CA Bundle length: ${#CA_BUNDLE} characters"
```

### 3.3 Deploy Scheduler with Webhook (Robust Bootstrap)
```bash
# Navigate to Helm chart directory
cd ../charts/gpu-scheduler

# Deploy scheduler with webhook enabled
helm install gpu-scheduler . \
  --namespace gpu-scheduler-system \
  --set webhook.enabled=true \
  --set webhook.caBundle="$CA_BUNDLE" \
  --set image.repository=registry.gitlab.com/evgenii19/gpu-scheduler/gpu-scheduler \
  --set image.tag=latest \
  --set image.pullPolicy=Always

# Check deployment status after 30 seconds
sleep 30
kubectl get deployment gpu-scheduler -n gpu-scheduler-system

# If deployment shows 0/1 READY, apply the chicken-and-egg fix:
echo 'Checking for chicken-and-egg problem...'
READY=$(kubectl get deployment gpu-scheduler -n gpu-scheduler-system -o jsonpath='{.status.readyReplicas}')
if [ "$READY" != "1" ]; then
  echo 'Applying chicken-and-egg fix...'
  
  # Temporarily remove webhook configuration
  kubectl delete mutatingwebhookconfiguration gpu-scheduler-webhook 2>/dev/null || true
  
  # Restart deployment to allow pods to start
  kubectl rollout restart deployment/gpu-scheduler -n gpu-scheduler-system
  
  # Wait for pods to be ready
  kubectl wait --for=condition=available deployment/gpu-scheduler \
    --namespace gpu-scheduler-system --timeout=120s
  
  # Re-enable webhook configuration
  helm upgrade gpu-scheduler . \
    --namespace gpu-scheduler-system \
    --set webhook.enabled=true \
    --set webhook.caBundle="$CA_BUNDLE" \
    --set image.repository=registry.gitlab.com/evgenii19/gpu-scheduler/gpu-scheduler \
    --set image.tag=latest \
    --set image.pullPolicy=Always
  
  echo 'Fix applied successfully!'
else
  echo 'Deployment successful on first try!'
fi
```

### 3.4 Verify Scheduler and Webhook Deployment
```bash
# Check scheduler pod has 2/2 containers (scheduler + webhook)
kubectl get pods -n gpu-scheduler-system

# Verify webhook configuration exists
kubectl get mutatingwebhookconfiguration gpu-scheduler-webhook

# Check scheduler logs
kubectl logs -l app.kubernetes.io/name=gpu-scheduler -n gpu-scheduler-system -c scheduler

# Check webhook logs
kubectl logs -l app.kubernetes.io/name=gpu-scheduler -n gpu-scheduler-system -c webhook

# Verify health endpoint
kubectl port-forward svc/gpu-scheduler 8080:8080 -n gpu-scheduler-system &
curl http://localhost:8080/health
# Should return: {"service":"gpu-scheduler","status":"healthy"}
```

**✅ Expected Result:**
```
NAME                             READY   STATUS    RESTARTS   AGE
gpu-scheduler-xxxxx-xxxxx        2/2     Running   0          60s

NAME                    WEBHOOKS   AGE
gpu-scheduler-webhook   1          60s
```

**🔧 Note**: The robust bootstrap approach above automatically detects and fixes the chicken-and-egg problem where the webhook configuration tries to call the webhook service before it's ready. This race condition occurs frequently enough that automatic detection and fixing is necessary for reliable deployment.

## Step 4: Deploy Test Service and Verify GPU Scheduling

### 4.1 Deploy GPU Scheduler Check Test Service
```bash
# Deploy the test service using Helm chart
helm install gpu-test charts/gpu-scheduler-check \
  --namespace gpu-scheduler-tests \
  --create-namespace \
  --set image.repository=registry.gitlab.com/evgenii19/gpu-scheduler/gpu-scheduler-check \
  --set image.tag=latest \
  --set image.pullPolicy=Always
```

### 4.2 Wait for Test Pods to be Ready
```bash
# Wait for all test pods to be ready
kubectl wait --for=condition=ready pod -l "app.kubernetes.io/name=gpu-scheduler-check" \
  -n gpu-scheduler-tests --timeout=120s

# Check pod placement across nodes
kubectl get pods -l "app.kubernetes.io/name=gpu-scheduler-check" \
  -n gpu-scheduler-tests -o wide
```

### 4.3 Verify GPU Scheduling Results
```bash
# Check the logs to verify CUDA_VISIBLE_DEVICES was set correctly
kubectl logs -l "app.kubernetes.io/name=gpu-scheduler-check" \
  -n gpu-scheduler-tests --tail=10

# For the first pod on node4 (pod 3)
kubectl logs gpu-test-service-gpu-scheduler-check-3 -n gpu-scheduler-tests

# For the second pod on node4 (pod 4)  
kubectl logs gpu-test-service-gpu-scheduler-check-4 -n gpu-scheduler-tests
```

**✅ Expected Log Results:**
```
Node: gpu-scheduler-cluster-worker, CUDA_VISIBLE_DEVICES: 0,1    (Pod 0 on node1)
Node: gpu-scheduler-cluster-worker2, CUDA_VISIBLE_DEVICES: 2     (Pod 1 on node2)
Node: gpu-scheduler-cluster-worker3, CUDA_VISIBLE_DEVICES: 0,1,2 (Pod 2 on node3)
Node: gpu-scheduler-cluster-worker4, CUDA_VISIBLE_DEVICES: 3     (Pod 3 on node4)
Node: gpu-scheduler-cluster-worker4, CUDA_VISIBLE_DEVICES: 3     (Pod 4 on node4)
```

## Step 5: Generate Required Task Outputs

### 5.1 Generate kubectl get pod -o wide -A Output
```bash
# Create outputs directory if it doesn't exist
mkdir -p outputs

# Generate the required kubectl output
kubectl get pod -o wide -A > outputs/kubectl-get-pods-wide.txt

# Verify the file was created
cat outputs/kubectl-get-pods-wide.txt
```

## Step 6: ArgoCD Deployment

### 6.1 Install ArgoCD
```bash
# Create ArgoCD namespace
kubectl create namespace argocd

# Install ArgoCD
kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml

# Wait for ArgoCD to be ready
kubectl wait --for=condition=ready pod -l app.kubernetes.io/name=argocd-server -n argocd --timeout=300s

# Get initial admin password
ARGOCD_PASSWORD=$(kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath="{.data.password}" | base64 -d)
echo "ArgoCD admin password: $ARGOCD_PASSWORD"
```

### 6.2 Install ArgoCD CLI (Optional)
```bash
# Install ArgoCD CLI for better management
curl -sSL -o argocd-linux-amd64 https://github.com/argoproj/argo-cd/releases/latest/download/argocd-linux-amd64
sudo install -m 555 argocd-linux-amd64 /usr/local/bin/argocd
rm argocd-linux-amd64

# Login to ArgoCD (use password from step 6.1)
kubectl port-forward svc/argocd-server -n argocd 8080:443 &
argocd login localhost:8080 --username admin --password $ARGOCD_PASSWORD --insecure
```

### 6.3 Deploy ArgoCD Project
```bash
# Apply the ArgoCD project configuration
kubectl apply -f argocd/gpu-scheduler-project.yaml

# Verify project was created
kubectl get appproject gpu-scheduler -n argocd
```

### 6.4 Register Local Cluster
```bash
# This step is ESSENTIAL for ApplicationSets to work!
# Without this, ApplicationSets will generate 0 applications
kubectl apply -f argocd/local-cluster-secret.yaml

# Verify cluster secret was created
kubectl get secret local-cluster -n argocd
```

### 6.5 Deploy ApplicationSet
```bash
# Deploy the complete ApplicationSet
kubectl apply -f argocd/gpu-scheduler-complete-applicationset.yaml

# Verify ApplicationSet was created
kubectl get applicationset gpu-scheduler-complete -n argocd

# Wait for applications to be generated (may take 30-60 seconds)
sleep 60
kubectl get applications -n argocd
```

### 6.6 Verify GitOps Deployment
```bash
# Check applications status
kubectl get applications -n argocd

# View detailed application status (if ArgoCD CLI is installed)
argocd app list 2>/dev/null || echo "Use kubectl for status check"

# Check that ArgoCD deployed the same pods we had before
kubectl get pods -n gpu-scheduler-system
kubectl get pods -n gpu-scheduler-tests -o wide

# Verify GPU scheduling is still working
kubectl logs -l "app.kubernetes.io/name=gpu-scheduler-check" -n gpu-scheduler-tests --tail=5
```