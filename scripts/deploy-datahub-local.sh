#!/bin/bash
set -e

echo "=== Deploying DataHub to Local k3d Cluster ==="
echo ""

# 1. Add DataHub Helm repo
echo "Adding DataHub Helm repo..."
helm repo add datahub https://helm.datahubproject.io/
helm repo update

# 2. Create namespace
echo "Creating datahub namespace..."
kubectl create namespace datahub --dry-run=client -o yaml | kubectl apply -f -

# 3. Create MySQL secret (required by charts)
echo "Creating MySQL secrets..."
kubectl create secret generic mysql-secrets \
  --from-literal=mysql-root-password=datahub \
  --namespace datahub \
  --dry-run=client -o yaml | kubectl apply -f -

# 4. Install Prerequisites (MySQL, Elasticsearch, Kafka)
echo "Installing DataHub Prerequisites..."
helm upgrade --install prerequisites datahub/datahub-prerequisites \
  --namespace datahub \
  -f k8s/datahub/prerequisites-values.yaml \
  --wait \
  --timeout 10m

echo "Waiting for Elasticsearch to be ready..."
kubectl wait --for=condition=ready pod -l app=elasticsearch-master -n datahub --timeout=300s

# 5. Install DataHub Core
echo "Installing DataHub Core..."
helm upgrade --install datahub datahub/datahub \
  --namespace datahub \
  -f k8s/datahub/values-base.yaml \
  -f k8s/datahub/values-dev.yaml \
  --wait \
  --timeout 15m

echo ""
echo "✅ DataHub Deployed Successfully!"
echo ""
echo "To access DataHub:"
echo "  kubectl port-forward svc/datahub-datahub-frontend -n datahub 9002:9002"
echo ""
echo "  URL: http://localhost:9002"
echo "  Username: datahub"
echo "  Password: datahub"

