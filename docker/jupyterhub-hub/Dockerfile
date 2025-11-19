FROM statkube/spark-base:spark4.0.1-py3.12-1

ENV DEBIAN_FRONTEND=noninteractive

# kubespawner is distributed on PyPI as jupyterhub-kubespawner
RUN pip install --no-cache-dir \
      jupyterhub \
      jupyterlab \
      jupyterhub-kubespawner

# Ensure the jupyterhub binary is on PATH for the non-root user that the chart uses
RUN ln -s "${PYENV_ROOT}/versions/3.12.7/bin/jupyterhub" /usr/local/bin/jupyterhub || true

COPY jupyterhub_config.py /etc/jupyterhub/jupyterhub_config.py

WORKDIR /srv/jupyterhub


