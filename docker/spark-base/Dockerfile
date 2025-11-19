FROM eclipse-temurin:11-jdk-jammy AS deps-downloader

RUN apt-get update && apt-get install -y curl

WORKDIR /tmp/jars

# 1. Hadoop S3A (Must match Spark's bundled Hadoop 3.3.4)
RUN curl -O https://repo1.maven.org/maven2/org/apache/hadoop/hadoop-aws/3.3.4/hadoop-aws-3.3.4.jar && \
    curl -O https://repo1.maven.org/maven2/com/amazonaws/aws-java-sdk-bundle/1.12.623/aws-java-sdk-bundle-1.12.623.jar

# 2. Iceberg (Standard REST Catalog support + AWS bundle for S3/MinIO)
RUN curl -O https://repo1.maven.org/maven2/org/apache/iceberg/iceberg-spark-runtime-3.5_2.12/1.9.0/iceberg-spark-runtime-3.5_2.12-1.9.0.jar && \
    curl -O https://repo1.maven.org/maven2/org/apache/iceberg/iceberg-aws-bundle/1.9.0/iceberg-aws-bundle-1.9.0.jar

# 3. Delta Lake (Core + Storage + Spark)
ENV DELTA_VERSION=3.2.0
RUN curl -O https://repo1.maven.org/maven2/io/delta/delta-spark_2.12/${DELTA_VERSION}/delta-spark_2.12-${DELTA_VERSION}.jar && \
    curl -O https://repo1.maven.org/maven2/io/delta/delta-storage/${DELTA_VERSION}/delta-storage-${DELTA_VERSION}.jar

FROM eclipse-temurin:11-jdk-jammy

ENV DEBIAN_FRONTEND=noninteractive \
    SPARK_VERSION=3.5.3 \
    SPARK_HOME=/opt/spark \
    JAVA_HOME=/opt/java/openjdk \
    UV_PROJECT_ENVIRONMENT=/ \
    PIP_NO_CACHE_DIR=1 \
    PYENV_ROOT=/opt/pyenv

ENV PATH="${JAVA_HOME}/bin:${PYENV_ROOT}/versions/3.12.7/bin:${PYENV_ROOT}/bin:${PYENV_ROOT}/shims:${SPARK_HOME}/bin:${SPARK_HOME}/sbin:/root/.local/bin:${PATH}"

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

# Install Python 3.12.7 via pyenv into /opt/pyenv, accessible to non-root users
RUN mkdir -p "${PYENV_ROOT}" && \
    git clone https://github.com/pyenv/pyenv.git "${PYENV_ROOT}" && \
    "${PYENV_ROOT}/bin/pyenv" install 3.12.7 && \
    "${PYENV_ROOT}/bin/pyenv" global 3.12.7 && \
    chmod -R a+rx "${PYENV_ROOT}"

# Install uv package manager
RUN curl -LsSf https://astral.sh/uv/install.sh | sh && \
    ln -s /root/.local/bin/uv /usr/local/bin/uv

RUN mkdir -p "${SPARK_HOME}" /opt/spark/jars

# REPLACED: Download inside Docker
# WITH: Copy local file
COPY spark-3.5.3-bin-hadoop3.tgz /tmp/spark.tgz

RUN tar -xzf /tmp/spark.tgz -C "${SPARK_HOME}" --strip-components=1 && \
    rm /tmp/spark.tgz

# COPY the JARs from the downloader stage
COPY --from=deps-downloader /tmp/jars/*.jar ${SPARK_HOME}/jars/

COPY requirements.txt /tmp/requirements.txt

ENV UV_PYTHON="${PYENV_ROOT}/versions/3.12.7/bin/python"

RUN UV_PYTHON="${UV_PYTHON}" uv pip install --system --require-hashes -r /tmp/requirements.txt

COPY entrypoint.sh /opt/entrypoint.sh
RUN chmod +x /opt/entrypoint.sh

WORKDIR /opt/workdir

ENTRYPOINT ["/opt/entrypoint.sh"]
CMD ["bash"]

