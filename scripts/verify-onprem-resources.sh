#!/bin/bash
# =============================================================================
# Resource Verification Script (Online & On-Prem)
# =============================================================================
# This script verifies that all required resources are available.
# Run this BEFORE attempting deployment.
#
# Usage:
#   # On-prem mode (default):
#   ./verify-onprem-resources.sh
#
#   # Online mode (test with internet access):
#   DOCKER_REGISTRY="skip" \
#   GHCR_REGISTRY="skip" \
#   HELM_REPO_URL="skip" \
#   MAVEN_REPO_URL="https://repo1.maven.org/maven2" \
#   ./verify-onprem-resources.sh
#
# Configuration Modes:
#   - On-prem (Nexus): Use the default configuration below
#   - Online (Internet): Override with environment variables as shown above
#
# The script auto-detects repository structure:
#   - Flat structure (Nexus spark-jars): Uses filename-only URLs
#   - Hierarchical structure (Maven Central): Uses org/group/artifact/version/file.jar
#
# Quick Switch Examples:
#   For testing with Maven Central (online):
#     MAVEN_REPO_URL="https://repo1.maven.org/maven2"
#   For on-prem Nexus (flat structure):
#     MAVEN_REPO_URL="https://srvnexus1.dst.dk/repository/apache-spark/spark-jars"
#   For on-prem Nexus (Maven proxy):
#     MAVEN_REPO_URL="https://srvnexus1.dst.dk/repository/maven-central"
# =============================================================================

set -e

# =============================================================================
# CONFIGURATION - UPDATE THESE FOR YOUR ENVIRONMENT
# =============================================================================
# All variables can be overridden by environment variables

# Docker registry (Nexus Docker proxy for Docker Hub images)
# Online: leave empty or set to "" to use Docker Hub directly
# On-prem: set to your Nexus Docker proxy (e.g., srvnexus1.dst.dk:18079)
: "${DOCKER_REGISTRY:=srvnexus1.dst.dk:18079}"

# GHCR registry (Nexus Docker proxy for ghcr.io images)
# Online: set to "ghcr.io"
# On-prem: set to your Nexus GHCR proxy
: "${GHCR_REGISTRY:=srvnexus1.dst.dk:18083}"

# Helm repository URL (Nexus Helm proxy)
# Online: not needed for direct Helm repo access
# On-prem: set to your Nexus Helm proxy
: "${HELM_REPO_URL:=https://srvnexus1.dst.dk:/repository/}"

# Maven repository URL (Nexus Maven proxy) - for JAR verification
# For flat JAR storage (just filenames): https://srvnexus1.dst.dk/repository/apache-spark/spark-jars
# For Maven standard layout: https://srvnexus1.dst.dk/repository/maven-central or https://repo1.maven.org/maven2
# The script will auto-detect which structure to use based on the URL
# Can be overridden by setting MAVEN_REPO_URL environment variable
: "${MAVEN_REPO_URL:=https://srvnexus1.dst.dk/repository/apache-spark/spark-jars}"

# Auto-detect repository structure based on URL
# Flat structure: URLs containing "spark-jars" or other indicators
# Hierarchical structure: Maven Central, Nexus maven-central, etc.
if [[ "${MAVEN_REPO_URL}" == *"spark-jars"* ]]; then
    USE_FLAT_MAVEN_STRUCTURE=true
else
    USE_FLAT_MAVEN_STRUCTURE=false
fi

# =============================================================================
# REQUIRED DOCKER IMAGES (Docker Hub via Nexus)
# =============================================================================
DOCKER_IMAGES=(
    "eclipse-temurin:11-jdk-jammy"
    "busybox:1.36"
    "minio/minio:RELEASE.2024-11-07T00-52-20Z"
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
    "jupyter-hub"
)

