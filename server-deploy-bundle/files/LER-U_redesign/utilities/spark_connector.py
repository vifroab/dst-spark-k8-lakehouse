# ---
# jupyter:
#   jupytext:
#     cell_metadata_filter: tags
#     formats: py:percent
#     notebook_metadata_filter: -widgets,-varInspector
#     text_representation:
#       extension: .py
#       format_name: percent
#       format_version: '1.3'
#       jupytext_version: 1.18.1
# ---

# %%
"""
DST Data Platform - Spark Connector
====================================

A pythonic, class-based Spark session manager with automatic environment detection.

This module provides a singleton `SparkConnector` class that simplifies Spark session
management by automatically configuring connections based on the current git branch.

Primary Public Interface:
-------------------------
- `SparkConnector(size="S")`: Get the singleton connector instance.
- `connector.session`: Property to access the active `SparkSession`.
- `connector.env`: Property to access detailed environment and resource info.
- `connector.restart(size="S")`: Stop the current session and start a new one.
- `connector.stop()`: Manually shut down the Spark session.

Example Usage:
--------------
    from spark_connector import SparkConnector

    # Get a Spark session for the current git branch
    connector = SparkConnector(size="M")
    spark = connector.session

    # Access environment details
    print(f"Connected to environment: {connector.env.env_name}")
    print(f"Using bucket: {connector.env.bucket}")

    # Run Spark jobs
    spark.sql("SHOW DATABASES").show()

    # Clean up when done
    connector.stop()
"""

import os
import sys
import socket
import subprocess
import getpass
from pathlib import Path
from typing import Optional, Dict, Tuple, List, ClassVar
from dataclasses import dataclass, field
from enum import Enum

from pyspark.sql import SparkSession

# %%
# =============================================================================
# INTERNAL: Enums & Constants
# These are implementation details and not part of the public API.
# =============================================================================


class _CatalogType(Enum):
    """(Internal) Catalog implementation types."""

    IN_MEMORY = "in-memory"
    HIVE = "hive"


class _RuntimeEnv(Enum):
    """(Internal) Runtime environment types."""

    KUBERNETES = "kubernetes"
    DOCKER = "docker"
    HOST = "host"


# (Internal) Resource size configurations are embedded for user convenience.
_RESOURCE_SIZES: Dict[str, Dict[str, any]] = {
    "XS": {
        "cores_max": 2,
        "executor_cores": 1,
        "executor_memory": "2g",
        "memory_overhead": "512m",
    },
    "S": {
        "cores_max": 8,
        "executor_cores": 3,
        "executor_memory": "3g",
        "memory_overhead": "1g",
    },
    "M": {
        "cores_max": 16,
        "executor_cores": 8,
        "executor_memory": "64g",
        "memory_overhead": "4g",
    },
    "L": {
        "cores_max": 32,
        "executor_cores": 16,
        "executor_memory": "128g",
        "memory_overhead": "8g",
    },
    "XL": {
        "cores_max": 64,
        "executor_cores": 32,
        "executor_memory": "512g",
        "memory_overhead": "16g",
    },
}

# (Internal) Bucket configuration from environment variables.
_BUCKETS = {
    "dev": os.environ.get("BUCKET_DEV", "dev"),
    "test": os.environ.get("BUCKET_TEST", "test"),
    "prod": os.environ.get("BUCKET_PROD", "prod"),
    "sbx": os.environ.get("BUCKET_SBX", "sbx"),
    "user_prefix": os.environ.get("BUCKET_USER_PREFIX", "user-"),
}

# (Internal) HMS port mapping (service_name, host_port).
_HMS_CONFIG = {
    "sbx": ("hms-sbx", 9086),
    "dev": ("hms-dev", 9083),
    "test": ("hms-test", 9084),
    "prod": ("hms-prod", 9085),
}


# %%
# =============================================================================
# PUBLIC: Data Classes for Introspection
# These classes provide structured information about the session.
# =============================================================================


