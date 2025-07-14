# GPU Scheduler Check Service

A test service that validates GPU scheduler assignments by continuously logging the node name and CUDA_VISIBLE_DEVICES environment variable.

## Purpose

This service is designed to test and validate the GPU scheduler functionality by:
1. Logging the node name where the pod is running
2. Displaying the CUDA_VISIBLE_DEVICES environment variable set by the scheduler
3. Providing continuous monitoring of GPU assignments

## Features

- **Continuous Logging**: Logs GPU assignment information at configurable intervals
- **Environment Validation**: Checks for required environment variables and logs warnings
- **Graceful Shutdown**: Handles SIGTERM and SIGINT signals properly
- **Configurable Interval**: Log interval can be set via environment variable
- **Error Handling**: Robust error handling and validation
- **Security**: Runs as non-root user

## Usage

### Environment Variables

- `NODE_NAME`: The Kubernetes node name (usually set by Kubernetes)
- `CUDA_VISIBLE_DEVICES`: GPU devices assigned by the scheduler
- `LOG_INTERVAL`: Logging interval in seconds (default: 10)
- `POD_NAMESPACE`: Pod namespace for debug information
- `HOSTNAME`: Pod name for debug information

### Log Format

The service logs in this format:
```
Node: <node_name>, CUDA_VISIBLE_DEVICES: <gpu_devices>
```

### Example Output

```
2025-07-09 03:00:00,000 - __main__ - INFO - GPU Scheduler Check service starting...
2025-07-09 03:00:00,000 - __main__ - INFO - Log interval: 10 seconds
2025-07-09 03:00:00,000 - __main__ - INFO - Environment validation passed
2025-07-09 03:00:00,000 - __main__ - INFO - Node: node1, CUDA_VISIBLE_DEVICES: 0,1
2025-07-09 03:00:10,000 - __main__ - INFO - Node: node1, CUDA_VISIBLE_DEVICES: 0,1
```

## Docker Image

### Build
```bash
docker build -t gpu-scheduler-check:latest .
```

### Run Locally
```bash
docker run --rm \
  -e NODE_NAME=test-node \
  -e CUDA_VISIBLE_DEVICES=0,1 \
  -e LOG_INTERVAL=5 \
  gpu-scheduler-check:latest
```

## Kubernetes Deployment

This service should be deployed with:
```yaml
spec:
  schedulerName: gpu-scheduler
  annotations:
    gpu-scheduling-map: |
      0=node1:0,1
      1=node2:2
```

The scheduler will:
1. Place the pod on the specified node
2. Set the CUDA_VISIBLE_DEVICES environment variable
3. The service will log this information for validation

## Testing GPU Scheduler

1. Deploy multiple replicas with different GPU scheduling maps
2. Check logs to verify pods are placed on correct nodes
3. Verify CUDA_VISIBLE_DEVICES matches the scheduling annotation
4. Monitor logs to ensure continuous operation

## Files

- `main.py` - Main service implementation
- `Dockerfile` - Container configuration
- `requirements.txt` - Python dependencies (none currently)
- `README.md` - This documentation