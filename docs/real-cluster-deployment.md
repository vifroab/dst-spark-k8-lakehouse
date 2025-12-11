# Real Kubernetes Cluster Deployment Guide

This guide covers deploying the Spark K8s Hub on a **real Kubernetes cluster** (not k3d/kind dev environments). Use this when deploying to production or staging environments on-premises.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                              KUBERNETES CLUSTER                                     │
│                                                                                     │
│  ┌─────────────────────────────────────────────────────────────────────────────┐    │
│  │                         INGRESS CONTROLLER                                  │    │
│  │                    (nginx-ingress / Traefik)                                │    │
│  │                                                                             │    │
│  │   jupyter.dst.dk ──► JupyterHub    datahub.dst.dk ──► DataHub Frontend      │    │
│  └─────────────────────────────────────────────────────────────────────────────┘    │
│                                        │                                            │
│         ┌──────────────────────────────┴──────────────────────────────┐             │
│         │                                                             │             │
│         ▼                                                              ▼            │
│  ┌──────────────────────────────────┐    ┌─────────────────────────────────────┐    │
│  │     NAMESPACE: jhub              │    │      NAMESPACE: datahub             │    │
│  │  ┌────────────────────────────┐  │    │  ┌──────────────────────────────┐   │    │
│  │  │      JupyterHub            │  │    │  │     DataHub Frontend         │   │    │
│  │  │  ┌──────────────────────┐  │  │    │  │     DataHub GMS              │   │    │
│  │  │  │   Hub (k8s-hub)      │  │  │    │  │     MAE/MCE Consumers        │   │    │
│  │  │  │   Proxy              │  │  │    │  └──────────────────────────────┘   │    │
│  │  │  └──────────────────────┘  │  │    │  ┌──────────────────────────────┐   │    │
│  │  │  ┌──────────────────────┐  │  │    │  │   Prerequisites:             │   │    │
│  │  │  │  User Notebook Pods  │──┼──┼────┼──│   • MySQL                    │   │    │
│  │  │  │  (spark-notebook)    │  │  │    │  │   • Elasticsearch            │   │    │
│  │  │  │                      │  │  │    │  │   • Kafka + Schema Registry  │   │    │
│  │  │  │  ServiceAccount:     │  │  │    │  └──────────────────────────────┘   │    │
│  │  │  │  spark-sa            │  │  │    └─────────────────────────────────────┘    │
│  │  │  └──────────┬───────────┘  │  │                                               │
│  │  └─────────────┼──────────────┘  │                                               │
│  └────────────────┼─────────────────┘                                               │
│                   │                                                                 │
│                   │ Spark Submit (K8s native)                                       │
│                   ▼                                                                 │
│  ┌──────────────────────────────────┐    ┌─────────────────────────────────────┐    │
│  │   NAMESPACE: spark-operator      │    │      NAMESPACE: default             │    │
│  │  ┌────────────────────────────┐  │    │  ┌──────────────────────────────┐   │    │
│  │  │    Spark Operator          │  │    │  │   Spark Driver Pod           │   │    │
│  │  │    (watches SparkApps)     │◄─┼────┼──│   Spark Executor Pods        │   │    │
│  │  └────────────────────────────┘  │    │  │   (dynamically created)      │   │    │
│  └──────────────────────────────────┘    │  └──────────────────────────────┘   │    │
│                                          └─────────────────────────────────────┘    │
│                                                                                     │
│  ┌──────────────────────────────────┐    ┌─────────────────────────────────────┐    │
│  │     NAMESPACE: polaris           │    │      NAMESPACE: minio               │    │
│  │  ┌────────────────────────────┐  │    │  ┌──────────────────────────────┐   │    │
│  │  │    Apache Polaris          │◄─┼────┼──│       MinIO                  │   │    │
│  │  │    (Iceberg REST Catalog)  │  │    │  │   (S3-compatible storage)    │   │    │
│  │  │                            │  │    │  │                              │   │    │
│  │  │    :8181 - API             │  │    │  │   :9000 - S3 API             │   │    │
│  │  │    :8182 - Management      │  │    │  │   :9001 - Console            │   │    │
│  │  └────────────────────────────┘  │    │  │                              │   │    │
│  └──────────────────────────────────┘    │  │   PVC: minio-pvc (10Gi)      │   │    │
│                                          │  └──────────────────────────────┘   │    │
│                                          └─────────────────────────────────────┘    │
│                                                                                     │
└─────────────────────────────────────────────────────────────────────────────────────┘
                                          │
                                          │ Pull images
                                          ▼
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                           NEXUS REPOSITORY (srvnexus1.dst.dk)                       │
│                                                                                     │
│   :18079 (Docker Hub proxy)          :18083 (GHCR proxy)                            │
│   • jupyterhub/k8s-hub               • googlecloudplatform/spark-operator           │
│   • statkube/spark-base                                                             │
│   • statkube/spark-notebook          Helm repos:                                    │
│   • minio/minio                      • /repository/spark-operator                   │
│   • apache/polaris                   • /repository/jupyterhub                       │
│   • acryldata/datahub-*              • /repository/datahub                          │
│                                                                                     │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

