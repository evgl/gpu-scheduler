# GPU Scheduler Helm Chart

Production-ready Helm chart for deploying the GPU scheduler with mutating admission webhook for complete GPU scheduling functionality.

## Overview

This Helm chart deploys a complete GPU scheduling solution consisting of:

1. **Custom Scheduler**: Places pods on designated nodes based on annotations
2. **Mutating Admission Webhook** (recommended): Automatically injects CUDA_VISIBLE_DEVICES environment variables
3. **TLS Security**: Secure webhook communication with certificate management

**Recommended Usage**: Deploy with webhook enabled for full GPU scheduling functionality including automatic environment variable injection.

## Quick Start

### Recommended: Deploy with Webhook (Full Functionality)

```bash
# Generate TLS certificates
cd ../../gpu-scheduler
./generate-webhook-certs.sh
kubectl apply -f certs/webhook-tls-secret.yaml

# Get CA bundle
CA_BUNDLE=$(cat certs/ca.crt | base64 -w 0)

# Deploy with webhook enabled
helm install gpu-scheduler . \
  --namespace gpu-scheduler-system \
  --create-namespace \
  --set webhook.enabled=true \
  --set webhook.caBundle=$CA_BUNDLE \
  --set image.repository=registry.gitlab.com/evgenii19/gpu-scheduler/gpu-scheduler \
  --set image.tag=latest \
  --set image.pullPolicy=Always
```

### Alternative: Scheduler Only (Limited Functionality)

**Note**: This deployment lacks automatic CUDA_VISIBLE_DEVICES injection. Only use for testing or when webhook is not needed.

```bash
helm install gpu-scheduler . \
  --namespace gpu-scheduler-system \
  --create-namespace \
  --set webhook.enabled=false \
  --set image.repository=registry.gitlab.com/evgenii19/gpu-scheduler/gpu-scheduler \
  --set image.tag=latest \
  --set image.pullPolicy=Always
```

## Configuration

**Note**: The examples above use the GitLab Container Registry (`registry.gitlab.com/evgenii19/gpu-scheduler/gpu-scheduler`) which is the recommended image source for production deployments.

**Recommendation**: Deploy with webhook enabled for full GPU scheduling functionality including automatic CUDA_VISIBLE_DEVICES injection.

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

### Webhook Resources (if enabled)
- **MutatingWebhookConfiguration**: Configures webhook endpoint
- **Secret**: TLS certificates for secure communication

## Usage

### Pod Annotation Format

```yaml
apiVersion: v1
kind: Pod
metadata:
  annotations:
    gpu-scheduling-map: |
      0=node1:0,1
      1=node2:2
      2=node3:0,1,2
spec:
  schedulerName: gpu-scheduler
  containers:
  - name: app
    image: nvidia/cuda:11.0-base
    # CUDA_VISIBLE_DEVICES automatically set by webhook!
```

### StatefulSet Example

```yaml
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: gpu-workload
spec:
  replicas: 3
  template:
    metadata:
      annotations:
        gpu-scheduling-map: |
          0=node1:0,1
          1=node2:2
          2=node3:0,1,2
    spec:
      schedulerName: gpu-scheduler
      containers:
      - name: worker
        image: my-gpu-app:latest
```

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

## Troubleshooting

### Common Issues

**Scheduler not scheduling pods:**
- Verify RBAC permissions
- Check node selector and tolerations
- Review scheduler logs

**Webhook not working:**
- Verify TLS certificates are valid
- Check webhook service is running
- Review webhook logs for errors

**Environment variables not set:**
- Ensure webhook is enabled and configured (recommended deployment)
- Verify pod uses `schedulerName: gpu-scheduler`
- Check annotation format is correct
- Confirm TLS certificates are properly configured

See [../../docs/TROUBLESHOOTING.md](../../docs/TROUBLESHOOTING.md) for detailed troubleshooting guide.

## Development

### Testing

```bash
# Lint chart
helm lint .

# Render templates
helm template gpu-scheduler . --values values.yaml

# Test with webhook enabled
helm template gpu-scheduler . \
  --set webhook.enabled=true \
  --set webhook.caBundle="LS0t..."
```

### Customization

The chart can be customized by modifying `values.yaml` or providing custom values:

```bash
# Custom values file
helm install gpu-scheduler . -f custom-values.yaml

# Command line overrides
helm install gpu-scheduler . \
  --set resources.limits.cpu=1000m \
  --set webhook.enabled=true
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

### Alternative: Upgrade Scheduler Only

```bash
# Upgrade deployment without webhook (limited functionality)
helm upgrade gpu-scheduler . \
  --namespace gpu-scheduler-system \
  --set webhook.enabled=false \
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