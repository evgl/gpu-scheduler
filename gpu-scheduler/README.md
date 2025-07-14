# GPU Scheduler

Custom Kubernetes scheduler for GPU device assignment with automatic CUDA_VISIBLE_DEVICES environment variable injection.

## Architecture

The GPU scheduler consists of two components:

1. **Scheduler**: Assigns pods to specific nodes based on the `gpu-scheduling-map` annotation
2. **Mutating Webhook**: Injects `CUDA_VISIBLE_DEVICES` environment variable before pod creation

## Features

- Custom pod scheduling based on GPU assignments
- Automatic CUDA_VISIBLE_DEVICES environment variable injection
- Support for multi-GPU assignments
- Health check endpoints
- Secure webhook with TLS

## Components

### Scheduler (`scheduler.py`)
- Watches for pods with `schedulerName: gpu-scheduler`
- Parses `gpu-scheduling-map` annotation
- Assigns pods to specified nodes based on pod index

### Webhook Server (`webhook_server.py`)
- Intercepts pod creation requests
- Injects CUDA_VISIBLE_DEVICES environment variable
- Runs on port 8443 with TLS

### Health Server (`health_server.py`)
- Provides `/health` and `/ready` endpoints
- Runs on port 8080

## Configuration

### Environment Variables
- `SCHEDULER_NAME`: Name of the scheduler (default: `gpu-scheduler`)

### Annotation Format
```yaml
metadata:
  annotations:
    gpu-scheduling-map: |
      0=node1:0,1
      1=node2:2
      2=node3:0,1,2
      3=node4:3
      4=node4:3
```

Format: `<pod-index>=<node-name>:<gpu-devices>`
- `pod-index`: Index of the pod (extracted from pod name)
- `node-name`: Target Kubernetes node
- `gpu-devices`: Comma-separated GPU device IDs

## Building

```bash
docker build -t gpu-scheduler:latest .
```

The image includes both the scheduler and webhook server. Use different commands to run each component:
- Scheduler: `python -u scheduler.py`
- Webhook: `python -u webhook_server.py`

## Running Locally

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Run the scheduler:
```bash
python scheduler.py
```

3. Run the webhook server (requires TLS certificates):
```bash
python webhook_server.py
```

## Deployment

Use the provided Helm chart for deployment. The chart handles:
- TLS certificate generation for the webhook
- RBAC configuration
- Service creation
- Webhook registration

## Testing

Run unit tests:
```bash
python test_scheduler.py
python test_basic.py
```

## How It Works

1. User creates a pod with `schedulerName: gpu-scheduler` and `gpu-scheduling-map` annotation
2. Webhook intercepts pod creation and injects CUDA_VISIBLE_DEVICES based on pod index
3. Scheduler receives the pod and schedules it to the specified node
4. Pod runs with correct GPU assignment

## Security

- Runs as non-root user (UID 1000)
- Read-only root filesystem
- Webhook uses TLS for secure communication
- Minimal required RBAC permissions