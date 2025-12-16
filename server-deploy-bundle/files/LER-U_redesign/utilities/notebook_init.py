# ensure repo root is importable BEFORE importing utilities.*
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from pyspark.sql import SparkSession
from utilities.spark_connector import get_spark_session
from utilities import env_resolver as er
from utilities import dwh_bootstrap as bs

# presets + notebook overrides
PRESETS = {
    "small":  dict(cores_max=8,  executor_cores=4, executor_memory="8g",  memory_overhead="2g"),
    "medium": dict(cores_max=24, executor_cores=4, executor_memory="12g", memory_overhead="2g"),
    "large":  dict(cores_max=48, executor_cores=4, executor_memory="16g", memory_overhead="3g"),
}

ns = get_ipython().user_ns  # type: ignore[name-defined]
preset   = ns.get("INIT_PRESET", "medium")
domains  = ns.get("INIT_DOMAINS", ["leru","elevniv6"])
do_boot  = bool(ns.get("INIT_BOOTSTRAP", True))

# restart spark to pick up new confs
try:
    s = SparkSession.getActiveSession()
    if s: s.stop()
except Exception:
    pass

cfg = PRESETS[preset]
spark = get_spark_session(**cfg, dynamic_allocation=False)

# env context
ctx = er.resolve_context()
bucket = str(ctx["bucket"])
print(f"[init] Spark {spark.version} | bucket={bucket}")

# optional bootstrap
if do_boot:
    for d in domains:
        bs.bootstrap_layers(
            spark, bucket=bucket, domain=d,
            layers=("01_indsamlet","02_skemaindlaest","03_integreret",
                    "04_transformeret","05_faerdigbehandlet","06_fortrolig","07_publiceret"),
        )
    print("[bootstrap] done")

# expose in notebook
ns.update({"spark": spark, "ctx": ctx, "bucket": bucket, "domains": domains, "PRESETS": PRESETS})
