# Glossary of Distributed Systems Terms

Every distributed systems abbreviation and architectural term across the book links directly to its definition below. Each entry states the physical or consistency constraint that motivates the mechanism, its role in production infrastructure, and (where applicable) a concise Rust snippet illustrating the pattern.

### `2PC`: Two-Phase Commit {#term-2pc}

Atomic commitment protocol across distributed participants split into a prepare phase (every participant durably logs intent and votes) and a commit phase (coordinator finalizes once all votes succeed). Blocking occurs if the coordinator crashes after participants have voted `YES`, holding locks until recovery.

```rust
enum Vote { Prepared, Abort }
enum Decision { Commit, Abort }
```

### `ABR`: Adaptive Bitrate Streaming {#term-abr}

Client-driven video delivery technique that dynamically switches between encoded bitrate renditions on segment boundaries based on measured throughput and playback buffer occupancy, preventing rebuffering stalls under variable wireless bandwidth.

### `ACID`: Atomicity, Consistency, Isolation, Durability {#term-acid}

Transactional guarantee set for database systems: all-or-nothing execution (atomicity), invariant preservation (consistency), concurrency control equivalent to a serial schedule (isolation), and survival across crashes via non-volatile storage (durability).

### `Anycast`: BGP Anycast Routing {#term-anycast}

Network addressing scheme advertising the same IP prefix from multiple globally distributed Points of Presence via BGP so internet routers direct each client packet to the topologically nearest healthy edge location.

### `APNs`: Apple Push Notification Service {#term-apns}

Persistent HTTP/2 push gateway operated by Apple that multiplexes wake-up notifications over a single battery-efficient TCP connection to iOS and macOS devices when background applications are suspended.

### `AZ`: Availability Zone {#term-az}

Physically isolated datacenter facility within a cloud region equipped with independent power, cooling, and network uplinks, typically separated by 0.5 to 2 ms RTT to support synchronous quorum replication across failure domains.

### `Backpressure`: End-to-End Flow Control {#term-backpressure}

Feedback mechanism allowing a slower downstream consumer to throttle an upstream producer via bounded queues, TCP receive-window shrinkage, or HTTP/2 stream credits so memory stays bounded under overload.

```rust
// Bounded channel exerts backpressure when full
let (tx, rx) = tokio::sync::mpsc::channel::<Event>(1024);
tx.send(event).await?;
```

### `BASE`: Availability-First Soft-State Eventual Consistency {#term-base}

Availability-first consistency model (`Basically Available, Soft State, Eventual Consistency`) contrasting with ACID: systems continue serving reads and writes during partitions, tolerate transient state divergence, and converge asynchronously once communication heals.

### `BDP`: Bandwidth-Delay Product {#term-bdp}

Product of link bandwidth and round-trip latency (`B * RTT`), quantifying the bytes that must remain in flight to saturate a network path. Socket buffers smaller than the BDP starve throughput even on uncongested links.

```rust
// 10 Gbps link with 20 ms RTT requires 25 MiB in flight
let bdp_bytes: u64 = (10_000_000_000 / 8) * 20 / 1_000;
```

### `BGP`: Border Gateway Protocol {#term-bgp}

Inter-domain path-vector routing protocol exchanging IP prefix reachability across Autonomous Systems on the public internet, underpinning global traffic engineering and Anycast edge failover.

### `Bloom Filter`: Probabilistic Set Membership Structure {#term-bloom-filter}

Compact bit-array structure using `k` independent hash functions (`~10 bits` per element for 1% false positives) with zero false negatives. Storage engines and crawlers query Bloom filters in RAM to avoid expensive disk seeks for absent keys.

```rust
fn might_contain(bits: &[u64], hashes: &[u64]) -> bool {
    hashes.iter().all(|&h| {
        let idx = (h as usize) % (bits.len() * 64);
        (bits[idx / 64] & (1u64 << (idx % 64))) != 0
    })
}
```

### `Bulkhead`: Fault-Isolation Partitioning {#term-bulkhead}

Resilience pattern that isolates thread pools, connection pools, or memory quotas per tenant or downstream dependency so a slow or failing subsystem cannot exhaust shared resources for unrelated requests.

