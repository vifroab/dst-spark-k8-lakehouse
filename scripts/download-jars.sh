#!/bin/bash
# Download required JAR dependencies for Spark
# Run this script when connected to the internet to refresh the local JAR cache
# These JARs will be COPIED into the Docker image during build (no runtime download needed)
#
# Usage:
#   ./download-jars.sh                                    # Download from Maven Central (internet)
#   ./download-jars.sh --nexus                            # Download from Nexus flat repo (on-prem)
#   MAVEN_REPO_URL=https://repo1.maven.org/maven2 ./download-jars.sh           # Maven Central
#   MAVEN_REPO_URL=https://srvnexus1.dst.dk/repository/apache-spark/spark-jars ./download-jars.sh  # Nexus flat
#   MAVEN_REPO_URL=https://srvnexus1.dst.dk/repository/maven-central ./download-jars.sh            # Nexus Maven
#
# The script auto-detects repository structure:
#   - Flat structure: URLs containing "spark-jars" use filename-only
#   - Hierarchical structure: Standard Maven repos use org/group/artifact/version/file.jar

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
JARS_DIR="${SCRIPT_DIR}/../docker/spark-base/jars"

# Default to Maven Central
MAVEN_BASE_URL="${MAVEN_REPO_URL:-https://repo1.maven.org/maven2}"

# Auto-detect repository structure based on URL or flag
# Check for --nexus flag
if [[ "$1" == "--nexus" ]]; then
    # Use Nexus flat structure
    MAVEN_BASE_URL="${MAVEN_REPO_URL:-https://srvnexus1.dst.dk/repository/apache-spark/spark-jars}"
    USE_FLAT_STRUCTURE=true
    echo "Mode: On-prem Nexus (forced via --nexus flag)"
fi

# Auto-detect flat structure based on URL patterns
if [[ "${MAVEN_BASE_URL}" == *"spark-jars"* ]] || \
   [[ "${MAVEN_BASE_URL}" == *"flat"* ]] || \
   [[ "${MAVEN_BASE_URL}" == *"srvnexus1"* && "${MAVEN_BASE_URL}" == *"spark"* ]]; then
    USE_FLAT_STRUCTURE=true
fi

# Determine structure
if [[ "${USE_FLAT_STRUCTURE}" == "true" ]]; then
    STRUCTURE_TYPE="flat (filename-only)"
else
    STRUCTURE_TYPE="hierarchical (standard Maven)"
fi

echo "Creating jars directory at: ${JARS_DIR}"
mkdir -p "${JARS_DIR}"

cd "${JARS_DIR}"

echo "Maven repository: ${MAVEN_BASE_URL}"
echo "Repository structure: ${STRUCTURE_TYPE}"
echo ""
echo "Usage examples:"
echo "  Online (Maven Central):     ./download-jars.sh"
echo "  On-prem (Nexus flat):       ./download-jars.sh --nexus"
echo "  Custom repo:                MAVEN_REPO_URL=https://... ./download-jars.sh"
echo ""

download_jar() {
    local jar_path="$1"
    local jar_name=$(basename "${jar_path}")
    
    if [[ "${USE_FLAT_STRUCTURE}" == "true" ]]; then
        # Flat structure: just use the filename
        local url="${MAVEN_BASE_URL}/${jar_name}"
    else
        # Hierarchical structure: use full Maven path
        local url="${MAVEN_BASE_URL}/${jar_path}"
    fi
    
    echo "  Downloading ${jar_name}..."
    curl -LO "${url}"
}

echo "Downloading Hadoop S3A JARs (for Spark's bundled Hadoop 3.3.4)..."
download_jar "org/apache/hadoop/hadoop-aws/3.3.4/hadoop-aws-3.3.4.jar"
download_jar "com/amazonaws/aws-java-sdk-bundle/1.12.623/aws-java-sdk-bundle-1.12.623.jar"

echo ""
echo "Downloading Iceberg JARs (REST Catalog support + AWS bundle for S3/MinIO)..."
download_jar "org/apache/iceberg/iceberg-spark-runtime-3.5_2.12/1.9.0/iceberg-spark-runtime-3.5_2.12-1.9.0.jar"
download_jar "org/apache/iceberg/iceberg-aws-bundle/1.9.0/iceberg-aws-bundle-1.9.0.jar"

echo ""
echo "Downloading Delta Lake JARs..."
DELTA_VERSION=3.2.0
download_jar "io/delta/delta-spark_2.12/${DELTA_VERSION}/delta-spark_2.12-${DELTA_VERSION}.jar"
download_jar "io/delta/delta-storage/${DELTA_VERSION}/delta-storage-${DELTA_VERSION}.jar"

echo ""
echo "Downloading OpenLineage Spark JAR (for DataHub lineage)..."
OPENLINEAGE_VERSION=1.24.2
download_jar "io/openlineage/openlineage-spark_2.12/${OPENLINEAGE_VERSION}/openlineage-spark_2.12-${OPENLINEAGE_VERSION}.jar"

echo ""
echo "Downloaded JARs:"
ls -la "${JARS_DIR}"

echo ""
echo "Done! JARs are ready for Docker build."
echo "These files will be COPIED into the image during 'docker build'."

