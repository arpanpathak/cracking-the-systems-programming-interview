# GpuWorkload Operator

An idiomatic Kubernetes operator written with **controller-runtime** using the
Kubebuilder project layout.

- CRD group: `gpucloud.example.com`
- Kind: `GpuWorkload`
- Controller creates an owned `Deployment` and `Service` for each workload.
- When `spec.gpuCount > 0`, the container requests
  `nvidia.com/gpu: <gpuCount>` as a resource limit.
- Status reports ready/available replicas and Kubernetes conditions.

## Commands

```bash
# Run tests
go test ./...

# Generate deepcopy + CRDs (requires controller-gen in PATH)
make generate
make manifests

# Live verify on Kind
../scripts/verify-kind.sh

# Cleanup
../scripts/cleanup-kind.sh
```

## API design

See `config/crd/bases/gpucloud.example.com_gpuworkloads.yaml`.

```yaml
apiVersion: gpucloud.example.com/v1
kind: GpuWorkload
metadata:
  name: triton-demo
spec:
  image: nvcr.io/nvidia/tritonserver:24.05-py3
  replicas: 1
  gpuCount: 1
  runtimeClassName: nvidia
  servicePort: 8000
  containerPort: 8000
  command: ["tritonserver"]
  args: ["--model-repository=/models"]
```

## How the controller thinks

1. Get latest `GpuWorkload`.
2. Calculate default replicas/ports if omitted.
3. `CreateOrUpdate` the `Deployment`.
4. `CreateOrUpdate` the `Service`.
5. Read `Deployment.Status` and update CR status/conditions.
6. Owned resources are watched through owner references.
