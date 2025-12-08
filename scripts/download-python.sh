#!/bin/bash
# Download Python source and uv binary for offline Docker builds
# Run this script when connected to the internet to refresh local copies
#
# Usage:
#   ./download-python.sh                    # Download from internet (python.org, GitHub)
#   ./download-python.sh --nexus            # Download from Nexus raw repo (on-prem)
#   RAW_REPO_URL=https://... ./download-python.sh  # Custom raw repo URL
#
# For on-prem, ensure these files are uploaded to your Nexus raw repository:
#   - Python-3.12.7.tgz
#   - spark-3.5.3-bin-hadoop3.tgz
#   - uv-x86_64-unknown-linux-gnu.tar.gz
#   - uv-aarch64-unknown-linux-gnu.tar.gz

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SPARK_BASE_DIR="${SCRIPT_DIR}/../docker/spark-base"

PYTHON_VERSION="3.12.7"
UV_VERSION="0.5.5"
SPARK_VERSION="3.5.3"

# Default: download from internet
USE_NEXUS=false

# Check for --nexus flag
if [[ "$1" == "--nexus" ]]; then
    USE_NEXUS=true
fi

# Nexus raw repository URL (override with RAW_REPO_URL environment variable)
NEXUS_RAW_URL="${RAW_REPO_URL:-https://srvnexus1.dst.dk/repository/raw-hosted}"

echo "Creating directories..."
mkdir -p "${SPARK_BASE_DIR}"

cd "${SPARK_BASE_DIR}"

if [[ "${USE_NEXUS}" == "true" ]]; then
    echo ""
    echo "Mode: On-prem Nexus"
    echo "Raw repository: ${NEXUS_RAW_URL}"
    echo ""
    
    echo "Downloading Python ${PYTHON_VERSION} source from Nexus..."
    curl -LO "${NEXUS_RAW_URL}/Python-${PYTHON_VERSION}.tgz"
    
    echo ""
    echo "Downloading Spark ${SPARK_VERSION} from Nexus..."
    curl -LO "${NEXUS_RAW_URL}/spark-${SPARK_VERSION}-bin-hadoop3.tgz"
    
    echo ""
    echo "Downloading uv binary (linux-x86_64) from Nexus..."
    curl -LO "${NEXUS_RAW_URL}/uv-x86_64-unknown-linux-gnu.tar.gz"
    
    echo ""
    echo "Downloading uv binary (linux-aarch64) from Nexus..."
    curl -LO "${NEXUS_RAW_URL}/uv-aarch64-unknown-linux-gnu.tar.gz"
else
    echo ""
    echo "Mode: Internet (direct download)"
echo ""
    
echo "Downloading Python ${PYTHON_VERSION} source..."
curl -LO "https://www.python.org/ftp/python/${PYTHON_VERSION}/Python-${PYTHON_VERSION}.tgz"
    
    echo ""
    echo "Downloading Spark ${SPARK_VERSION}..."
    curl -LO "https://archive.apache.org/dist/spark/spark-${SPARK_VERSION}/spark-${SPARK_VERSION}-bin-hadoop3.tgz"

echo ""
echo "Downloading uv binary (linux-x86_64 for amd64 builds)..."
curl -LO "https://github.com/astral-sh/uv/releases/download/${UV_VERSION}/uv-x86_64-unknown-linux-gnu.tar.gz"

echo ""
echo "Downloading uv binary (linux-aarch64 for arm64 builds)..."
curl -LO "https://github.com/astral-sh/uv/releases/download/${UV_VERSION}/uv-aarch64-unknown-linux-gnu.tar.gz"
fi

echo ""
echo "Downloaded files:"
ls -la Python-*.tgz spark-*.tgz uv-*.tar.gz 2>/dev/null || echo "Some files may not exist yet"

echo ""
echo "Done! Python source, Spark, and uv binaries are ready for Docker build."