# =============================================================================
# REQUIRED MAVEN JARS
# =============================================================================
# Define JAR filenames and their Maven paths
# The script will automatically use the appropriate structure
MAVEN_JAR_NAMES=(
    "hadoop-aws-3.3.4.jar"
    "aws-java-sdk-bundle-1.12.623.jar"
    "iceberg-spark-runtime-3.5_2.12-1.9.0.jar"
    "iceberg-aws-bundle-1.9.0.jar"
    "delta-spark_2.12-3.2.0.jar"
    "delta-storage-3.2.0.jar"
)

MAVEN_JAR_PATHS=(
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
    if [[ -n "${DOCKER_REGISTRY}" && "${DOCKER_REGISTRY}" != "skip" ]]; then
    section "Verifying Docker Hub Images from ${DOCKER_REGISTRY}"
    else
        section "Verifying Docker Hub Images (direct access)"
    fi
    
    for image in "${DOCKER_IMAGES[@]}"; do
        if [[ -n "${DOCKER_REGISTRY}" && "${DOCKER_REGISTRY}" != "skip" ]]; then
        full_image="${DOCKER_REGISTRY}/${image}"
        else
            full_image="${image}"
        fi
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
    if [[ -n "${GHCR_REGISTRY}" && "${GHCR_REGISTRY}" != "skip" ]]; then
    section "Verifying GHCR Images from ${GHCR_REGISTRY}"
    else
        section "Verifying GHCR Images (direct from ghcr.io)"
    fi
    info "These images are from ghcr.io (GitHub Container Registry)"
    
    for image in "${GHCR_IMAGES[@]}"; do
        if [[ -n "${GHCR_REGISTRY}" && "${GHCR_REGISTRY}" != "skip" ]]; then
        full_image="${GHCR_REGISTRY}/${image}"
        else
            full_image="ghcr.io/${image}"
        fi
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
    if [[ -z "${HELM_REPO_URL}" || "${HELM_REPO_URL}" == "skip" ]]; then
        section "Skipping Helm Chart Verification"
        info "Helm charts available from public repos:"
        info "  - Spark Operator: https://kubeflow.github.io/spark-operator"
        info "  - JupyterHub: https://jupyterhub.github.io/helm-chart/"
        return 0
    fi
    
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
    
    if [[ "${USE_FLAT_MAVEN_STRUCTURE}" == "true" ]]; then
        info "Using flat repository structure (filename-only)"
    else
        info "Using hierarchical Maven repository structure"
    fi
    
    # Iterate through JAR arrays using index
    for i in "${!MAVEN_JAR_NAMES[@]}"; do
        jar_name="${MAVEN_JAR_NAMES[$i]}"
        maven_path="${MAVEN_JAR_PATHS[$i]}"
        echo -n "  Checking ${jar_name}... "
        
        if [[ "${USE_FLAT_MAVEN_STRUCTURE}" == "true" ]]; then
            # Flat structure: just use filename
            jar_url="${MAVEN_REPO_URL}/${jar_name}"
        else
            # Hierarchical structure: use full Maven path
            jar_url="${MAVEN_REPO_URL}/${maven_path}"
        fi
        
        if curl -sf -I "${jar_url}" > /dev/null 2>&1; then
            pass "${jar_name}"
        else
            fail "${jar_name} - not found at ${jar_url}"
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
echo "  Docker Registry:     ${DOCKER_REGISTRY}"
echo "  GHCR Registry:       ${GHCR_REGISTRY}"
echo "  Helm Repo URL:       ${HELM_REPO_URL}"
echo "  Maven Repo URL:      ${MAVEN_REPO_URL}"
if [[ "${USE_FLAT_MAVEN_STRUCTURE}" == "true" ]]; then
    echo "  Maven Structure:     flat (filename-only)"
else
    echo "  Maven Structure:     hierarchical (standard Maven)"
fi
echo ""
info "To test with Maven Central (online), change MAVEN_REPO_URL to: https://repo1.maven.org/maven2"
warn "Update the configuration variables at the top of this script for your environment"

verify_docker_images
verify_ghcr_images
verify_helm_charts
verify_maven_jars
verify_external_downloads
verify_pypi_packages
print_summary

exit ${FAILURES}

