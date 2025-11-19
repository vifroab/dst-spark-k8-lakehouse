FROM statkube/spark-base:spark3.5.3-py3.12-1

ENV DEBIAN_FRONTEND=noninteractive \
    HOME=/home/jovyan \
    JUPYTER_ALLOW_ROOT=1 \
    PYSPARK_PYTHON=python3 \
    PYSPARK_DRIVER_PYTHON=python3

RUN uv pip install --system --no-cache \
      jupyterlab \
      notebook \
      jupytext \
      ipykernel \
      jupyterhub \
      black \
      isort \
      flake8 \
      gitpython

RUN python -m ipykernel install --name spark-k8s --display-name "Spark K8s (Python 3.12)"

# --- NEW: Add Template Notebook ---
COPY getting_started.py /home/jovyan/getting_started.py
# Ensure permissions
RUN chown -R 1000:1000 /home/jovyan/getting_started.py
# ----------------------------------

# JupyterHub chart/KubeSpawner will set the command; we just provide the tools.
RUN mkdir -p /home/jovyan && chmod -R a+rwx /home/jovyan
WORKDIR /home/jovyan

