# On-Prem Deployment Guide

This guide explains how to deploy the Spark K8s Hub in an air-gapped on-prem environment where external resources are accessed via Nexus proxy.

## Overview

The project supports two deployment modes:

| Mode | Description |
|------|-------------|
| **internet** | Direct access to Docker Hub, public Helm repos, Maven Central |
| **onprem** | All resources via Nexus proxy (srvnexus1:80888) |

## Quick Start

### 1. Switch to On-Prem Mode

```bash
./scripts/set-environment.sh onprem
```

### 2. Configure Nexus Endpoints

Edit `ansible/inventory/onprem.yml` and update the `CHANGEME` placeholders:

```yaml
# GHCR proxy port
ghcr_registry_prefix: "srvnexus1:YOUR_GHCR_PORT/"

# Helm repository URLs
helm_spark_operator_repo_url: "https://srvnexus1:YOUR_PORT/repository/helm-hosted/spark-operator"
helm_jupyterhub_repo_url: "https://srvnexus1:YOUR_PORT/repository/helm-hosted/jupyterhub"
```

### 3. Pre-download Dependencies

While connected to the internet, download all required files:

```bash
# Download Python source and uv binary
./scripts/download-python.sh

# Download Spark JARs
./scripts/download-jars.sh
```

### 4. Build Docker Images

```bash
# Build spark-base (uses eclipse-temurin from Nexus)
docker build \
  --build-arg BASE_IMAGE=srvnexus1:80888/eclipse-temurin:11-jdk-jammy \
  -t statkube/spark-base:spark3.5.3-py3.12-1 \
  docker/spark-base/

# Build spark-notebook (uses spark-base from Nexus)
docker build \
  --build-arg BASE_IMAGE=srvnexus1:80888/statkube/spark-base:spark3.5.3-py3.12-1 \
  -t statkube/spark-notebook:spark3.5.3-py3.12-1 \
  docker/spark-notebook/

# Build jupyterhub-hub (uses spark-base from Nexus)
docker build \
  --build-arg BASE_IMAGE=srvnexus1:80888/statkube/spark-base:spark3.5.3-py3.12-1 \
  -t statkube/jupyterhub-hub:spark3.5.3-py3.12-1 \
  docker/jupyterhub-hub/
```

### 5. Deploy

```bash
cd ansible/playbooks
ansible-playbook -i ../inventory/active.yml kind_dev.yml
```

## Architecture

### Resource Sources

| Resource | Internet | On-Prem |
|----------|----------|---------|
| Docker base images | Docker Hub | `srvnexus1:80888/` |
| GHCR images | `ghcr.io/` | `srvnexus1:<port>/` |
| Helm charts | Public repos | Nexus Helm proxy |
| Maven JARs | Downloaded at build | Pre-downloaded locally |
| Python packages | PyPI (via uv) | Pre-baked in image |
| APT packages | Ubuntu repos | Via sources.list |

### Pre-downloaded Files

The following files must be present in the `docker/spark-base/` directory before building:

| File | Source | Script |
|------|--------|--------|
| `Python-3.12.7.tgz` | python.org | `download-python.sh` |
| `uv-x86_64-unknown-linux-gnu.tar.gz` | GitHub releases | `download-python.sh` |
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
│   │   ├── internet.yml    # Internet configuration
│   │   └── active.yml      # Symlink to active config
│   └── playbooks/
│       └── kind_dev.yml    # Main deployment playbook
├── docker/
│   └── spark-base/
│       ├── Dockerfile      # Uses BASE_IMAGE ARG
│       ├── jars/           # Pre-downloaded JARs
│       ├── Python-*.tgz    # Pre-downloaded Python
│       └── uv-*.tar.gz     # Pre-downloaded uv
├── k8s/
│   ├── jupyterhub/
│   │   ├── values-base.yaml
│   │   ├── values-dev.yaml
│   │   └── values-onprem.yaml  # On-prem image refs
│   ├── minio/
│   │   ├── minio.yaml          # Internet version
│   │   └── minio-onprem.yaml   # On-prem version
│   └── polaris/
│       ├── polaris.yaml        # Internet version
│       └── polaris-onprem.yaml # On-prem version
└── scripts/
    ├── download-jars.sh    # Download JAR dependencies
    ├── download-python.sh  # Download Python & uv
    └── set-environment.sh  # Switch environments
```

## Reverting to Internet Mode

To switch back to direct internet access:

```bash
./scripts/set-environment.sh internet
```

Then build images without the BASE_IMAGE override (uses defaults):

```bash
docker build -t statkube/spark-base:spark3.5.3-py3.12-1 docker/spark-base/
docker build -t statkube/spark-notebook:spark3.5.3-py3.12-1 docker/spark-notebook/
docker build -t statkube/jupyterhub-hub:spark3.5.3-py3.12-1 docker/jupyterhub-hub/
```

## Nexus Repository Requirements

Your Nexus instance should have the following repositories configured:

### Docker Proxy
- Type: Docker (proxy)
- Port: 80888
- Proxies: Docker Hub (https://registry-1.docker.io)

### GHCR Proxy (if needed)
- Type: Docker (proxy)
- Port: (configure as needed)
- Proxies: ghcr.io

### Helm Proxy
- Type: Helm (proxy/hosted)
- Proxies:
  - https://kubeflow.github.io/spark-operator
  - https://jupyterhub.github.io/helm-chart/

### APT Proxy
- Configured via `/etc/apt/sources.list` on build machines
- Should proxy Ubuntu Jammy (22.04) repositories

## Troubleshooting

### Image Pull Errors

If pods fail to pull images, verify:
1. Nexus proxy is accessible from the cluster
2. Image names include the correct registry prefix
3. For on-prem, use `*-onprem.yaml` manifests

### Build Failures

If Docker builds fail:
1. Ensure all pre-downloaded files exist
2. Run `./scripts/download-python.sh` and `./scripts/download-jars.sh`
3. Verify the REGISTRY_PREFIX is set correctly

### Check Current Configuration

```bash
./scripts/set-environment.sh status
```