### `CAP`: Consistency, Availability, Partition Tolerance {#term-cap}

Theorem proving that during a network partition, a distributed data store must choose between linearizable consistency (rejecting writes on the minority side) and full availability (serving potentially stale or divergent state).

### `CAS`: Compare-And-Swap {#term-cas}

Atomic read-modify-write primitive that updates a memory word or database row if and only if its current value matches an expected version, forming the foundation of lock-free structures and optimistic concurrency control.

```rust
state.compare_exchange_weak(
    expected,
    next,
    Ordering::AcqRel,
    Ordering::Acquire,
)
```

### `CDC`: Change Data Capture / Content-Defined Chunking {#term-cdc}

In databases, CDC streams committed row mutations from the write-ahead log into downstream queues or caches without dual-write races. In file synchronization, content-defined chunking uses a rolling hash to anchor variable-size block boundaries on content patterns so insertions preserve downstream chunk hashes.

### `CDE`: Cardholder Data Environment {#term-cde}

Network-segmented infrastructure scope storing, processing, or transmitting raw payment card numbers under PCI-DSS, minimized by replacing Primary Account Numbers with opaque vault tokens at the edge.

### `CDN`: Content Delivery Network {#term-cdn}

Globally distributed hierarchy of edge caching proxies that terminate TLS near end users and serve static assets, media segments, and cacheable API responses without traversing backhaul links to the origin datacenter.

### `Circuit Breaker`: Fail-Fast Overload Protection {#term-circuit-breaker}

State machine (`Closed -> Open -> Half-Open`) wrapping remote RPC calls that trips open when downstream error rates or timeouts breach a threshold, rejecting traffic immediately to prevent cascading thread exhaustion and allow recovery.

### `Consistent Hashing`: Minimal-Movement Key Partitioning {#term-consistent-hashing}

Ring-based partitioning scheme mapping both keys and server virtual nodes onto a circular hash space so adding or removing a storage node relocates only `1/N` of keys rather than rehashing the entire dataset.

### `CRDT`: Conflict-Free Replicated Data Type {#term-crdt}

Data structure whose state merges or operations are mathematically associative, commutative, and idempotent, guaranteeing strong eventual consistency across replicas without a central locking coordinator.

### `DASH`: Dynamic Adaptive Streaming over HTTP {#term-dash}

Open ISO standard for adaptive bitrate media delivery using XML Media Presentation Description (MPD) manifests and chunked HTTP byte-range or segment requests compatible with standard CDN caches.

### `DNS`: Domain Name System {#term-dns}

Hierarchical distributed directory translating human-readable hostnames into IPv4/IPv6 addresses and service records, also leveraged for geographic traffic steering and coarse load balancing with TTL-governed caching.

### `ECMP`: Equal-Cost Multi-Path Routing {#term-ecmp}

Stateless L3/L4 router hashing over the packet 5-tuple (source/destination IP, ports, protocol) that spreads flows evenly across multiple equal-cost next-hop load balancers without per-connection router state.

### `Epoch`: Monotonic Generation Counter {#term-epoch}

Strictly increasing logical version number incremented on leadership changes, membership reconfigurations, or garbage-collection barriers to order concurrent events and fence stale nodes.

### `Erasure Coding`: Parity-Based Storage Redundancy {#term-erasure-coding}

Reed-Solomon encoding that splits an object into `k` data shards and `m` parity shards so any `k` of `k + m` shards reconstruct the original data, achieving higher durability than 3-way replication at roughly `1.3x to 1.5x` storage overhead.

### `Eventual Consistency`: Asynchronous Convergence Model {#term-eventual-consistency}

Weak consistency guarantee ensuring that if no new updates arrive for a given key, all replicas eventually converge to the identical value, trading immediate read freshness for low latency and partition availability.

### `FCM`: Firebase Cloud Messaging {#term-fcm}

Cross-platform push notification gateway operated by Google that maintains persistent multiplexed connections to Android and web clients for low-power asynchronous message delivery.

### `Fencing Token`: Monotonic Lease Authority Guard {#term-fencing-token}

