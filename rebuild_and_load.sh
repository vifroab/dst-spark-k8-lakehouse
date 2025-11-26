#!/bin/bash
set -e

echo "Building spark-notebook image (v12)..."
# Adjust path if running from subdirectory
docker build -t statkube/spark-notebook:spark3.5.3-py3.12-1-v12 -f docker/spark-notebook/Dockerfile docker/spark-notebook

echo "Loading image into Kind cluster 'spark-cluster'..."
kind load docker-image statkube/spark-notebook:spark3.5.3-py3.12-1-v12 --name spark-cluster

echo "Restarting JupyterHub singleuser pods..."
# Deleting the pods forces the statefulset/deployment to recreate them with the new image (if imagePullPolicy allows or if image changed)
# Since we updated values-base.yaml to v5, we should run helm upgrade or just update the deployment if we want to be quick.
# But running helm upgrade is safer to ensure config matches.

echo "Running Helm Upgrade to apply new image tag..."
# Check if we are in the root of the repo
if [ -f "k8s/jupyterhub/values-base.yaml" ]; then
    helm upgrade --install jhub jupyterhub/jupyterhub \
      --namespace jhub-dev \
      -f k8s/jupyterhub/values-base.yaml \
      -f k8s/jupyterhub/values-dev.yaml
else
    echo "Warning: Could not find k8s/jupyterhub/values-base.yaml. Skipping helm upgrade."
    echo "Please run 'helm upgrade' manually or ensure you are in the project root."
fi

# Force restart of any running singleuser pods to pick up changes immediately if helm doesn't trigger it (it should if image tag changed)
kubectl delete pods -n jhub-dev -l component=singleuser-server --ignore-not-found

echo "Done! Your new image with dst_metrics is ready."

