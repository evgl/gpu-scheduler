# GPU Scheduler

A complete Kubernetes GPU scheduling system with custom scheduler and mutating admission webhook that assigns pods to specific nodes and automatically injects CUDA_VISIBLE_DEVICES environment variables.

## Overview

This project provides a two-component solution: a custom Kubernetes scheduler for pod placement and a mutating admission webhook for automatic CUDA_VISIBLE_DEVICES environment variable injection. Together, they process GPU scheduling annotations and assign pods to specified nodes with the correct GPU device visibility. The system includes a complete GitOps deployment pipeline using ArgoCD and comprehensive testing capabilities.

## Features

- **Custom GPU Scheduler**: Kubernetes scheduler that interprets GPU assignment annotations
- **Mutating Admission Webhook**: Automatically injects CUDA_VISIBLE_DEVICES environment variables
- **Pod Placement**: Assigns pods to specific nodes based on configuration
- **Environment Variable Injection**: Sets `CUDA_VISIBLE_DEVICES` for GPU device visibility before pod creation
- **TLS Security**: Secure webhook communication with certificate management
- **Test Service**: Validates GPU scheduling functionality with continuous logging
- **GitOps Deployment**: ArgoCD ApplicationSets for automated deployment
- **Production Ready**: Helm charts with security best practices
- **Local Development**: KinD cluster setup for testing

## Quick Start

🚀 **NEW: Complete Setup Guide Available!**  
For a comprehensive step-by-step guide from scratch to working system, see: **[COMPLETE_SETUP_GUIDE.md](COMPLETE_SETUP_GUIDE.md)**

### Prerequisites

- Kubernetes cluster (or KinD for local development)
- Helm 3.x
- ArgoCD (optional, for GitOps deployment)
- Docker (for building images)

### 1. Clone Repository

```bash
git clone https://gitlab.com/evgenii19/gpu-scheduler.git
cd gpu-scheduler
```

### 2. Build Images

```bash
# Build GPU scheduler image
cd gpu-scheduler
docker build -t gpu-scheduler:latest .

# Build test service image  
cd ../gpu-scheduler-check
docker build -t gpu-scheduler-check:latest .
```

### 3. Deploy with Helm

**Option A: Basic Deployment (Scheduler Only)**
```bash
# Install GPU scheduler without webhook
helm install gpu-scheduler charts/gpu-scheduler \
  --namespace gpu-scheduler-system \
  --create-namespace

# Install test service
helm install gpu-test charts/gpu-scheduler-check \
  --namespace gpu-scheduler-tests \
  --create-namespace
```

**Option B: Full Deployment (Scheduler + Webhook)**
```bash
# Generate TLS certificates for webhook
cd gpu-scheduler
./generate-webhook-certs.sh
kubectl apply -f certs/webhook-tls-secret.yaml

# Get CA bundle
CA_BUNDLE=$(cat certs/ca.crt | base64 -w 0)

# Install GPU scheduler with webhook
helm install gpu-scheduler charts/gpu-scheduler \
  --namespace gpu-scheduler-system \
  --create-namespace \
  --set webhook.enabled=true \
  --set webhook.caBundle=$CA_BUNDLE

# Install test service
helm install gpu-test charts/gpu-scheduler-check \
  --namespace gpu-scheduler-tests \
  --create-namespace
```

### 4. Verify Deployment

```bash
# Check scheduler is running (should show 2/2 if webhook enabled, 1/1 if not)
kubectl get pods -l app.kubernetes.io/name=gpu-scheduler -n gpu-scheduler-system

# Check webhook configuration (if enabled)
kubectl get mutatingwebhookconfiguration gpu-scheduler-webhook

# Check test service logs
kubectl logs -l app.kubernetes.io/name=gpu-scheduler-check -n gpu-scheduler-tests -f

# Expected output with webhook:
# Node: gpu-scheduler-cluster-worker, CUDA_VISIBLE_DEVICES: 0,1
# Node: gpu-scheduler-cluster-worker2, CUDA_VISIBLE_DEVICES: 2
# Node: gpu-scheduler-cluster-worker3, CUDA_VISIBLE_DEVICES: 0,1,2
```

## Architecture

```
User Creates Pod
      │
      ▼
┌─────────────────────┐    ┌─────────────────────┐
│ Mutating Admission  │    │  Custom GPU         │
│     Webhook         │───▶│   Scheduler         │
│ (Inject CUDA_VARS)  │    │ (Pod Placement)     │
└─────────────────────┘    └─────────────────────┘
      │                              │
      ▼                              ▼
┌─────────────────────┐    ┌─────────────────────┐
│  Pod with GPU Env   │    │  Pod on Target      │
│     Variables       │    │      Node           │
└─────────────────────┘    └─────────────────────┘

Deployment Architecture:
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   ArgoCD        │    │  GPU Scheduler   │    │ Test Service    │
│  ApplicationSet │───▶│     Helm Chart   │───▶│   Helm Chart    │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         │                        │                       │
         │                        ▼                       ▼
         │              ┌──────────────────┐    ┌─────────────────┐
         │              │Scheduler+Webhook │    │  Test Pods      │
         │              │  (Control Plane) │    │ (Worker Nodes)  │
         │              └──────────────────┘    └─────────────────┘
         │                        │                       │
         └────────────────────────┼───────────────────────┘
                                  ▼
                        ┌──────────────────────┐
                        │   Kubernetes API     │
                        │   Pod Scheduling     │
                        └──────────────────────┘
```

## Usage

### GPU Scheduling Annotation

Add the following annotation to your pod or deployment:

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: gpu-workload-0
  annotations:
    gpu-scheduling-map: |
      0=node1:0,1
      1=node2:2
      2=node3:0,1,2
      3=node4:3
      4=node4:3
