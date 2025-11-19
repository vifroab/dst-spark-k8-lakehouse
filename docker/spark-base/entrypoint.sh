#!/usr/bin/env bash
set -euo pipefail

CMD="${1:-}"
shift || true

case "${CMD}" in
  executor)
    # Spark on Kubernetes passes executor configuration via environment variables
    exec "${SPARK_HOME}/bin/spark-class" org.apache.spark.executor.CoarseGrainedExecutorBackend \
      --driver-url "${SPARK_DRIVER_URL}" \
      --executor-id "${SPARK_EXECUTOR_ID}" \
      --cores "${SPARK_EXECUTOR_CORES}" \
      --app-id "${SPARK_APPLICATION_ID}" \
      --resourceProfileId "${SPARK_RESOURCE_PROFILE_ID:-0}" \
      --hostname "${SPARK_EXECUTOR_POD_IP}"
    ;;
  "")
    # No subcommand: drop into a shell
    exec bash
    ;;
  *)
    # Fallback: execute given command
    exec "${CMD}" "$@"
    ;;
esac


