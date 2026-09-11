# Image URL to use all building/pushing image targets
IMG ?= gpu-cloud-operator:latest
# ENVTEST_K8S_VERSION refers to the version of kubebuilder assets.
ENVTEST_K8S_VERSION ?= 1.31.0

# Get the currently used golang install path (in case GOPATH is not set)
ifeq (,$(shell go env GOPATH))
GOPATH ?= $(shell go env GOPATH)
else
GOPATH ?= $(shell go env GOPATH)
endif

CONTROLLER_GEN ?= $(shell which controller-gen)
ifeq (,$(CONTROLLER_GEN))
CONTROLLER_GEN = $(GOPATH)/bin/controller-gen
endif

.PHONY: all
all: generate manifests test

.PHONY: generate
generate: controller-gen ## Generate code (deepcopy)
	$(CONTROLLER_GEN) object:headerFile="hack/boilerplate.go.txt" paths="./..."

.PHONY: manifests
manifests: controller-gen ## Generate CRD manifests
	$(CONTROLLER_GEN) crd paths="./..." output:crd:artifacts:config=config/crd/bases
	$(CONTROLLER_GEN) rbac:roleName=manager-role paths="./..." output:rbac:artifacts:config=config/rbac

.PHONY: test
test:
	go test ./...

.PHONY: run
run:
	go run ./cmd/main.go

.PHONY: controller-gen
controller-gen:
	@if ! command -v controller-gen >/dev/null 2>&1; then \
		echo "controller-gen not found; install with: go install sigs.k8s.io/controller-tools/cmd/controller-gen@latest"; \
		exit 1; \
	fi
	@echo "controller-gen: $$(command -v controller-gen)"
