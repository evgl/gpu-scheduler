# GPU Scheduler Ansible Playbook

This Ansible playbook automates the complete installation of the GPU Scheduler system, following all steps from the COMPLETE_SETUP_GUIDE.md.

## 🎯 What This Playbook Does

1. **Prerequisites Verification**: Checks that Docker, kubectl, Helm, and KinD are installed (provides installation links if missing)
2. **KinD Cluster Setup**: Creates a 5-node cluster with proper GPU node labeling
3. **Container Images**: Builds GPU scheduler and test service images
4. **GPU Scheduler Deployment**: Deploys scheduler with mutating webhook (includes chicken-and-egg fix)
5. **Test Service**: Deploys test pods to verify GPU scheduling works correctly
6. **ArgoCD GitOps**: Installs ArgoCD and configures ApplicationSets for GitOps workflow

## 📋 Prerequisites

- **Required tools must be installed manually first**:
  - Docker 20.10+ ([Install Guide](https://docs.docker.com/get-docker/))
  - kubectl 1.19+ ([Install Guide](https://kubernetes.io/docs/tasks/tools/))
  - Helm 3.x ([Install Guide](https://helm.sh/docs/intro/install/))
  - KinD 0.11+ ([Install Guide](https://kind.sigs.k8s.io/docs/user/quick-start/#installation))
- Internet connection for downloading images
- At least 8GB of free RAM for the KinD cluster

## 🚀 Quick Start

### 1. Install Ansible

```bash
# Install Ansible via pip
pip3 install ansible
```

For other installation methods, see the [official Ansible installation guide](https://docs.ansible.com/ansible/latest/installation_guide/index.html).

### 2. Install Required Ansible Collections

```bash
cd ansible-gpu-scheduler
ansible-galaxy collection install -r requirements.yml
```

### 3. Run the Complete Setup

```bash
# Run the entire setup process
ansible-playbook -i inventory.yml playbook.yml

# Or run with specific tags
ansible-playbook -i inventory.yml playbook.yml --tags prerequisites
ansible-playbook -i inventory.yml playbook.yml --tags cluster
ansible-playbook -i inventory.yml playbook.yml --tags build
ansible-playbook -i inventory.yml playbook.yml --tags scheduler
ansible-playbook -i inventory.yml playbook.yml --tags test
ansible-playbook -i inventory.yml playbook.yml --tags argocd
```

## 🔧 Configuration Options

Edit `group_vars/all.yml` to customize:

```yaml
# Use GitLab registry (default for production)
use_local_images: false
image_registry: "registry.gitlab.com/evgenii19/gpu-scheduler"

# Or use local images (for development)
use_local_images: true
```

## 📝 Playbook Structure

```
ansible-gpu-scheduler/
├── playbook.yml              # Main playbook
├── inventory.yml             # Inventory (localhost)
├── requirements.yml          # Ansible Galaxy dependencies
├── ansible.cfg              # Ansible configuration
├── group_vars/
│   └── all.yml              # Configuration variables
└── roles/
    ├── prerequisites/tasks/  # Verify Docker, kubectl, Helm, KinD are installed
    ├── kind-cluster/tasks/   # Create and configure cluster
    ├── build-images/tasks/   # Build container images
    ├── gpu-scheduler/tasks/  # Deploy scheduler with webhook
    ├── test-service/tasks/   # Deploy and verify test pods
    └── argocd/tasks/         # Install and configure ArgoCD
```

### 🏗️ Role Structure Best Practices

This playbook follows Ansible best practices by:
- **Only creating directories that are used** - no empty `defaults/`, `vars/`, `handlers/`, or `templates/` folders
- **Clean, minimal structure** - easier to understand and maintain
- **Focused roles** - each role has a single responsibility
- **Consistent naming** - clear role names that match their function

> **Note**: As the project grows, you can add other standard Ansible directories like `defaults/main.yml`, `vars/main.yml`, `handlers/main.yml`, or `templates/` only when you actually need them.

## 🏷️ Available Tags

- `prerequisites`: Verify required tools are installed
- `cluster`: Create KinD cluster
- `build`: Build Docker images (skipped if using registry)
- `scheduler`: Deploy GPU scheduler
- `test`: Deploy test service
- `argocd`, `gitops`: Install ArgoCD

## 🔍 Verification

After successful completion, verify the setup:

```bash
# Check scheduler pods (should show 2/2 containers)
kubectl get pods -n gpu-scheduler-system

# Check test pod GPU assignments
kubectl logs -l "app.kubernetes.io/name=gpu-scheduler-check" -n gpu-scheduler-tests --tail=5

# Access scheduler health endpoint
kubectl port-forward svc/gpu-scheduler 8080:8080 -n gpu-scheduler-system
# Then visit: http://localhost:8080/health

# Access ArgoCD UI (password shown in playbook output)
kubectl port-forward svc/argocd-server -n argocd 8080:443
# Then visit: https://localhost:8080
```

## ⚙️ Advanced Usage

### Run Only Specific Steps

```bash
# Only verify prerequisites
ansible-playbook -i inventory.yml playbook.yml --tags prerequisites

# Skip building images (use registry instead)
ansible-playbook -i inventory.yml playbook.yml --skip-tags build
```

### Clean Up Everything

```bash
# Delete the KinD cluster
kind delete cluster --name gpu-scheduler-cluster

# Remove Docker images
docker rmi gpu-scheduler:latest gpu-scheduler-check:latest
```

### Debugging

```bash
# Run with verbose output
ansible-playbook -i inventory.yml playbook.yml -vvv

# Check specific role
ansible-playbook -i inventory.yml playbook.yml --tags scheduler --check
```