#!/bin/bash
# =============================================================================
# On-Prem Resource Verification Script
# =============================================================================
# This script verifies that all required resources are available in the
# on-prem Nexus environment. Run this BEFORE attempting deployment.
#
# Usage:
#   ./verify-onprem-resources.sh
#
# Configuration:
#   Edit the variables below to match your Nexus setup
# =============================================================================

set -e

# =============================================================================
# CONFIGURATION - UPDATE THESE FOR YOUR ENVIRONMENT
# =============================================================================

# Docker registry (Nexus Docker proxy for Docker Hub images)
DOCKER_REGISTRY="srvnexus1:80888"

# GHCR registry (Nexus Docker proxy for ghcr.io images)
GHCR_REGISTRY="srvnexus1:CHANGEME"

# Helm repository URL (Nexus Helm proxy)
HELM_REPO_URL="https://srvnexus1:CHANGEME/repository/helm-hosted"

# Maven repository URL (Nexus Maven proxy) - for JAR verification
MAVEN_REPO_URL="https://srvnexus1:CHANGEME/repository/maven-central"

# =============================================================================
# REQUIRED DOCKER IMAGES (Docker Hub via Nexus)
# =============================================================================
DOCKER_IMAGES=(
    "eclipse-temurin:11-jdk-jammy"
    "busybox:1.36"
    "minio/minio:latest"
    "apache/polaris:latest"
    "jupyterhub/k8s-hub:4.3.1"
)

# =============================================================================
# REQUIRED GHCR IMAGES (ghcr.io via Nexus)
# =============================================================================
GHCR_IMAGES=(
    "googlecloudplatform/spark-operator:v1beta2-1.3.8-3.1.1"
)

# =============================================================================
# REQUIRED HELM CHARTS
# =============================================================================
HELM_CHARTS=(
    "spark-operator"
    "jupyterhub"
)

# =============================================================================
# REQUIRED MAVEN JARS
# =============================================================================
MAVEN_JARS=(
    "org/apache/hadoop/hadoop-aws/3.3.4/hadoop-aws-3.3.4.jar"
    "com/amazonaws/aws-java-sdk-bundle/1.12.623/aws-java-sdk-bundle-1.12.623.jar"
    "org/apache/iceberg/iceberg-spark-runtime-3.5_2.12/1.9.0/iceberg-spark-runtime-3.5_2.12-1.9.0.jar"
    "org/apache/iceberg/iceberg-aws-bundle/1.9.0/iceberg-aws-bundle-1.9.0.jar"
    "io/delta/delta-spark_2.12/3.2.0/delta-spark_2.12-3.2.0.jar"
    "io/delta/delta-storage/3.2.0/delta-storage-3.2.0.jar"
)

# =============================================================================
# REQUIRED PYTHON PACKAGES (PyPI)
# =============================================================================
PYPI_PACKAGES=(
    "pyspark==3.5.3"
    "pandas==2.2.3"
    "numpy==2.1.2"
    "pyarrow==18.0.0"
    "jupyterlab"
    "jupyterhub"
    "jupyterlab-git"
)

# =============================================================================
# REQUIRED EXTERNAL DOWNLOADS
# =============================================================================
EXTERNAL_URLS=(
    "https://www.python.org/ftp/python/3.12.7/Python-3.12.7.tgz"
    "https://github.com/astral-sh/uv/releases/download/0.5.5/uv-x86_64-unknown-linux-gnu.tar.gz"
    "https://archive.apache.org/dist/spark/spark-3.5.3/spark-3.5.3-bin-hadoop3.tgz"
)

# =============================================================================
# COLOR OUTPUT
# =============================================================================
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

pass() { echo -e "${GREEN}✓ PASS${NC}: $1"; }
fail() { echo -e "${RED}✗ FAIL${NC}: $1"; FAILURES=$((FAILURES + 1)); }
warn() { echo -e "${YELLOW}⚠ WARN${NC}: $1"; }
info() { echo -e "${BLUE}ℹ INFO${NC}: $1"; }
section() { echo -e "\n${BLUE}=== $1 ===${NC}"; }

FAILURES=0

# =============================================================================
# VERIFICATION FUNCTIONS
# =============================================================================

verify_docker_images() {
    section "Verifying Docker Hub Images from ${DOCKER_REGISTRY}"
    
    for image in "${DOCKER_IMAGES[@]}"; do
        full_image="${DOCKER_REGISTRY}/${image}"
        echo -n "  Checking ${image}... "
        
        if docker manifest inspect "${full_image}" > /dev/null 2>&1; then
            pass "${image}"
        else
            # Try with docker pull (slower but more reliable)
            if docker pull "${full_image}" > /dev/null 2>&1; then
                pass "${image}"
            else
                fail "${image} - not found in registry"
            fi
        fi
    done
}