@dataclass(frozen=True)
class ResourceConfig:
    """
    (Public) Immutable resource configuration for a cluster size.
    Users can inspect this via `connector.env.resource`.
    """

    size: str
    cores_max: int
    executor_cores: int
    executor_memory: str
    memory_overhead: str

    @property
    def executor_instances(self) -> int:
        """Calculate optimal number of executor instances."""
        return max(1, self.cores_max // self.executor_cores)

    @classmethod
    def _from_size(cls, size: str) -> "ResourceConfig":
        """(Internal) Factory method to create from size name."""
        size_key = size.upper()
        if size_key not in _RESOURCE_SIZES:
            raise ValueError(
                f"Invalid size '{size}'. Available: {list(_RESOURCE_SIZES.keys())}"
            )
        config = _RESOURCE_SIZES[size_key]
        return cls(size=size_key, **config)


@dataclass(frozen=True)
class SessionInfo:
    """
    (Public) Complete session information for introspection.
    This is the primary object for users to get details about the active environment.
    Accessible via the `connector.env` property.
    """

    username: str
    branch: str
    env_name: str
    catalog_type: str
    bucket: str
    hms_uri: str
    spark_master: str
    resource: ResourceConfig
    runtime: str
    python_version: str = field(
        default_factory=lambda: f"{sys.version_info.major}.{sys.version_info.minor}"
    )

    def to_dict(self) -> Dict[str, str]:
        """(Internal) Convert to flat dictionary for Spark config."""
        return {
            "username": self.username,
            "branch": self.branch,
            "env_name": self.env_name,
            "catalog_type": self.catalog_type,
            "bucket": self.bucket,
            "hms_uri": self.hms_uri,
            "spark_master": self.spark_master,
            "size": self.resource.size,
            "executor_instances": str(self.resource.executor_instances),
            "executor_cores": str(self.resource.executor_cores),
            "executor_memory": self.resource.executor_memory,
            "memory_overhead": self.resource.memory_overhead,
            "python_version": self.python_version,
            "runtime": self.runtime,
        }


# %%
# =============================================================================
# INTERNAL: Utility Functions
# These helper functions contain the core logic for detection and mapping.
# =============================================================================


def _get_git_branch() -> Optional[str]:
    """(Internal) Get current git branch with upstream fallback."""
    try:
        branch = (
            subprocess.check_output(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"], stderr=subprocess.DEVNULL
            )
            .strip()
            .decode("utf-8")
        )
        if branch and "/" not in branch and branch != "HEAD":
            try:
                upstream = (
                    subprocess.check_output(
                        [
                            "git",
                            "rev-parse",
                            "--abbrev-ref",
                            "--symbolic-full-name",
                            "@{u}",
                        ],
                        stderr=subprocess.DEVNULL,
                    )
                    .strip()
                    .decode("utf-8")
                )
                if upstream and "/" in upstream:
                    return upstream.split("/", 1)[1]
            except subprocess.CalledProcessError:
                pass
        return branch if branch != "HEAD" else None
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


def _detect_runtime() -> Tuple[_RuntimeEnv, str, str, str]:
    """(Internal) Detect runtime and return network configuration."""

    # Kubernetes (JupyterHub notebooks / Spark on K8s)
    if os.environ.get("KUBERNETES_SERVICE_HOST") or os.path.exists("/var/run/secrets/kubernetes.io/serviceaccount/token"):
        hostname = socket.gethostname()
        driver_host = None
        try:
            driver_host = socket.gethostbyname(hostname)
        except Exception:
            driver_host = None

        # Fallback: best-effort egress-based IP discovery
        if not driver_host or driver_host.startswith("127."):
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                s.connect(("8.8.8.8", 80))
                driver_host = s.getsockname()[0]
                s.close()
            except Exception:
                driver_host = "127.0.0.1"

        spark_master = os.environ.get("SPARK_MASTER", "k8s://https://kubernetes.default.svc")
        minio_host = os.environ.get("MINIO_HOSTNAME", "minio.minio.svc")
        return _RuntimeEnv.KUBERNETES, spark_master, driver_host, minio_host

    hostname = socket.gethostname()
    is_docker = hostname.startswith("global-") or os.path.exists("/.dockerenv")
    if is_docker:
        return _RuntimeEnv.DOCKER, "spark://spark-master:7077", hostname, "minio"
    else:
        driver_host = "host.docker.internal"
        try:
            cmd = "ifconfig | grep -A 4 'bridge100' | tail -1 | awk '{print $2}'"
            host_ip = (
                subprocess.check_output(cmd, shell=True, stderr=subprocess.DEVNULL)
                .strip()
                .decode("utf-8")
            )
            if host_ip:
                print(
                    f"Found host IP on Docker network: {host_ip}. Using it for the driver."
                )
                driver_host = host_ip
        except Exception:
            print(
                "Could not determine host IP. Falling back to 'host.docker.internal'."
            )
        return (
            _RuntimeEnv.HOST,
            "spark://localhost:7077",
            driver_host,
            os.environ.get("MINIO_HOSTNAME", "localhost"),
        )


def _find_local_jars() -> List[Path]:
    """(Internal) Find required JARs for host machine driver."""
    # ... (Implementation is correct and can be considered an internal detail)
    required = [
        "delta-spark_2.13-4.0.0.jar",
        "delta-storage-4.0.0.jar",
        "hadoop-aws-3.4.0.jar",
        "bundle-2.23.19.jar",
    ]
    search_paths = [
        Path.cwd(),
        Path(__file__).resolve().parent,
        Path(__file__).resolve().parent.parent,
    ]
    found = set()
    for base_path in search_paths:
        jars_dir = base_path / "jars"
        if jars_dir.exists():
            for jar_name in required:
                if (jars_dir / jar_name).is_file():
                    found.add(jars_dir / jar_name)
    return list(found)


def _map_branch_to_environment(
    branch: Optional[str], username: str
) -> Tuple[str, str, _CatalogType, Optional[Tuple]]:
    """(Internal) Map git branch to environment details."""
    user = (username or "default_user").lower()
    if branch and branch.startswith("local/"):
        return (
            "local-sandbox",
            f"s3a://{_BUCKETS['user_prefix']}{user}",
            _CatalogType.IN_MEMORY,
            None,
        )
    if not branch or branch.startswith("feature/"):
        return "sbx", f"s3a://{_BUCKETS['sbx']}", _CatalogType.HIVE, _HMS_CONFIG["sbx"]
    if branch in ("develop", "dev"):
        return "dev", f"s3a://{_BUCKETS['dev']}", _CatalogType.HIVE, _HMS_CONFIG["dev"]
    if branch.startswith(("release/", "hotfix/")):
        return (
            "test",
            f"s3a://{_BUCKETS['test']}",
            _CatalogType.HIVE,
            _HMS_CONFIG["test"],
        )
    if branch in ("main", "master"):
        return (
            "prod",
            f"s3a://{_BUCKETS['prod']}",
            _CatalogType.HIVE,
            _HMS_CONFIG["prod"],
        )
    raise ValueError(f"Branch '{branch}' is not mapped to a known environment.")


def _bootstrap_domain(spark: SparkSession, domain: str):
    """(Internal) The core logic for bootstrapping a single domain."""
    bucket = spark.conf.get("dst.env.bucket")
    print(f"[Bootstrap] Starting sync for domain '{domain}' in bucket '{bucket}'...")

    layer_map = {
        "01_indsamlet": "01inds",
        "02_skemaindlaest": "02skem",
        "03_integreret": "03inte",
        "04_transformeret": "04tran",
        "05_faerdigbehandlet": "05faer",
        "06_fortrolig": "06fort",
        "07_publiceret": "07publ",
    }

    def qid(s: str) -> str:
        return f"`{s.replace('`', '``')}`"

    # Create databases first
    for layer_dir, layer_suffix in layer_map.items():
        db_name = f"{domain}_{layer_suffix}"
        db_location = f"{bucket}/{domain}/{layer_dir}/"
        spark.sql(
            f"CREATE DATABASE IF NOT EXISTS {qid(db_name)} LOCATION '{db_location}'"
        )

    print(f"[Bootstrap] Scanning for new tables in domain '{domain}'...")
    jvm = spark._jvm
    conf = spark._jsc.hadoopConfiguration()
    Path = jvm.org.apache.hadoop.fs.Path

    for layer_dir, layer_suffix in layer_map.items():
        db_name = f"{domain}_{layer_suffix}"
        layer_location = f"{bucket}/{domain}/{layer_dir}/"
        try:
            # **FIX**: Get the filesystem for the specific path to avoid 'Wrong FS' error
            fs = Path(layer_location).getFileSystem(conf)
            for item in fs.listStatus(Path(layer_location)):
                if item.isDirectory():
                    table_path = item.getPath().toString()
                    table_name = item.getPath().getName()
                    delta_log_path = Path(table_path, "_delta_log")
                    if fs.exists(delta_log_path):
                        spark.sql(
                            f"CREATE TABLE IF NOT EXISTS {qid(db_name)}.{qid(table_name)} USING DELTA LOCATION '{table_path}'"
                        )
        except Exception as e:
            if "FileNotFoundException" in str(e):
                pass  # It's okay if a layer directory doesn't exist
            else:
                print(f"  - Warning: Could not scan {layer_location}. Error: {e}")

    print(f"[Bootstrap] Domain '{domain}' synchronization complete.")


# %%
# =============================================================================
# PUBLIC: The Main Connector Class
# This is the primary entry point for users.
# =============================================================================


class SparkConnector:
    """
    (Public) Singleton Spark session manager.

    This class provides a single, consistent entry point to get a Spark session.
    It automatically handles configuration, environment detection, and resource
    management. The singleton pattern ensures that only one SparkContext exists
    per application.

    **Public Methods:**
        - `__init__(size="S", force_new=False)`: Get or create the session.
        - `restart(size="S")`: A convenient way to stop and start a new session.
        - `stop()`: Manually shut down the Spark session.

    **Public Properties:**
        - `session` -> SparkSession: The active Spark session.
        - `env` -> SessionInfo: Detailed information about the session.
        - `is_active` -> bool: Check if the session is currently running.
    """

    _instance: ClassVar[Optional["SparkConnector"]] = None
    _session: Optional[SparkSession] = None
    _session_info: Optional[SessionInfo] = None
    _branch_at_creation: Optional[str] = None

    def __new__(
        cls,
        size: str = "S",
        dynamic_allocation: bool = True,
        idle_timeout: str = "10m",
        force_new: bool = False,
    ):
        """(Public) Get or create the singleton instance."""
        # **FIX**: More robust singleton logic to handle restarts correctly.
        if force_new and cls._instance:
            cls._instance.stop()

        if cls._instance is None or not cls._instance.is_active:
            instance = super().__new__(cls)
            cls._instance = instance
            return instance

        current_branch = _get_git_branch()
        if cls._instance._branch_at_creation != current_branch:
            print("\n" + "!" * 80)
            print("  WARNING: Git branch has changed since session creation!")
            print(f"    Session was for branch: '{cls._instance._branch_at_creation}'")
            print(f"    You are now on branch:  '{current_branch}'")
            print("    Your Spark environment is out of sync.")
            print("    --> To fix, run: `connector = SparkConnector(force_new=True)` or `connector.restart()`")
            print("!" * 80 + "\n")

        return cls._instance

    def __init__(
        self,
        size: str = "S",
        dynamic_allocation: bool = True,
        idle_timeout: str = "10m",
        force_new: bool = False,
    ):
        """
        (Public) Initialize the connector and get a Spark session.

        Args:
            size (str): The resource profile to use (e.g., "XS", "S", "M").
            dynamic_allocation (bool): If True (default), executors will be released when idle.
            idle_timeout (str): How long an executor must be idle before being released.
            force_new (bool): If True, stops any active session and creates a new one.
        """
        # **FIX**: Prevent re-initialization on existing instances.
        if (
            hasattr(self, "_session_info")
            and self._session_info is not None
            and not force_new
        ):
            return

        if (
            force_new and self._session
        ):  # Should have been stopped by __new__, but as a safeguard
            self.stop()
        self._initialize_session(size, dynamic_allocation, idle_timeout)

    def _initialize_session(
        self, size: str, dynamic_allocation: bool, idle_timeout: str
    ) -> None:
        """(Internal) The core logic for creating and configuring a Spark session."""
        # ... (most of the method is the same) ...
        # MinIO credentials
        minio_user = os.environ.get("MINIO_USER")
        minio_pass = os.environ.get("MINIO_PASSWORD")

        username = getpass.getuser().lower()
        branch = _get_git_branch()
        resource = ResourceConfig._from_size(size)
        runtime, spark_master, driver_host, minio_host = _detect_runtime()

        # In Kubernetes we do not rely on git branches or HMS; we use service DNS and sane defaults.
        if runtime == _RuntimeEnv.KUBERNETES:
            minio_user = minio_user or os.environ.get("MINIO_ACCESS_KEY")
            minio_pass = minio_pass or os.environ.get("MINIO_SECRET_KEY")
            if not minio_user or not minio_pass:
                raise ValueError("MINIO_USER/MINIO_PASSWORD (or MINIO_ACCESS_KEY/MINIO_SECRET_KEY) must be set in Kubernetes.")
            env_name = os.environ.get("DST_ENV", "k8s")
            bucket = os.environ.get("DST_BUCKET", "s3a://polaris")
            catalog_type = _CatalogType.IN_MEMORY
            hms_details = None
        else:
            if not minio_user or not minio_pass:
                raise ValueError("MINIO_USER and MINIO_PASSWORD must be set.")
            env_name, bucket, catalog_type, hms_details = _map_branch_to_environment(
                branch, username
            )

        hms_uri = ""
        if hms_details:
            hms_service, hms_port = hms_details
            hms_uri = (
                f"thrift://{hms_service}:9083"
                if runtime == _RuntimeEnv.DOCKER
                else f"thrift://localhost:{hms_port}"
            )

        self._session_info = SessionInfo(
            username=username,
            branch=branch or "unknown",
            env_name=env_name,
            catalog_type=catalog_type.value,
            bucket=bucket,
            hms_uri=hms_uri,
            spark_master=spark_master,
            resource=resource,
            runtime=runtime.value,
        )
        self._branch_at_creation = branch

        self._print_config()

        builder = self._build_session_builder(
            minio_user,
            minio_pass,
            minio_host,
            driver_host,
            resource,
            dynamic_allocation,
            idle_timeout,
        )
        if runtime == _RuntimeEnv.HOST:
            builder = self._add_local_jars(builder)
        builder = self._configure_catalog(builder, catalog_type, hms_uri)

        self._session = builder.getOrCreate()
        self._sync_to_spark()

        print("\n" + "=" * 80 + "\n SPARK SESSION ACTIVE\n" + "=" * 80)
        self._print_session_info()
        print("=" * 80 + "\n")

    # --- Changed to fix mismatch of localhost when writing to minio by docker executors
    
    def _build_session_builder(
        self,
        minio_user,
        minio_pass,
        minio_host,
        driver_host,
        resource,
        dynamic_alloc,
        idle_timeout,
    ) -> SparkSession.Builder:
        """(Internal) Constructs the SparkSession.Builder with all configurations."""
        info = self._session_info

        is_k8s = info.runtime == _RuntimeEnv.KUBERNETES.value

        # S3 endpoint(s)
        if is_k8s:
            # Inside Kubernetes, both driver and executors reach MinIO via cluster DNS
            s3_endpoint = os.environ.get("MINIO_S3_ENDPOINT", f"http://{minio_host}:9000")
            executor_endpoint = s3_endpoint
            driver_endpoint = s3_endpoint
        else:
            # Local docker/host split endpoints (legacy dev behavior)
            executor_endpoint = "http://minio:9000"
            driver_endpoint = "http://localhost:9000"

        pyspark_python = os.environ.get("PYSPARK_PYTHON", "python3")

        builder = (
            SparkSession.builder.appName(f"DST-{info.username}-{info.env_name}")
            .master(info.spark_master)
            .config("spark.driver.host", driver_host)
            .config("spark.driver.bindAddress", "0.0.0.0")

            # ---------- S3A / MinIO ----------
            .config("spark.hadoop.fs.s3a.endpoint", driver_endpoint)
            .config("spark.hadoop.fs.s3a.path.style.access", "true")
            .config("spark.hadoop.fs.s3a.impl", "org.apache.hadoop.fs.s3a.S3AFileSystem")
            .config("spark.hadoop.fs.s3a.connection.ssl.enabled", "false")
            .config("spark.hadoop.fs.s3a.access.key", minio_user)
            .config("spark.hadoop.fs.s3a.secret.key", minio_pass)

            # Make reads/writes consistent for executors if they need a different endpoint
            .config("spark.executor.extraJavaOptions", f"-Dfs.s3a.endpoint={executor_endpoint}")
            .config("spark.driver.extraJavaOptions",   f"-Dfs.s3a.endpoint={driver_endpoint}")

            # Faster overwrite on S3/MinIO
            .config("spark.hadoop.mapreduce.outputcommitter.factory.scheme.s3a",
                    "org.apache.hadoop.fs.s3a.commit.S3ACommitterFactory")
            .config("spark.hadoop.fs.s3a.committer.name", "directory")

            # ---------- Warehouse / Python ----------
            .config("spark.sql.warehouse.dir", f"{info.bucket}/warehouse/")
            .config("hive.exec.scratchdir", f"{info.bucket}/scratch/")
            .config("spark.local.dir", f"{info.bucket}/spark-tmp/")
            .config("spark.pyspark.python", pyspark_python)
            .config("spark.pyspark.driver.python", sys.executable)
            .config("spark.executorEnv.PYSPARK_PYTHON", pyspark_python)

            # ---------- Iceberg + Delta ----------
            .config("spark.sql.extensions",
                    "org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions,io.delta.sql.DeltaSparkSessionExtension")
            .config("spark.sql.catalog.spark_catalog", "org.apache.spark.sql.delta.catalog.DeltaCatalog")
            .config("spark.sql.sources.default", "delta")

            # ---------- Resources ----------
            .config("spark.cores.max", str(resource.cores_max))
            .config("spark.executor.cores", str(resource.executor_cores))
            .config("spark.executor.memory", resource.executor_memory)
            .config("spark.executor.memoryOverhead", resource.memory_overhead)
            .config("spark.executor.instances", str(resource.executor_instances))
            .config("spark.dynamicAllocation.enabled", str(dynamic_alloc).lower())

            # ---------- Sensible perf defaults ----------
            .config("spark.sql.shuffle.partitions", "64")
            .config("spark.speculation", "false")
        )

        if dynamic_alloc:
            builder = builder.config("spark.dynamicAllocation.executorIdleTimeout", idle_timeout)

        # Kubernetes-specific Spark-on-K8s settings
        if is_k8s:
            default_image = "statkube/spark-notebook:spark3.5.3-py3.12-1"
            executor_image = (
                os.environ.get("SPARK_EXECUTOR_IMAGE")
                or os.environ.get("SPARK_NOTEBOOK_IMAGE")
                or default_image
            )
            namespace = (
                os.environ.get("POD_NAMESPACE")
                or os.environ.get("JUPYTERHUB_NAMESPACE")
                or "jhub-dev"
            )
            service_account = os.environ.get("SPARK_SERVICE_ACCOUNT", "spark-sa")

            builder = (
                builder
                .config("spark.kubernetes.container.image", executor_image)
                .config("spark.kubernetes.container.image.pullPolicy", "IfNotPresent")
                .config("spark.kubernetes.namespace", namespace)
                .config("spark.driver.port", "7077")
                .config("spark.kubernetes.authenticate.driver.serviceAccountName", service_account)
                .config("spark.kubernetes.authenticate.caCertFile", "/var/run/secrets/kubernetes.io/serviceaccount/ca.crt")
                .config("spark.kubernetes.authenticate.oauthTokenFile", "/var/run/secrets/kubernetes.io/serviceaccount/token")
                .config("spark.kubernetes.executor.deleteOnTermination", "false")
            )

            # Optional Polaris (Iceberg REST) wiring (defaults match this repo's k8s manifests)
            polaris_uri = os.environ.get("POLARIS_URI", "http://polaris.polaris.svc:8181/api/catalog")
            polaris_token_uri = os.environ.get("POLARIS_TOKEN_URI", "http://polaris.polaris.svc:8181/api/catalog/v1/oauth/tokens")
            polaris_warehouse = os.environ.get("POLARIS_WAREHOUSE", "polaris")
            polaris_credential = os.environ.get("POLARIS_CREDENTIAL", "root:s3cr3t")
            polaris_scope = os.environ.get("POLARIS_SCOPE", "PRINCIPAL_ROLE:ALL")
            polaris_realm = os.environ.get("POLARIS_REALM", "POLARIS")
            region = os.environ.get("AWS_REGION", "us-east-1")

            # Pass AWS credentials as system properties (helps Iceberg AWS clients)
            aws_java_opts = (
                f"-Daws.accessKeyId={minio_user} "
                f"-Daws.secretAccessKey={minio_pass} "
                f"-Daws.region={region} "
                "--add-opens=java.base/sun.nio.ch=ALL-UNNAMED "
                "--add-opens=java.base/java.nio=ALL-UNNAMED "
                "--add-exports=java.base/sun.nio.ch=ALL-UNNAMED"
            )

            builder = (
                builder
                .config("spark.driver.extraJavaOptions", aws_java_opts)
                .config("spark.executor.extraJavaOptions", aws_java_opts)
                .config("spark.kubernetes.executor.env.JDK_JAVA_OPTIONS", aws_java_opts)
                .config("spark.sql.catalog.polaris", "org.apache.iceberg.spark.SparkCatalog")
                .config("spark.sql.catalog.polaris.type", "rest")
                .config("spark.sql.catalog.polaris.uri", polaris_uri)
                .config("spark.sql.catalog.polaris.warehouse", polaris_warehouse)
                .config("spark.sql.catalog.polaris.credential", polaris_credential)
                .config("spark.sql.catalog.polaris.scope", polaris_scope)
                .config("spark.sql.catalog.polaris.header.Polaris-Realm", polaris_realm)
                .config("spark.sql.catalog.polaris.oauth2-server-uri", polaris_token_uri)
                .config("spark.sql.catalog.polaris.client.region", region)
                .config("spark.sql.catalog.polaris.io-impl", "org.apache.iceberg.aws.s3.S3FileIO")
                .config("spark.sql.catalog.polaris.s3.endpoint", s3_endpoint)
                .config("spark.sql.catalog.polaris.s3.access-key-id", minio_user)
                .config("spark.sql.catalog.polaris.s3.secret-access-key", minio_pass)
                .config("spark.sql.catalog.polaris.s3.path-style-access", "true")
                .config("spark.executorEnv.AWS_ACCESS_KEY_ID", minio_user)
                .config("spark.executorEnv.AWS_SECRET_ACCESS_KEY", minio_pass)
                .config("spark.executorEnv.AWS_REGION", region)
            )

        return builder


    def _add_local_jars(self, builder: SparkSession.Builder) -> SparkSession.Builder:
        """(Internal) Adds locally found JARs for the driver on a host machine."""
        # ... (Implementation is an internal detail)
        jars = _find_local_jars()
        if not jars:
            raise RuntimeError(
                "Running from host requires local JARs. Please add them to a 'jars' directory."
            )
        jars_str = [str(j) for j in jars]
        return builder.config("spark.jars", ",".join(jars_str)).config(
            "spark.driver.extraClassPath", ":".join(jars_str)
        )

    def _configure_catalog(self, builder, catalog_type, hms_uri):
        """(Internal) Configures the catalog for Hive or in-memory."""
        # ... (Implementation is an internal detail)
        if catalog_type == _CatalogType.IN_MEMORY:
            return builder.config(
                "spark.sql.catalogImplementation", "in-memory"
            ).config("spark.hadoop.hive.metastore.uris", "")
        else:
            return (
                builder.config("spark.sql.catalogImplementation", "hive")
                .config("spark.hadoop.hive.metastore.uris", hms_uri)
                .enableHiveSupport()
            )

    def _sync_to_spark(self):
        """(Internal) Syncs session info to the SparkSession object."""
        # ... (Implementation is an internal detail)
        for key, value in self._session_info.to_dict().items():
            self._session.conf.set(f"dst.env.{key}", value)
        setattr(self._session, "env", self._session_info)

    def _print_config(self):
        """(Internal) Prints the configuration summary before session creation."""
        # ... (Implementation is an internal detail)
        info = self._session_info
        print("\n" + "=" * 80 + "\n CONFIGURING SPARK SESSION\n" + "=" * 80)
        print(
            f"  User:        {info.username}\n  Branch:      {info.branch}\n  Environment: {info.env_name}\n  Bucket:      {info.bucket}\n  Size:        {info.resource.size}\n  Runtime:     {info.runtime}"
        )
        print("=" * 80)

    def _print_session_info(self):
        """(Internal) Prints a summary of the active session."""
        # ... (Implementation is an internal detail)
        info = self._session_info
        print(
            f"  Environment:  {info.env_name}\n  Branch:       {info.branch}\n  Bucket:       {info.bucket}\n  Size:         {info.resource.size}"
        )
        if info.hms_uri:
            print(f"  HMS:          {info.hms_uri}")

    @property
    def session(self) -> SparkSession:
        """(Public) The active SparkSession instance."""
        if not self._session:
            raise RuntimeError("No active Spark session. Initialize connector first.")
        return self._session

    @property
    def env(self) -> SessionInfo:
        """(Public) Detailed information about the current session's environment."""
        if not self._session_info:
            raise RuntimeError("No session info available.")
        return self._session_info

    @property
    def is_active(self) -> bool:
        """(Public) Returns True if the Spark session is running."""
        if not self._session:
            return False
        try:
            self._session.sparkContext.getConf()
            return True
        except Exception:
            return False

    def stop(self) -> None:
        """(Public) Stops the active Spark session and resets the connector."""
        if self._session:
            print("Stopping Spark session...")
            self._session.stop()
            self._session = None
            self._session_info = None
            self._branch_at_creation = None
            SparkConnector._instance = None
            print("Session stopped.")

    def restart(
        self,
        size: Optional[str] = None,
        dynamic_allocation: bool = True,
        idle_timeout: str = "10m",
    ) -> "SparkConnector":
        """
        (Public) Stops the current session and starts a new one.

        Args:
            size (str, optional): The new resource profile. If None, uses the previous size.
            dynamic_allocation (bool): Whether to enable dynamic allocation (default: True).
            idle_timeout (str): The idle timeout for the new session.

        Returns:
            The re-initialized SparkConnector instance.
        """
        # **FIX**: Simplified and more robust restart logic.
        current_size = self._session_info.resource.size if self._session_info else "S"
        # The __new__ method now handles stopping the old instance.
        self.__init__(
            size or current_size, dynamic_allocation, idle_timeout, force_new=True
        )
        return self

    def bootstrap(self, domain: Optional[str] = None) -> None:
        """
        (Public) Synchronizes S3 data layers with the Hive Metastore for a domain.

        This method is fully automatic. It creates databases and registers Delta
        tables, making them queryable via SQL.

        Args:
            domain (str, optional): The domain to bootstrap.
                - If provided, that specific domain is synced.
                - If NOT provided, the method will attempt to auto-detect the domain
                  based on the environment, providing the most intuitive behavior.
        """
        if not self.is_active:
            raise RuntimeError("Cannot bootstrap with an inactive Spark session.")

        domain_to_bootstrap = domain

        # If no domain is specified, apply intelligent, automatic detection
        if domain_to_bootstrap is None:
            if self.env.env_name == "local-sandbox":
                domain_to_bootstrap = self.env.username
                print(
                    f"No domain specified. Defaulting to username '{domain_to_bootstrap}' for the local sandbox."
                )
            else:
                # For shared environments, try to auto-detect the domain
                print(
                    f"No domain specified for shared '{self.env.env_name}' environment. Attempting auto-detection..."
                )
                bucket = self.env.bucket

                # List top-level directories in the bucket
                try:
                    jvm = self.session._jvm
                    conf = self.session._jsc.hadoopConfiguration()
                    Path = jvm.org.apache.hadoop.fs.Path
                    fs = jvm.org.apache.hadoop.fs.FileSystem.get(
                        jvm.java.net.URI(bucket), conf
                    )

                    possible_domains = []
                    known_layers = {
                        "01_indsamlet",
                        "02_skemaindlaest",
                        "03_integreret",
                        "04_transformeret",
                        "05_faerdigbehandlet",
                        "06_fortrolig",
                        "07_publiceret",
                    }

                    for item in fs.listStatus(Path(bucket)):
                        if item.isDirectory():
                            dir_name = item.getPath().getName()
                            if (
                                not dir_name.startswith(("_", "."))
                                and dir_name not in known_layers
                            ):
                                possible_domains.append(dir_name)

                    if len(possible_domains) == 1:
                        domain_to_bootstrap = possible_domains[0]
                        print(
                            f"Auto-detected a single domain: '{domain_to_bootstrap}'. Proceeding with bootstrap."
                        )
                    elif len(possible_domains) > 1:
                        print("Multiple possible domains found in this bucket. Please specify which one to bootstrap.")
                        print("    Available domains:", ", ".join(possible_domains))
                        print(f'    Example: connector.bootstrap(domain="{possible_domains[0]}")')
                        return
                    else:
                        print(" Could not auto-detect any domains in this bucket.")
                        print("    Please create a domain directory in your bucket or specify a domain.")
                        print('    Example: connector.bootstrap(domain="your_new_domain")')
                        return

                except Exception as e:
                    print(f" Error during domain auto-detection: {e}")
                    return

        # Proceed with the bootstrap logic
        _bootstrap_domain(self.session, domain_to_bootstrap)

    def __enter__(self) -> SparkSession:
        """(Public) Allows use as a context manager: `with SparkConnector() as spark:`"""
        return self.session

    def __exit__(self, exc_type, exc_val, exc_tb):
        """(Public) Context manager exit. Does not stop the session by default."""
        pass

    def __repr__(self) -> str:
        """(Public) A developer-friendly string representation."""
        if not self.is_active:
            return "<SparkConnector: inactive>"
        return f"<SparkConnector: env='{self.env.env_name}' size='{self.env.resource.size}' branch='{self.env.branch}'>"
