# Base image - override for on-prem registries
# Internet: docker build -t statkube/spark-base:spark3.5.3-py3.12-1 .
# On-prem:  docker build --build-arg BASE_IMAGE=srvnexus1:80888/eclipse-temurin:11-jdk-jammy -t ...
ARG BASE_IMAGE=eclipse-temurin:11-jdk-jammy

FROM ${BASE_IMAGE}

ENV DEBIAN_FRONTEND=noninteractive \
    SPARK_VERSION=3.5.3 \
    SPARK_HOME=/opt/spark \
    JAVA_HOME=/opt/java/openjdk \
    UV_PROJECT_ENVIRONMENT=/ \
    PIP_NO_CACHE_DIR=1 \
    PYTHON_VERSION=3.12.7

ENV PATH="${JAVA_HOME}/bin:/usr/local/python/bin:${SPARK_HOME}/bin:${SPARK_HOME}/sbin:/usr/local/bin:${PATH}"

# Install build dependencies for Python and runtime dependencies
# Note: In on-prem environments, APT sources are configured via /etc/apt/sources.list
# to point to Nexus proxy - no changes needed here
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
      curl \
      wget \
      ca-certificates \
      git \
      make \
      build-essential \
      libssl-dev \
      zlib1g-dev \
      libbz2-dev \
      libreadline-dev \
      libsqlite3-dev \
      llvm \
      libncurses5-dev \
      libncursesw5-dev \
      xz-utils \
      tk-dev \
      libffi-dev \
      liblzma-dev \
      bash \
      tini && \
    rm -rf /var/lib/apt/lists/*

# ============================================
# Install Python from source (no git/pyenv needed)
# ============================================
# Pre-download Python source with: scripts/download-python.sh
COPY Python-${PYTHON_VERSION}.tgz /tmp/Python.tgz

RUN cd /tmp && \
    tar -xzf Python.tgz && \
    cd Python-${PYTHON_VERSION} && \
    ./configure --prefix=/usr/local/python \
                --enable-optimizations \
                --with-ensurepip=install && \
    make -j$(nproc) && \
    make install && \
    cd / && \
    rm -rf /tmp/Python* && \
    ln -sf /usr/local/python/bin/python3 /usr/local/bin/python && \
    ln -sf /usr/local/python/bin/python3 /usr/local/bin/python3 && \
    ln -sf /usr/local/python/bin/pip3 /usr/local/bin/pip && \
    ln -sf /usr/local/python/bin/pip3 /usr/local/bin/pip3

# ============================================
# Install uv package manager (pre-downloaded binary)
# ============================================
# Pre-download uv binaries with: scripts/download-python.sh
# Both amd64 and arm64 binaries are copied; we select based on architecture
COPY uv-x86_64-unknown-linux-gnu.tar.gz /tmp/uv-amd64.tar.gz
COPY uv-aarch64-unknown-linux-gnu.tar.gz /tmp/uv-arm64.tar.gz

RUN ARCH=$(uname -m) && \
    cd /tmp && \
    if [ "$ARCH" = "x86_64" ]; then \
        tar -xzf uv-amd64.tar.gz && \
        mv uv-x86_64-unknown-linux-gnu/uv /usr/local/bin/uv && \
        mv uv-x86_64-unknown-linux-gnu/uvx /usr/local/bin/uvx; \
    elif [ "$ARCH" = "aarch64" ]; then \
        tar -xzf uv-arm64.tar.gz && \
        mv uv-aarch64-unknown-linux-gnu/uv /usr/local/bin/uv && \
        mv uv-aarch64-unknown-linux-gnu/uvx /usr/local/bin/uvx; \
    else \
        echo "Unsupported architecture: $ARCH" && exit 1; \
    fi && \
    chmod +x /usr/local/bin/uv /usr/local/bin/uvx && \
    rm -rf /tmp/uv*

# ============================================
# Install Spark
# ============================================
RUN mkdir -p "${SPARK_HOME}" /opt/spark/jars

# Pre-downloaded Spark distribution (already in repo)
COPY spark-3.5.3-bin-hadoop3.tgz /tmp/spark.tgz

RUN tar -xzf /tmp/spark.tgz -C "${SPARK_HOME}" --strip-components=1 && \
    rm /tmp/spark.tgz

# ============================================
# Install JAR dependencies (pre-downloaded, no curl needed)
# ============================================
# Pre-download JARs with: scripts/download-jars.sh
# JARs include: Hadoop AWS, Iceberg, Delta Lake
COPY jars/*.jar ${SPARK_HOME}/jars/

# ============================================
# Install Python dependencies
# ============================================
COPY requirements.txt /tmp/requirements.txt

ENV UV_PYTHON="/usr/local/python/bin/python3"

RUN UV_PYTHON="${UV_PYTHON}" uv pip install --system --require-hashes -r /tmp/requirements.txt

# ============================================
# Entrypoint
# ============================================
COPY entrypoint.sh /opt/entrypoint.sh
RUN chmod +x /opt/entrypoint.sh

WORKDIR /opt/workdir

ENTRYPOINT ["/opt/entrypoint.sh"]
CMD ["bash"]