verify_ghcr_images() {
    section "Verifying GHCR Images from ${GHCR_REGISTRY}"
    info "These images are from ghcr.io (GitHub Container Registry)"
    
    for image in "${GHCR_IMAGES[@]}"; do
        full_image="${GHCR_REGISTRY}/${image}"
        echo -n "  Checking ${image}... "
        
        if docker manifest inspect "${full_image}" > /dev/null 2>&1; then
            pass "${image}"
        else
            # Try with docker pull (slower but more reliable)
            if docker pull "${full_image}" > /dev/null 2>&1; then
                pass "${image}"
            else
                fail "${image} - not found in GHCR registry"
            fi
        fi
    done
    
    info "Original source: ghcr.io/googlecloudplatform/spark-operator:v1beta2-1.3.8-3.1.1"
}

verify_helm_charts() {
    section "Verifying Helm Charts from ${HELM_REPO_URL}"
    
    for chart in "${HELM_CHARTS[@]}"; do
        echo -n "  Checking ${chart}... "
        
        # Try to search for the chart in the repo
        if curl -sf "${HELM_REPO_URL}/${chart}/index.yaml" > /dev/null 2>&1 || \
           curl -sf "${HELM_REPO_URL}/index.yaml" 2>/dev/null | grep -q "${chart}"; then
            pass "${chart}"
        else
            fail "${chart} - not found in Helm repo"
        fi
    done
    
    info "Manual verification: helm repo add test-repo ${HELM_REPO_URL} && helm search repo test-repo"
}

verify_maven_jars() {
    section "Verifying Maven JARs from ${MAVEN_REPO_URL}"
    
    for jar in "${MAVEN_JARS[@]}"; do
        jar_name=$(basename "${jar}")
        echo -n "  Checking ${jar_name}... "
        
        if curl -sf -I "${MAVEN_REPO_URL}/${jar}" > /dev/null 2>&1; then
            pass "${jar_name}"
        else
            fail "${jar_name} - not found in Maven repo"
        fi
    done
}

verify_external_downloads() {
    section "Verifying External Downloads"
    info "These files should be pre-downloaded and stored locally or in Nexus raw repo"
    
    for url in "${EXTERNAL_URLS[@]}"; do
        filename=$(basename "${url}")
        echo "  Required: ${filename}"
        echo "    Source: ${url}"
    done
    
    echo ""
    info "Download these files and place in docker/spark-base/:"
    echo "    - Python-3.12.7.tgz"
    echo "    - uv-x86_64-unknown-linux-gnu.tar.gz"
    echo "    - spark-3.5.3-bin-hadoop3.tgz (already in repo)"
    echo "    - jars/*.jar (use scripts/download-jars.sh)"
}

verify_pypi_packages() {
    section "Required PyPI Packages"
    info "These are pre-baked into Docker images via requirements.txt"
    info "If using Nexus PyPI proxy, ensure these packages are cached:"
    
    for pkg in "${PYPI_PACKAGES[@]}"; do
        echo "  - ${pkg}"
    done
}

print_summary() {
    section "SUMMARY"
    
    if [ ${FAILURES} -eq 0 ]; then
        echo -e "${GREEN}All automated checks passed!${NC}"
    else
        echo -e "${RED}${FAILURES} check(s) failed!${NC}"
    fi
    
    echo ""
    echo "Manual verification checklist:"
    echo "  [ ] Docker Hub images accessible from ${DOCKER_REGISTRY}"
    echo "  [ ] GHCR images (Spark Operator) accessible from ${GHCR_REGISTRY}"
    echo "  [ ] Helm charts accessible from ${HELM_REPO_URL}"
    echo "  [ ] Maven JARs accessible from ${MAVEN_REPO_URL}"
    echo "  [ ] APT sources.list configured for Nexus APT proxy"
    echo "  [ ] Pre-downloaded files available (Python, uv, Spark, JARs)"
    echo ""
    echo "For detailed instructions, see: docs/onprem-deployment.md"
}

# =============================================================================
# MAIN
# =============================================================================

echo "=============================================="
echo "On-Prem Resource Verification"
echo "=============================================="
echo ""
echo "Configuration:"
echo "  Docker Registry: ${DOCKER_REGISTRY}"
echo "  GHCR Registry:   ${GHCR_REGISTRY}"
echo "  Helm Repo URL:   ${HELM_REPO_URL}"
echo "  Maven Repo URL:  ${MAVEN_REPO_URL}"
echo ""
warn "Update the configuration variables at the top of this script for your environment"

verify_docker_images
verify_ghcr_images
verify_helm_charts
verify_maven_jars
verify_external_downloads
verify_pypi_packages
print_summary

exit ${FAILURES}

