#!/bin/bash
set -e

CLUSTER_NAME="${K3D_CLUSTER_NAME:-spark-cluster}"
IMAGE_TAG="${IMAGE_TAG:-spark3.5.3-py3.12-1}"

echo "=== Rebuild and Load Images for k3d ==="
echo "Cluster: $CLUSTER_NAME"
echo "Image tag: $IMAGE_TAG"
echo ""

# Check if k3d cluster exists
if ! k3d cluster list | grep -q "$CLUSTER_NAME"; then
    echo "Error: k3d cluster '$CLUSTER_NAME' not found."
    echo "Create it first with: ansible-playbook ansible/playbooks/k3d_dev.yml -i ansible/inventory/internet.yml"
    exit 1
fi

# Build images
echo "Building spark-base image..."
docker build \
  -t statkube/spark-base:$IMAGE_TAG \
  --build-arg USE_NEXUS_APT=false \
  --build-arg UV_INDEX_URL=https://pypi.org/simple \
  -f docker/spark-base/Dockerfile docker/spark-base

echo ""
echo "Building spark-notebook image..."
docker build -t statkube/spark-notebook:$IMAGE_TAG -f docker/spark-notebook/Dockerfile docker/spark-notebook

echo ""
echo "Building jupyterhub-hub image..."
docker build -t statkube/jupyterhub-hub:$IMAGE_TAG -f docker/jupyterhub-hub/Dockerfile docker/jupyterhub-hub

# Load images into k3d
echo ""
echo "Loading spark-base image into k3d cluster '$CLUSTER_NAME'..."
k3d image import statkube/spark-base:$IMAGE_TAG -c $CLUSTER_NAME

echo ""
echo "Loading spark-notebook image into k3d cluster '$CLUSTER_NAME'..."
k3d image import statkube/spark-notebook:$IMAGE_TAG -c $CLUSTER_NAME

echo ""
echo "Loading jupyterhub-hub image into k3d cluster '$CLUSTER_NAME'..."
k3d image import statkube/jupyterhub-hub:$IMAGE_TAG -c $CLUSTER_NAME

# Run Helm upgrade
echo ""
echo "Running Helm Upgrade to apply image..."
if [ -f "k8s/jupyterhub/values-base.yaml" ]; then
    helm upgrade --install jhub jupyterhub/jupyterhub \
      --namespace jhub-dev \
      -f k8s/jupyterhub/values-base.yaml \
      -f k8s/jupyterhub/values-k3d.yaml
else
    echo "Warning: Could not find k8s/jupyterhub/values-base.yaml. Skipping helm upgrade."
    echo "Please run 'helm upgrade' manually or ensure you are in the project root."
fi

# Force restart of any running singleuser pods
echo ""
echo "Restarting JupyterHub singleuser pods..."
kubectl delete pods -n jhub-dev -l component=singleuser-server --ignore-not-found

echo ""
echo "✅ Done! Images rebuilt and loaded into k3d."
echo ""
echo "Access JupyterHub at: http://localhost:8080"
echo "Login: any username / password: test"
