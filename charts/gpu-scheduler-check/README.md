# GPU Scheduler Check Helm Chart

A Helm chart for deploying the GPU Scheduler Check service to validate GPU scheduling assignments in Kubernetes.

## Description

This chart deploys test pods that use the GPU scheduler and log their node assignments and CUDA_VISIBLE_DEVICES values. It's designed to validate that the GPU scheduler is working correctly.

## Installation

```bash
helm install gpu-test ./gpu-scheduler-check-chart
```

## Configuration

The following table lists the configurable parameters and their default values:

| Parameter | Description | Default |
|-----------|-------------|---------|
| `replicaCount` | Number of test pods to deploy | `3` |
| `image.repository` | Test service image repository | `gpu-scheduler-check` |
| `image.tag` | Test service image tag | `latest` |
| `image.pullPolicy` | Image pull policy | `IfNotPresent` |
| `gpuScheduling.enabled` | Enable GPU scheduling | `true` |
| `gpuScheduling.schedulerName` | Scheduler name to use | `gpu-scheduler` |
| `gpuScheduling.schedulingMap` | GPU scheduling configuration | See values.yaml |
| `testService.logInterval` | Logging interval in seconds | `10` |
| `resources.requests.cpu` | CPU requests | `50m` |
| `resources.requests.memory` | Memory requests | `64Mi` |
| `resources.limits.cpu` | CPU limits | `100m` |
| `resources.limits.memory` | Memory limits | `128Mi` |

## GPU Scheduling Configuration

The chart uses a configurable GPU scheduling map in `values.yaml`:

```yaml
gpuScheduling:
  schedulingMap:
    - podIndex: 0
      nodeName: "node1"
      gpuDevices: "0,1"
    - podIndex: 1
      nodeName: "node2"
      gpuDevices: "2"
    - podIndex: 2
      nodeName: "node3"
      gpuDevices: "0,1,2"
```

This generates the annotation:
```yaml
gpu-scheduling-map: |
  0=node1:0,1
  1=node2:2
  2=node3:0,1,2
```

## Usage

1. **Deploy the chart:**
   ```bash
   helm install gpu-test ./gpu-scheduler-check-chart
   ```

2. **Check pod placement:**
   ```bash
   kubectl get pods -l app.kubernetes.io/name=gpu-scheduler-check -o wide
   ```

3. **View logs to verify GPU assignments:**
   ```bash
   kubectl logs -l app.kubernetes.io/name=gpu-scheduler-check -f
   ```

4. **Expected log output:**
   ```
   Node: node1, CUDA_VISIBLE_DEVICES: 0,1
   Node: node2, CUDA_VISIBLE_DEVICES: 2
   Node: node3, CUDA_VISIBLE_DEVICES: 0,1,2
   ```

## Customization

### Change Replica Count and Scheduling
```bash
helm install gpu-test ./gpu-scheduler-check-chart \
  --set replicaCount=5 \
  --set gpuScheduling.schedulingMap[0].nodeName=worker-1
```

### Custom Log Interval
```bash
helm install gpu-test ./gpu-scheduler-check-chart \
  --set testService.logInterval=5
```

### Disable GPU Scheduling (for testing)
```bash
helm install gpu-test ./gpu-scheduler-check-chart \
  --set gpuScheduling.enabled=false
```

## Prerequisites

- Kubernetes cluster with GPU scheduler deployed
- GPU scheduler must be running and configured
- Nodes should be labeled appropriately for GPU scheduling

## Troubleshooting

### Pods Not Scheduled
- Check if GPU scheduler is running: `kubectl get pods -n kube-system`
- Verify scheduler name matches: `kubectl describe pod <pod-name>`

### CUDA_VISIBLE_DEVICES Not Set
- Check scheduler logs for errors
- Verify annotation format is correct
- Ensure pod index matches scheduling map

### Pods on Wrong Nodes
- Verify node names in scheduling map
- Check if nodes exist: `kubectl get nodes`
- Review scheduler logs for placement decisions

## Development

This chart was built from scratch (not using `helm create`) to ensure:
- Clean, intentional structure
- Only necessary components
- GPU scheduler-specific configuration
- Proper test service annotations

## Files

- `Chart.yaml` - Chart metadata
- `values.yaml` - Default configuration values
- `templates/deployment.yaml` - Test service deployment
- `templates/serviceaccount.yaml` - Service account (minimal permissions)
- `templates/_helpers.tpl` - Template helper functions
- `templates/NOTES.txt` - Post-installation instructions

Checkpoint 5: Test Service Helm Chart - COMPLETED ✅

  Key Achievements:
  1. Clean Chart Structure: Built from scratch (not using helm create) for intentional, minimal structure
  2. GPU Scheduling Integration: Configurable GPU scheduling map with proper annotation generation
  3. Test Configuration: Configurable replica count, log interval, and environment variables
  4. Security: Non-root user, minimal RBAC, proper security contexts
  5. Documentation: Complete README and usage instructions

  Key Features:
  - GPU Scheduling Map: Configurable via values.yaml with helper template for annotation generation
  - Environment Variables: Automatic injection of NODE_NAME, POD_NAME, POD_NAMESPACE, LOG_INTERVAL
  - Replica Management: Configurable replica count (default 3) for testing multiple assignments
  - Resource Management: CPU (50m/100m) and memory (64Mi/128Mi) limits
  - Security: Non-root user (65534), minimal service account permissions
  - Flexibility: Configurable scheduler name, image repository, and test parameters

  Example GPU Scheduling Configuration:
  gpuScheduling:
    schedulingMap:
      - podIndex: 0, nodeName: "node1", gpuDevices: "0,1"
      - podIndex: 1, nodeName: "node2", gpuDevices: "2"
      - podIndex: 2, nodeName: "node3", gpuDevices: "0,1,2"

  Testing Results:
  - Helm lint passed ✓
  - Template rendering successful ✓
  - GPU scheduling annotation correctly formatted ✓
  - Custom values override working ✓
  - Complete documentation provided ✓

  The test service chart is now ready to deploy and validate GPU scheduler functionality in any Kubernetes cluster.