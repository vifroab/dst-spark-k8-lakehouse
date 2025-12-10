import os
import pandas as pd
from .core import build_record

class PythonMetricsLogger:
    def __init__(self, buffer_path="/lakehouse/dst/system/metrics_staging"):
        self.buffer_path = buffer_path
        os.makedirs(self.buffer_path, exist_ok=True)

    def log_metric(self, **kwargs):
        rec = build_record(**kwargs)
        df = pd.DataFrame([rec])
        df.to_parquet(os.path.join(self.buffer_path, f"{rec['run_id']}.parquet"))
        return rec["run_id"]

