from pyspark.sql import SparkSession
from pyspark.sql.types import (
    StructType,
    StructField,
    StringType,
    LongType,
    DoubleType,
    TimestampType,
    MapType,
    IntegerType,
)
from .core import build_record

# Define schema explicitly to avoid inference errors
METRICS_SCHEMA = StructType(
    [
        StructField("event_timestamp", TimestampType(), True),
        StructField("run_id", StringType(), True),
        StructField("layer", StringType(), True),
        StructField("project", StringType(), True),
        StructField("dataset_year", IntegerType(), True),
        StructField("description", StringType(), True),
        StructField("metric_value", DoubleType(), True),
        StructField("metric_unit", StringType(), True),
        StructField("metric_function", StringType(), True),
        StructField("job_name", StringType(), True),
        StructField("extra", MapType(StringType(), StringType()), True),
        StructField("status", StringType(), True),
        StructField("duration_ms", LongType(), True),
        # Added new columns
        StructField("table_name", StringType(), True),
        StructField("source_path", StringType(), True),
    ]
)


class SparkMetricsLogger:
    def __init__(self, table_path="s3a://polaris/metrics/activity_log", spark=None):
        self.spark = spark or SparkSession.builder.getOrCreate()
        self.table_path = table_path
        # Ensure schema migration on init (optional but good for dev)
        self._ensure_schema_evolution()

    def _ensure_schema_evolution(self):
        # Simple check: if table exists, we might need to merge schema.
        # For now, we rely on Delta's schema evolution via .option("mergeSchema", "true")
        pass

    def log_metric(self, **kwargs):
        rec = build_record(**kwargs)
        # Use the explicit schema
        df = self.spark.createDataFrame([rec], schema=METRICS_SCHEMA)

        # Enable schema merging to allow adding new columns (table_name, source_path)
        df.write.format("delta").mode("append").option("mergeSchema", "true").save(
            self.table_path
        )

        return rec["run_id"]
