#!/bin/bash
# Download required JAR dependencies for Spark
# Run this script when connected to the internet to refresh the local JAR cache
# These JARs will be COPIED into the Docker image during build (no runtime download needed)

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
JARS_DIR="${SCRIPT_DIR}/../docker/spark-base/jars"

echo "Creating jars directory at: ${JARS_DIR}"
mkdir -p "${JARS_DIR}"

cd "${JARS_DIR}"

echo ""
echo "Downloading Hadoop S3A JARs (for Spark's bundled Hadoop 3.3.4)..."
curl -LO https://repo1.maven.org/maven2/org/apache/hadoop/hadoop-aws/3.3.4/hadoop-aws-3.3.4.jar
curl -LO https://repo1.maven.org/maven2/com/amazonaws/aws-java-sdk-bundle/1.12.623/aws-java-sdk-bundle-1.12.623.jar

echo ""
echo "Downloading Iceberg JARs (REST Catalog support + AWS bundle for S3/MinIO)..."
curl -LO https://repo1.maven.org/maven2/org/apache/iceberg/iceberg-spark-runtime-3.5_2.12/1.9.0/iceberg-spark-runtime-3.5_2.12-1.9.0.jar
curl -LO https://repo1.maven.org/maven2/org/apache/iceberg/iceberg-aws-bundle/1.9.0/iceberg-aws-bundle-1.9.0.jar

echo ""
echo "Downloading Delta Lake JARs..."
DELTA_VERSION=3.2.0
curl -LO "https://repo1.maven.org/maven2/io/delta/delta-spark_2.12/${DELTA_VERSION}/delta-spark_2.12-${DELTA_VERSION}.jar"
curl -LO "https://repo1.maven.org/maven2/io/delta/delta-storage/${DELTA_VERSION}/delta-storage-${DELTA_VERSION}.jar"

echo ""
echo "Downloaded JARs:"
ls -la "${JARS_DIR}"

echo ""
echo "Done! JARs are ready for Docker build."
echo "These files will be COPIED into the image during 'docker build'."

