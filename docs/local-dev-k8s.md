### Local Spark-on-Kubernetes dev with kind, Spark Operator and JupyterHub

This repo includes a minimal setup to run Spark 4.0.1 on Kubernetes using kind, the Spark Operator and JupyterHub-backed notebooks.

### 1. Build images

- **spark-base**:
  - Contains Java 21, Python 3.12, Spark 4.0.1, uv and common JARs.
  - Installs Python dependencies from `docker/spark-base/requirements.txt` (including `pyspark`) using `uv pip install --system`.
- **spark-notebook**:
  - `FROM statkube/spark-base:spark4.0.1-py3.12-1`.
  - Adds JupyterLab, notebook, ipykernel, jupytext and dev tools.
- **JupyterHub hub**:
  - Uses the official chart image pinned in `k8s/jupyterhub/values-base.yaml` (`quay.io/jupyterhub/k8s-hub:4.3.1`).

Build locally (example tags, adjust as needed):

```bash
docker build -t statkube/spark-base:spark4.0.1-py3.12-1 docker/spark-base
docker build -t statkube/spark-notebook:spark4.0.1-py3.12-1 docker/spark-notebook
```

### 2. Start kind dev cluster and deploy stack

Prerequisites on your laptop:

- kind
- kubectl
- helm
- ansible

Run the Ansible playbook:

```bash
ansible-playbook ansible/playbooks/kind_dev.yml
```

What it does:

- Ensures a kind cluster named `spark-dev` exists and sets the context.
- Optionally (if `load_images` is set to `true` in the playbook) loads your local images into kind.
- Adds Helm repos for Spark Operator and JupyterHub.
- Deploys Spark Operator using:
  - `k8s/spark-operator/values-base.yaml`
  - `k8s/spark-operator/values-dev.yaml`
- Deploys JupyterHub using:
  - `k8s/jupyterhub/values-base.yaml`
  - `k8s/jupyterhub/values-dev.yaml`

### 3. Access JupyterHub and run a Spark job

After the playbook completes:

```bash
kubectl get pods -n jhub-dev
kubectl get pods -n spark-operator
```

To access JupyterHub in dev, you can use port-forwarding:

```bash
kubectl port-forward -n jhub-dev svc/proxy-public 8000:80
```

Then open `http://localhost:8000` in a browser and log in with any username and password `test`.

Inside a notebook, create a SparkSession that uses Spark-on-Kubernetes:

```python
from pyspark.sql import SparkSession

spark = (
    SparkSession.builder.appName("notebook-test")
    .master("k8s://https://kubernetes.default.svc")
    .config("spark.kubernetes.container.image", "statkube/spark-base:spark4.0.1-py3.12-1")
    .config("spark.kubernetes.authenticate.driver.serviceAccountName", "spark-sa")
    .getOrCreate()
)
```

### 4. Example SparkApplications

You can also submit jobs via the Spark Operator:

```bash
kubectl apply -f k8s/spark-apps/spark-pi.yaml
kubectl get sparkapplications
```

There is also a PySpark example in `k8s/spark-apps/pyspark-example.yaml`.

### 5. DST uv model and upgrades

- **No live upgrades with uv in notebooks for production-relevant packages**:
  - Notebooks, Spark driver and executors must use the same versions of internal packages such as `mydstlib`.
  - Do **not** run `uv pip install` in notebooks to upgrade these packages.
- **All production-relevant packages are baked into the Docker image**:
  - `docker/spark-base/requirements.txt` lists the approved Python packages.
  - The Dockerfile installs them via `uv pip install --system -r requirements.txt`.
- **Upgrade flow**:
  - A developer publishes a new version of an internal package (e.g. `mydstlib==1.4.0`) to the internal registry using uv in a build environment.
  - Platform/IT updates the `docker/spark-base` image (e.g. `RUN uv pip install mydstlib==1.4.0`) and builds a new tag.
  - The new image tag is referenced in:
    - JupyterHub values (`k8s/jupyterhub/values-*.yaml`) for the singleuser and hub images.
    - Spark Operator jobs (`k8s/spark-apps/*.yaml`) and any direct `spark-submit` configs.
  - JupyterHub and Spark Operator are redeployed with the new image versions, keeping notebook, CI and Spark cluster in sync.

### 6. Prod-like profile

The same charts and images can be used for a prod-like profile:

- Use `k8s/spark-operator/values-base.yaml` + `k8s/spark-operator/values-prodlike.yaml`.
- Use `k8s/jupyterhub/values-base.yaml` + `k8s/jupyterhub/values-prodlike.yaml`.
- Point images at your registry, e.g. `srvnexus1.dst.dk:18081/statkube/...`.

In a real production cluster you would additionally:

- Enable and configure ingress for JupyterHub.
- Replace dummy auth with OIDC/LDAP.
- Configure storage classes and secrets for S3/ADLS and other backends.


