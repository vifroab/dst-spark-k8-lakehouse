#!/bin/bash
# Environment Switching Script
# Switches between on-prem and internet configurations
#
# Usage:
#   ./set-environment.sh onprem   # Configure for on-prem deployment
#   ./set-environment.sh internet # Configure for internet deployment (default)
#   ./set-environment.sh status   # Show current configuration

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="${SCRIPT_DIR}/.."
INVENTORY_DIR="${REPO_ROOT}/ansible/inventory"
ACTIVE_INVENTORY="${INVENTORY_DIR}/active.yml"

show_usage() {
    echo "Usage: $0 {onprem|internet|status}"
    echo ""
    echo "Commands:"
    echo "  onprem   - Configure for on-prem deployment (uses Nexus proxies)"
    echo "  internet - Configure for internet deployment (direct access)"
    echo "  status   - Show current active configuration"
    echo ""
    echo "Examples:"
    echo "  $0 onprem"
    echo "  $0 internet"
    echo ""
    echo "After switching, run Ansible playbooks with:"
    echo "  cd ansible/playbooks"
    echo "  ansible-playbook -i ../inventory/active.yml kind_dev.yml"
}

show_status() {
    echo "=== Environment Configuration Status ==="
    echo ""
    
    if [ -L "${ACTIVE_INVENTORY}" ]; then
        TARGET=$(readlink "${ACTIVE_INVENTORY}")
        echo "Active inventory: ${TARGET}"
        
        if [[ "${TARGET}" == *"onprem"* ]]; then
            echo "Environment: ON-PREM"
            echo "  - Docker images: via Nexus proxy (srvnexus1:80888)"
            echo "  - Helm charts: via Nexus"
            echo "  - K8s manifests: *-onprem.yaml variants"
        else
            echo "Environment: INTERNET"
            echo "  - Docker images: direct from Docker Hub"
            echo "  - Helm charts: direct from public repos"
            echo "  - K8s manifests: standard .yaml files"
        fi
    elif [ -f "${ACTIVE_INVENTORY}" ]; then
        echo "Active inventory exists but is not a symlink"
        echo "Consider running '$0 internet' or '$0 onprem' to set up properly"
    else
        echo "No active inventory configured"
        echo "Run '$0 internet' or '$0 onprem' to configure"
    fi
    
    echo ""
    echo "Available inventories:"
    ls -la "${INVENTORY_DIR}"/*.yml 2>/dev/null || echo "  (none found)"
}

set_environment() {
    local ENV=$1
    local SOURCE_FILE="${INVENTORY_DIR}/${ENV}.yml"
    
    if [ ! -f "${SOURCE_FILE}" ]; then
        echo "ERROR: Inventory file not found: ${SOURCE_FILE}"
        exit 1
    fi
    
    # Remove existing symlink or file
    rm -f "${ACTIVE_INVENTORY}"
    
    # Create symlink to selected environment
    ln -s "${ENV}.yml" "${ACTIVE_INVENTORY}"
    
    echo "=== Environment switched to: ${ENV} ==="
    echo ""
    
    if [ "${ENV}" == "onprem" ]; then
        echo "Configuration:"
        echo "  - Docker images will be pulled from Nexus proxy"
        echo "  - Helm charts will be fetched from Nexus"
        echo "  - K8s manifests will use *-onprem.yaml variants"
        echo ""
        echo "IMPORTANT: Update the following in ansible/inventory/onprem.yml:"
        echo "  - ghcr_registry_prefix (set the correct port)"
        echo "  - helm_spark_operator_repo_url"
        echo "  - helm_jupyterhub_repo_url"
        echo ""
        echo "Before building Docker images, run:"
        echo "  ./scripts/download-jars.sh"
        echo "  ./scripts/download-python.sh"
    else
        echo "Configuration:"
        echo "  - Docker images will be pulled directly from Docker Hub"
        echo "  - Helm charts will be fetched from public repositories"
        echo "  - K8s manifests will use standard .yaml files"
    fi
    
    echo ""
    echo "To deploy, run:"
    echo "  cd ansible/playbooks"
    echo "  ansible-playbook -i ../inventory/active.yml kind_dev.yml"
    echo ""
    echo "To build Docker images:"
    if [ "${ENV}" == "onprem" ]; then
        echo "  # Build spark-base"
        echo "  docker build --build-arg BASE_IMAGE=srvnexus1:80888/eclipse-temurin:11-jdk-jammy \\"
        echo "    -t statkube/spark-base:spark3.5.3-py3.12-1 docker/spark-base/"
        echo ""
        echo "  # Build spark-notebook"
        echo "  docker build --build-arg BASE_IMAGE=srvnexus1:80888/statkube/spark-base:spark3.5.3-py3.12-1 \\"
        echo "    -t statkube/spark-notebook:spark3.5.3-py3.12-1 docker/spark-notebook/"
    else
        echo "  docker build -t statkube/spark-base:spark3.5.3-py3.12-1 docker/spark-base/"
        echo "  docker build -t statkube/spark-notebook:spark3.5.3-py3.12-1 docker/spark-notebook/"
    fi
}

# Main
case "${1:-}" in
    onprem)
        set_environment "onprem"
        ;;
    internet)
        set_environment "internet"
        ;;
    status)
        show_status
        ;;
    -h|--help|help)
        show_usage
        ;;
    *)
        echo "ERROR: Unknown command: ${1:-}"
        echo ""
        show_usage
        exit 1
        ;;
esac

