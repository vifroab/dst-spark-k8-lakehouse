"""
dst_metrics - Metrics logging for DST data pipelines.

Usage:
    from dst_metrics import SparkMetricContext, SparkMetricsLogger
    from dst_metrics import PythonMetricsLogger
    from dst_metrics import count_files, df_count, df_avg, df_error_count
"""

from .context import SparkMetricContext
from .spark_logger import SparkMetricsLogger, METRICS_SCHEMA
from .python_logger import PythonMetricsLogger
from .core import build_record
from .utils import count_files, df_count, df_avg, df_error_count

__all__ = [
    # Main classes
    "SparkMetricContext",
    "SparkMetricsLogger",
    "PythonMetricsLogger",
    # Schema
    "METRICS_SCHEMA",
    # Core
    "build_record",
    # Utils
    "count_files",
    "df_count",
    "df_avg",
    "df_error_count",
]

