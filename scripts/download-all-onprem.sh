#!/bin/bash
# =============================================================================
# Download All Dependencies for On-Prem Deployment
# =============================================================================
# This script downloads all required files from Nexus for building Docker images.
# Run this AFTER verify-onprem-resources-on-server.sh passes.
#
# Usage:
#   ./scripts/download-all-onprem.sh
#
# Prerequisites:
#   - Nexus Maven proxy has the required JARs
#   - Nexus raw repository has Python, Spark, and uv files
#   - All checks pass in verify-onprem-resources-on-server.sh
#
# =============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="${SCRIPT_DIR}/.."

# =============================================================================
# CONFIGURATION - Update these for your environment
# =============================================================================
# Maven repository for JARs (flat structure with just filenames)
: "${MAVEN_REPO_URL:=https://srvnexus1.dst.dk/repository/apache-spark/spark-jars}"

# Raw repository for Python, Spark, uv downloads
: "${RAW_REPO_URL:=https://srvnexus1.dst.dk/repository/raw-hosted}"

# =============================================================================
# COLOR OUTPUT
# =============================================================================
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

info() { echo -e "${BLUE}ℹ${NC} $1"; }
success() { echo -e "${GREEN}✓${NC} $1"; }
warn() { echo -e "${YELLOW}⚠${NC} $1"; }
error() { echo -e "${RED}✗${NC} $1"; }

# =============================================================================
# MAIN
# =============================================================================

echo "=============================================="
echo "On-Prem Dependency Download"
echo "=============================================="
echo ""
echo "Configuration:"
echo "  Maven Repo (JARs): ${MAVEN_REPO_URL}"
echo "  Raw Repo (files):  ${RAW_REPO_URL}"
echo ""

# Check if raw repo URL is set to something useful
if [[ "${RAW_REPO_URL}" == *"raw-hosted"* ]]; then
    warn "Using default RAW_REPO_URL. Make sure your IT team has uploaded files to:"
    echo "    ${RAW_REPO_URL}"
    echo ""
    echo "  Required files in raw repo:"
    echo "    - Python-3.12.7.tgz"
    echo "    - spark-3.5.3-bin-hadoop3.tgz"
    echo "    - uv-x86_64-unknown-linux-gnu.tar.gz"
    echo "    - uv-aarch64-unknown-linux-gnu.tar.gz"
    echo ""
fi

# -----------------------------------------------------------------------------
# Download JARs from Nexus Maven proxy
# -----------------------------------------------------------------------------
info "Downloading JARs from Nexus Maven proxy..."
cd "${REPO_ROOT}"
MAVEN_REPO_URL="${MAVEN_REPO_URL}" ./scripts/download-jars.sh --nexus

if [ $? -eq 0 ]; then
    success "JARs downloaded successfully"
else
    error "Failed to download JARs"
    exit 1
fi

echo ""

# -----------------------------------------------------------------------------
# Download Python, Spark, uv from Nexus raw repo
# -----------------------------------------------------------------------------
info "Downloading Python, Spark, and uv from Nexus raw repo..."
cd "${REPO_ROOT}"
RAW_REPO_URL="${RAW_REPO_URL}" ./scripts/download-python.sh --nexus

if [ $? -eq 0 ]; then
    success "Python/Spark/uv downloaded successfully"
else
    error "Failed to download Python/Spark/uv files"
    warn "If raw repo is not available, copy these files manually to docker/spark-base/:"
    echo "    - Python-3.12.7.tgz"
    echo "    - spark-3.5.3-bin-hadoop3.tgz"
    echo "    - uv-x86_64-unknown-linux-gnu.tar.gz"
    exit 1
fi

echo ""

# -----------------------------------------------------------------------------
# Verify all files exist
# -----------------------------------------------------------------------------
info "Verifying downloaded files..."

SPARK_BASE="${REPO_ROOT}/docker/spark-base"
MISSING=0

check_file() {
    if [ -f "$1" ]; then
        success "Found: $(basename $1)"
    else
        error "Missing: $(basename $1)"
        MISSING=$((MISSING + 1))
    fi
}

check_file "${SPARK_BASE}/Python-3.12.7.tgz"
check_file "${SPARK_BASE}/spark-3.5.3-bin-hadoop3.tgz"
check_file "${SPARK_BASE}/uv-x86_64-unknown-linux-gnu.tar.gz"
check_file "${SPARK_BASE}/jars/hadoop-aws-3.3.4.jar"
check_file "${SPARK_BASE}/jars/aws-java-sdk-bundle-1.12.623.jar"
check_file "${SPARK_BASE}/jars/iceberg-spark-runtime-3.5_2.12-1.9.0.jar"
check_file "${SPARK_BASE}/jars/iceberg-aws-bundle-1.9.0.jar"
check_file "${SPARK_BASE}/jars/delta-spark_2.12-3.2.0.jar"
check_file "${SPARK_BASE}/jars/delta-storage-3.2.0.jar"

echo ""

if [ ${MISSING} -eq 0 ]; then
    echo "=============================================="
    success "All dependencies downloaded successfully!"
    echo "=============================================="
    echo ""
    echo "Next steps:"
    echo "  1. Build images:"
    echo "     docker build \\"
    echo "       --build-arg BASE_IMAGE=srvnexus1.dst.dk:18079/eclipse-temurin:11-jdk-jammy \\"
    echo "       -t srvnexus1.dst.dk:18079/statkube/spark-base:spark3.5.3-py3.12-1 \\"
    echo "       docker/spark-base/"
    echo ""
    echo "     docker build \\"
    echo "       --build-arg BASE_IMAGE=srvnexus1.dst.dk:18079/statkube/spark-base:spark3.5.3-py3.12-1 \\"
    echo "       -t srvnexus1.dst.dk:18079/statkube/spark-notebook:spark3.5.3-py3.12-1 \\"
    echo "       docker/spark-notebook/"
    echo ""
    echo "  2. Push to Nexus:"
    echo "     docker push srvnexus1.dst.dk:18079/statkube/spark-base:spark3.5.3-py3.12-1"
    echo "     docker push srvnexus1.dst.dk:18079/statkube/spark-notebook:spark3.5.3-py3.12-1"
    echo ""
    echo "  3. Deploy:"
    echo "     ansible-playbook ansible/playbooks/k3d_dev.yml -i ansible/inventory/onprem.yml"
else
    echo "=============================================="
    error "${MISSING} file(s) missing!"
    echo "=============================================="
    echo ""
    echo "Options:"
    echo "  1. Ask IT team to upload missing files to Nexus raw repo"
    echo "  2. Copy files manually from another machine"
    echo "  3. Use the full zip with all files included"
    exit 1
fi

