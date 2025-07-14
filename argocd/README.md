# GPU Scheduler ArgoCD Configuration

This directory contains ArgoCD ApplicationSet and Project configurations for deploying the GPU Scheduler system using GitOps.

## Files

### Core Configuration
- `gpu-scheduler-project.yaml` - ArgoCD Project definition with RBAC and resource permissions
- `gpu-scheduler-complete-applicationset.yaml` - Complete ApplicationSet managing both scheduler and test service
- `local-cluster-secret.yaml` - **REQUIRED**: Cluster registration secret for local development

### Individual ApplicationSets (Alternative)
- `gpu-scheduler-applicationset.yaml` - ApplicationSet for GPU scheduler only
- `gpu-scheduler-check-applicationset.yaml` - ApplicationSet for test service only

## Important: Local Cluster Secret

**The `local-cluster-secret.yaml` file is ESSENTIAL for ApplicationSets to work!**

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

### Git Repository
- Update `repoURL` in ApplicationSets to your GitLab repository
- Ensure repository contains the Helm charts:
  - `gpu-scheduler-chart/`
  - `gpu-scheduler-check-chart/`

## Installation

### 1. Deploy Project
```bash
kubectl apply -f gpu-scheduler-project.yaml
```

### 2. Register Local Cluster (REQUIRED)
```bash
# This step is ESSENTIAL for ApplicationSets to work!
kubectl apply -f local-cluster-secret.yaml
```

### 3. Deploy ApplicationSet (Choose One)

**Option A: Complete ApplicationSet (Recommended)**
```bash
kubectl apply -f gpu-scheduler-complete-applicationset.yaml
```

**Option B: Individual ApplicationSets**
```bash
kubectl apply -f gpu-scheduler-applicationset.yaml
kubectl apply -f gpu-scheduler-check-applicationset.yaml
```

### 4. Verify Deployment
```bash
# Check applications
argocd app list

# Check application status
argocd app get gpu-scheduler-complete

# View sync status
argocd app sync gpu-scheduler-complete
```

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
```

### Repository Configuration
Update the repository URL in ApplicationSets:
```yaml
source:
  repoURL: git@gitlab.com:evgenii19/gpu-scheduler.git
```

## Sync Policies

### Automated Sync
- **Prune**: Remove resources not in Git
- **Self Heal**: Automatically sync when drift detected
- **Allow Empty**: Prevent deletion of all resources

### Sync Options
- `CreateNamespace=true` - Auto-create target namespaces
- `PrunePropagationPolicy=foreground` - Proper resource cleanup
- `ApplyOutOfSyncOnly=true` - Only sync changed resources
- `ServerSideApply=true` - Use server-side apply for better conflict resolution

### Retry Policy
- **Limit**: 5 retry attempts
- **Backoff**: Exponential backoff (5s to 3m)

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

## Troubleshooting

### ApplicationSet Not Creating Applications
- Verify cluster labels match selector
- Check ArgoCD project permissions
- Ensure repository access is configured

### Sync Failures
- Check resource quotas in target namespaces
- Verify RBAC permissions
- Review ArgoCD server logs

### GPU Scheduling Issues
- Ensure GPU scheduler is running in wave 1
- Verify node names in scheduling map exist
- Check scheduler logs for errors

### Test Service Not Logging
- Verify CUDA_VISIBLE_DEVICES is set
- Check if pods are placed on correct nodes
- Review test service logs for errors

## Security

### RBAC
- Project-level RBAC controls access
- Namespace isolation between components
- Cluster resource restrictions

### Sync Windows
- Applications can be synced 24/7
- Manual sync always allowed
- No blackout windows configured

## Customization

### Environment-Specific Values
Create environment-specific ApplicationSets by:
1. Duplicating ApplicationSet files
2. Modifying cluster selector labels
3. Updating Helm values for each environment

### Multi-Cluster Deployment
The ApplicationSet automatically deploys to all clusters matching the selector, enabling:
- Development clusters
- Staging environments  
- Production deployments

## Dependencies

- **Sync Waves**: Scheduler (wave 1) deploys before test service (wave 2)
- **Health Checks**: ArgoCD waits for scheduler health before proceeding
- **Resource Dependencies**: Test service requires scheduler to be functional

Checkpoint 6: ArgoCD ApplicationSet - COMPLETED ✅

  Key Achievements:
  1. Complete GitOps Configuration: Created ApplicationSets for both GPU scheduler and test service
  2. Dependency Management: Implemented sync waves (scheduler=1, test service=2) for proper deployment order
  3. Multi-cluster Support: Cluster selector labels for environment-specific deployments
  4. Namespace Isolation: Separate namespaces for system components and tests
  5. Comprehensive RBAC: Project-level permissions and resource restrictions
  6. Automated Sync: Self-healing with prune policies and retry mechanisms

  Key Features:
  - ApplicationSet Options: Both complete and individual ApplicationSets provided
  - Sync Waves: Ensures GPU scheduler deploys before test service
  - Cluster Selection: Targets clusters labeled with environment: gpu-enabled
  - Namespace Management: Auto-creation of gpu-scheduler-system and gpu-scheduler-tests
  - GitOps Best Practices: Automated sync, self-heal, proper pruning policies
  - Resource Control: Comprehensive RBAC with cluster and namespace resource restrictions
  - Validation: Script to validate configuration and prerequisites

  ApplicationSet Structure:
  # Sync Wave 1: GPU Scheduler
  namespace: gpu-scheduler-system
  component: scheduler
  path: gpu-scheduler-chart

  # Sync Wave 2: Test Service  
  namespace: gpu-scheduler-tests
  component: test-service
  path: gpu-scheduler-check-chart

  Deployment Flow:
  1. ArgoCD Project creates RBAC and permissions
  2. ApplicationSet deploys GPU scheduler (wave 1)
  3. ApplicationSet waits for scheduler health
  4. ApplicationSet deploys test service (wave 2)
  5. Test service validates GPU scheduling functionality

  Testing Results:
  - YAML validation passed ✓
  - ApplicationSet generator syntax correct ✓
  - Project RBAC configured properly ✓
  - Sync policies validated ✓
  - Documentation complete ✓

  The GitOps configuration is now ready to deploy the complete GPU scheduler system to any Kubernetes cluster with proper ArgoCD setup.