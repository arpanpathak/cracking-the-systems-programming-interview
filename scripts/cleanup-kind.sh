#!/usr/bin/env bash
#
# Stops the local operator and deletes the Kind cluster created by verify-kind.sh.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CLUSTER_NAME="${CLUSTER_NAME:-systems-interview}"
PID_FILE="${REPO_ROOT}/operator/bin/operator.pid"

if [[ -f "${PID_FILE}" ]]; then
  PID="$(cat "${PID_FILE}")"
  if kill -0 "${PID}" 2>/dev/null; then
    echo "Stopping operator pid ${PID}"
    kill "${PID}" 2>/dev/null || true
  fi
  rm -f "${PID_FILE}"
fi

if kind get clusters 2>/dev/null | grep -qx "${CLUSTER_NAME}"; then
  echo "Deleting Kind cluster ${CLUSTER_NAME}"
  kind delete cluster --name "${CLUSTER_NAME}"
else
  echo "Kind cluster ${CLUSTER_NAME} does not exist"
fi
