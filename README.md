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
    # CUDA_VISIBLE_DEVICES automatically injected!
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
├── .gitlab-ci.yml                    # CI/CD pipeline configuration
├── README.md                         # Main documentation
├── COMPLETE_SETUP_GUIDE.md           # Step-by-step setup guide
├── gpu-scheduler/                    # Main scheduler service
│   ├── Dockerfile                    # Container image build
│   ├── scheduler.py                  # Custom scheduler logic
│   ├── webhook_server.py             # Admission webhook server
│   ├── health_server.py              # Health check endpoints
│   ├── requirements.txt              # Python dependencies
│   ├── generate-webhook-certs.sh     # TLS certificate generation
│   ├── test_basic.py                 # Unit tests
│   └── README.md                     # Service documentation
├── gpu-scheduler-check/              # Test/validation service
│   ├── Dockerfile                    # Container image build
│   ├── main.py                       # Test service logic
│   ├── requirements.txt              # Python dependencies
│   └── README.md                     # Service documentation
├── charts/                           # Helm deployment charts
│   ├── gpu-scheduler/                # Main scheduler chart
│   │   ├── Chart.yaml                # Chart metadata
│   │   ├── values.yaml               # Default configuration
│   │   ├── templates/                # Kubernetes manifests
│   │   └── README.md                 # Chart documentation
│   └── gpu-scheduler-check/          # Test service chart
│       ├── Chart.yaml                # Chart metadata
│       ├── values.yaml               # Default configuration
│       ├── templates/                # Kubernetes manifests
│       └── README.md                 # Chart documentation
├── argocd/                           # GitOps deployment configs
│   ├── gpu-scheduler-project.yaml           # ArgoCD project definition
│   ├── gpu-scheduler-complete-applicationset.yaml  # Complete deployment
│   ├── local-cluster-secret.yaml            # Local cluster registration
│   ├── validate-applicationset.sh           # Validation script
│   └── README.md                            # GitOps documentation
├── cluster/                          # Local development setup
│   ├── kind-config.yaml              # KinD cluster configuration
│   └── setup-cluster.sh              # Cluster setup script
└── outputs/                          # Test results and logs
```

### Test Service Configuration

Configure test service behavior:

```yaml
# values.yaml
replicaCount: 5

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
    - podIndex: 2
      nodeName: node3
      gpuDevices: "0,1,2"
    - podIndex: 3
      nodeName: node4
      gpuDevices: "3"
    - podIndex: 4
      nodeName: node4
      gpuDevices: "3"

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

# Check webhook health
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
# Node: node4, CUDA_VISIBLE_DEVICES: 3
# Node: node4, CUDA_VISIBLE_DEVICES: 3
```

## Documentation

### 📚 **Getting Started**

**Option 1: Automated Setup with Ansible (Recommended)**
```bash
# Install Ansible and dependencies
pip3 install ansible
cd ansible-gpu-scheduler
ansible-galaxy collection install -r requirements.yml

# Run complete automated setup
ansible-playbook -i inventory.yml playbook.yml
```

**Option 2: Manual Setup**
- **[Complete Setup Guide](COMPLETE_SETUP_GUIDE.md)** - Step-by-step guide from zero to working system

The Ansible playbook automates the entire setup process including:
- Prerequisites verification (Docker, kubectl, Helm, KinD)
- KinD cluster creation with GPU node labeling
- Container image building and deployment
- GPU scheduler and webhook deployment
- Test service validation
- ArgoCD GitOps configuration


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