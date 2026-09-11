# 08: Testing, CI/CD, Observability

The job description asks for "high-quality code through unit testing and integration
testing" plus CI/CD. The sections below cover what that requires.

## 1. Testing pyramid for cloud SDKs and operators

```text
         ╱ E2E (Kind, real cluster, real cloud)
        ╱  Integration (envtest, testcontainers, live API)
       ╱   Unit (pure logic, fake clients)
```

- **Unit tests**: fast, deterministic; test pure logic and controllers with fakes.
- **Integration tests**: real API server/etcd, CRDs, database, HTTP stubs.
- **E2E tests**: create a cluster, install operator, apply CR, wait for status.
- **Contract tests**: SDK ↔ REST API (OpenAPI schema).
- **Property/fuzz tests**: random inputs, serialization, edge cases.

## 2. Operator testing examples

### Fake client unit test (controller-runtime)

```go
scheme := runtime.NewScheme()
clientgoscheme.AddToScheme(scheme)
gpucloudv1.AddToScheme(scheme)

c := fake.NewClientBuilder().
    WithScheme(scheme).
    WithStatusSubresource(&gpucloudv1.GpuWorkload{}).
    Build()
```

Advantages: no cluster required, fast. Limitations: no admission webhooks and no
Deployment controller.

### Envtest

- Runs `kube-apiserver` and `etcd` locally.
- Install with `setup-envtest`.
- Test CRD creation, controller reconciliation, webhooks.
- Covers CRD schema and RBAC issues.

### Kind E2E

- Full Kubernetes with real kubelet/containerd.
- Deploy or run operator against cluster.
- Create CR, wait for Deployment Available and Service endpoints.
- This is what `scripts/verify-kind.sh` does.

## 3. SDK/CLI testing

- Mock HTTP with `wiremock`/`httptest`.
- Record/replay HTTP cassettes.
- Test retries with injected failures.
- Test output formats: JSON, YAML, table.
- Test auth refresh.
- Golden-file tests for CLI output.
- Test on Windows/Linux/macOS in CI (GitHub Actions matrix).

## 4. CI/CD pipeline

Example GitHub Actions jobs:

1. Lint and format.
2. Unit tests (Rust `cargo test`, Go `go test ./...`).
3. Generate manifests; fail on dirty git.
4. Build binaries (cross-platform).
5. E2E with Kind.
6. Publish container images / artifacts.
7. Release with semantic versioning and changelog.

Real-world CI for an operator:

```yaml
jobs:
  kind-e2e:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-go@v5
        with:
          go-version: 'stable'
      - uses: engineerd/setup-kind@v0.5.0   # or use kind action
      - run: kubectl apply -f config/crd/bases/
      - run: go test ./...
      - run: go run ./cmd/main.go &         # run operator
      - run: kubectl apply -f config/samples/... 
      - run: kubectl wait --for=condition=Available deployment/...
```

## 5. Observability

- **Metrics**: Prometheus (controller-runtime exposes `/metrics` by default).
  - Work queue depth, reconcile errors, reconcile duration.
  - Business metrics: active GPU workloads, GPU allocatable vs used.
- **Logs**: structured JSON logs (`slog` in Go, `tracing` in Rust).
- **Traces**: OpenTelemetry across API, control plane, operator.
- **Alerts**:
  - `GpuWorkloadNotReady` after 10 minutes.
  - `ReconcileErrorRate > 1%`.
  - `NodeNotReady` with GPU workloads.
  - `nvidia-smi` unavailable / Xid errors.
- **Dashboards**: Grafana panels for node GPU util, temperature, memory, power, ECC.

## 6. Performance and load testing

- `k6`, `locust`, `hey` for REST APIs.
- Measure p50/p95/p99 latency, throughput, error rate.
- Test SDK retry behavior under 429/5xx.
- Profile Rust/Go with `pprof`, `perf`, `flamegraph`.
- Tuning targets: connection pools, JSON encode/decode, pagination, caching.

## Questions to expect

- Testing an operator without a GPU cluster
- Making a flaky SDK test reliable
- Metrics for a GPU cloud control plane
- Rolling out a breaking API change
- What belongs in unit tests against e2e tests
