#!/bin/bash
# Download Python source and uv binary for offline Docker builds
# Run this script when connected to the internet to refresh local copies

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SPARK_BASE_DIR="${SCRIPT_DIR}/../docker/spark-base"

PYTHON_VERSION="3.12.7"
UV_VERSION="0.5.5"

echo "Creating directories..."
mkdir -p "${SPARK_BASE_DIR}"

cd "${SPARK_BASE_DIR}"

echo ""
echo "Downloading Python ${PYTHON_VERSION} source..."
curl -LO "https://www.python.org/ftp/python/${PYTHON_VERSION}/Python-${PYTHON_VERSION}.tgz"

echo ""
echo "Downloading uv binary (linux-x86_64 for amd64 builds)..."
curl -LO "https://github.com/astral-sh/uv/releases/download/${UV_VERSION}/uv-x86_64-unknown-linux-gnu.tar.gz"

echo ""
echo "Downloading uv binary (linux-aarch64 for arm64 builds)..."
curl -LO "https://github.com/astral-sh/uv/releases/download/${UV_VERSION}/uv-aarch64-unknown-linux-gnu.tar.gz"

echo ""
echo "Downloaded files:"
ls -la Python-*.tgz uv-*.tar.gz 2>/dev/null || echo "Some files may not exist yet"

echo ""
echo "Done! Python source and uv binaries are ready for Docker build."
echo ""
echo "Build commands:"
echo "  For x86_64/amd64 (production, on-prem servers):"
echo "    docker build --platform linux/amd64 -t statkube/spark-base:spark3.5.3-py3.12-1 docker/spark-base/"
echo ""
echo "  For arm64 (Apple Silicon local dev):"
echo "    docker build --platform linux/arm64 -t statkube/spark-base:spark3.5.3-py3.12-1 docker/spark-base/"

