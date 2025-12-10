# Base image - override for on-prem registries
# Internet: docker build -t statkube/spark-notebook:spark3.5.3-py3.12-1 .
# On-prem:  docker build --build-arg BASE_IMAGE=srvnexus1:80888/statkube/spark-base:spark3.5.3-py3.12-1 -t ...
ARG BASE_IMAGE=statkube/spark-base:spark3.5.3-py3.12-1

FROM ${BASE_IMAGE}

ENV DEBIAN_FRONTEND=noninteractive \
    HOME=/home/jovyan \
    JUPYTER_ALLOW_ROOT=1 \
    PYSPARK_PYTHON=python3 \
    PYSPARK_DRIVER_PYTHON=python3

# Install JupyterLab and extensions
RUN uv pip install --system --no-cache \
      jupyterlab \
      notebook \
      jupytext \
      ipykernel \
      jupyterhub \
      black \
      isort \
      flake8 \
      gitpython \
      jupyterlab-git \
      nbstripout

RUN python -m ipykernel install --name spark-k8s --display-name "Spark K8s (Python 3.12)"

# Create home directory early for git config
RUN mkdir -p /home/jovyan && touch /home/jovyan/.gitconfig

# Configure git for JupyterLab (system-wide)
RUN git config --system init.defaultBranch main && \
    git config --system core.editor "nano" && \
    git config --system credential.helper cache

# Configure nbstripout as a git filter (system-wide, so it applies to all repos)
RUN git config --system filter.nbstripout.clean "nbstripout" && \
    git config --system filter.nbstripout.smudge cat && \
    git config --system filter.nbstripout.required true && \
    git config --system diff.ipynb.textconv "nbstripout -t"

# --- NEW: Add Template Notebooks & Connector ---
COPY getting_started.py /home/jovyan/getting_started.py
COPY connector.py /home/jovyan/connector.py
COPY 01_polaris_demo.ipynb /home/jovyan/01_polaris_demo.ipynb
COPY 02_iceberg_demo.ipynb /home/jovyan/02_iceberg_demo.ipynb
COPY 03_delta_demo.ipynb /home/jovyan/03_delta_demo.ipynb
COPY 04_metrics_demo.py /home/jovyan/04_metrics_demo.py
RUN jupytext --to notebook /home/jovyan/04_metrics_demo.py
COPY 05_datahub_lineage_demo.ipynb /home/jovyan/05_datahub_lineage_demo.ipynb
COPY 06_pipeline_metrics_demo.ipynb /home/jovyan/06_pipeline_metrics_demo.ipynb

# Add dst_metrics package
COPY dst_metrics /home/jovyan/dst_metrics

# Ensure permissions
RUN chown -R 1000:1000 /home/jovyan/
# ----------------------------------

# JupyterHub chart/KubeSpawner will set the command; we just provide the tools.
RUN mkdir -p /home/jovyan && chmod -R a+rwx /home/jovyan
WORKDIR /home/jovyan