Strictly increasing integer issued by a lock service or consensus leader on every lease acquisition; storage servers reject any write carrying a token lower than the highest token already observed, preventing zombie leaders from corrupting state after GC pauses.

```rust
fn write_guarded(store: &mut Store, token: u64, key: &str, val: &[u8]) -> Result<(), Error> {
    if token < store.max_seen_token {
        return Err(Error::StaleFencingToken);
    }
    store.max_seen_token = token;
    store.put(key, val)
}
```

### `FIX`: Financial Information eXchange Protocol {#term-fix}

Standardized session and application messaging protocol used by institutional trading firms and brokerages to submit orders and receive execution reports, often paired with binary SBE payloads on low-latency venues.

### `FST`: Finite State Transducer {#term-fst}

Immutable directed acyclic automaton that shares both common prefixes and common suffixes across sorted keys while attaching numeric weights or output offsets, powering compact off-heap autocomplete and search indexes.

### `GCRA`: Generic Cell Rate Algorithm {#term-gcra}

Single-variable leaky-bucket rate limiter tracking a Theoretical Arrival Time (`TAT`) per key, enforcing exact smooth pacing and burst allowance using one atomic 64-bit timestamp instead of per-request lists.

```rust
fn allow_gcra(tat_ns: &mut u64, now_ns: u64, emission_ns: u64, burst_ns: u64) -> bool {
    let allow_at = tat_ns.saturating_sub(burst_ns);
    if now_ns < allow_at {
        return false;
    }
    *tat_ns = (*tat_ns).max(now_ns) + emission_ns;
    true
}
```

### `Group Commit`: Amortized Write-Ahead Log Flushing {#term-group-commit}

Storage optimization that batches concurrent transactions arriving during an active `fsync` into a single sequential WAL flush, multiplying write throughput while preserving strict durability for every acknowledged request.

### `gRPC`: High-Performance Remote Procedure Call Framework {#term-grpc}

RPC framework layered over HTTP/2 and Protocol Buffers supporting multiplexed bidirectional streaming, deadline propagation, typed code generation, and pluggable client-side load balancing.

### `H3`: Hexagonal Hierarchical Spatial Index {#term-h3}

Geospatial indexing system developed by Uber that partitions the globe into hierarchical hexagonal cells, offering uniform neighbor distances (unlike rectangular grids) for low-latency nearby-driver and spatial proximity queries.

### `Hedged Request`: Tail-Latency Duplicate Dispatch {#term-hedged-request}

Technique that dispatches a secondary read request to another replica if the primary request exceeds a short delay threshold (such as the P95 latency), cancelling the slower response to cut P99 tail latency with modest extra load.

### `HLC`: Hybrid Logical Clock {#term-hlc}

Timestamp combining physical wall-clock time (`pt`) with a logical counter (`lc`) so events stay closely bounded to NTP/PTP physical time while strictly capturing causal happens-before ordering across distributed nodes.

### `HLL`: HyperLogLog Cardinality Sketch {#term-hll}

Probabilistic register array estimating distinct element counts within `< 1%` standard error using roughly `12 KiB` of associatively mergeable memory, widely used for unique-visitor and ad-click counting.

### `HLS`: HTTP Live Streaming {#term-hls}

Apple-originated adaptive media protocol dividing audio/video streams into short immutable segments (`.ts` or `.m4s`) referenced by `.m3u8` playlists served over standard HTTP CDNs.

### `HSM`: Hardware Security Module {#term-hsm}

Tamper-resistant physical cryptographic appliance that generates, stores, and applies encryption and signing keys inside dedicated silicon so raw key material never enters host RAM.

### `HTTP/2`: Multiplexed Binary HTTP Protocol {#term-http-2}

Binary framing revision of HTTP supporting concurrent multiplexed streams over a single TCP connection, HPACK header compression, and stream prioritization, though still subject to TCP-level head-of-line blocking on packet loss.

### `HTTP/3`: QUIC-Based HTTP Protocol {#term-http-3}

Latest HTTP specification running over UDP-based QUIC so independent logical streams recover from packet loss without stalling sibling streams, while integrating TLS 1.3 into a 1-RTT or 0-RTT handshake.

