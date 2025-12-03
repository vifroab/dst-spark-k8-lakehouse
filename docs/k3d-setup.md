# k3d Setup Guide

## Why k3d Instead of kind?

**k3d** (k3s in Docker) is recommended over kind for this project because:

- ✅ **Production Alignment:** Rancher SUSE uses k3s/RKE2 in production
- ✅ **Lighter & Faster:** Uses 50% less memory, starts in 30-60 seconds
- ✅ **Built-in LoadBalancer:** ServiceLB works out-of-box (no MetalLB needed)
- ✅ **Built-in Ingress:** Traefik pre-installed
- ✅ **Port Forwarding:** Easy localhost access without kubectl port-forward

## Prerequisites

On the Ubuntu server, ensure these are installed:
- ✅ Docker
- ✅ kubectl
- ✅ helm
- ⚠️ **k3d** (only new requirement)

### Install k3d

**Online:**
```bash
curl -s https://raw.githubusercontent.com/k3d-io/k3d/main/install.sh | bash
```

**Air-gapped (download on internet machine, transfer to server):**
```bash
# Download
wget https://github.com/k3d-io/k3d/releases/download/v5.6.0/k3d-linux-amd64

# Install on server
sudo install -o root -g root -m 0755 k3d-linux-amd64 /usr/local/bin/k3d

# Verify
k3d version
```

## Quick Start

### 1. Create Cluster with Port Mapping

```bash
k3d cluster create spark-cluster \
  --agents 2 \
  --port "8080:80@loadbalancer" \
  --port "8443:443@loadbalancer"
```

**This exposes:**
- `localhost:8080` → LoadBalancer services on port 80
- `localhost:8443` → LoadBalancer services on port 443

### 2. Verify Cluster

```bash
kubectl cluster-info
kubectl get nodes
# Should show: 1 server + 2 agent nodes
```

### 3. Load Docker Images

```bash
# Load your custom images into k3d
k3d image import statkube/spark-base:spark3.5.3-py3.12-1 -c spark-cluster
k3d image import statkube/spark-notebook:spark3.5.3-py3.12-1 -c spark-cluster
```

### 4. Deploy Using Ansible

```bash
cd ansible/playbooks

# Internet mode (default)
ansible-playbook -i ../inventory/internet.yml k3d_dev.yml

# With pre-loaded images
ansible-playbook -i ../inventory/internet.yml k3d_dev.yml -e load_images=true

# On-prem mode
ansible-playbook -i ../inventory/onprem.yml k3d_dev.yml
```

## Accessing Services

With k3d's LoadBalancer support, services are automatically accessible:

**JupyterHub:**
```bash
# Get the LoadBalancer IP/port
kubectl get svc -n jhub-dev

# If using port mapping, access at:
http://localhost:8080
```

**No kubectl port-forward needed!** ✅

## Cluster Management

**Stop cluster:**
```bash
k3d cluster stop spark-cluster
```

**Start cluster:**
```bash
k3d cluster start spark-cluster
```

**Delete cluster:**
```bash
k3d cluster delete spark-cluster
```

**List clusters:**
```bash
k3d cluster list
```

## Differences from kind

| Operation | kind | k3d |
|-----------|------|-----|
| Create cluster | `kind create cluster --name NAME` | `k3d cluster create NAME` |
| Load image | `kind load docker-image IMAGE --name NAME` | `k3d image import IMAGE -c NAME` |
| Context name | `kind-NAME` | `k3d-NAME` |
| LoadBalancer | ❌ Needs MetalLB | ✅ Built-in ServiceLB |
| Ingress | ❌ Needs installation | ✅ Traefik included |
| Port mapping | Complex | Simple with `--port` flag |

## Advanced Configuration

### Multi-node Cluster
```bash
k3d cluster create spark-cluster \
  --servers 3 \
  --agents 3 \
  --port "8080:80@loadbalancer"
```

### With Registry
```bash
k3d cluster create spark-cluster \
  --registry-create spark-registry:0.0.0.0:5000 \
  --agents 2
```

### Custom k3s Arguments
```bash
k3d cluster create spark-cluster \
  --k3s-arg "--disable=traefik@server:0" \
  --agents 2
```

## Troubleshooting

### Port Already in Use
```bash
# Error: port 8080 already allocated
# Solution: Use different port or stop conflicting service
k3d cluster create spark-cluster --agents 2 --port "8090:80@loadbalancer"
```

### Image Not Found
```bash
# Make sure to import images after cluster creation
k3d image import YOUR-IMAGE:TAG -c spark-cluster
```

### Cannot Connect to Cluster
```bash
# Ensure context is set
kubectl config use-context k3d-spark-cluster

# Check cluster is running
k3d cluster list
```

## Migration from kind

If you have an existing kind setup:

1. **Export configs** from kind cluster (if needed)
2. **Create k3d cluster** with same name
3. **Load images** into k3d
4. **Deploy** using Ansible (same as before)

Both can coexist on the same machine!

## Resources

- k3d Documentation: https://k3d.io/
- k3s Documentation: https://k3s.io/
- Rancher Documentation: https://rancher.com/docs/

## Next Steps

After cluster creation:
1. Deploy Spark Operator → See `k8s/spark-operator/`
2. Deploy JupyterHub → See `k8s/jupyterhub/`
3. Run example notebooks → See `docker/spark-notebook/*.ipynb`

See also: `docs/local_setup.md` for complete deployment guide.

