import uuid
from datetime import datetime

def build_record(
    layer,
    project,
    dataset_year,
    description,
    value,
    unit,
    function,
    job_name=None,
    extra=None,
    run_id=None,
    status=None,
    duration_ms=None,
    table_name=None,
    source_path=None
):
    """Return a dict formatted for writing to Delta."""
    return {
        "event_timestamp": datetime.utcnow(),
        "run_id": run_id or str(uuid.uuid4()),
        "layer": str(layer),
        "project": project,
        "dataset_year": int(dataset_year),
        "description": description,
        "metric_value": float(value),
        "metric_unit": unit,
        "metric_function": function,
        "job_name": job_name,
        "extra": extra or {},
        "status": status,
        "duration_ms": duration_ms,
        "table_name": table_name,
        "source_path": source_path
    }
