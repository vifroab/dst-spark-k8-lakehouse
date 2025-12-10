# ---
# jupyter:
#   jupytext:
#     text_representation:
#       extension: .py
#       format_name: percent
#       format_version: '1.3'
#       jupytext_version: 1.14.0
#   kernelspec:
#     display_name: Spark K8s (Python 3.12)
#     language: python
#     name: spark-k8s
# ---

# %% [markdown]
# # Metric Logger Demo
#
# This notebook demonstrates how to use the `dst_metrics` package to log job metrics and data metrics to the lakehouse.

# %%
from dst_metrics.context import SparkMetricContext
from dst_metrics.spark_logger import SparkMetricsLogger
from dst_metrics.utils import count_files, df_count, df_avg, df_error_count
from pyspark.sql import SparkSession

spark = (
    SparkSession.builder.appName("DST Metrics Demo")
    .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension")
    .config(
        "spark.sql.catalog.spark_catalog",
        "org.apache.spark.sql.delta.catalog.DeltaCatalog",
    )
    .config("spark.master", "local[4]")
    .config("spark.driver.memory", "2g")
    .getOrCreate()
)

# %%
# Define paths
# Using /tmp/leru for demo purposes so it works out of the box.
# In production, this would be /mnt/nfs/leru/...
input_path = "/tmp/leru/input/customers"
output_path = "/tmp/leru/output/customers_joined"
orders_path = "/tmp/leru/orders"

# --- Setup Dummy Data for Demo ---
import os

os.makedirs(input_path, exist_ok=True)

# Create customers CSV
spark.range(10).selectExpr("id as customer_id", "id * 100 as amount").write.mode(
    "overwrite"
).option("header", True).csv(input_path)

# Create orders Delta table
spark.range(10).selectExpr(
    "id as customer_id", "'order_' || id as order_id"
).write.format("delta").mode("overwrite").save(orders_path)
# -------------------------------

# %%
with SparkMetricContext(
    layer=3,
    project="leru",
    dataset_year=2024,
    description="Join customers + orders",
    job_name="join_customers_orders",
) as ctx:
    # We don't need to instantiate logger manually anymore
    # logger = SparkMetricsLogger(spark=spark)

    # ---- 1. Number of files processed ----
    file_count = count_files(input_path)
    ctx.log_metric(
        layer=3,
        project="leru",
        dataset_year=2024,
        description="Files processed",
        value=file_count,
        unit="files",
        function="count",
        job_name="file_count",
        source_path=input_path,
    )

    # ---- 2. Rows loaded ----
    df = spark.read.option("header", True).csv(input_path)
    row_count = df_count(df)
    ctx.log_metric(
        layer=3,
        project="leru",
        dataset_year=2024,
        description="Rows loaded",
        value=row_count,
        unit="rows",
        function="count",
        job_name="input_row_count",
        table_name="input_customers",
    )

    # ---- 3. Perform join ----
    orders_df = spark.read.format("delta").load(orders_path)
    joined_df = df.join(orders_df, "customer_id")

    # Rows in join result
    joined_count = df_count(joined_df)
    ctx.log_metric(
        layer=3,
        project="leru",
        dataset_year=2024,
        description="Rows joined",
        value=joined_count,
        unit="rows",
        function="count",
        job_name="join_output_count",
        table_name="output_customers_joined",
    )

    # ---- 4. Average amount column ----
    # Ensure amount is cast to double for aggregation
    joined_df = joined_df.withColumn("amount", joined_df["amount"].cast("double"))
    avg_amount = df_avg(joined_df, "amount")
    ctx.log_metric(
        layer=3,
        project="leru",
        dataset_year=2024,
        description="Average amount (orders)",
        value=avg_amount,
        unit="amount",
        function="avg",
        job_name="avg_amount",
    )

    # ---- 5. Number of error rows ----
    # Assume a boolean column `is_error` exists
    from pyspark.sql.functions import lit

    joined_df = joined_df.withColumn("is_error", lit(False))
    error_count = df_error_count(joined_df, "is_error")
    ctx.log_metric(
        layer=3,
        project="leru",
        dataset_year=2024,
        description="Error rows",
        value=error_count,
        unit="rows",
        function="count",
        job_name="error_count",
    )

    # Write result
    joined_df.write.format("delta").mode("overwrite").save(output_path)

# %% [markdown]
# ## Run 2: Simulate a Second Run
# Let's simulate running the same job again (e.g. the next day) to see how multiple runs appear in the logs.

# %%
with SparkMetricContext(
    layer=3,
    project="leru",
    dataset_year=2024,
    description="Join customers + orders (Run 2)",
    job_name="join_customers_orders",
) as ctx:
    # ... (Simulate metrics with slightly different values to show variation) ...
    ctx.log_metric(
        layer=3,
        project="leru",
        dataset_year=2024,
        description="Files processed",
        value=15,  # More files
        unit="files",
        function="count",
        job_name="file_count",
    )

    ctx.log_metric(
        layer=3,
        project="leru",
        dataset_year=2024,
        description="Rows loaded",
        value=150,  # More rows
        unit="rows",
        function="count",
        job_name="input_row_count",
    )

    ctx.log_metric(
        layer=3,
        project="leru",
        dataset_year=2024,
        description="Rows joined",
        value=148,
        unit="rows",
        function="count",
        job_name="join_output_count",
    )

# %% [markdown]
# ## Analytics: What Users Want to Know

# %% [markdown]
# ### 1. Job Execution History
# "When did this job run, and did it succeed?"

# %%
from pyspark.sql.functions import col

df_metrics = spark.read.format("delta").load(
    "/lakehouse/dst/system/metrics/activity_log"
)

# Filter for job completion events
history_df = (
    df_metrics.filter(col("metric_function") == "completion")
    .select("job_name", "event_timestamp", "run_id", "status", "duration_ms")
    .orderBy(col("event_timestamp").desc())
)

history_df.show(truncate=False)

# %% [markdown]
# ### 2. Data Volume Trends
# "How many rows are we processing over time?"

# %%
# Filter for rows joined over time
volume_df = (
    df_metrics.filter(
        (col("metric_unit") == "rows") & (col("job_name") == "join_output_count")
    )
    .select("event_timestamp", "run_id", "metric_value")
    .withColumnRenamed("metric_value", "rows_joined")
    .orderBy(col("event_timestamp").desc())
)

volume_df.show(truncate=False)

# %% [markdown]
# ### 3. View All Logged Metrics
# View the entire metrics table sorted by timestamp to see every event logged.

# %%
df_metrics.orderBy(col("event_timestamp").desc()).show(100, truncate=False)
