# Spark on Kubernetes with JupyterHub

A production-ready setup for running Apache Spark on Kubernetes with JupyterHub, designed for both internet-connected and air-gapped environments.

![Architecture Diagram](docs/images/diagram.svg)

## 🎯 Overview

This project provides:
- **Apache Spark 3.5.3** with Delta Lake and Apache Iceberg support
- **JupyterHub** for multi-user notebook access
- **Spark Operator** for Kubernetes-native Spark jobs
- **Apache Polaris** catalog for lakehouse table management
- **Air-gapped deployment** support via Nexus proxies

## 🚀 Quick Start

### Prerequisites

**Local Development:**
- Docker Desktop
- kubectl
- Helm 3
- k3d (recommended) or kind
- Ansible

**On-Prem Server:**
- Docker
- kubectl
- Helm 3
- k3d (recommended)

### 1. Local Setup (with Internet)

```bash
# Clone repository
git clone <repository-url>
cd spark-k8-hub

# Install k3d (recommended)
brew install k3d  # macOS
# or
curl -s https://raw.githubusercontent.com/k3d-io/k3d/main/install.sh | bash

# Build Docker images
docker build -t statkube/spark-base:spark3.5.3-py3.12-1 \
  -f docker/spark-base/Dockerfile docker/spark-base

docker build -t statkube/spark-notebook:spark3.5.3-py3.12-1 \
  -f docker/spark-notebook/Dockerfile docker/spark-notebook

# Create k3d cluster and deploy
cd ansible/playbooks
ansible-playbook -i ../inventory/internet.yml k3d_dev.yml -e load_images=true

# Access JupyterHub
kubectl port-forward svc/proxy-public -n jhub-dev 8080:80
# Open http://localhost:8080
```

### 2. On-Prem Setup (Air-Gapped)

See [On-Prem Deployment Guide](docs/onprem-deployment.md)

## 📚 Documentation

### Setup Guides
- **[k3d Setup](docs/k3d-setup.md)** - Recommended local Kubernetes (k3s)
- **[Local Setup](docs/local_setup.md)** - Complete development setup
- **[On-Prem Deployment](docs/onprem-deployment.md)** - Air-gapped installation

### Configuration
- **[APT Proxy Setup](docs/apt-proxy-setup.md)** - Configure Nexus APT proxy for Docker builds
- **[IT Team Setup Guide](docs/IT-TEAM-NEXUS-SETUP.md)** - Quick reference for administrators
- **[Resource Checklist](docs/onprem-resource-checklist.md)** - Required resources for on-prem

### Architecture
- **[Local Dev Architecture](docs/local-dev-k8s.md)** - System architecture overview

## 🏗️ Project Structure

```
spark-k8-hub/
├── ansible/                    # Deployment automation
│   ├── inventory/
│   │   ├── internet.yml       # Internet-connected config
│   │   └── onprem.yml         # Air-gapped config
│   └── playbooks/
│       └── kind_dev.yml       # Local cluster deployment
├── docker/
│   ├── spark-base/            # Base Spark image
│   ├── spark-notebook/        # JupyterHub notebook image
│   └── jupyterhub-hub/        # JupyterHub hub image
├── k8s/                       # Kubernetes manifests
│   ├── jupyterhub/           # JupyterHub configuration
│   ├── spark-operator/       # Spark Operator config
│   ├── minio/                # MinIO (S3-compatible storage)
│   ├── polaris/              # Apache Polaris catalog
│   └── spark-apps/           # Example Spark applications
├── scripts/
│   ├── verify-onprem-resources.sh  # Verify air-gapped resources
│   ├── download-jars.sh            # Download Spark JARs
│   └── set-environment.sh          # Environment setup
└── docs/                     # Documentation

```

## 🔧 Key Components

### Spark Base Image
- **Python 3.12.7** (compiled from source)
- **Apache Spark 3.5.3** with Hadoop 3.3.4
- **Delta Lake 3.2.0** for ACID transactions
- **Apache Iceberg 1.9.0** for lakehouse tables
- **uv** package manager for fast Python installs

### JupyterHub Integration
- Multi-user Spark notebook environment
- KubeSpawner for per-user pods
- Pre-configured Spark connection
- Git integration via jupyterlab-git
- Example notebooks included

