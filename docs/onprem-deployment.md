# On-Prem Deployment Guide

This guide explains how to deploy the Spark K8s Hub in an air-gapped on-prem environment where external resources are accessed via Nexus proxy.

## Overview

The project supports two deployment modes:

| Mode | Description |
|------|-------------|
| **internet** | Direct access to Docker Hub, public Helm repos, Maven Central |
| **onprem** | All resources via Nexus proxy (srvnexus1.dst.dk) |

## Prerequisites

Before deploying, verify all required resources are available in Nexus:

```bash
./verify-onprem-resources-on-server.sh
```

All checks should pass (green) before proceeding.

## Quick Start

### 1. Download Dependencies from Nexus

After verification passes, download all build dependencies from Nexus:

```bash
# Download everything from Nexus (JARs, Python, Spark, uv)
./scripts/download-all-onprem.sh
```

Or download individually:

```bash
# Download JARs from Nexus Maven proxy
./scripts/download-jars.sh --nexus

# Download Python, Spark, uv from Nexus raw repo
./scripts/download-python.sh --nexus
```

**Note:** The Python/Spark/uv files require a Nexus raw repository. If not available, copy these files manually to `docker/spark-base/` or use the full zip with files included.

### 2. Build Docker Images

Build images using Nexus-proxied base images:

```bash
# Build spark-base
docker build \
  --build-arg BASE_IMAGE=srvnexus1.dst.dk:18079/eclipse-temurin:11-jdk-jammy \
  -t srvnexus1.dst.dk:18079/statkube/spark-base:spark3.5.3-py3.12-1 \
  docker/spark-base/

# Build spark-notebook
docker build \
  --build-arg BASE_IMAGE=srvnexus1.dst.dk:18079/statkube/spark-base:spark3.5.3-py3.12-1 \
  -t srvnexus1.dst.dk:18079/statkube/spark-notebook:spark3.5.3-py3.12-1 \
  docker/spark-notebook/
```

### 3. Push Images to Nexus

```bash
docker push srvnexus1.dst.dk:18079/statkube/spark-base:spark3.5.3-py3.12-1
docker push srvnexus1.dst.dk:18079/statkube/spark-notebook:spark3.5.3-py3.12-1
```

### 4. Deploy with Ansible

```bash
ansible-playbook ansible/playbooks/k3d_dev.yml -i ansible/inventory/onprem.yml
```

### 5. Access JupyterHub

```
http://localhost:8080
Login: any username / password: test
```

## Architecture

### Resource Sources

| Resource | Internet | On-Prem |
|----------|----------|---------|
| Docker Hub images | `image:tag` | `srvnexus1.dst.dk:18079/image:tag` |
| GHCR images | `ghcr.io/image:tag` | `srvnexus1.dst.dk:18083/image:tag` |
| Helm charts | Public repos | `https://srvnexus1.dst.dk/repository/...` |
| Maven JARs | Downloaded at build | Pre-downloaded locally |
| Python packages | PyPI (via uv) | Pre-baked in image |

### Required Images in Nexus

Docker Hub proxy (port 18079):
- `eclipse-temurin:11-jdk-jammy`
- `busybox:1.36`
- `minio/minio:RELEASE.2024-11-07T00-52-20Z`
- `apache/polaris:0.9.0`
- `jupyterhub/k8s-hub:4.3.1`

GHCR proxy (port 18083):
- `googlecloudplatform/spark-operator:v1beta2-1.3.8-3.1.1`

### Pre-downloaded Files

The following files must be present in `docker/spark-base/` before building:

| File | Source | Script |
|------|--------|--------|
| `Python-3.12.7.tgz` | python.org | `download-python.sh` |
| `uv-x86_64-unknown-linux-gnu.tar.gz` | GitHub releases | `download-python.sh` |
| `uv-aarch64-unknown-linux-gnu.tar.gz` | GitHub releases | `download-python.sh` |
| `spark-3.5.3-bin-hadoop3.tgz` | Already in repo | - |
| `jars/*.jar` | Maven Central | `download-jars.sh` |

### JAR Dependencies

Located in `docker/spark-base/jars/`:

- `hadoop-aws-3.3.4.jar` - S3A filesystem support
- `aws-java-sdk-bundle-1.12.623.jar` - AWS SDK for S3
- `iceberg-spark-runtime-3.5_2.12-1.9.0.jar` - Apache Iceberg
- `iceberg-aws-bundle-1.9.0.jar` - Iceberg AWS integration
- `delta-spark_2.12-3.2.0.jar` - Delta Lake
- `delta-storage-3.2.0.jar` - Delta Lake storage

## File Structure

```
├── ansible/
│   ├── inventory/
│   │   ├── onprem.yml      # On-prem configuration
│   │   └── internet.yml    # Internet configuration
│   └── playbooks/
│       └── k3d_dev.yml     # Main deployment playbook
├── docker/
│   └── spark-base/
│       ├── Dockerfile      # Uses BASE_IMAGE ARG
│       ├── jars/           # Pre-downloaded JARs
│       ├── Python-*.tgz    # Pre-downloaded Python
│       └── uv-*.tar.gz     # Pre-downloaded uv
├── k8s/
│   ├── jupyterhub/
│   │   ├── values-base.yaml
│   │   ├── values-k3d.yaml
│   │   └── values-onprem.yaml    # On-prem image refs
│   ├── minio/
│   │   ├── minio.yaml            # Internet version
│   │   └── minio-onprem.yaml     # On-prem version
│   ├── polaris/
│   │   ├── polaris.yaml              # Internet version
│   │   ├── polaris-onprem.yaml       # On-prem version
│   │   ├── polaris-bootstrap.yaml    # Internet bootstrap
│   │   └── polaris-bootstrap-onprem.yaml  # On-prem bootstrap
│   └── spark-operator/
│       ├── values-base.yaml
│       ├── values-dev.yaml
│       └── values-onprem.yaml    # On-prem image refs
└── verify-onprem-resources-on-server.sh  # Verify Nexus resources
```

## Comparison: Internet vs On-Prem

The playbook automatically selects the correct manifests based on inventory:

| Component | Internet | On-Prem |
|-----------|----------|---------|
| Spark Operator | `values-base.yaml` + `values-dev.yaml` | `values-base.yaml` + `values-onprem.yaml` + `values-dev.yaml` |
| JupyterHub | `values-base.yaml` + `values-k3d.yaml` | `values-base.yaml` + `values-onprem.yaml` + `values-k3d.yaml` |
| MinIO | `minio.yaml` | `minio-onprem.yaml` |
| Polaris | `polaris.yaml` | `polaris-onprem.yaml` |
| Bootstrap | `polaris-bootstrap.yaml` (alpine) | `polaris-bootstrap-onprem.yaml` (busybox) |

## Nexus Repository Requirements

Your Nexus instance should have the following repositories configured:

### Docker Hub Proxy
- Type: Docker (proxy)
- Port: 18079
- Proxies: Docker Hub (https://registry-1.docker.io)

### GHCR Proxy
- Type: Docker (proxy)
- Port: 18083
- Proxies: ghcr.io

### Helm Repositories
- `spark-operator`: Helm proxy for https://kubeflow.github.io/spark-operator
- `jupyterhub`: Helm proxy for https://jupyterhub.github.io/helm-chart/

## Troubleshooting

### Image Pull Errors

If pods fail to pull images:
1. Run `./verify-onprem-resources-on-server.sh` to check Nexus availability
2. Verify image names include the correct registry prefix
3. Check k3s can reach Nexus: `crictl pull srvnexus1.dst.dk:18079/busybox:1.36`

### Build Failures

If Docker builds fail:
1. Ensure all pre-downloaded files exist in `docker/spark-base/`
2. Run `./scripts/download-python.sh` and `./scripts/download-jars.sh`
3. Verify the base image is accessible: `docker pull srvnexus1.dst.dk:18079/eclipse-temurin:11-jdk-jammy`

### Helm Chart Errors

If Helm fails to fetch charts:
1. Test Helm repo: `helm repo add test-spark https://srvnexus1.dst.dk/repository/spark-operator`
2. Verify chart exists: `helm search repo test-spark`

### Check Pod Status

```bash
kubectl get pods -A
kubectl describe pod <pod-name> -n <namespace>
kubectl logs <pod-name> -n <namespace>
```
