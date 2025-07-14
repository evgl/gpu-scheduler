# GPU Scheduler - Complete Setup Guide

This comprehensive guide will take you from zero to a fully working GPU scheduler system with automatic CUDA_VISIBLE_DEVICES injection. Follow these steps to see the complete solution in action.

## 📋 Table of Contents

1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Step 1: Local Cluster Setup](#step-1-local-cluster-setup)
4. [Step 2: Build Container Images](#step-2-build-container-images)
5. [Step 3: Deploy GPU Scheduler with Webhook](#step-3-deploy-gpu-scheduler-with-webhook)
6. [Step 4: Test Complete Solution](#step-4-test-complete-solution)
7. [Step 5: Verify End-to-End Results](#step-5-verify-end-to-end-results)
8. [Step 6: ArgoCD Deployment (Optional)](#step-6-argocd-deployment-optional)
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

### 3.3 Deploy Scheduler with Webhook
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

# Wait for deployment to be ready
kubectl wait --for=condition=available deployment/gpu-scheduler \
  --namespace gpu-scheduler-system --timeout=60s
```

### 3.4 Verify Scheduler and Webhook Deployment
```bash
# Check scheduler pod now has 2/2 containers (scheduler + webhook)
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

## Step 4: Test Complete Solution

### 4.1 Create Test Pod with Webhook
```bash
# Create a test pod to verify webhook functionality
cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: Pod
metadata:
  name: webhook-test-0
  namespace: gpu-scheduler-tests
  annotations:
    gpu-scheduling-map: "0=node1:0,1"
spec:
  schedulerName: gpu-scheduler
  containers:
  - name: test
    image: busybox
    command: ["sh", "-c", "echo 'CUDA_VISIBLE_DEVICES='$CUDA_VISIBLE_DEVICES; sleep 300"]
EOF
```

### 4.2 Verify Pod Placement and Environment
```bash
# Check pod was scheduled to correct node
kubectl get pod webhook-test-0 -n gpu-scheduler-tests -o wide
# Should be on gpu-scheduler-cluster-worker (node1)

# Check environment variable was injected
kubectl logs webhook-test-0 -n gpu-scheduler-tests
# Should show: CUDA_VISIBLE_DEVICES=0,1
```

### 4.3 Test Multiple Pods
```bash
# Create additional test pods
cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: Pod
metadata:
  name: webhook-test-1
  namespace: gpu-scheduler-tests
  annotations:
    gpu-scheduling-map: |
      0=node1:0,1
      1=node2:2
      2=node3:0,1,2
spec:
  schedulerName: gpu-scheduler
  containers:
  - name: test
    image: busybox
    command: ["sh", "-c", "echo 'Pod 1: CUDA_VISIBLE_DEVICES='$CUDA_VISIBLE_DEVICES; sleep 300"]
---
apiVersion: v1
kind: Pod
metadata:
  name: webhook-test-2
  namespace: gpu-scheduler-tests
  annotations:
    gpu-scheduling-map: |
      0=node1:0,1
      1=node2:2
      2=node3:0,1,2
spec:
  schedulerName: gpu-scheduler
  containers:
  - name: test
    image: busybox
    command: ["sh", "-c", "echo 'Pod 2: CUDA_VISIBLE_DEVICES='$CUDA_VISIBLE_DEVICES; sleep 300"]
EOF
```

### 4.4 Check Webhook Processing
```bash
# View webhook logs to see processing
kubectl logs -l app.kubernetes.io/name=gpu-scheduler -n gpu-scheduler-system -c webhook --tail=10
```

**✅ Expected Webhook Logs:**
```
2025-07-11 01:19:26,486 - root - INFO - Injecting CUDA_VISIBLE_DEVICES=0,1 for pod webhook-test-0 (index 0)
2025-07-11 01:19:26,486 - root - INFO - Injecting CUDA_VISIBLE_DEVICES=2 for pod webhook-test-1 (index 1)
2025-07-11 01:19:26,502 - root - INFO - Injecting CUDA_VISIBLE_DEVICES=0,1,2 for pod webhook-test-2 (index 2)
```

## Step 5: Verify End-to-End Results

### 5.1 Check Complete Pod Status
```bash
# Get comprehensive pod status
kubectl get pods -n gpu-scheduler-tests -o wide

# Check all test pod logs
kubectl logs webhook-test-0 -n gpu-scheduler-tests
kubectl logs webhook-test-1 -n gpu-scheduler-tests  
kubectl logs webhook-test-2 -n gpu-scheduler-tests
```

### 5.2 Validate Environment Variables
```bash
# Verify environment variables are set correctly
kubectl exec webhook-test-0 -n gpu-scheduler-tests -- env | grep CUDA
kubectl exec webhook-test-1 -n gpu-scheduler-tests -- env | grep CUDA
kubectl exec webhook-test-2 -n gpu-scheduler-tests -- env | grep CUDA
```

### 5.3 Generate Final Validation Report
```bash
# Create comprehensive status report
echo "=== GPU Scheduler Validation Report ===" > validation-results.txt
echo "Date: $(date)" >> validation-results.txt
echo "" >> validation-results.txt

echo "=== Cluster Status ===" >> validation-results.txt
kubectl get nodes >> validation-results.txt
echo "" >> validation-results.txt

echo "=== Scheduler Status ===" >> validation-results.txt
kubectl get pods -n gpu-scheduler-system >> validation-results.txt
echo "" >> validation-results.txt

echo "=== Test Pods Status ===" >> validation-results.txt
kubectl get pods -n gpu-scheduler-tests -o wide >> validation-results.txt
echo "" >> validation-results.txt

echo "=== Environment Variable Validation ===" >> validation-results.txt
echo "webhook-test-0:" >> validation-results.txt
kubectl logs webhook-test-0 -n gpu-scheduler-tests | grep CUDA >> validation-results.txt
echo "webhook-test-1:" >> validation-results.txt
kubectl logs webhook-test-1 -n gpu-scheduler-tests | grep CUDA >> validation-results.txt
echo "webhook-test-2:" >> validation-results.txt
kubectl logs webhook-test-2 -n gpu-scheduler-tests | grep CUDA >> validation-results.txt

# View the report
cat validation-results.txt
```

**✅ Expected Final Results:**
```
=== GPU Scheduler Validation Report ===

webhook-test-0: CUDA_VISIBLE_DEVICES=0,1    ✅ (Scheduled to node1)
webhook-test-1: CUDA_VISIBLE_DEVICES=2      ✅ (Scheduled to node2)  
webhook-test-2: CUDA_VISIBLE_DEVICES=0,1,2  ✅ (Scheduled to node3)
```

## 🎉 Success! You Have a Working GPU Scheduler

If you see the expected results above, you have successfully:

1. ✅ **Custom Scheduler Working**: Pods placed on designated nodes
2. ✅ **Webhook Working**: CUDA_VISIBLE_DEVICES automatically injected
3. ✅ **End-to-End Functionality**: Complete GPU scheduling solution
4. ✅ **Production Ready**: Secure TLS communication and proper RBAC

## Development

This chart was built from scratch (not using `helm create`) to ensure:
- Clean, intentional structure
- Only necessary components
- GPU scheduler-specific configuration
- Proper test service annotations

## Step 6: ArgoCD Deployment (Optional)

If you want to use ArgoCD ApplicationSets for GitOps deployment:

### 6.1 Install ArgoCD (if not already installed)
```bash
kubectl create namespace argocd
kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml

# Wait for ArgoCD to be ready
kubectl wait --for=condition=available deployment -n argocd --all --timeout=300s
```

### 6.2 Register Local Cluster (ESSENTIAL!)
```bash
# This step is CRITICAL for ApplicationSets to work!
# Without this secret, ApplicationSets will not find any matching clusters
kubectl apply -f argocd/local-cluster-secret.yaml
```

**Why this is needed:**
- ArgoCD doesn't automatically know about the local cluster for ApplicationSets
- The secret registers the cluster with the `environment: gpu-enabled` label
- Without this, you'll see "generated 0 applications" errors

### 6.3 Deploy ArgoCD Resources

**Container Registry Configuration:**
The ApplicationSet is configured to pull images from GitLab Container Registry:
```yaml
# GPU Scheduler Image
image:
  repository: registry.gitlab.com/evgenii19/gpu-scheduler/gpu-scheduler
  tag: latest
  pullPolicy: Always

# GPU Scheduler Check Image  
image:
  repository: registry.gitlab.com/evgenii19/gpu-scheduler/gpu-scheduler-check
  tag: latest
  pullPolicy: Always
```

**Note**: The same GitLab registry parameters are used in all deployment methods (Helm, ArgoCD) to ensure consistency.

```bash
# Apply the ArgoCD project
kubectl apply -f argocd/gpu-scheduler-project.yaml

# Deploy the ApplicationSet
kubectl apply -f argocd/gpu-scheduler-complete-applicationset.yaml

# Monitor application creation
kubectl get applications -n argocd

# Check ApplicationSet status
kubectl get applicationset -n argocd
```

### 6.4 Troubleshoot ApplicationSet Issues
If applications aren't created:
```bash
# Check ApplicationSet controller logs
kubectl logs -n argocd -l app.kubernetes.io/name=argocd-applicationset-controller

# Verify cluster secret exists
kubectl get secret -n argocd local-cluster -o yaml

# Check ApplicationSet status
kubectl describe applicationset gpu-scheduler-complete -n argocd
```

## Troubleshooting

### Common Issues and Solutions

**Problem**: Scheduler pod showing 1/1 instead of 2/2
```bash
# Solution: Webhook not enabled or certificates missing
helm get values gpu-scheduler -n gpu-scheduler-system
# Verify webhook.enabled=true and caBundle is set
```

**Problem**: ImagePullBackOff error when deploying
```bash
# Solution: Use GitLab registry instead of local image
helm upgrade gpu-scheduler . \
  --namespace gpu-scheduler-system \
  --set image.repository=registry.gitlab.com/evgenii19/gpu-scheduler/gpu-scheduler \
  --set image.tag=latest \
  --set image.pullPolicy=Always
```

**Problem**: Pods not getting CUDA_VISIBLE_DEVICES
```bash
# Solution: Check webhook logs and configuration
kubectl logs -l app.kubernetes.io/name=gpu-scheduler -n gpu-scheduler-system -c webhook
kubectl get mutatingwebhookconfiguration gpu-scheduler-webhook
```

**Problem**: Webhook returns 404 errors  
```bash
# Solution: Usually fixed by rebuilding and reloading image
cd gpu-scheduler
docker build -t gpu-scheduler:latest .
kind load docker-image gpu-scheduler:latest --name gpu-scheduler-cluster
kubectl rollout restart deployment/gpu-scheduler -n gpu-scheduler-system
```

**Problem**: TLS certificate issues
```bash
# Solution: Regenerate certificates
cd gpu-scheduler
rm -rf certs/
./generate-webhook-certs.sh
kubectl delete secret gpu-scheduler-webhook-tls -n gpu-scheduler-system
kubectl apply -f certs/webhook-tls-secret.yaml
```

**Congratulations! You now have a fully functional GPU scheduler system! 🚀**