### `Idempotency`: Safe Retry Invariance {#term-idempotency}

Property guaranteeing that applying the same operation multiple times produces the identical system state as applying it once, enforced in distributed APIs via client-generated idempotency keys persisted atomically with the business mutation.

### `IOPS`: Input/Output Operations Per Second {#term-iops}

Storage device throughput metric counting discrete random read or write operations completed per second, distinguishing random-access NVMe SSD capacity from sequential bandwidth limits.

### `ITCH`: Market Data Dissemination Protocol {#term-itch}

Ultra-low-latency binary multicast feed protocol (pioneered by NASDAQ) broadcasting every order addition, modification, cancellation, and trade tick so subscribers can reconstruct an exact limit order book locally.

### `JSON`: JavaScript Object Notation {#term-json}

Human-readable UTF-8 text interchange format standard for public REST APIs, trading higher CPU parsing cost and wire verbosity for universal debuggability compared to binary schemas like Protobuf.

### `KRaft`: Kafka Raft Metadata Mode {#term-kraft}

Native Raft-based metadata consensus quorum built directly into Apache Kafka, replacing external ZooKeeper clusters so partition leadership elections and metadata recovery scale to millions of partitions.

### `L4`: Layer-4 Transport Load Balancer {#term-l4}

High-throughput packet-level load balancer routing TCP/UDP flows using IP addresses and ports without terminating TLS or inspecting HTTP payloads, often paired with Direct Server Return (DSR).

### `L7`: Layer-7 Application Load Balancer {#term-l7}

Reverse proxy terminating TLS and parsing HTTP/gRPC headers to perform path-based routing, prefix sharding, authentication, rate limiting, and connection pooling toward backend services.

### `LFU`: Least Frequently Used Eviction Policy {#term-lfu}

Cache eviction strategy discarding items with the lowest historical access count (often decayed via TinyLFU sketches) to protect hot working sets from one-time scan pollution.

### `Linearizability`: Strong Single-Copy Consistency {#term-linearizability}

Strongest single-object consistency model requiring every operation to appear to take effect atomically at a single point in real time between its invocation and response, matching the illusion of one sequential machine.

### `LRU`: Least Recently Used Eviction Policy {#term-lru}

Cache eviction algorithm combining a hash map with a doubly linked list to evict the entry untouched for the longest interval in `O(1)` time, well suited to workloads with strong temporal locality.

### `LSM`: Log-Structured Merge-Tree {#term-lsm}

Write-optimized storage engine converting random mutations into sequential appends across an in-memory MemTable, a durable WAL, and immutable sorted disk levels (SSTables) merged asynchronously via background compaction.

### `Merkle Tree`: Hierarchical Cryptographic Hash Tree {#term-merkle-tree}

Binary or n-ary tree in which each leaf hashes a data block or key range and each internal node hashes its children's digests, allowing two replicas to pinpoint divergent ranges in `O(log N)` network round trips.

### `mTLS`: Mutual Transport Layer Security {#term-mtls}

Cryptographic authentication mode in which both client and server present and verify X.509 certificates during the TLS handshake, enforcing zero-trust service-to-service identity inside microservices meshes.

### `MVCC`: Multi-Version Concurrency Control {#term-mvcc}

Database concurrency technique retaining timestamped versions of modified rows so snapshot readers observe a consistent historical view without blocking concurrent writers or taking read locks.

### `NTP`: Network Time Protocol {#term-ntp}

Packet-exchange protocol synchronizing host system clocks against stratum time servers over commodity networks, typically bounded within 1 to 50 ms of UTC and vulnerable to backward step adjustments.

### `NVMe`: Non-Volatile Memory Express {#term-nvme}

High-concurrency PCIe storage interface offering thousands of parallel submission and completion queues directly attached to flash controllers, delivering sub-100-microsecond random access and millions of IOPS.

### `OLAP`: Online Analytical Processing {#term-olap}

Columnar query workload optimized for scanning, filtering, and aggregating millions of historical rows (such as ClickHouse, Pinot, or Scuba) rather than single-row transactional updates.

### `OLTP`: Online Transactional Processing {#term-oltp}

