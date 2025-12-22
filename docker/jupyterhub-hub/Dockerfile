# Base image - override for on-prem registries
# Internet: docker build -t statkube/jupyterhub-hub:spark3.5.3-py3.12-1 .
# On-prem:  docker build --build-arg BASE_IMAGE=srvnexus1:80888/statkube/spark-base:spark3.5.3-py3.12-1 -t ...
ARG BASE_IMAGE=statkube/spark-base:spark3.5.3-py3.12-1

FROM ${BASE_IMAGE}

ENV DEBIAN_FRONTEND=noninteractive

# kubespawner is distributed on PyPI as jupyterhub-kubespawner
RUN pip install --no-cache-dir \
      jupyterhub \
      jupyterlab \
      jupyterhub-kubespawner \
      jupyterhub-nativeauthenticator \
      pycurl

# Ensure the jupyterhub binary is on PATH for the non-root user that the chart uses
RUN ln -s /usr/local/python/bin/jupyterhub /usr/local/bin/jupyterhub || true

COPY jupyterhub_config.py /etc/jupyterhub/jupyterhub_config.py

WORKDIR /srv/jupyterhub
