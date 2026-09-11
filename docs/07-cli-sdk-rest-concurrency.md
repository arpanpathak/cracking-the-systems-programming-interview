# 07: CLI/SDK, REST, Concurrency (Python/Go/Rust)

The JD emphasizes SDKs, CLIs, RESTful services, and Python/Go/Rust. The
expectation is working code in the language claimed as a strength, together with
an account of how a cloud SDK is structured.

## 1. REST API design for GPU cloud services

A clean GPU cloud API might look like:

| Method | Path | Purpose |
|---|---|---|
| GET | `/v1/gpu-workloads` | list workloads |
| POST | `/v1/gpu-workloads` | create workload (async) |
| GET | `/v1/gpu-workloads/{id}` | get workload + status |
| PATCH | `/v1/gpu-workloads/{id}` | update/scale workload |
| DELETE | `/v1/gpu-workloads/{id}` | terminate workload |
| GET | `/v1/gpu-workloads/{id}/metrics` | GPU/network metrics |
| GET | `/v1/gpu-types` | catalog of GPU types |

Async create:

```http
HTTP/1.1 202 Accepted
Location: /v1/operations/op-123
Idempotency-Key: client-generated-key
```

The SDK should:

- authenticate once and refresh tokens,
- retry idempotent requests with exponential backoff,
- follow `Location` for long-running operations,
- surface typed errors,
- expose pagination as iterators/generators,
- support timeouts and cancellation.

## 2. Python SDK essentials

Typical structure:

```text
gpucloud/
├── client.py          # HTTP session, auth, retries
├── models.py          # dataclasses/Pydantic models
├── operations.py      # async operation polling
├── gpu_workloads.py   # resource methods
└── exceptions.py
```

Key details:

- Use `requests` or `httpx` (async) with a shared `Session`/`Client`.
- Use `tenacity` or custom retry for 429/5xx and idempotent retries.
- Use `dataclasses`/Pydantic for typed models.
- Expose `client.gpu_workloads.create(...)`.
- Cross-platform file paths/config via `platformdirs`, no shell-specific assumptions.

## 3. Go SDK essentials

```go
type Client struct {
    baseURL    string
    http       *http.Client
    token      TokenProvider
    Workloads  *WorkloadsClient
}

func New(options ...Option) (*Client, error)
func (c *Client) gpuWorkloads(ctx context.Context, id string) (*Workload, error)
```

Go SDK practices:

- `context.Context` through every call for cancellation/timeouts.
- `http.Client` with transport timeouts and connection pooling.
- Options pattern for auth, retries, user agent.
- Typed errors with `errors.Is`.
- Generate client from OpenAPI (`oapi-codegen`) or keep hand-written for control.

## 4. Rust SDK/CLI essentials

Rust is increasingly common for CLI tools because of speed, static binaries, and
cargo distribution.

Crate choices:

| Need | Crate |
|---|---|
| HTTP | `reqwest` (async) |
| JSON | `serde` / `serde_json` |
| CLI | `clap` (derive) |
| Async runtime | `tokio` |
| Errors | `thiserror`, `anyhow` |
| Table output | `comfy-table` |
| Config | `directories` |
| Testing | built-in `#[test]`, `assert_cmd` for CLI |

CLI pattern:

```text
gpucloud create workload --name demo --gpu A100 --count 4 --region us-central
gpucloud get workload demo -o json
gpucloud logs demo --follow
```

## 5. Concurrency patterns to know

### Token bucket rate limiter

Allows burst `capacity` tokens, refills at `rate` per second. In Rust this is a
`tokio::sync::Mutex` or a set of atomics.

### Worker pool

A queue of jobs, N workers, results channel. This models CLI batch operations,
event processing, and multi-threaded API calls.

### Cancellation/timeouts

- Rust: `tokio::time::timeout`, `CancellationToken`.
- Go: `context.WithTimeout`.
- Python: `asyncio.wait_for`.

### Backpressure and retries

- Bounded channels; an unbounded channel removes backpressure.
- Retry with jitter, honoring `Retry-After`.
- Idempotency keys for non-safe methods.

### Distributed patterns

- Distributed rate limit: Redis token bucket / GCRA.
- Leaky bucket for API protection.
- Consistent hashing for sharded queues.
- Outbox pattern for reliable event publishing.

## 6. Code generation

The JD mentions code generation as a plus. Real-world usage:

- OpenAPI → Python/Go/Rust client.
- protobuf → gRPC code.
- CRD types → client (controller-gen, client-gen).
- Templates for CLI project scaffolding.
- SDK tools commonly ship generated API clients.

## Exercises

1. Write a typed Rust client method that retries 429s.
2. Write a Python generator that pages through all workloads.
3. Write a Go method that streams logs from a pod-like API.
4. How an SDK is versioned when the REST API changes.
5. Explain how a CLI should handle auth expiry and refresh.