Row-oriented database workload serving high volumes of short, indexed, ACID point reads and writes (such as payments, bookings, and metadata commits) with strict millisecond latency targets.

### `OT`: Operational Transformation {#term-ot}

Collaborative editing algorithm that rewrites incoming positional operations against concurrent edits already applied on a canonical server timeline so all editors converge to identical document text.

### `OUCH`: Low-Latency Order Entry Protocol {#term-ouch}

Minimalist fixed-width binary TCP protocol used on electronic stock exchanges to submit, replace, and cancel orders with deterministic microsecond parsing overhead and zero variable-length text tags.

### `Outbox`: Transactional Outbox Pattern {#term-outbox}

Reliability pattern writing domain state changes and outbound event records in the same local ACID database transaction, allowing an asynchronous relay or CDC tailer to publish events to Kafka with at-least-once certainty.

```rust
// Atomic SQL transaction writes both ledger row and outbox event
tx.execute("INSERT INTO payments (id, cents) VALUES ($1, $2)", &[&id, &cents])?;
tx.execute("INSERT INTO outbox (event_id, payload) VALUES ($1, $2)", &[&ev_id, &blob])?;
tx.commit()?;
```

### `P99`: 99th Percentile Tail Latency {#term-p99}

Latency threshold below which 99% of observed requests complete. In fan-out architectures querying 50 backend shards in parallel, a 1% per-shard slowdown affects nearly 40% of end-user requests, making P99 more informative than mean latency.

### `PACELC`: Partition-Availability-Consistency / Else-Latency-Consistency {#term-pacelc}

Extension of CAP stating that during a network partition (`P`) a system trades off availability (`A`) versus consistency (`C`), and even during normal operation (`E`) it still trades off low latency (`L`) versus strong consistency (`C`).

### `Paxos`: Fault-Tolerant Consensus Protocol {#term-paxos}

Foundational distributed consensus family guaranteeing safety (a single agreed value per slot) across asynchronous networks with crash failures as long as a strict majority quorum (`f + 1` of `2f + 1`) remains reachable.

### `PCI-DSS`: Payment Card Industry Data Security Standard {#term-pci-dss}

Compliance and security framework mandating encryption, network isolation, strict access controls, and immutable audit logging for any system storing, processing, or transmitting payment cardholder data.

### `PoP`: Point of Presence {#term-pop}

Regional edge facility hosting CDN caches, Anycast routers, and TLS termination proxies close to end-user ISPs to cut round-trip latency and absorb volumetric traffic before it reaches core datacenters.

### `Protobuf`: Protocol Buffers {#term-protobuf}

Compact, schema-driven binary serialization format using numeric field tags and varint encoding, enabling backward-compatible API evolution and fast zero-allocation parsing in high-throughput RPC pipelines.

### `PSP`: Payment Service Provider {#term-psp}

External financial gateway (such as Stripe or Adyen) connecting merchant payment services to card networks and acquiring banks, introducing asynchronous settlement webhooks and external timeout failure modes.

### `PTP`: Precision Time Protocol {#term-ptp}

IEEE 1588 hardware-timestamped clock synchronization protocol achieving sub-microsecond accuracy across datacenter racks, essential for financial exchange telemetry and tight distributed commit ordering.

### `QUIC`: Quick UDP Internet Connections {#term-quic}

Encrypted, multiplexed transport protocol built over UDP with connection migration (surviving Wi-Fi to cellular handoffs), integrated TLS 1.3 handshakes, and independent per-stream loss recovery.

### `Quorum`: Majority Intersection Set {#term-quorum}

Subset of replicas satisfying `W + R > N` (and `2W > N` for leader election) so every read quorum intersects the latest write quorum on at least one up-to-date node, tolerating up to `floor((N - 1) / 2)` node failures.

### `RAFT`: Understandable Replicated State Machine Consensus {#term-raft}

Leader-based consensus protocol decomposing replication into leader election (with monotonic terms), log replication, and safety invariants so a cluster of `2f + 1` nodes executes an identical deterministic command log despite `f` crashes.

```rust
struct AppendEntriesReq {
    term: u64,
    leader_id: u32,
    prev_log_index: u64,
    prev_log_term: u64,
    leader_commit: u64,
}
```

