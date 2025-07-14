# GPU Scheduler Helm Chart

Production-ready Helm chart for deploying the GPU scheduler with mutating admission webhook for complete GPU scheduling functionality.

## Overview

This Helm chart deploys a complete GPU scheduling solution consisting of:

1. **Custom Scheduler**: Places pods on designated nodes based on annotations
2. **Mutating Admission Webhook** : Automatically injects CUDA_VISIBLE_DEVICES environment variables
3. **TLS Security**: Secure webhook communication with certificate management

**Recommended Usage**: Deploy with webhook enabled for full GPU scheduling functionality including automatic environment variable injection.

## Configuration

**Note**: The examples use the GitLab Container Registry (`registry.gitlab.com/evgenii19/gpu-scheduler/gpu-scheduler`) which is the recommended image source for deployments.

### Values.yaml Options

```yaml
# Basic scheduler configuration
scheduler:
  name: gpu-scheduler

# Webhook configuration (recommended)
webhook:
  enabled: true                     # Recommended: enable webhook for full functionality
  caBundle: ""                      # Base64-encoded CA certificate (required when enabled)
  failurePolicy: Ignore             # Webhook failure handling

# Container image
image:
  repository: gpu-scheduler              # Default: use GitLab registry in production
  tag: latest
  pullPolicy: IfNotPresent              # Use Always for GitLab registry

# Resource limits
resources:
  requests:
    cpu: 100m
    memory: 128Mi
  limits:
    cpu: 500m
    memory: 512Mi

# Node placement
nodeSelector:
  node-role.kubernetes.io/control-plane: ""

tolerations:
  - key: node-role.kubernetes.io/control-plane
    operator: Exists
    effect: NoSchedule
  - key: node-role.kubernetes.io/master
    operator: Exists
    effect: NoSchedule
```

## Components

### Deployment
- **Pod**: Runs both scheduler and webhook containers (recommended configuration)
- **Containers**: 
  - `scheduler`: Main scheduling logic
  - `webhook`: Automatic CUDA_VISIBLE_DEVICES injection (recommended)

### Services
- **Health Service**: Port 8080 for health checks
- **Webhook Service**: Port 443 for webhook requests (when enabled)

### RBAC
- **ServiceAccount**: `gpu-scheduler`
- **ClusterRole**: Permissions for pods, nodes, bindings, events
- **ClusterRoleBinding**: Binds role to service account

### Webhook Resources
- **MutatingWebhookConfiguration**: Configures webhook endpoint
- **Secret**: TLS certificates for secure communication


## Security Features

- **Non-root containers**: All containers run as non-root user
- **Read-only filesystem**: Containers use read-only root filesystem
- **TLS encryption**: Webhook communication secured with TLS certificates
- **Minimal RBAC**: Principle of least privilege for permissions
- **Security contexts**: Pod and container security contexts applied

## Monitoring

### Health Checks

```bash
# Check scheduler health
kubectl port-forward svc/gpu-scheduler 8080:8080 -n gpu-scheduler-system
curl http://localhost:8080/health

# Check scheduler logs
kubectl logs -l app.kubernetes.io/name=gpu-scheduler -n gpu-scheduler-system -c scheduler

# Check webhook logs (recommended deployment)
kubectl logs -l app.kubernetes.io/name=gpu-scheduler -n gpu-scheduler-system -c webhook
```

### Webhook Validation

```bash
# Verify webhook is configured
kubectl get mutatingwebhookconfiguration gpu-scheduler-webhook

# Test environment variable injection
kubectl exec <test-pod> -- env | grep CUDA_VISIBLE_DEVICES
```

## Upgrade

### Recommended: Upgrade with Webhook Enabled

```bash
# Upgrade deployment with webhook (recommended)
helm upgrade gpu-scheduler . \
  --namespace gpu-scheduler-system \
  --set webhook.enabled=true \
  --set webhook.caBundle=$CA_BUNDLE \
  --set image.repository=registry.gitlab.com/evgenii19/gpu-scheduler/gpu-scheduler \
  --set image.tag=latest \
  --set image.pullPolicy=Always
```

## Uninstall

```bash
# Remove deployment
helm uninstall gpu-scheduler -n gpu-scheduler-system

# Clean up webhook configuration (if used)
kubectl delete mutatingwebhookconfiguration gpu-scheduler-webhook

# Remove TLS secret (if used)
kubectl delete secret gpu-scheduler-webhook-tls -n gpu-scheduler-system
```