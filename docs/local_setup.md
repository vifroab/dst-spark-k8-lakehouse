# Local Spark-on-Kubernetes Dev Environment

![Architecture Diagram](images/diagram.svg)


This guide explains how to build the local Docker images (Spark base + Notebook) and deploy the full stack (Spark Operator + JupyterHub) to a local `kind` cluster.

## 1. Overview of Images

We use a mix of custom-built images (which we maintain) and official upstream images (which we pull).

| Image | Tag | Source | Description |
| :--- | :--- | :--- | :--- |
| `statkube/spark-base` | `spark3.5.3-py3.12-1` | **Custom Build** | Contains Java 21, Python 3.12, Spark 3.5.3, and `uv` for dependencies. Used by Spark Executors. |
| `statkube/spark-notebook` | `spark3.5.3-py3.12-1` | **Custom Build** | Extends `spark-base`. Adds JupyterLab, Jupytext, and dev tools. Used by JupyterHub single-user pods (Driver). |
| `quay.io/jupyterhub/k8s-hub` | `4.3.1` | **Upstream** | Official JupyterHub control plane image. We **do not** build this; we use it as defined in the Helm chart. |

### Enterprise Registry Pattern (Nexus)

In the corporate environment (DST), we use a **Nexus Group Registry** (`srvnexus1.dst.dk:18086`) that acts as a unified source for both internal and public images.

*   **Internal Images**: Stored in the private registry component (e.g., `statkube/*`).
*   **Public Images**: Proxied from Docker Hub (e.g., `python`, `ubuntu`).

By configuring the Docker daemon with a registry mirror, all pulls are routed through Nexus:

```json
// /etc/docker/daemon.json
{
  "registry-mirrors": ["https://srvnexus1.dst.dk:18086"]
}
```

This allows transparent access:
*   `docker pull python:3.12` -> fetched via Nexus Proxy -> Docker Hub.
*   `docker pull srvnexus1.dst.dk:18086/statkube/spark-base...` -> fetched from Nexus Private Registry.

## 2. Dependency Management Best Practices

We use `uv` for fast, deterministic package management.

### The "Immutable Image" Policy
To ensure Spark jobs run reliably, the **Driver** (Notebook) and **Executors** (Workers) must have identical Python environments.

1.  **Centralized Definition**: All shared libraries (e.g., `pandas`, `numpy`, internal libs) are defined in `docker/spark-base/requirements.txt`.
2.  **Base Image**: The `spark-base` image installs these requirements using `uv pip install --system`.
3.  **Notebook Image**: The `spark-notebook` image extends `spark-base`, inheriting the exact same environment.

**Rule for Users**: Do **not** install libraries inside the notebook (e.g., `!pip install`) if you intend to use them in Spark jobs. Instead, add them to the base image requirements and rebuild. This guarantees that the code works on the cluster exactly as it does in the notebook.

## 3. Build Images (Local Dev)

Run these commands from the root of the repo to build the custom images.

```bash
# 1. Ensure entrypoint is executable
chmod +x docker/spark-base/entrypoint.sh

# 2. Build Base Image
docker build -t statkube/spark-base:spark3.5.3-py3.12-1 docker/spark-base

# 3. Build Notebook Image (depends on base)
docker build -t statkube/spark-notebook:spark3.5.3-py3.12-1 docker/spark-notebook
```

## 4. Deploy to Local Kubernetes (Kind)

We use Ansible to orchestrate the setup: creating the cluster, loading the local images (so Kind doesn't try to pull them from a remote registry), and installing the Helm charts.

```bash
# Create cluster, load images, and deploy Spark Operator + JupyterHub
ansible-playbook ansible/playbooks/kind_dev.yml -e "load_images=true"
```

### Troubleshooting Deployment
If you need to redeploy just the Helm charts (e.g., after changing `values.yaml`):

```bash
# Update JupyterHub config
helm upgrade --install jhub jupyterhub/jupyterhub \
  --namespace jhub-dev \
  -f k8s/jupyterhub/values-base.yaml \
  -f k8s/jupyterhub/values-dev.yaml

# Update Spark Operator config
helm upgrade --install spark-operator spark-operator/spark-operator \
  --namespace spark-operator \
  -f k8s/spark-operator/values-base.yaml \
  -f k8s/spark-operator/values-dev.yaml
```

## 5. Access JupyterHub

Once deployed, expose the JupyterHub service:

```bash
kubectl port-forward -n jhub-dev svc/proxy-public 8000:80
```

- **URL**: [http://localhost:8000](http://localhost:8000)
- **Login**: Any username (e.g., `admin`), Password: `test`

## 6. Run a Spark Job

Inside a Jupyter Notebook, use this boilerplate to connect to the cluster.

**Note:** In the local dev environment, we must explicitly set the driver host IP so Executors in the `default` namespace can connect back to the Notebook in `jhub-dev`.

```python
import socket
import os
from pyspark.sql import SparkSession

# Robustly get the pod's real IP address
s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
s.connect(("8.8.8.8", 80))
driver_ip = s.getsockname()[0]
s.close()

spark = (
    SparkSession.builder.appName("notebook-test")
    .master("k8s://https://kubernetes.default.svc")
    .config("spark.kubernetes.container.image", "statkube/spark-base:spark3.5.3-py3.12-1")
    .config("spark.kubernetes.namespace", "default")
    
    # Network Configuration for Dev
    .config("spark.driver.host", driver_ip)
    .config("spark.driver.bindAddress", "0.0.0.0")
    .config("spark.driver.port", "7077")
    
    .config("spark.kubernetes.authenticate.driver.serviceAccountName", "spark-sa")
    .config("spark.kubernetes.authenticate.caCertFile", "/var/run/secrets/kubernetes.io/serviceaccount/ca.crt")
    .config("spark.kubernetes.authenticate.oauthTokenFile", "/var/run/secrets/kubernetes.io/serviceaccount/token")
    .config("spark.hadoop.hadoop.security.authentication", "simple")
    .config("spark.hadoop.hadoop.security.authorization", "false")
    
    .config("spark.executor.memory", "512m")
    .config("spark.kubernetes.executor.deleteOnTermination", "false")
    .getOrCreate()
)

# Test the cluster
spark.range(10).show()
```