### Data Flow

```
┌─────────────┐      ┌─────────────┐      ┌─────────────┐      ┌─────────────┐
│   User      │      │ JupyterHub  │      │   Spark     │      │   MinIO     │
│  Browser    │─────►│  Notebook   │─────►│  Driver +   │─────►│   (S3)      │
│             │      │             │      │  Executors  │      │             │
└─────────────┘      └─────────────┘      └──────┬──────┘      └─────────────┘
                                                 │
                                                 │ Iceberg metadata
                                                 ▼
                                          ┌─────────────┐
                                          │   Polaris   │
                                          │  (Catalog)  │
                                          └──────┬──────┘
                                                 │
                                                 │ Lineage (optional)
                                                 ▼
                                          ┌─────────────┐
                                          │   DataHub   │
                                          │  (Metadata) │
                                          └─────────────┘
```

### Namespaces & Services Summary

| Namespace | Service | Port | Purpose |
|-----------|---------|------|---------|
| `jhub` | proxy-public | 80 | JupyterHub entry point |
| `jhub` | hub | 8081 | JupyterHub hub service |
| `spark-operator` | spark-operator | - | Watches SparkApplication CRDs |
| `minio` | minio | 9000, 9001 | S3 API + Web Console |
| `polaris` | polaris | 8181, 8182 | REST Catalog API + Management |
| `datahub` | datahub-frontend | 9002 | DataHub UI |
| `datahub` | datahub-gms | 8080 | DataHub Metadata Service |
| `default` | - | - | Spark driver/executor pods run here |

### RBAC & Service Accounts

```
┌─────────────────────────────────────────────────────────────────┐
│  ServiceAccount: spark-sa                                        │
│                                                                  │
│  Created in: jhub, default namespaces                           │
│                                                                  │
│  Permissions (via spark-rbac.yaml):                             │
│  • Create/delete pods (for Spark executors)                     │
│  • Create/delete services                                        │
│  • Create/delete configmaps                                      │
│  • Watch pods and services                                       │
└─────────────────────────────────────────────────────────────────┘
```

---

## Migration Checklist

### Phase 1: Infrastructure Prerequisites

- [ ] **Nexus Docker Hub proxy** available at `srvnexus1.dst.dk:18079`
- [ ] **Nexus GHCR proxy** available at `srvnexus1.dst.dk:18083`
- [ ] **Nexus hosted registry** for custom images (confirm port with IT - likely 18080)
- [ ] **Helm repos in Nexus** configured:
  - [ ] `spark-operator` proxy for `https://kubeflow.github.io/spark-operator`
  - [ ] `jupyterhub` proxy for `https://jupyterhub.github.io/helm-chart/`
  - [ ] `datahub` proxy for `https://helm.datahubproject.io/`
- [ ] **Run verification script**: `./verify-onprem-resources-on-server.sh` (all green)

### Phase 2: Kubernetes Cluster Requirements

- [ ] `kubectl` configured with real cluster access
- [ ] Helm 3.x installed
- [ ] **StorageClass** available for persistent volumes (e.g., Ceph, NFS)
- [ ] **Ingress Controller** deployed (nginx-ingress, Traefik, etc.)
- [ ] DNS configured for JupyterHub domain (e.g., `jupyter.dst.dk`)

