Server deploy bundle (spark-k8-hub / stat-kube-zero)

What this bundle contains
- ansible/playbooks/k3d_dev.yml
  - on-prem path uses k8s/jupyterhub/values-k3d-onprem.yaml (persistent home, no hostPath mounts)
- k8s/jupyterhub/values-base.yaml
  - spawn form: environment dropdown (sbx/dev/test/prod) + MinIO username/password
  - sets DST_ENV, DST_BUCKET=s3a://<env>, POLARIS_WAREHOUSE=<env>
  - adds /home/jovyan/leru symlink if /opt/leru exists (harmless otherwise)
- k8s/jupyterhub/values-onprem.yaml
  - image registry/tag for on-prem notebook + hub images
- k8s/jupyterhub/values-k3d-onprem.yaml
  - enables persistent user home via dynamic PVC
- k8s/polaris/polaris-bootstrap-onprem.yaml
  - bootstraps Polaris catalogs: sbx/dev/test/prod (+ polaris)
- k8s/spark-operator/values-base.yaml
  - fixes webhook cert write by mounting writable dir
- LER-U_redesign/utilities + LER-U_redesign/getting_started
  - include your updated LER-U utilities + demos (if you want to push to Azure DevOps)

IMPORTANT NOTES
1) MinIO
- You said the server already runs MinIO.
- Do NOT apply our minio-onprem.yaml from this repo unless you want to replace it.
- Ensure your existing MinIO has buckets: sbx/dev/test/prod and user policies.

2) Persistent home (PVC)
- This is required if users clone Azure DevOps inside JupyterLab and expect it to persist.

Commands to run on the server
A) Copy files into your deployed repo (stat-kube-zero)
- Copy ansible/playbooks/k3d_dev.yml
- Copy k8s/jupyterhub/values-base.yaml
- Copy k8s/jupyterhub/values-onprem.yaml
- Copy k8s/jupyterhub/values-k3d-onprem.yaml
- Copy k8s/polaris/polaris-bootstrap-onprem.yaml
- Copy k8s/spark-operator/values-base.yaml

B) Deploy via Ansible (on-prem inventory)
cd <your-deployed-repo>
ansible-playbook -i ansible/inventory/onprem.yml ansible/playbooks/k3d_dev.yml

C) Polaris bootstrap (Job is immutable: delete then apply)
kubectl delete job -n polaris polaris-bootstrap-catalog --ignore-not-found
kubectl apply -f k8s/polaris/polaris-bootstrap-onprem.yaml
kubectl logs -n polaris job/polaris-bootstrap-catalog --tail=200

D) Verify user PVCs exist after user starts server
kubectl get pvc -n jhub-dev

E) User workflow (JupyterLab)
- Start server: select environment + enter MinIO user/pass
- Clone Azure DevOps repo into /home/jovyan/<repo> using JupyterLab Git UI
