import socket
from pyspark.sql import SparkSession


def get_driver_ip():
    """Get the Driver IP so Executors can connect back to us."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        driver_ip = s.getsockname()[0]
        s.close()
        return driver_ip
    except Exception:
        # Fallback for local testing if not in K8s/networked env
        return "127.0.0.1"


def create_spark_session(app_name="spark-k8s-app", enable_lineage=False):
    """
    Creates a SparkSession configured for:
    - Kubernetes (Spark on K8s)
    - Polaris (Iceberg Catalog)
    - MinIO (S3 Storage)
    - Delta Lake

    Args:
        app_name: Name for the Spark application
        enable_lineage: If True, enables OpenLineage/DataHub integration (requires DataHub running)
    """
    driver_ip = get_driver_ip()
    print(f"Initializing Spark Session '{app_name}' with Driver IP: {driver_ip}")

    # Common S3/MinIO Credentials
    s3_endpoint = "http://minio.minio.svc:9000"
    access_key = "admin"
    secret_key = "password"
    region = "us-east-1"

    # Polaris Config
    polaris_uri = "http://polaris.polaris.svc:8181/api/catalog"
    polaris_warehouse = "polaris"
    polaris_token_uri = "http://polaris.polaris.svc:8181/api/catalog/v1/oauth/tokens"

    # DataHub OpenLineage Config (for lineage tracking)
    datahub_gms_url = "http://datahub-datahub-gms.datahub.svc:8080"
    openlineage_namespace = "spark-k8s-hub"

    # Java Options to pass system properties to AWS SDK (crucial for Iceberg)
    # We also include Java 17+ module opens just in case
    aws_java_opts = (
        f"-Daws.accessKeyId={access_key} "
        f"-Daws.secretAccessKey={secret_key} "
        f"-Daws.region={region} "
        "--add-opens=java.base/sun.nio.ch=ALL-UNNAMED "
        "--add-opens=java.base/java.nio=ALL-UNNAMED "
        "--add-exports=java.base/sun.nio.ch=ALL-UNNAMED"
    )

    spark = (
        SparkSession.builder.appName(app_name)
        .master("k8s://https://kubernetes.default.svc")
        # --- Container Image ---
        # Note: We assume the image is already set in the pod template or we use the base
        # But for dynamic allocation/executors, we specify it here.
        # Ideally, this matches the image running the notebook.
        .config(
            "spark.kubernetes.container.image",
            "statkube/spark-notebook:spark3.5.3-py3.12-1",
        )
        .config("spark.kubernetes.container.image.pullPolicy", "IfNotPresent")
        .config("spark.kubernetes.namespace", "jhub-dev")  # Default to where we run
        # --- Networking ---
        .config("spark.driver.host", driver_ip)
        .config("spark.driver.bindAddress", "0.0.0.0")
        .config("spark.driver.port", "7077")
        # --- Service Account ---
        .config("spark.kubernetes.authenticate.driver.serviceAccountName", "spark-sa")
        .config(
            "spark.kubernetes.authenticate.caCertFile",
            "/var/run/secrets/kubernetes.io/serviceaccount/ca.crt",
        )
        .config(
            "spark.kubernetes.authenticate.oauthTokenFile",
            "/var/run/secrets/kubernetes.io/serviceaccount/token",
        )
        # --- S3 / MinIO Configuration (Hadoop S3A) ---
        .config("spark.hadoop.fs.s3a.endpoint", s3_endpoint)
        .config("spark.hadoop.fs.s3a.access.key", access_key)
        .config("spark.hadoop.fs.s3a.secret.key", secret_key)
        .config("spark.hadoop.fs.s3a.path.style.access", "true")
        .config("spark.hadoop.fs.s3a.connection.ssl.enabled", "false")
        .config("spark.hadoop.fs.s3a.impl", "org.apache.hadoop.fs.s3a.S3AFileSystem")
        # --- Spark SQL Extensions: Iceberg + Delta ---
        .config(
            "spark.sql.extensions",
            "org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions,io.delta.sql.DeltaSparkSessionExtension",
        )
        # Make the built-in catalog use Delta by default
        .config(
            "spark.sql.catalog.spark_catalog",
            "org.apache.spark.sql.delta.catalog.DeltaCatalog",
        )
        # --- Java Options (Driver & Executor) ---
        .config("spark.driver.extraJavaOptions", aws_java_opts)
        .config("spark.executor.extraJavaOptions", aws_java_opts)
        .config("spark.kubernetes.executor.env.JDK_JAVA_OPTIONS", aws_java_opts)
        # --- Polaris (Iceberg) Catalog Configuration ---
        .config("spark.sql.catalog.polaris", "org.apache.iceberg.spark.SparkCatalog")
        .config("spark.sql.catalog.polaris.type", "rest")
        .config("spark.sql.catalog.polaris.uri", polaris_uri)
        .config("spark.sql.catalog.polaris.warehouse", polaris_warehouse)
        .config("spark.sql.catalog.polaris.credential", "root:s3cr3t")
        .config("spark.sql.catalog.polaris.scope", "PRINCIPAL_ROLE:ALL")
        .config("spark.sql.catalog.polaris.header.Polaris-Realm", "POLARIS")
        .config("spark.sql.catalog.polaris.oauth2-server-uri", polaris_token_uri)
        .config("spark.sql.catalog.polaris.client.region", region)
        # --- Iceberg S3 File IO (for writing data to MinIO) ---
        .config(
            "spark.sql.catalog.polaris.io-impl", "org.apache.iceberg.aws.s3.S3FileIO"
        )
        .config("spark.sql.catalog.polaris.s3.endpoint", s3_endpoint)
        .config("spark.sql.catalog.polaris.s3.access-key-id", access_key)
        .config("spark.sql.catalog.polaris.s3.secret-access-key", secret_key)
        .config("spark.sql.catalog.polaris.s3.path-style-access", "true")
        # --- Executor Config ---
        .config("spark.executor.memory", "512m")
        .config("spark.kubernetes.executor.deleteOnTermination", "false")
        # --- Environment Variables for Executors (Backup) ---
        .config("spark.executorEnv.AWS_ACCESS_KEY_ID", access_key)
        .config("spark.executorEnv.AWS_SECRET_ACCESS_KEY", secret_key)
        .config("spark.executorEnv.AWS_REGION", region)
    )

    # --- OpenLineage Configuration (DataHub Lineage) ---
    # Only enable if explicitly requested (requires DataHub running)
    if enable_lineage:
        spark = (
            spark.config("spark.openlineage.transport.type", "http")
            .config(
                "spark.openlineage.transport.url",
                f"{datahub_gms_url}/openapi/openlineage/",
            )
            .config("spark.openlineage.namespace", openlineage_namespace)
            .config("spark.openlineage.parentJobNamespace", openlineage_namespace)
            .config("spark.openlineage.parentJobName", app_name)
            .config(
                "spark.extraListeners",
                "io.openlineage.spark.agent.OpenLineageSparkListener",
            )
        )

    return spark.getOrCreate()