spec:
  schedulerName: gpu-scheduler
  containers:
  - name: gpu-app
    image: nvidia/cuda:11.0-base
    command: ["nvidia-smi"]
    # CUDA_VISIBLE_DEVICES automatically injected by webhook!
```

### Annotation Format

```
gpu-scheduling-map: |
  <pod_index>=<node_name>:<gpu_devices>
```

Where:
- `pod_index`: Pod index (0, 1, 2, ...)
- `node_name`: Target Kubernetes node name
- `gpu_devices`: Comma-separated GPU device IDs for CUDA_VISIBLE_DEVICES

### Example Configurations

**Single GPU per Pod:**
```yaml
gpu-scheduling-map: |
  0=node1:0
  1=node1:1
  2=node2:0
```

**Multiple GPUs per Pod:**
```yaml
gpu-scheduling-map: |
  0=node1:0,1
  1=node2:2,3
  2=node3:0,1,2,3
```

## Repository Structure

```
gpu-scheduler/
├── gpu-scheduler/          # Scheduler service code
├── gpu-scheduler-check/    # Test service code  
├── charts/                 # Helm charts
├── argocd/                 # GitOps configurations
├── cluster/                # Local development setup
├── outputs/                # Validation results
└── scripts/                # Utility scripts
```

## Development

### Local Cluster Setup

Create a local KinD cluster with GPU scheduler configuration:

```bash
cd cluster
./setup-cluster.sh
```

This creates a 5-node cluster (1 control-plane + 4 workers) with proper labels.

### Building and Testing

```bash
# Build images
./scripts/build-images.sh

# Run tests
cd gpu-scheduler
python test_basic.py

# Deploy locally
./scripts/deploy-local.sh
```

### GitOps Deployment

Deploy using ArgoCD ApplicationSets:

```bash
# Apply ArgoCD project
kubectl apply -f argocd/gpu-scheduler-project.yaml

# Deploy applications
kubectl apply -f argocd/gpu-scheduler-complete-applicationset.yaml

# Monitor deployment
kubectl get applications -n argocd
```

## Configuration

### Scheduler Configuration

Configure the scheduler via Helm values:

```yaml
# values.yaml
scheduler:
  name: gpu-scheduler

# Enable webhook for automatic CUDA_VISIBLE_DEVICES injection
webhook:
  enabled: true
  caBundle: "<base64-encoded-ca-certificate>"

resources:
  requests:
    cpu: 100m
    memory: 128Mi
  limits:
    cpu: 500m
    memory: 512Mi
    
nodeSelector:
  node-role.kubernetes.io/control-plane: ""
```

### Test Service Configuration

Configure test service behavior:

```yaml
# values.yaml
replicaCount: 3

gpuScheduling:
  enabled: true
  schedulerName: gpu-scheduler
  schedulingMap:
    - podIndex: 0
      nodeName: node1
      gpuDevices: "0,1"
    - podIndex: 1
      nodeName: node2
      gpuDevices: "2"

testService:
  logInterval: 10
```

## Monitoring

### Health Checks

The scheduler provides health endpoints:

```bash
# Check scheduler health
kubectl port-forward svc/gpu-scheduler 8080:8080 -n gpu-scheduler-system
curl http://localhost:8080/health

# Check webhook health (if enabled)
kubectl logs -l app.kubernetes.io/name=gpu-scheduler -n gpu-scheduler-system -c webhook
```

### Validation

Monitor test service logs to verify GPU assignments:

```bash
# View test logs
kubectl logs -l app.kubernetes.io/name=gpu-scheduler-check -f

# Expected output:
# Node: node1, CUDA_VISIBLE_DEVICES: 0,1
# Node: node2, CUDA_VISIBLE_DEVICES: 2
# Node: node3, CUDA_VISIBLE_DEVICES: 0,1,2
```

## Troubleshooting

### Common Issues

**Scheduler Not Scheduling Pods:**
```bash
# Check scheduler logs
kubectl logs -l app.kubernetes.io/name=gpu-scheduler

# Verify RBAC permissions
kubectl auth can-i create bindings --as=system:serviceaccount:gpu-scheduler-system:gpu-scheduler
```

**CUDA_VISIBLE_DEVICES Not Set:**
```bash
# Check if webhook is enabled and working
kubectl get mutatingwebhookconfiguration gpu-scheduler-webhook

# Check webhook logs
kubectl logs -l app.kubernetes.io/name=gpu-scheduler -n gpu-scheduler-system -c webhook

# Check annotation format
kubectl get pod <pod-name> -o yaml | grep -A 10 annotations

# Verify scheduler is processing the pod
kubectl describe pod <pod-name>

# Check pod environment variables
kubectl exec <pod-name> -- env | grep CUDA
```

**ArgoCD Sync Issues:**
```bash
# Check application status
kubectl get applications -n argocd

# View sync errors
kubectl describe application <app-name> -n argocd
```

## Documentation

### 📚 **Getting Started**
- **[Complete Setup Guide](COMPLETE_SETUP_GUIDE.md)** - Step-by-step guide from zero to working system


## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Add tests for new functionality
5. Commit your changes (`git commit -m 'Add amazing feature'`)
6. Push to the branch (`git push origin feature/amazing-feature`)
7. Open a Merge Request

### Development Guidelines

- Follow Python PEP 8 style guide
- Add unit tests for new features
- Update documentation for API changes
- Test changes with local KinD cluster
- Ensure Helm charts lint successfully

## Security

- All containers run as non-root users
- RBAC follows principle of least privilege
- Security contexts enforce read-only filesystems where possible
- Regular security scanning via CI/CD pipeline