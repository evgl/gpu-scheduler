# GPU Scheduler Check Helm Chart

A Helm chart for deploying the GPU Scheduler Check service to validate GPU scheduling assignments in Kubernetes.

## Description

This chart deploys test pods that use the GPU scheduler and log their node assignments and CUDA_VISIBLE_DEVICES values. It's designed to validate that the GPU scheduler is working correctly.


## Configuration

The following table lists the configurable parameters and their default values:

| Parameter | Description | Default |
|-----------|-------------|---------|
| `replicaCount` | Number of test pods to deploy | `5` |
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
    - podIndex: 3
      nodeName: "node4"
      gpuDevices: "3"
    - podIndex: 4
      nodeName: "node4"
      gpuDevices: "3"
```

This configuration demonstrates the complete GPU scheduling scenario:
- **Node1**: Single pod (0) with 2 GPUs (0,1)
- **Node2**: Single pod (1) with 1 GPU (2)
- **Node3**: Single pod (2) with 3 GPUs (0,1,2)
- **Node4**: Multiple pods (3,4) sharing the same GPU (3) - showcasing resource sharing

This generates the annotation:
```yaml
gpu-scheduling-map: |
  0=node1:0,1
  1=node2:2
  2=node3:0,1,2
  3=node4:3
  4=node4:3
```

## Customization

### Change Replica Count and Scheduling
```bash
# Example: Deploy 3 pods instead of default 5
helm install gpu-test ./gpu-scheduler-check-chart \
  --set replicaCount=5 \
  --set gpuScheduling.schedulingMap[0].nodeName=worker-1
```

**Note**: When changing `replicaCount`, ensure it matches the number of entries in your `schedulingMap`. If you deploy more pods than scheduling entries, the extra pods will not be scheduled by the GPU scheduler.

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