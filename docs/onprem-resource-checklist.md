# On-Prem Resource Checklist for IT

This document lists all external resources required for deploying the Spark K8s Hub in an air-gapped environment.

## Quick Verification

Run the verification script to test connectivity:
```bash
./scripts/verify-onprem-resources.sh
```

---

## 1. Docker Images (Nexus Docker Proxy)

### Docker Hub Images
Available via `srvnexus1:80888/`:

| Image | Version | Source |
|-------|---------|--------|
| `eclipse-temurin` | `11-jdk-jammy` | Docker Hub |
| `busybox` | `1.36` | Docker Hub |
| `minio/minio` | `latest` | Docker Hub |
| `apache/polaris` | `latest` | Docker Hub |
| `jupyterhub/k8s-hub` | `4.3.1` | Docker Hub |

**Test command:**
```bash
docker pull srvnexus1:80888/eclipse-temurin:11-jdk-jammy
```

### GHCR Images (GitHub Container Registry)
Available via `srvnexus1:<GHCR_PORT>/`:

| Image | Version | Source |
|-------|---------|--------|
| `googlecloudplatform/spark-operator` | `v1beta2-1.3.8-3.1.1` | ghcr.io |

**Original source:**
```
ghcr.io/googlecloudplatform/spark-operator:v1beta2-1.3.8-3.1.1
```

**Test command:**
```bash
docker pull srvnexus1:<GHCR_PORT>/googlecloudplatform/spark-operator:v1beta2-1.3.8-3.1.1
```

---

## 2. Helm Charts (Nexus Helm Proxy)

| Chart | Source Repository |
|-------|-------------------|
| `spark-operator` | https://kubeflow.github.io/spark-operator |
| `jupyterhub` | https://jupyterhub.github.io/helm-chart/ |

**Test command:**
```bash
helm repo add nexus-helm https://srvnexus1:PORT/repository/helm-hosted
helm search repo nexus-helm
```

---

## 3. Maven JARs (Nexus Maven Proxy)

Download from Maven Central and cache in Nexus:

| JAR | Group ID | Version |
|-----|----------|---------|
| `hadoop-aws` | `org.apache.hadoop` | `3.3.4` |
| `aws-java-sdk-bundle` | `com.amazonaws` | `1.12.623` |
| `iceberg-spark-runtime-3.5_2.12` | `org.apache.iceberg` | `1.9.0` |
| `iceberg-aws-bundle` | `org.apache.iceberg` | `1.9.0` |
| `delta-spark_2.12` | `io.delta` | `3.2.0` |
| `delta-storage` | `io.delta` | `3.2.0` |

**Direct download URLs:**
```
https://repo1.maven.org/maven2/org/apache/hadoop/hadoop-aws/3.3.4/hadoop-aws-3.3.4.jar
https://repo1.maven.org/maven2/com/amazonaws/aws-java-sdk-bundle/1.12.623/aws-java-sdk-bundle-1.12.623.jar
https://repo1.maven.org/maven2/org/apache/iceberg/iceberg-spark-runtime-3.5_2.12/1.9.0/iceberg-spark-runtime-3.5_2.12-1.9.0.jar
https://repo1.maven.org/maven2/org/apache/iceberg/iceberg-aws-bundle/1.9.0/iceberg-aws-bundle-1.9.0.jar
https://repo1.maven.org/maven2/io/delta/delta-spark_2.12/3.2.0/delta-spark_2.12-3.2.0.jar
https://repo1.maven.org/maven2/io/delta/delta-storage/3.2.0/delta-storage-3.2.0.jar
```

---

## 4. Pre-Downloaded Files (Store in Nexus Raw Repo or File Share)

These files are COPIED into Docker images during build (not downloaded at runtime):

| File | Size (approx) | Download URL |
|------|---------------|--------------|
| `Python-3.12.7.tgz` | ~26 MB | https://www.python.org/ftp/python/3.12.7/Python-3.12.7.tgz |
| `uv-x86_64-unknown-linux-gnu.tar.gz` | ~12 MB | https://github.com/astral-sh/uv/releases/download/0.5.5/uv-x86_64-unknown-linux-gnu.tar.gz |
| `spark-3.5.3-bin-hadoop3.tgz` | ~400 MB | https://archive.apache.org/dist/spark/spark-3.5.3/spark-3.5.3-bin-hadoop3.tgz |

**Note:** `spark-3.5.3-bin-hadoop3.tgz` is already included in the repository.

---

## 5. APT Packages (Nexus APT Proxy)

The build machines need `/etc/apt/sources.list` configured to use Nexus APT proxy.

Required packages from Ubuntu 22.04 (Jammy):
```
curl wget ca-certificates git make build-essential
libssl-dev zlib1g-dev libbz2-dev libreadline-dev
libsqlite3-dev llvm libncurses5-dev libncursesw5-dev
xz-utils tk-dev libffi-dev liblzma-dev bash tini
```

---

## 6. PyPI Packages (Optional - Nexus PyPI Proxy)

If caching PyPI packages, the following are required:

**Core packages:**
- pyspark==3.5.3
- pandas==2.2.3
- numpy==2.1.2
- pyarrow==18.0.0
- requests==2.32.3

**Jupyter packages:**
- jupyterlab
- notebook
- jupyterhub
- jupyterhub-kubespawner
- jupyterlab-git
- jupytext
- ipykernel

**Dev tools:**
- black, isort, flake8, gitpython

**Note:** These are pre-baked into Docker images. PyPI proxy only needed if rebuilding images on-prem.

---

## Verification Checklist

- [ ] Docker proxy accessible at `srvnexus1:80888`
- [ ] All Docker images pullable from proxy
- [ ] Helm repository configured and charts available
- [ ] Maven JARs accessible or pre-downloaded
- [ ] Python/uv tarballs available
- [ ] APT sources.list configured on build machines
- [ ] Network connectivity from Kubernetes nodes to Nexus

---

## Scripts Provided

| Script | Purpose |
|--------|---------|
| `scripts/download-jars.sh` | Downloads Maven JARs for offline build |
| `scripts/download-python.sh` | Downloads Python source and uv binary |
| `scripts/verify-onprem-resources.sh` | Verifies on-prem resources are accessible |
| `scripts/set-environment.sh` | Switches between internet/onprem config |

---

## Contact

For issues with resource availability, contact the development team with:
1. Output of `./scripts/verify-onprem-resources.sh`
2. Nexus repository configuration details
3. Network connectivity test results

