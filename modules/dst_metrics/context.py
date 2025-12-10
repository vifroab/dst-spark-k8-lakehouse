import uuid
import time
from .spark_logger import SparkMetricsLogger


class SparkMetricContext:
    def __init__(
        self, layer, project, dataset_year, description, job_name=None, table_path=None
    ):
        self.layer = layer
        self.project = project
        self.dataset_year = dataset_year
        self.description = description
        self.job_name = job_name
        self.table_path = table_path
        self.run_id = str(uuid.uuid4())  # Generate run_id once for the whole context

    def __enter__(self):
        self.start = time.time()
        if self.table_path:
            self.logger = SparkMetricsLogger(table_path=self.table_path)
        else:
            self.logger = SparkMetricsLogger()
        # Pass the context (self) back so the user can access run_id
        return self

    def log_metric(self, **kwargs):
        """Helper to log metrics using the shared run_id."""
        # Ensure run_id is passed if not explicitly provided
        if "run_id" not in kwargs:
            kwargs["run_id"] = self.run_id
        self.logger.log_metric(**kwargs)

    def __exit__(self, exc_type, exc, tb):
        duration_ms = int((time.time() - self.start) * 1000)
        status = "success" if exc_type is None else "failure"

        self.logger.log_metric(
            layer=self.layer,
            project=self.project,
            dataset_year=self.dataset_year,
            description=self.description,
            value=1,
            unit="job",
            function="completion",
            job_name=self.job_name,
            extra={},
            status=status,
            duration_ms=duration_ms,
            run_id=self.run_id,  # Use the same run_id
        )

        return False  # Do not suppress errors