### Spark Operator
- Kubernetes-native Spark job submission
- Automatic driver/executor pod management
- Integration with Kubernetes RBAC

## 🌐 Deployment Modes

### Internet Mode (Default)
- Pulls images from Docker Hub
- Downloads packages from Maven Central, PyPI
- Helm charts from public repositories

### On-Prem Mode (Air-Gapped)
- Uses Nexus proxies for all resources:
  - Docker images (Docker Hub, GHCR)
  - Maven JARs
  - PyPI packages
  - APT packages
  - Helm charts
- Pre-downloaded dependencies
- No internet access required

**Switch between modes** by changing inventory file:
```bash
# Internet
ansible-playbook -i ../inventory/internet.yml k3d_dev.yml

# On-prem
ansible-playbook -i ../inventory/onprem.yml k3d_dev.yml
```

## 🔍 Resource Verification

Verify all required resources are available before deployment:

```bash
# Online (test with Maven Central)
DOCKER_REGISTRY="skip" \
GHCR_REGISTRY="skip" \
HELM_REPO_URL="skip" \
MAVEN_REPO_URL="https://repo1.maven.org/maven2" \
./scripts/verify-onprem-resources.sh

# On-prem (test with Nexus)
./scripts/verify-onprem-resources.sh
```

## 📦 Required Dependencies

### For Docker Builds
- **Spark JARs:** hadoop-aws, iceberg, delta-lake (6 files)
- **Python:** Python-3.12.7.tgz
- **uv:** uv binaries for amd64 and arm64
- **Spark:** spark-3.5.3-bin-hadoop3.tgz

Download with:
```bash
./scripts/download-jars.sh           # From Maven Central
./scripts/download-jars.sh --nexus   # From Nexus
```

### For Nexus Setup (On-Prem)
See [IT Team Setup Guide](docs/IT-TEAM-NEXUS-SETUP.md) for:
- Docker registry proxies (Docker Hub, GHCR)
- Maven repository proxies
- Helm chart repositories
- APT package proxies
- PyPI proxies

## 🎓 Example Notebooks

Included in `docker/spark-notebook/`:
- **01_polaris_demo.ipynb** - Apache Polaris catalog integration
- **02_iceberg_demo.ipynb** - Iceberg table operations
- **03_delta_demo.ipynb** - Delta Lake transactions
- **04_metrics_demo.ipynb** - Custom metrics with OpenLineage

## 🔐 Security Considerations

- Service accounts with minimal RBAC permissions
- Namespace isolation (jhub-dev, spark-operator, default)
- Optional network policies
- Secrets management for credentials

## 🐛 Troubleshooting

### Verification Script Fails
```bash
# Check specific section that failed
./scripts/verify-onprem-resources.sh

# Test Maven repo manually
curl -I https://srvnexus1.dst.dk/repository/apache-spark/spark-jars/hadoop-aws-3.3.4.jar
```

### Docker Build Fails in Air-Gapped Environment
```bash
# Ensure APT sources.list is configured
# Uncomment in docker/spark-base/Dockerfile:
COPY sources.list.nexus /etc/apt/sources.list

# Update sources.list.nexus with your Nexus URLs
```

### Images Not Found in k3d
```bash
# Import images after building
k3d image import statkube/spark-base:spark3.5.3-py3.12-1 -c spark-cluster
k3d image import statkube/spark-notebook:spark3.5.3-py3.12-1 -c spark-cluster
```

### JupyterHub Not Accessible
```bash
# Check service status
kubectl get svc -n jhub-dev

# Port forward to access
kubectl port-forward svc/proxy-public -n jhub-dev 8080:80
```

## 🤝 Contributing

This is an internal DST project. For questions or issues, contact the team.

## 📝 License

Internal use only - DST (Danmarks Statistik)

## 🔗 Related Links

- [Apache Spark](https://spark.apache.org/)
- [JupyterHub](https://jupyter.org/hub)
- [Spark Operator](https://github.com/kubeflow/spark-operator)
- [Apache Iceberg](https://iceberg.apache.org/)
- [Delta Lake](https://delta.io/)
- [k3d](https://k3d.io/)
- [Rancher](https://rancher.com/)

---

**Version:** 1.0  
**Last Updated:** November 2024  
**Maintained by:** DST Platform Team