### `RAID`: Redundant Array of Independent Disks {#term-raid}

Local disk striping and mirroring/parity organization improving single-host I/O bandwidth or tolerating individual drive failures, though distributed cloud systems increasingly prefer cross-host replication or erasure coding.

### `Read-Your-Writes`: Session Consistency Guarantee {#term-ryw}

Guarantee ensuring that once a client commits a write, subsequent reads within that same session observe the written value (or a newer one), implemented by pinning post-write reads to the leader or tracking a session commit watermark.

### `Replication Lag`: Primary-to-Follower Delay {#term-replication-lag}

Elapsed time or log-offset distance between a write committing on the primary node and becoming visible on an asynchronous read replica, governing stale-read risk and failover RPO exposure.

### `RPO`: Recovery Point Objective {#term-rpo}

Maximum acceptable age of data lost during a catastrophic failure, measured in time or transactions (for example, `RPO = 0` demands synchronous quorum durability before acknowledging writes).

### `RTO`: Recovery Time Objective {#term-rto}

Maximum acceptable duration of service unavailability during failover or disaster recovery, bounded by failure-detection timeouts, leader election latency, and standby state-replay time.

### `RTT`: Round-Trip Time {#term-rtt}

Elapsed network transit time for a packet to travel from sender to receiver and return, establishing the physical lower bound on synchronous consensus commits, TCP/TLS handshakes, and cross-region RPCs.

### `SAGA`: Long-Running Compensating Transaction Pattern {#term-saga}

Coordination pattern replacing distributed 2PC locks with a sequence of local ACID transactions where each step publishes an event or invokes the next service, and any failure triggers explicit compensating actions in reverse order.

### `SBE`: Simple Binary Encoding {#term-sbe}

Zero-copy, fixed-offset binary wire format standardized by the FIX Trading Community so financial matching engines encode and decode market orders directly from network ring buffers without heap allocation.

### `Sharding`: Horizontal Data Partitioning {#term-sharding}

Splitting a dataset across independent storage nodes by hash, key range, or geographic cell so write throughput, RAM footprint, and blast radius scale horizontally beyond a single machine.

### `SimHash`: Locality-Sensitive Document Fingerprint {#term-simhash}

64-bit weighted feature hash in which near-duplicate web pages differ in only a few bits (small Hamming distance), allowing web crawlers to detect mirrors and template copies in `O(1)` lookup tables.

### `SLA`: Service Level Agreement {#term-sla}

Legally or contractually binding reliability commitment to external customers specifying uptime or latency thresholds alongside financial credit penalties when breached.

### `SLI`: Service Level Indicator {#term-sli}

Quantitative runtime metric measuring user-facing service health, such as the ratio of successful HTTP requests completing under 100 ms over a rolling 5-minute window.

### `SLO`: Service Level Objective {#term-slo}

Internal engineering reliability target over an SLI (for example, 99.95% availability over 30 days), defining an explicit error budget that balances feature velocity against operational stability.

### `Split-Brain`: Dual-Leader Partition Hazard {#term-split-brain}

Failure state in which a network partition causes two isolated subsets of nodes to believe they each hold exclusive leadership and accept conflicting writes simultaneously, prevented by strict majority quorums and fencing tokens.

### `SQL`: Structured Query Language {#term-sql}

Declarative relational query language backed by B-tree/MVCC engines providing ACID transactions, secondary indexes, and schema constraints for metadata, ledgers, and booking inventories.

### `SSD`: Solid-State Drive {#term-ssd}

Flash-based non-volatile storage device delivering orders-of-magnitude lower random read/write latency than spinning disks, managed internally by a Flash Translation Layer that performs wear leveling and garbage collection.

### `SSE`: Server-Sent Events {#term-sse}

Unidirectional HTTP streaming protocol pushing UTF-8 event frames from server to browser over a persistent connection with automatic reconnection and `Last-Event-ID` resume semantics.

### `SSTable`: Sorted String Table {#term-sstable}

Immutable, key-sorted on-disk file produced when an LSM MemTable flushes to storage, paired with sparse index blocks and Bloom filters to serve point lookups and range scans sequentially.

