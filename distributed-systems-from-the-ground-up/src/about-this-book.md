# Preface

Distributed systems engineering operates under physical and theoretical constraints that single-node abstractions conceal: asynchronous message delivery, unbounded network delay, independent component crashes, clock drift across unsynchronized oscillators, and volatile kernel page caches. Designing reliable infrastructure requires deriving architectures directly from explicit safety and liveness invariants, fault boundaries, and quantitative resource limits rather than informal component sketches.

In this book, I examine the architecture of fault-tolerant distributed systems from first principles. For every system, I establish the actors, verifiable functional contracts, explicit latency and availability Service Level Objectives (SLOs), and storage, compute, and bandwidth envelopes prior to introducing algorithms, wire protocols, or deployment topologies.

## Organization of the Text

The twenty-eight chapters are grouped into six thematic parts:

- **Part I (Chapters 1 to 6): Distributed Key-Value Store.** In Chapter 1, I specify the system architecture, consistency model, partitioning scheme, and failure-handling contracts of a strongly consistent key-value store. In Chapters 2 to 6, I detail the low-level design and empirical verification of its core mechanisms: durable write-ahead logging, leader-follower quorum replication, Raft leader election with monotonic term fencing, consistent-hash request routing, and group commit.
- **Part II (Chapters 7 to 13): Core Infrastructure Primitives.** I analyze foundational platform services that enforce fairness, ordering, caching, coordination, and asynchronous decoupling: distributed rate limiting, unique identifier generation, distributed caching, distributed locking, partitioned message queues, job scheduling, and notification delivery.
- **Part III (Chapters 14 to 18): Content, Media, and Communication Systems.** I analyze read-intensive and media-delivery architectures: URL shortening, social news feeds, chunked object storage, adaptive video streaming, and real-time messaging.
- **Part IV (Chapters 19 to 21): Transactional and Marketplace Systems.** I analyze domains governed by strict transactional integrity, concurrency control, and real-time spatial state: payment processing with double-entry ledgers, high-contention ticket booking, and geospatial ride-hailing dispatch.
- **Part V (Chapters 22 to 24): Search, Indexing, and Observability.** I analyze low-latency prefix indexing, polite distributed web crawling, and high-cardinality metrics ingestion and monitoring.
- **Part VI (Chapters 25 to 28): Synchronization and Low-Latency Streaming.** I analyze conflict resolution, operational convergence, deterministic execution, and stream processing: file synchronization, collaborative editing, a single-threaded stock exchange matching engine, and click aggregation.

## Architectural Methodology

Across every system design chapter, I adhere to an explicit engineering progression aligned with formal systems documentation standards (ISO/IEC/IEEE 26514):

1. **Requirements and Capacity Bounds:** I specify actors, use-case boundaries, numbered functional and non-functional requirements, and order-of-magnitude storage, throughput, and memory calculations upfront.
2. **External and Internal Interface Contracts:** I define HTTP/2 or gRPC endpoints, preconditions, idempotency semantics, error payloads, and storage schemas before examining internal optimizations.
3. **Control-Plane and Data-Plane Separation:** I isolate low-frequency metadata management, topology coordination, and policy compilation from the latency-critical request path.
4. **Failure Modes, Tail Latency, and Observability:** I evaluate network partitions, hot-key skew, lock contention, and gray failures, specifying automated recovery invariants and Service Level Indicators (SLIs) for each failure domain.

## Companion Implementations and Prerequisites

The companion [`code/`](https://github.com/arpanpathak/cracking-the-systems-programming-interview/tree/prep-v2/distributed-systems-from-the-ground-up/code) directory contains the runnable Part I storage subsystems and the workload simulations cited across Parts II to VI, allowing readers to reproduce the throughput measurements, skew distributions, and crash-recovery experiments reported in the text.

For the system design chapters, I assume foundational knowledge of HTTP semantics, relational databases, data structures, and TCP/IP networking. For the low-level implementation chapters in Part I, I additionally assume reading familiarity with Rust. Every distributed systems primitive is derived when first introduced and consolidated in each chapter's engineering glossary.

## References and Provenance

The protocols and trade-offs presented in this volume draw upon primary distributed systems literature and published production engineering reports, including work on Raft consensus, Dynamo, Spanner, CockroachDB, Stripe's atomic-phase idempotency and GCRA rate-limiting systems, and classical transaction-processing theory. Full bibliographic citations appear at the close of each chapter.

*Arpan Pathak*
