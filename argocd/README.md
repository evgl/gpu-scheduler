# GPU Scheduler ArgoCD Configuration

This directory contains ArgoCD ApplicationSet and Project configurations for deploying the GPU Scheduler system using GitOps.

## Files

### Core Configuration
- `gpu-scheduler-project.yaml` - ArgoCD Project definition with RBAC and resource permissions
- `gpu-scheduler-complete-applicationset.yaml` - Complete ApplicationSet managing both scheduler and test service
- `local-cluster-secret.yaml` - **REQUIRED**: Cluster registration secret for local development

When you create a fresh cluster, ArgoCD doesn't automatically know about the local cluster for ApplicationSet generators. You must apply this secret:

```bash
kubectl apply -f argocd/local-cluster-secret.yaml
```

This secret:
- Registers the local cluster with ArgoCD
- Adds the `environment: gpu-enabled` label that ApplicationSets use for cluster selection
- Enables the ApplicationSet to target `https://kubernetes.default.svc`

Without this secret, ApplicationSets will show:
- No applications created
- "generated 0 applications" in logs
- No matching clusters for the selector

## Deployment Architecture

The ApplicationSet deploys two components with proper dependency ordering:

1. **GPU Scheduler** (Sync Wave 1)
   - Namespace: `gpu-scheduler-system`
   - Runs on control plane nodes
   - Provides custom scheduling capability

2. **GPU Scheduler Check** (Sync Wave 2)
   - Namespace: `gpu-scheduler-tests`
   - Deploys test pods using the GPU scheduler
   - Validates scheduling functionality

## Prerequisites

### ArgoCD Setup
- ArgoCD installed in cluster
- ArgoCD CLI configured
- Proper RBAC permissions

### Cluster Requirements
- Kubernetes cluster with GPU nodes
- Nodes labeled with `environment: gpu-enabled`
- Control plane nodes accessible for scheduler placement


## Configuration

### Cluster Selection
Applications are deployed to clusters with the label:
```yaml
environment: gpu-enabled
```

Add this label to target clusters:
```bash
kubectl label cluster <cluster-name> environment=gpu-enabled
```

### GPU Scheduling Map
Default configuration in the ApplicationSet:
```yaml
gpuScheduling:
  schedulingMap:
    - podIndex: 0, nodeName: node1, gpuDevices: "0,1"
    - podIndex: 1, nodeName: node2, gpuDevices: "2"  
    - podIndex: 2, nodeName: node3, gpuDevices: "0,1,2"
    - podIndex: 3, nodeName: node4, gpuDevices: "3"
    - podIndex: 4, nodeName: node4, gpuDevices: "3"
```

## Monitoring

### Application Health
```bash
# Check application health
argocd app get gpu-scheduler-complete

# View application tree
argocd app get gpu-scheduler-complete --show-managed-fields
```

### Pod Validation
```bash
# Check scheduler deployment
kubectl get pods -n gpu-scheduler-system

# Check test service logs
kubectl logs -n gpu-scheduler-tests -l app.kubernetes.io/name=gpu-scheduler-check -f

# Verify pod placement
kubectl get pods -n gpu-scheduler-tests -o wide
```