### `Tail Latency`: High-Percentile Response Delay {#term-tail-latency}

Slowest 1% to 0.1% of requests (P99/P99.9) caused by garbage collection pauses, queue buildup, disk compaction, or packet retransmissions; tail latency compounds multiplicatively across microservice fan-outs.

### `TCP`: Transmission Control Protocol {#term-tcp}

Connection-oriented, byte-stream transport protocol providing reliable ordered delivery, sliding-window flow control, and congestion control at the cost of handshake RTT and head-of-line blocking under packet loss.

### `TLS`: Transport Layer Security {#term-tls}

Cryptographic transport protocol (currently TLS 1.3) providing confidentiality, integrity, and server/client authentication over TCP or QUIC with forward secrecy and 1-RTT connection establishment.

### `Tombstone`: Logical Deletion Marker {#term-tombstone}

Special marker record written instead of immediately erasing bytes in LSM storage engines, distributed sync logs, and Sequence CRDTs so deletions propagate reliably to offline replicas before epoch-gated garbage collection.

### `TrueTime`: Bounded-Uncertainty Distributed Clock API {#term-truetime}

Google Spanner clock service backed by GPS receivers and atomic clocks that exposes an explicit uncertainty interval `[earliest, latest]` (`~1 to 7 ms`), enabling external consistency by waiting out the uncertainty bound before commit (`commit-wait`).

### `TSDB`: Time-Series Database {#term-tsdb}

Storage engine optimized for append-heavy timestamped metric streams, combining inverted label indexes with delta-of-delta timestamp and XOR floating-point compression for high-ratio telemetry retention.

### `TTL`: Time To Live {#term-ttl}

Expiration duration attached to cache entries, DNS records, distributed leases, or storage objects so stale state is automatically invalidated and bounded without manual cleanup.

### `UDP`: User Datagram Protocol {#term-udp}

Minimal connectionless datagram transport adding only port multiplexing and checksums over IP, serving as the substrate for QUIC, DNS, VoIP, and multicast exchange market-data feeds (MoldUDP64).

### `Vector Clock`: Partial-Order Causality Tracker {#term-vector-clock}

Array of logical counters indexed by replica ID that captures exact causal happens-before relationships and detects concurrent conflicting writes when neither vector dominates the other.

```rust
fn happens_before(a: &[u64], b: &[u64]) -> bool {
    let all_le = a.iter().zip(b).all(|(x, y)| x <= y);
    let any_lt = a.iter().zip(b).any(|(x, y)| x < y);
    all_le && any_lt
}
```

### `VNode`: Virtual Node {#term-vnode}

Logical shard token placed at multiple positions on a consistent-hashing ring per physical server, smoothing key distribution variance and allowing heterogeneous hardware capacities to take proportional load.

### `WAL`: Write-Ahead Log {#term-wal}

Append-only sequential disk log recording every state mutation before modifying in-memory indexes or data pages, guaranteeing crash atomicity and durability via ordered `fsync` replay on restart.

```rust
// Append length-prefixed framed record and sync before acknowledging client
wal_file.write_all(&frame)?;
wal_file.sync_data()?;
```

### `WARC`: Web ARChive Format {#term-warc}

ISO 28500 container format concatenating raw HTTP request/response headers, payloads, and crawl metadata into large compressed archive segments for web crawlers such as Common Crawl.

### `Watermark`: Event-Time Progress Frontier {#term-watermark}

Monotonic timestamp `W(t)` propagated through a streaming dataflow asserting that the engine expects no further non-late events with event time earlier than `W(t)`, triggering window emission and bounding state retention.

### `WebSocket`: Full-Duplex Persistent Framing Protocol {#term-websocket}

Stateful bidirectional messaging protocol upgraded from HTTP/1.1 over a single long-lived TCP connection, eliminating polling overhead for real-time chat, collaborative editing, and live ticker feeds.

### `Zero-Copy`: Direct Kernel-to-NIC Data Transfer {#term-zero-copy}

I/O technique (`sendfile`, `splice`, or kernel-bypass ring buffers) transferring bytes directly between page cache or preallocated buffers and network hardware without redundant user-space copies.
