#!/usr/bin/env bash
#
# Installs the local toolchain used by this repository:
#   Go, kubectl, Kind, controller-gen
#
# This script is intended for developers without sudo access. It installs into:
#   GOROOT: $HOME/.local/go
#   GOPATH: $HOME/go
#   ~/bin  : kubectl and kind
#
# Usage:
#   scripts/setup-tools.sh
set -euo pipefail

HOMEDIR="${HOME}"
LOCAL_DIR="${HOMEDIR}/.local"
GOROOT="${LOCAL_DIR}/go"
GOPATH="${HOMEDIR}/go"
BIN_DIR="${HOMEDIR}/bin"

mkdir -p "${LOCAL_DIR}" "${GOPATH}" "${BIN_DIR}"

if ! command -v go >/dev/null 2>&1 && [[ ! -x "${GOROOT}/bin/go" ]]; then
  echo "==> Installing Go for linux/arm64 into ${GOROOT}"
  GO_VERSION="$(curl -s https://go.dev/VERSION?m=text | head -1)"
  curl -sSLo /tmp/"${GO_VERSION}".linux-arm64.tar.gz "https://go.dev/dl/${GO_VERSION}.linux-arm64.tar.gz"
  tar -C "${LOCAL_DIR}" -xzf /tmp/"${GO_VERSION}".linux-arm64.tar.gz
  rm -f /tmp/"${GO_VERSION}".linux-arm64.tar.gz
fi

export PATH="${GOROOT}/bin:${GOPATH}/bin:${BIN_DIR}:${PATH}"

if ! command -v kubectl >/dev/null 2>&1 && [[ ! -x "${BIN_DIR}/kubectl" ]]; then
  echo "==> Installing kubectl into ${BIN_DIR}"
  K8S_VERSION="$(curl -sL https://dl.k8s.io/release/stable.txt)"
  curl -sSLo "${BIN_DIR}/kubectl" "https://dl.k8s.io/release/${K8S_VERSION}/bin/linux/arm64/kubectl"
  chmod +x "${BIN_DIR}/kubectl"
fi

if ! command -v kind >/dev/null 2>&1 && [[ ! -x "${BIN_DIR}/kind" ]]; then
  echo "==> Installing kind into ${BIN_DIR}"
  curl -sSLo "${BIN_DIR}/kind" "https://github.com/kubernetes-sigs/kind/releases/latest/download/kind-linux-arm64"
  chmod +x "${BIN_DIR}/kind"
fi

if ! command -v controller-gen >/dev/null 2>&1 && [[ ! -x "${GOPATH}/bin/controller-gen" ]]; then
  echo "==> Installing controller-gen into ${GOPATH}/bin"
  GOBIN="${GOPATH}/bin" go install sigs.k8s.io/controller-tools/cmd/controller-gen@latest
fi

echo
echo "Toolchain ready. Add to your shell profile:"
echo 'export GOROOT="$HOME/.local/go"'
echo 'export GOPATH="$HOME/go"'
echo 'export PATH="$GOROOT/bin:$GOPATH/bin:$HOME/bin:$PATH"'