### Phase 3: Build & Push Custom Docker Images

- [ ] Download build dependencies:
  ```bash
  ./scripts/download-all-onprem.sh
  ```
- [ ] Build `spark-base`:
  ```bash
  docker build \
    --build-arg BASE_IMAGE=srvnexus1.dst.dk:18079/eclipse-temurin:11-jdk-jammy \
    -t srvnexus1.dst.dk:18079/statkube/spark-base:spark3.5.3-py3.12-1 \
    -f docker/spark-base/Dockerfile \
    docker/spark-base/
  ```
- [ ] Build `spark-notebook`:
  ```bash
  docker build \
    --build-arg BASE_IMAGE=srvnexus1.dst.dk:18079/statkube/spark-base:spark3.5.3-py3.12-1 \
    -t srvnexus1.dst.dk:18079/statkube/spark-notebook:spark3.5.3-py3.12-1 \
    -f docker/spark-notebook/Dockerfile \
    docker/spark-notebook/
  ```
- [ ] Push to Nexus hosted registry:
  ```bash
  docker push srvnexus1.dst.dk:18079/statkube/spark-base:spark3.5.3-py3.12-1
  docker push srvnexus1.dst.dk:18079/statkube/spark-notebook:spark3.5.3-py3.12-1
  ```

### Phase 4: Create Production Configuration Files

