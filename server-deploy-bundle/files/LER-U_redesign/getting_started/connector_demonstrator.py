# ---
# jupyter:
#   jupytext:
#     cell_metadata_filter: tags
#     formats: ipynb,py:percent
#     notebook_metadata_filter: -widgets,-varInspector
#     text_representation:
#       extension: .py
#       format_name: percent
#       format_version: '1.3'
#       jupytext_version: 1.18.1
#   kernelspec:
#     display_name: Spark K8s (Python 3.12)
#     language: python
#     name: spark-k8s
# ---

# %% [markdown]
"""
# SparkConnector Demonstration (k3d/JupyterHub + Spark-on-Kubernetes)

This demo supports **two ways** to choose environment (`sbx/dev/test/prod`):

1) **JupyterHub profile selection (recommended best practice)**
   - The profile injects `DST_ENV`, `DST_BUCKET`, `POLARIS_WAREHOUSE`.

2) **Git branch mapping (optional legacy behavior)**
   - If a git repo is present in the notebook pod, this demo can map the current
     branch to an environment and set the same env vars *before* Spark starts.

Branch → Environment mapping used here:
- `feature/*` (and unknown) → `sbx`
- `dev` / `develop` → `dev`
- `release/*` or `hotfix/*` → `test`
- `main` / `master` → `prod`

Notes:
- MinIO credentials are **user credentials** (MINIO_USER/MINIO_PASSWORD) and are
  provided at spawn time by the JupyterHub start form.
- This file is mounted into the notebook pod at `/opt/leru/getting_started`.
"""

# %% [markdown]
# ## 1) Verify LER-U mount

# %%
import os
import utilities

print("utilities.__file__ =", utilities.__file__)
print("/opt/leru exists    =", os.path.exists("/opt/leru"))

# %% [markdown]
# ## 2) Optional: derive sbx/dev/test/prod from git branch

# %%
import subprocess
from pathlib import Path


def _git_branch(repo_dir: str | None = None) -> str | None:
    """Return current git branch name, or None if not a git repo."""
    cmd = ["git"]
    if repo_dir:
        cmd += ["-C", repo_dir]
    cmd += ["rev-parse", "--abbrev-ref", "HEAD"]
    try:
        out = subprocess.check_output(cmd, stderr=subprocess.DEVNULL).decode().strip()
        return None if out in ("", "HEAD") else out
    except Exception:
        return None


def _branch_to_env(branch: str | None) -> str:
    if not branch:
        return "sbx"
    if branch.startswith("feature/"):
        return "sbx"
    if branch in ("dev", "develop"):
        return "dev"
    if branch.startswith(("release/", "hotfix/")):
        return "test"
    if branch in ("main", "master"):
        return "prod"
    return "sbx"


# Choose where to look for git:
# - If you have this repo cloned in the pod, prefer it
# - Otherwise use current working directory
repo_candidate = "/home/jovyan/spark-k8-hub"
repo_dir = repo_candidate if Path(repo_candidate, ".git").exists() else None

branch = _git_branch(repo_dir)
env_from_git = _branch_to_env(branch)

print("git_repo_dir =", repo_dir or "(none)")
print("git_branch   =", branch)
print("env_from_git =", env_from_git)

# Toggle: set to True if you want git to override the JupyterHub profile env vars
USE_GIT_FOR_ENV = True

if USE_GIT_FOR_ENV:
    os.environ["DST_ENV"] = env_from_git
    os.environ["DST_BUCKET"] = f"s3a://{env_from_git}"
    os.environ["POLARIS_WAREHOUSE"] = env_from_git
    # optional for debugging
    if branch:
        os.environ["DST_GIT_BRANCH"] = branch

print("DST_ENV          =", os.environ.get("DST_ENV"))
print("DST_BUCKET       =", os.environ.get("DST_BUCKET"))
print("POLARIS_WAREHOUSE=", os.environ.get("POLARIS_WAREHOUSE"))

# %% [markdown]
# ## 3) Create Spark session via SparkConnector

# %%
from utilities.spark_connector import SparkConnector

connector = SparkConnector(size="XS", force_new=True)
spark = connector.session

print("\n--- Connector env ---")
print("env_name      =", connector.env.env_name)
print("runtime       =", connector.env.runtime)
print("spark_master  =", connector.env.spark_master)
print("bucket        =", connector.env.bucket)
print("catalog_type  =", connector.env.catalog_type)

# %% [markdown]
# ## 4) Spark sanity

# %%
print("count =", spark.range(1000).count())

# %% [markdown]
# ## 5) Delta write/read to the selected bucket

# %%
path = f"{connector.env.bucket}/demo/connector_demonstrator_env_select/delta_table"
(
    spark.range(10)
    .withColumnRenamed("id", "n")
    .write.format("delta")
    .mode("overwrite")
    .save(path)
)

print("Wrote Delta to:", path)
print("Read back:")
spark.read.format("delta").load(path).show()

# %% [markdown]
# ## 6) Polaris/Iceberg smoke test (uses POLARIS_WAREHOUSE / catalog)

# %%
try:
    # Catalog is always named "polaris" in Spark config, but warehouse/catalog name comes from env.
    spark.sql("CREATE DATABASE IF NOT EXISTS polaris.demo").show()
    spark.sql("DROP TABLE IF EXISTS polaris.demo.users")
    spark.sql(
        """
        CREATE TABLE polaris.demo.users (
            id INT,
            name STRING
        )
        USING iceberg
        """
    )
    spark.sql("INSERT INTO polaris.demo.users VALUES (1, 'Alice'), (2, 'Bob')")
    spark.sql("SELECT * FROM polaris.demo.users").show()
    print("✅ Polaris/Iceberg smoke test OK")
except Exception as e:
    print("⚠️ Polaris/Iceberg smoke test skipped/failed:")
    print(e)

# %% [markdown]
# ## 7) Cleanup

# %%
connector.stop()
print("Stopped Spark session")

# %%
