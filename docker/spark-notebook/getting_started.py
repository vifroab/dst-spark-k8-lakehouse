# ---
# jupyter:
#   jupytext:
#     text_representation:
#       extension: .py
#       format_name: light
#       format_version: '1.5'
#       jupytext_version: 1.14.0
#   kernelspec:
#     display_name: Spark K8s (Python 3.12)
#     language: python
#     name: spark-k8s
# ---

# # Getting Started with Spark on Kubernetes + Polaris + MinIO
#
# This notebook verifies that your environment is correctly set up to:
# 1. Connect to the Spark cluster (K8s).
# 2. Talk to MinIO (S3).
# 3. Use Polaris as the Iceberg Catalog.

import socket
from pyspark.sql import SparkSession

# 1. Get the Driver IP so Executors can connect back to us
s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
s.connect(("8.8.8.8", 80))
driver_ip = s.getsockname()[0]
s.close()

print(f"Driver IP: {driver_ip}")

# 2. Initialize Spark Session
# Note: We configure Polaris (Iceberg) + Delta + MinIO here.
spark = (
    SparkSession.builder.appName("polaris-demo")
    .master("k8s://https://kubernetes.default.svc")
    # --- Container Image ---
    .config(
        "spark.kubernetes.container.image", "statkube/spark-base:spark3.5.3-py3.12-1"
    )
    .config("spark.kubernetes.container.image.pullPolicy", "IfNotPresent")
    .config("spark.kubernetes.namespace", "default")
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
    # --- S3 / MinIO Configuration ---
    .config("spark.hadoop.fs.s3a.endpoint", "http://minio.minio.svc:9000")
    .config("spark.hadoop.fs.s3a.access.key", "admin")
    .config("spark.hadoop.fs.s3a.secret.key", "password")
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
    # --- Java 17/21 Compatibility (for executors) ---
    .config(
        "spark.driver.extraJavaOptions",
        "--add-opens=java.base/sun.nio.ch=ALL-UNNAMED --add-opens=java.base/java.nio=ALL-UNNAMED --add-exports=java.base/sun.nio.ch=ALL-UNNAMED",
    )
    .config(
        "spark.executor.extraJavaOptions",
        "--add-opens=java.base/sun.nio.ch=ALL-UNNAMED --add-opens=java.base/java.nio=ALL-UNNAMED --add-exports=java.base/sun.nio.ch=ALL-UNNAMED",
    )
    .config(
        "spark.kubernetes.executor.env.JDK_JAVA_OPTIONS",
        "--add-opens=java.base/sun.nio.ch=ALL-UNNAMED --add-opens=java.base/java.nio=ALL-UNNAMED --add-exports=java.base/sun.nio.ch=ALL-UNNAMED",
    )
    # --- Polaris (Iceberg) Catalog Configuration (REST + S3 via Polaris server) ---
    .config("spark.sql.catalog.polaris", "org.apache.iceberg.spark.SparkCatalog")
    .config("spark.sql.catalog.polaris.type", "rest")
    .config(
        "spark.sql.catalog.polaris.uri", "http://polaris.polaris.svc:8181/api/catalog"
    )
    # This is the name of the catalog we bootstrap via k8s/polaris/polaris-bootstrap.yaml
    .config("spark.sql.catalog.polaris.warehouse", "polaris")
    .config("spark.sql.catalog.polaris.credential", "root:s3cr3t")
    .config("spark.sql.catalog.polaris.scope", "PRINCIPAL_ROLE:ALL")
    .config(
        "spark.sql.catalog.polaris.header.X-Iceberg-Access-Delegation",
        "vended-credentials",
    )
    .config("spark.sql.catalog.polaris.client.region", "irrelevant")
    .config("spark.executor.memory", "512m")
    .config("spark.kubernetes.executor.deleteOnTermination", "false")
    .getOrCreate()
)

print("Spark Session Created!")

# 3. Create a Database (Namespace) in Polaris (Iceberg)
print("Creating namespace 'demo' in Polaris...")
spark.sql("CREATE DATABASE IF NOT EXISTS polaris.demo").show()

# 4. Create an Iceberg table backed by MinIO via Polaris (no hard-coded LOCATION)
print("Creating Iceberg table 'polaris.demo.users'...")
spark.sql("DROP TABLE IF EXISTS polaris.demo.users")
spark.sql("""
    CREATE TABLE polaris.demo.users (
        id INT,
        name STRING,
        age INT
    )
    USING iceberg
""").show()

# Debug: Print table properties to verify that Polaris set an S3 location
print("Table Properties (polaris.demo.users):")
spark.sql("DESCRIBE EXTENDED polaris.demo.users").show(truncate=False)

# 5. Create a Delta table backed by MinIO
print("Creating Delta table 'delta.`s3a://polaris/delta/demo/users_delta`'...")
spark.sql("""
    CREATE TABLE IF NOT EXISTS delta.`s3a://polaris/delta/demo/users_delta` (
        id INT,
        name STRING,
        age INT
    ) USING delta
""")

# 6. Write Data to Iceberg
print("Writing data to Iceberg...")
spark.sql("INSERT INTO polaris.demo.users VALUES (1, 'Alice', 30), (2, 'Bob', 25)")

# 7. Write Data to Delta
print("Writing data to Delta...")
spark.sql(
    "INSERT INTO delta.`s3a://polaris/delta/demo/users_delta` VALUES (3, 'Carol', 40), (4, 'Dave', 35)"
)

# 8. Read Data back from both
print("Reading data back from Iceberg...")
spark.sql("SELECT * FROM polaris.demo.users").show()

print("Reading data back from Delta...")
spark.sql("SELECT * FROM delta.`s3a://polaris/delta/demo/users_delta`").show()

# 7. Verify underlying S3 files (Optional check via Hadoop API)
# This confirms that files are actually landing in MinIO
fs = spark._jvm.org.apache.hadoop.fs.FileSystem.get(spark._jsc.hadoopConfiguration())
print("FileSystem accessible:", fs.getUri())

spark.stop()
