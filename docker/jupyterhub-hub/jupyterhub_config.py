import os

c = get_config()  # type: ignore[name-defined]

c.JupyterHub.ip = "0.0.0.0"
c.JupyterHub.port = 8000

c.JupyterHub.spawner_class = "kubespawner.KubeSpawner"

c.KubeSpawner.image = os.environ.get(
    "JUPYTERHUB_SINGLEUSER_IMAGE", "statkube/spark-notebook:spark4.0.1-py3.12-1"
)
c.KubeSpawner.cmd = ["python", "-m", "jupyterhub.singleuser"]

c.JupyterHub.authenticator_class = "jupyterhub.auth.DummyAuthenticator"
c.DummyAuthenticator.password = os.environ.get("JUPYTERHUB_DUMMY_PASSWORD", "test")