- [ ] Create `k8s/jupyterhub/values-prod.yaml` (see template below)
- [ ] Create `k8s/jupyterhub/ingress-prod.yaml` for your ingress controller
- [ ] Review and update secrets (don't use dev passwords in production!)

### Phase 5: Deploy Components

- [ ] **Add Helm repos** (via Nexus):
  ```bash
  helm repo add spark-operator https://srvnexus1.dst.dk/repository/spark-operator
  helm repo add jupyterhub https://srvnexus1.dst.dk/repository/jupyterhub
  helm repo add datahub https://srvnexus1.dst.dk/repository/datahub
  helm repo update
  ```

- [ ] **Deploy Spark Operator**:
  ```bash
  helm upgrade --install spark-operator spark-operator/spark-operator \
    --version 1.1.27 \
    -n spark-operator --create-namespace \
    -f k8s/spark-operator/values-base.yaml \
    -f k8s/spark-operator/values-onprem.yaml
  ```

- [ ] **Deploy MinIO**:
  ```bash
  kubectl apply -f k8s/minio/minio-onprem.yaml
  kubectl wait --for=condition=available deployment/minio -n minio --timeout=120s
  ```

- [ ] **Deploy Polaris**:
  ```bash
  kubectl apply -f k8s/polaris/polaris-onprem.yaml
  kubectl wait --for=condition=available deployment/polaris -n polaris --timeout=120s
  kubectl delete job polaris-bootstrap-catalog -n polaris --ignore-not-found
  kubectl apply -f k8s/polaris/polaris-bootstrap-onprem.yaml
  ```

- [ ] **Deploy JupyterHub**:
  ```bash
  helm upgrade --install jhub jupyterhub/jupyterhub \
    -n jhub --create-namespace \
    -f k8s/jupyterhub/values-base.yaml \
    -f k8s/jupyterhub/values-onprem.yaml \
    -f k8s/jupyterhub/values-prod.yaml
  ```

- [ ] **Create Service Accounts & RBAC**:
  ```bash
  kubectl apply -f k8s/jupyterhub/service-account.yaml
  kubectl apply -f k8s/jupyterhub/spark-rbac.yaml
  kubectl create serviceaccount spark-sa --namespace default --dry-run=client -o yaml | kubectl apply -f -
  ```

- [ ] **Deploy Ingress**:
  ```bash
  kubectl apply -f k8s/jupyterhub/ingress-prod.yaml
  ```

- [ ] **Deploy DataHub** (optional):
  ```bash
  kubectl create namespace datahub
  kubectl create secret generic mysql-secrets \
    --from-literal=mysql-root-password=<SECURE-PASSWORD> \
    --namespace datahub
  
  helm upgrade --install prerequisites datahub/datahub-prerequisites \
    --namespace datahub \
    -f k8s/datahub/prerequisites-values.yaml \
    --timeout 10m --wait
  
  kubectl wait --for=condition=ready pod -l app=elasticsearch-master -n datahub --timeout=300s
  
  helm upgrade --install datahub datahub/datahub \
    --namespace datahub \
    -f k8s/datahub/values-base.yaml \
    -f k8s/datahub/values-onprem.yaml \
    --timeout 15m --wait
  ```

### Phase 6: Verification

- [ ] All pods running:
  ```bash
  kubectl get pods -n spark-operator
  kubectl get pods -n minio
  kubectl get pods -n polaris
  kubectl get pods -n jhub
  kubectl get pods -n datahub  # if deployed
  ```
- [ ] Ingress configured correctly:
  ```bash
  kubectl get ingress -A
  ```
- [ ] JupyterHub accessible via browser
- [ ] Test Spark job from JupyterHub notebook
- [ ] Polaris catalog accessible from Spark

---

## Key Differences: k3d vs Real Cluster

| Aspect | k3d (Dev) | Real Cluster (On-Prem) |
|--------|-----------|------------------------|
| **Images** | `k3d image import` | Must be in Nexus hosted registry |
| **Ingress** | k3d LoadBalancer + Traefik | Real Ingress Controller |
| **Storage** | Local path provisioner | Real StorageClass |
| **Playbook** | `k3d_dev.yml` | Manual steps (this guide) |
| **Security** | `xsrf_cookies: false` | **Enable XSRF protection** |

---

## Configuration Templates

### `k8s/jupyterhub/values-prod.yaml`

```yaml
# Production JupyterHub values
# Layer on top of values-base.yaml + values-onprem.yaml

proxy:
  service:
    type: ClusterIP  # Use Ingress for external access

hub:
  baseUrl: "/"  # Adjust to your ingress path
  config:
    JupyterHub:
      # ENABLE XSRF protection in production!
      tornado_settings:
        xsrf_cookies: true

singleuser:
  # Production resource limits
  memory:
    limit: 4G
    guarantee: 1G
  cpu:
    limit: 2
    guarantee: 0.5
  # Enable persistent storage
  storage:
    type: dynamic
    capacity: 10Gi
    # storageClass: your-storage-class  # Uncomment and set
  networkPolicy:
    enabled: true

# Enable image pre-pulling for faster spawns
prePuller:
  hook:
    enabled: true
  continuous:
    enabled: true
```

### `k8s/jupyterhub/ingress-prod.yaml` (nginx-ingress example)

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: jupyterhub-ingress
  namespace: jhub
  annotations:
    nginx.ingress.kubernetes.io/proxy-body-size: "64m"
spec:
  ingressClassName: nginx
  rules:
  - host: jupyter.your-domain.dk
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: proxy-public
            port:
              number: 80
  # Optional: TLS
  # tls:
  # - hosts:
  #   - jupyter.your-domain.dk
  #   secretName: jupyter-tls
```

---

## Troubleshooting

### Image Pull Errors
```bash
# Check pod events
kubectl describe pod <pod-name> -n <namespace>

# Verify image is accessible
crictl pull srvnexus1.dst.dk:18079/statkube/spark-notebook:spark3.5.3-py3.12-1
```

### Storage Issues
```bash
# Check available storage classes
kubectl get storageclass

# Check PVC status
kubectl get pvc -A
```

### Ingress Issues
```bash
# Check ingress controller logs
kubectl logs -n ingress-nginx -l app.kubernetes.io/name=ingress-nginx

# Verify service endpoints
kubectl get endpoints -n jhub
```

---

## Security Reminders

> ⚠️ **Before going to production:**
> - [ ] Change default passwords (MinIO: `admin/password`, Polaris: `root/s3cr3t`)
> - [ ] Enable TLS on ingress
> - [ ] Configure proper authentication (replace DummyAuthenticator)
> - [ ] Review network policies
> - [ ] Enable XSRF cookies (`xsrf_cookies: true`)

