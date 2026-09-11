#!/usr/bin/env bash
#
# Live verification of the GpuWorkload operator on Kind.
#
# Steps:
#   1. Create a Kind cluster (if not present).
#   2. Install the generated CRD.
#   3. Run `go test ./...`.
#   4. Build and start the operator locally against the Kind cluster.
#   5. Apply a CPU-safe GpuWorkload sample.
#   6. Wait for the Deployment to become Available and show evidence.
#
# Clean up with scripts/cleanup-kind.sh.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CLUSTER_NAME="${CLUSTER_NAME:-systems-interview}"
KIND_CONTEXT="kind-${CLUSTER_NAME}"
OPERATOR_LOG="${REPO_ROOT}/operator/bin/operator.log"
PID_FILE="${REPO_ROOT}/operator/bin/operator.pid"
BIN="${REPO_ROOT}/operator/bin/gpu-cloud-operator"
SAMPLE="${REPO_ROOT}/operator/config/samples/gpucloud_v1_gpuworkload_kind.yaml"

export GOROOT="${GOROOT:-$HOME/.local/go}"
export GOPATH="${GOPATH:-$HOME/go}"
export PATH="${GOROOT}/bin:${GOPATH}/bin:${HOME}/bin:${PATH}"

echo "==> Toolchain"
command -v go >/dev/null && go version
command -v kind >/dev/null && kind version
command -v kubectl >/dev/null && kubectl version --client | head -1

echo "==> Kind cluster: ${CLUSTER_NAME}"
if ! kind get clusters 2>/dev/null | grep -qx "${CLUSTER_NAME}"; then
  kind create cluster --name "${CLUSTER_NAME}"
else
  echo "cluster already exists"
fi
kubectl cluster-info --context "${KIND_CONTEXT}"

echo "==> CRD"
kubectl --context "${KIND_CONTEXT}" apply -f "${REPO_ROOT}/operator/config/crd/bases/"
kubectl --context "${KIND_CONTEXT}" wait \
  --for=condition=Established \
  crd/gpuworkloads.gpucloud.example.com \
  --timeout=60s

echo "==> Unit tests"
(
  cd "${REPO_ROOT}/operator"
  go test ./...
)

echo "==> Build operator"
mkdir -p "$(dirname "${BIN}")"
(
  cd "${REPO_ROOT}/operator"
  go build -o "${BIN}" ./cmd/main.go
)

echo "==> Start operator"
if [[ -f "${PID_FILE}" ]] && kill -0 "$(cat "${PID_FILE}")" 2>/dev/null; then
  echo "operator already running (pid $(cat "${PID_FILE}"))"
else
  "${BIN}" \
    --metrics-bind-address=127.0.0.1:18080 \
    --health-probe-bind-address=127.0.0.1:18081 \
    >"${OPERATOR_LOG}" 2>&1 &
  echo $! > "${PID_FILE}"
fi

echo "==> Wait for operator healthz"
for _ in $(seq 1 30); do
  if curl -fsS http://127.0.0.1:18081/healthz >/dev/null 2>&1; then
    echo "operator is healthy"
    break
  fi
  sleep 1
done
curl -fsS http://127.0.0.1:18081/healthz >/dev/null 2>&1 || {
  echo "operator did not become healthy; logs:"
  cat "${OPERATOR_LOG}"
  exit 1
}

echo "==> Apply GpuWorkload sample: ${SAMPLE}"
kubectl --context "${KIND_CONTEXT}" apply -f "${SAMPLE}"

WORKLOAD_NAME="triton-kind"
echo "==> Wait for Deployment ${WORKLOAD_NAME}-gpu"
kubectl --context "${KIND_CONTEXT}" rollout status \
  "deployment/${WORKLOAD_NAME}-gpu" \
  --namespace default \
  --timeout=180s

echo "==> Wait for GpuWorkload status"
kubectl --context "${KIND_CONTEXT}" wait \
  --for=jsonpath='{.status.phase}'=Ready \
  "gpuworkload/${WORKLOAD_NAME}" \
  --namespace default \
  --timeout=60s 2>/dev/null || true

echo
echo "================ LIVE VERIFICATION ================"
echo "--- GpuWorkload ---"
kubectl --context "${KIND_CONTEXT}" get gpuworkload "${WORKLOAD_NAME}" -n default -o yaml
echo
echo "--- Deployment ---"
kubectl --context "${KIND_CONTEXT}" get deployment "${WORKLOAD_NAME}-gpu" -n default -o wide
echo
echo "--- Service ---"
kubectl --context "${KIND_CONTEXT}" get service "${WORKLOAD_NAME}-svc" -n default -o wide
echo
echo "--- Pods ---"
kubectl --context "${KIND_CONTEXT}" get pods -n default -l "gpucloud.example.com/workload=${WORKLOAD_NAME}" -o wide
echo
echo "--- Operator log (tail) ---"
tail -40 "${OPERATOR_LOG}"
echo
echo "Verification complete. Cluster '${CLUSTER_NAME}' is still running."
echo "Cleanup with: scripts/cleanup-kind.sh"
