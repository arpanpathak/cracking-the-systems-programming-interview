// 1. Swaps theme-aware Material Design 3 SVGs (`figures/m3/*.svg` and
//    `art/ch*-plate.svg`) between light and dark variants automatically based
//    on the active mdBook theme (and forces light mode when printing).
// 2. Opens any figure diagram full screen on click/tap for inspection.
(function () {
    "use strict";

    var DARK_THEMES = ["coal", "navy", "ayu"];

    function isDark() {
        var classes = document.documentElement.classList;
        return DARK_THEMES.some(function (name) {
            return classes.contains(name);
        });
    }

    function swapDir(selector, dirPrefix, forceLight) {
        var dark = !forceLight && isDark();
        var darkPrefix = dirPrefix + "dark/";
        document.querySelectorAll(selector).forEach(function (img) {
            var current = img.getAttribute("src");
            var light = current.replace(darkPrefix, dirPrefix);
            var wanted = dark ? light.replace(dirPrefix, darkPrefix) : light;
            if (wanted !== current) {
                img.setAttribute("src", wanted);
            }
        });
    }

    function isPrintPage() {
        return /print\.html$/i.test(window.location.pathname) ||
            (window.matchMedia && window.matchMedia("print").matches);
    }

    function applyThemeAssets(forceLight) {
        var light = Boolean(forceLight) || isPrintPage();
        swapDir('img[src*="figures/m3/"]', "figures/m3/", light);
        swapDir('img.plate[src*="-plate.svg"]', "art/", light);
        swapDir('img.cover[src*="cover.svg"]', "art/", light);
    }

    function open(diagram) {
        var view = document.createElement("div");
        var picture = document.createElement("img");

        view.className = "figure-zoom";
        picture.src = diagram.src;
        picture.alt = diagram.alt;

        var upright = window.innerHeight > window.innerWidth;
        var wide = diagram.naturalWidth > diagram.naturalHeight * 1.2;

        if (upright && wide) {
            view.classList.add("turned");
        }

        function close() {
            view.remove();
            document.removeEventListener("keydown", onKey);
        }

        function onKey(event) {
            if (event.key === "Escape") {
                close();
            }
        }

        view.appendChild(picture);
        view.addEventListener("click", close);
        document.addEventListener("keydown", onKey);
        document.body.appendChild(view);
    }

    function labelThemeMenu() {
        var labels = {
            light: "Light (Paper)",
            rust: "Warm Parchment",
            navy: "Night Owl (Blue)",
            coal: "Material Deep Ocean",
            ayu: "Oceanic Next"
        };
        Object.keys(labels).forEach(function (id) {
            var btn = document.getElementById(id);
            if (btn) {
                btn.textContent = labels[id];
            }
        });
    }

    var GLOSSARY = {
        "2PC": ["term-2pc", "Two-Phase Commit: atomic distributed commit protocol split into prepare and commit phases."],
        "ABR": ["term-abr", "Adaptive Bitrate Streaming: dynamically switches video quality renditions on segment boundaries."],
        "ACID": ["term-acid", "Atomicity, Consistency, Isolation, Durability: transactional database guarantees."],
        "Anycast": ["term-anycast", "BGP Anycast Routing: advertises one IP prefix from multiple PoPs to route clients to the nearest edge."],
        "APNs": ["term-apns", "Apple Push Notification Service: persistent HTTP/2 push gateway for iOS and macOS devices."],
        "AZ": ["term-az", "Availability Zone: physically isolated datacenter failure domain within a cloud region."],
        "Backpressure": ["term-backpressure", "End-to-End Flow Control: slows upstream producers when downstream queues fill."],
        "BASE": ["term-base", "Basically Available, Soft State, Eventual Consistency: availability-first convergence model."],
        "BDP": ["term-bdp", "Bandwidth-Delay Product: bytes in flight (Bandwidth x RTT) required to saturate a link."],
        "BGP": ["term-bgp", "Border Gateway Protocol: inter-domain routing protocol exchanging IP reachability across Autonomous Systems."],
        "Bloom Filter": ["term-bloom-filter", "Probabilistic Set Membership: compact bit-array with zero false negatives and tunable false positives."],
        "Bulkhead": ["term-bulkhead", "Fault-Isolation Partitioning: isolates resource pools per tenant or dependency to contain failures."],
        "CAP": ["term-cap", "Consistency, Availability, Partition Tolerance: partition trade-off between linearizability and availability."],
        "CAS": ["term-cas", "Compare-And-Swap: atomic conditional update primitive used in lock-free code and optimistic concurrency."],
        "CDC": ["term-cdc", "Change Data Capture / Content-Defined Chunking: WAL row streaming or rolling-hash file chunking."],
        "CDE": ["term-cde", "Cardholder Data Environment: isolated PCI-DSS scope handling raw payment card numbers."],
        "CDN": ["term-cdn", "Content Delivery Network: globally distributed edge proxies caching assets close to end users."],
        "Circuit Breaker": ["term-circuit-breaker", "Fail-Fast Overload Protection: trips open on high error rates to prevent cascading exhaustion."],
        "Consistent Hashing": ["term-consistent-hashing", "Minimal-Movement Partitioning: ring hashing that relocates only 1/N keys on node membership change."],
        "CRDT": ["term-crdt", "Conflict-Free Replicated Data Type: algebraic structure guaranteeing strong eventual consistency without locks."],
        "DASH": ["term-dash", "Dynamic Adaptive Streaming over HTTP: ISO adaptive bitrate media standard using MPD manifests."],
        "DNS": ["term-dns", "Domain Name System: hierarchical directory translating hostnames to IP addresses."],
        "ECMP": ["term-ecmp", "Equal-Cost Multi-Path Routing: stateless L3/L4 5-tuple flow hashing across parallel next hops."],
        "Epoch": ["term-epoch", "Monotonic Generation Counter: logical version incremented on leadership changes or GC barriers."],
        "Erasure Coding": ["term-erasure-coding", "Parity-Based Redundancy: splits data into k data and m parity shards for low-overhead durability."],
        "Eventual Consistency": ["term-eventual-consistency", "Asynchronous Convergence: replicas converge to the same value once updates stop."],
        "FCM": ["term-fcm", "Firebase Cloud Messaging: persistent multiplexed push notification gateway for Android and web."],
        "Fencing Token": ["term-fencing-token", "Monotonic Lease Guard: strictly increasing token rejecting stale writes from zombie leaders."],
        "FIX": ["term-fix", "Financial Information eXchange: standardized institutional order and execution messaging protocol."],
        "FST": ["term-fst", "Finite State Transducer: compact prefix-and-suffix-sharing automaton for weighted autocomplete lookups."],
        "GCRA": ["term-gcra", "Generic Cell Rate Algorithm: single-timestamp leaky-bucket rate limiter enforcing smooth pacing."],
        "Group Commit": ["term-group-commit", "Amortized WAL Flushing: batches concurrent transactions into a single sequential fsync."],
        "gRPC": ["term-grpc", "High-Performance RPC Framework: typed Protobuf RPC over multiplexed HTTP/2 streams."],
        "H3": ["term-h3", "Hexagonal Hierarchical Spatial Index: global hexagonal grid with uniform neighbor distances."],
        "Hedged Request": ["term-hedged-request", "Tail-Latency Duplicate Dispatch: sends a backup read after a short delay to cut P99 latency."],
        "HLC": ["term-hlc", "Hybrid Logical Clock: combines physical wall-clock time with a logical causal counter."],
        "HLL": ["term-hll", "HyperLogLog: mergeable probabilistic cardinality sketch estimating distinct counts in ~12 KiB."],
        "HLS": ["term-hls", "HTTP Live Streaming: Apple adaptive media protocol using .m3u8 playlists and immutable segments."],
        "HSM": ["term-hsm", "Hardware Security Module: tamper-resistant silicon storing and applying cryptographic keys."],
        "HTTP/2": ["term-http-2", "Multiplexed Binary HTTP: concurrent streams and header compression over one TCP connection."],
        "HTTP/3": ["term-http-3", "QUIC-Based HTTP: multiplexed streams over UDP with independent per-stream loss recovery."],
        "Idempotency": ["term-idempotency", "Safe Retry Invariance: applying an operation repeatedly yields the identical state as applying it once."],
        "IOPS": ["term-iops", "Input/Output Operations Per Second: random storage operation throughput metric."],
        "ITCH": ["term-itch", "Market Data Protocol: ultra-low-latency binary multicast feed broadcasting order book ticks."],
        "JSON": ["term-json", "JavaScript Object Notation: human-readable UTF-8 text interchange format for REST APIs."],
        "KRaft": ["term-kraft", "Kafka Raft Metadata Mode: built-in Raft consensus replacing ZooKeeper in Apache Kafka."],
        "L4": ["term-l4", "Layer-4 Load Balancer: routes TCP/UDP flows by IP and port without terminating TLS."],
        "L7": ["term-l7", "Layer-7 Load Balancer: terminates TLS and inspects HTTP/gRPC headers for application routing."],
        "LFU": ["term-lfu", "Least Frequently Used: cache eviction discarding the lowest-frequency entries."],
        "Linearizability": ["term-linearizability", "Strong Single-Copy Consistency: every operation appears atomic in real-time order."],
        "LRU": ["term-lru", "Least Recently Used: O(1) cache eviction discarding the entry untouched longest."],
        "LSM": ["term-lsm", "Log-Structured Merge-Tree: write-optimized engine using MemTables, WAL, and compacted SSTables."],
        "Merkle Tree": ["term-merkle-tree", "Hierarchical Hash Tree: locates divergent replica key ranges in O(log N) round trips."],
        "mTLS": ["term-mtls", "Mutual TLS: bidirectional X.509 certificate authentication between communicating services."],
        "MVCC": ["term-mvcc", "Multi-Version Concurrency Control: timestamped row versions enabling non-blocking snapshot reads."],
        "NTP": ["term-ntp", "Network Time Protocol: synchronizes host clocks within 1 to 50 ms of UTC."],
        "NVMe": ["term-nvme", "Non-Volatile Memory Express: high-concurrency PCIe flash interface with microsecond access."],
        "OLAP": ["term-olap", "Online Analytical Processing: columnar storage optimized for large-scale aggregations."],
        "OLTP": ["term-oltp", "Online Transactional Processing: row-oriented ACID point reads and writes."],
        "OT": ["term-ot", "Operational Transformation: transforms concurrent positional edits against a canonical server log."],
        "OUCH": ["term-ouch", "Order Entry Protocol: fixed-width binary TCP protocol for microsecond exchange order submission."],
        "Outbox": ["term-outbox", "Transactional Outbox: writes state and outbound events in one local ACID transaction."],
        "P99": ["term-p99", "99th Percentile Latency: response-time threshold below which 99% of requests complete."],
        "PACELC": ["term-pacelc", "Partition/Else Trade-Off: trades A vs. C on partitions and Latency vs. Consistency otherwise."],
        "Paxos": ["term-paxos", "Fault-Tolerant Consensus: majority-quorum agreement protocol tolerating crash failures."],
        "PCI-DSS": ["term-pci-dss", "Payment Card Industry Data Security Standard: compliance standard for cardholder data."],
        "PoP": ["term-pop", "Point of Presence: regional edge facility hosting CDN caches and Anycast routers."],
        "Protobuf": ["term-protobuf", "Protocol Buffers: compact schema-driven binary serialization format for RPCs."],
        "PSP": ["term-psp", "Payment Service Provider: external gateway connecting merchants to card networks and banks."],
        "PTP": ["term-ptp", "Precision Time Protocol: hardware-timestamped sub-microsecond datacenter clock sync."],
        "QUIC": ["term-quic", "Quick UDP Internet Connections: encrypted, multiplexed UDP transport with 0/1-RTT handshakes."],
        "Quorum": ["term-quorum", "Majority Intersection Set: overlapping read and write subsets (W + R > N) guaranteeing fresh reads."],
        "RAFT": ["term-raft", "Raft Consensus: leader-based replicated state machine protocol with monotonic election terms."],
        "Raft": ["term-raft", "Raft Consensus: leader-based replicated state machine protocol with monotonic election terms."],
        "RAID": ["term-raid", "Redundant Array of Independent Disks: local disk striping, mirroring, or parity organization."],
        "Read-Your-Writes": ["term-ryw", "Session Consistency: guarantees a client observes its own committed writes on subsequent reads."],
        "Replication Lag": ["term-replication-lag", "Primary-to-Follower Delay: time or offset gap before primary commits appear on read replicas."],
        "RPO": ["term-rpo", "Recovery Point Objective: maximum acceptable age of data lost during a failure."],
        "RTO": ["term-rto", "Recovery Time Objective: maximum acceptable duration of downtime during failover."],
        "RTT": ["term-rtt", "Round-Trip Time: elapsed packet travel time from sender to receiver and back."],
        "SAGA": ["term-saga", "Compensating Transaction Pattern: replaces distributed 2PC locks with local commits and reverse compensations."],
        "SBE": ["term-sbe", "Simple Binary Encoding: zero-copy fixed-offset binary wire format for low-latency trading."],
        "Sharding": ["term-sharding", "Horizontal Partitioning: splits keys across independent storage nodes for scale."],
        "SimHash": ["term-simhash", "Locality-Sensitive Fingerprint: 64-bit document hash detecting near-duplicates via small Hamming distance."],
        "SLA": ["term-sla", "Service Level Agreement: contractual reliability commitment with external penalty terms."],
        "SLI": ["term-sli", "Service Level Indicator: quantitative runtime metric measuring user-facing service health."],
        "SLO": ["term-slo", "Service Level Objective: internal reliability target over an SLI defining an error budget."],
        "Split-Brain": ["term-split-brain", "Dual-Leader Hazard: two partitioned subsets accept conflicting writes without majority quorums."],
        "SQL": ["term-sql", "Structured Query Language: declarative relational query language for ACID databases."],
        "SSD": ["term-ssd", "Solid-State Drive: low-latency flash storage managed by a Flash Translation Layer."],
        "SSE": ["term-sse", "Server-Sent Events: unidirectional HTTP event streaming with automatic reconnect."],
        "SSTable": ["term-sstable", "Sorted String Table: immutable key-sorted on-disk file in an LSM storage engine."],
        "Tail Latency": ["term-tail-latency", "High-Percentile Delay: slowest 1% to 0.1% of requests that compound across fan-outs."],
        "TCP": ["term-tcp", "Transmission Control Protocol: reliable, ordered byte-stream transport with congestion control."],
        "TLS": ["term-tls", "Transport Layer Security: cryptographic protocol providing encryption and authentication."],
        "Tombstone": ["term-tombstone", "Logical Deletion Marker: propagates deletions across replicas before epoch-gated reclamation."],
        "TrueTime": ["term-truetime", "Bounded-Uncertainty Clock API: GPS/atomic clock interval enabling Spanner commit-wait."],
        "TSDB": ["term-tsdb", "Time-Series Database: storage engine optimized for timestamped metrics and XOR/delta compression."],
        "TTL": ["term-ttl", "Time To Live: expiration duration automatically invalidating cached entries or leases."],
        "UDP": ["term-udp", "User Datagram Protocol: connectionless datagram transport used by QUIC, DNS, and multicast feeds."],
        "Vector Clock": ["term-vector-clock", "Causality Tracker: per-replica logical counter vector detecting concurrent conflicting writes."],
        "VNode": ["term-vnode", "Virtual Node: logical consistent-hashing ring token smoothing key distribution across servers."],
        "WAL": ["term-wal", "Write-Ahead Log: append-only sequential disk log guaranteeing crash durability via replay."],
        "WARC": ["term-warc", "Web ARChive Format: ISO container format bundling crawled HTTP payloads and metadata."],
        "Watermark": ["term-watermark", "Event-Time Frontier: monotonic progress timestamp triggering window emission in stream engines."],
        "WebSocket": ["term-websocket", "Full-Duplex Framing Protocol: persistent bidirectional TCP messaging upgraded from HTTP."],
        "Zero-Copy": ["term-zero-copy", "Direct I/O Transfer: moves bytes between buffers and NIC without redundant user-space copies."]
    };

    function initGlossaryLinks() {
        var path = window.location.pathname || "";
        if (/\/(glossary|toc|cover)\.html$/.test(path)) return;
        var main = document.querySelector(".content main");
        if (!main) return;

        var keys = Object.keys(GLOSSARY).sort(function (a, b) { return b.length - a.length; });
        var escaped = keys.map(function (k) { return k.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"); });
        var re = new RegExp("(^|[^A-Za-z0-9_])(" + escaped.join("|") + ")(?=$|[^A-Za-z0-9_])", "g");

        var SKIP_TAGS = { A: 1, PRE: 1, SCRIPT: 1, STYLE: 1, H1: 1, H2: 1, H3: 1, H4: 1, H5: 1, H6: 1, BUTTON: 1 };

        function makeLink(term) {
            var info = GLOSSARY[term];
            var a = document.createElement("a");
            a.className = "md-abbr-link";
            a.href = "glossary.html#" + info[0];
            a.title = info[1];
            a.setAttribute("data-tooltip", info[1]);
            a.textContent = term;
            return a;
        }

        function linkTextNode(tNode, extraClass) {
            var str = tNode.nodeValue;
            re.lastIndex = 0;
            if (!re.test(str)) return;
            re.lastIndex = 0;
            var frag = document.createDocumentFragment();
            var lastIdx = 0;
            var m;
            while ((m = re.exec(str)) !== null) {
                var prefix = m[1];
                var term = m[2];
                var termStart = m.index + prefix.length;
                if (termStart > lastIdx) {
                    frag.appendChild(document.createTextNode(str.slice(lastIdx, termStart)));
                }
                var link = makeLink(term);
                if (extraClass) link.classList.add(extraClass);
                frag.appendChild(link);
                lastIdx = termStart + term.length;
            }
            if (lastIdx < str.length) {
                frag.appendChild(document.createTextNode(str.slice(lastIdx)));
            }
            tNode.parentNode.replaceChild(frag, tNode);
        }

        main.querySelectorAll("code").forEach(function (codeEl) {
            if (codeEl.closest("pre, a, h1, h2, h3, h4, h5, h6, button")) return;
            var txt = codeEl.textContent.trim();
            if (Object.prototype.hasOwnProperty.call(GLOSSARY, txt)) {
                var link = makeLink(txt);
                link.classList.add("md-abbr-code");
                codeEl.textContent = "";
                codeEl.appendChild(link);
                return;
            }
            var codeWalker = document.createTreeWalker(codeEl, NodeFilter.SHOW_TEXT, null, false);
            var codeTextNodes = [];
            var cNode;
            while ((cNode = codeWalker.nextNode())) {
                if (!cNode.nodeValue || !cNode.nodeValue.trim()) continue;
                if (cNode.parentElement && cNode.parentElement.closest("a")) continue;
                codeTextNodes.push(cNode);
            }
            codeTextNodes.forEach(function (tNode) { linkTextNode(tNode, "md-abbr-code"); });
        });

        var walker = document.createTreeWalker(main, NodeFilter.SHOW_TEXT, null, false);
        var textNodes = [];
        var node;
        while ((node = walker.nextNode())) {
            if (!node.nodeValue || !node.nodeValue.trim()) continue;
            var parent = node.parentElement;
            if (!parent) continue;
            var skip = false;
            var cur = parent;
            while (cur && cur !== main) {
                if (SKIP_TAGS[cur.tagName] || cur.tagName === "CODE") {
                    skip = true;
                    break;
                }
                cur = cur.parentElement;
            }
            if (!skip) textNodes.push(node);
        }

        textNodes.forEach(function (tNode) { linkTextNode(tNode, null); });
    }

    // Domain-accurate Material Design SVG icons mapped to Distributed Systems h2 & semantic h3 archetypes
    var DS_ICONS = {
        tune: '<path d="M3 17v2h6v-2H3zM3 5v2h10V5H3zm10 16v-2h8v-2h-8v-2h-2v6h2zM7 9v2H3v2h4v2h2V9H7zm14 4v-2H11v2h10zm-6-4h2V7h4V5h-4V3h-2v6z"/>',
        protocol: '<path d="M6.99 11L3 15l3.99 4v-3H14v-2H6.99v-3zM21 9l-3.99-4v3H10v2h7.01v3L21 9z"/>',
        layers: '<path d="M11.99 18.54l-7.37-5.73L3 14.07l9 7 9-7-1.63-1.27-7.38 5.74zM12 16l7.36-5.73L21 9l-9-7-9 7 1.63 1.27L12 16z"/>',
        shield: '<path d="M12 1L3 5v6c0 5.55 3.84 10.74 9 12 5.16-1.26 9-6.45 9-12V5l-9-4zm-2 16l-4-4 1.41-1.41L10 14.17l6.59-6.59L18 9l-8 8z"/>',
        split: '<path d="M14 4l2.29 2.29-2.88 2.88 1.42 1.42 2.88-2.88L20 10V4h-6zm-4 0H4v6l2.29-2.29 4.71 4.7V20h2v-8.41l-5.29-5.3L10 4z"/>',
        sync: '<path d="M12 4V1L8 5l4 4V6c3.31 0 6 2.69 6 6 0 1.01-.25 1.97-.7 2.8l1.46 1.46C19.54 15.03 20 13.57 20 12c0-4.42-3.58-8-8-8zm0 14c-3.31 0-6-2.69-6-6 0-1.01.25-1.97.7-2.8L5.24 7.74C4.46 8.97 4 10.43 4 12c0 4.42 3.58 8 8 8v3l4-4-4-4v3z"/>',
        fault: '<path d="M1 21h22L12 2 1 21zm12-3h-2v-2h2v2zm0-4h-2v-4h2v4z"/>',
        storage: '<path d="M2 20h20v-4H2v4zm2-3h2v2H4v-2zM2 4v4h20V4H2zm4 3H4V5h2v2zm-4 7h20v-4H2v4zm2-3h2v2H4v-2z"/>',
        memory: '<path d="M15 9H9v6h6V9zm-2 4h-2v-2h2v2zm8-2V9h-2V7c0-1.1-.9-2-2-2h-2V3h-2v2h-2V3H9v2H7c-1.1 0-2 .9-2 2v2H3v2h2v2H3v2h2v2c0 1.1.9 2 2 2h2v2h2v-2h2v2h2v-2h2c1.1 0 2-.9 2-2v-2h2v-2h-2v-2h2zm-4 6H7V7h10v10z"/>',
        speed: '<path d="M20.38 8.57l-1.23 1.85a8 8 0 0 1-.22 7.58H5.07A8 8 0 0 1 15.58 6.85l1.85-1.23A10 10 0 0 0 3.35 19a2 2 0 0 0 1.72 1h13.85a2 2 0 0 0 1.74-1 10 10 0 0 0-.27-10.44zm-9.79 6.84a2 2 0 0 0 2.83 0l5.66-8.49-8.49 5.66a2 2 0 0 0 0 2.83z"/>',
        bolt: '<path d="M7 2v11h3v9l7-12h-4l4-8z"/>',
        science: '<path d="M19.8 18.4L14 10.67V6.5l1.35-1.69c.26-.33.03-.81-.39-.81H9.04c-.42 0-.65.48-.39.81L10 6.5v4.17L4.2 18.4c-.49.66-.02 1.6.8 1.6h14c.82 0 1.29-.94.8-1.6z"/>',
        code: '<path d="M9.4 16.6L4.8 12l4.6-4.6L8 6l-6 6 6 6 1.4-1.4zm5.2 0l4.6-4.6-4.6-4.6L16 6l6 6-6 6-1.4-1.4z"/>',
        route: '<path d="M19 15.18V7c0-2.21-1.79-4-4-4s-4 1.79-4 4v10c0 1.1-.9 2-2 2s-2-.9-2-2V8.82C8.16 8.4 9 7.3 9 6c0-1.66-1.34-3-3-3S3 4.34 3 6c0 1.3.84 2.4 2 2.82V17c0 2.21 1.79 4 4 4s4-1.79 4-4V7c0-1.1.9-2 2-2s2 .9 2 2v8.18c-1.16.41-2 1.51-2 2.82 0 1.66 1.34 3 3 3s3-1.34 3-3c0-1.3-.84-2.4-2-2.82z"/>',
        case_study: '<path d="M12 7V3H2v18h20V7H12zM6 19H4v-2h2v2zm0-4H4v-2h2v2zm0-4H4V9h2v2zm0-4H4V5h2v2zm4 12H8v-2h2v2zm0-4H8v-2h2v2zm0-4H8V9h2v2zm0-4H8V5h2v2zm10 12h-8v-2h2v-2h-2v-2h2v-2h-2V9h8v10zm-2-8h-2v2h2v-2zm0 4h-2v2h2v-2z"/>',
        reading: '<path d="M21 5c-1.11-.35-2.33-.5-3.5-.5-1.95 0-4.05.4-5.5 1.5-1.45-1.1-3.55-1.5-5.5-1.5S2.45 4.9 1 6v14.65c0 .25.25.5.5.5.1 0 .15-.05.25-.05C3.1 20.45 5.05 20 6.5 20c1.95 0 4.05.4 5.5 1.5 1.35-.85 3.8-1.5 5.5-1.5 1.65 0 3.35.3 4.75 1.05.1.05.15.05.25.05.25 0 .5-.25.5-.5V6c-.6-.45-1.25-.75-2-1zm0 13.5c-1.1-.35-2.3-.5-3.5-.5-1.7 0-4.15.65-5.5 1.5V8c1.35-.85 3.8-1.5 5.5-1.5 1.2 0 2.4.15 3.5.5v11.5z"/>',
        summary: '<path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z"/>',
        video: '<path d="M18 4l2 4h-3l-2-4h-2l2 4h-3l-2-4H8l2 4H7L5 4H4c-1.1 0-1.99.9-1.99 2L2 18c0 1.1.9 2 2 2h16c1.1 0 2-.9 2-2V4h-4z"/>',
        globe: '<path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-1 17.93c-3.95-.49-7-3.85-7-7.93 0-.62.08-1.21.21-1.79L9 15v1c0 1.1.9 2 2 2v1.93zm6.9-2.54c-.26-.81-1-1.39-1.9-1.39h-1v-3c0-.55-.45-1-1-1H8v-2h2c.55 0 1-.45 1-1V7h2c1.1 0 2-.9 2-2v-.41c2.93 1.19 5 4.06 5 7.41 0 2.08-.8 3.97-2.1 5.39z"/>',
        notify: '<path d="M12 22c1.1 0 2-.9 2-2h-4c0 1.1.9 2 2 2zm6-6v-5c0-3.07-1.63-5.64-4.5-6.32V4c0-.83-.67-1.5-1.5-1.5s-1.5.67-1.5 1.5v.68C7.64 5.36 6 7.92 6 11v5l-2 2v1h16v-1l-2-2z"/>',
        ticket: '<path d="M22 10V6a2 2 0 0 0-2-2H4c-1.1 0-1.99.89-1.99 2v4c1.1 0 1.99.9 1.99 2s-.89 2-2 2v4c0 1.1.9 2 2 2h16c1.1 0 2-.9 2-2v-4c-1.1 0-2-.9-2-2s.9-2 2-2zm-9 7.5h-2v-2h2v2zm0-4.5h-2v-2h2v2zm0-4.5h-2v-2h2v2z"/>',
        tag: '<path d="M21.41 11.58l-9-9C12.05 2.22 11.55 2 11 2H4c-1.1 0-2 .9-2 2v7c0 .55.22 1.05.59 1.42l9 9c.36.36.86.58 1.41.58.55 0 1.05-.22 1.41-.59l7-7c.37-.36.59-.86.59-1.41 0-.55-.23-1.06-.59-1.42zM5.5 7C4.67 7 4 6.33 4 5.5S4.67 4 5.5 4 7 4.67 7 5.5 6.33 7 5.5 7z"/>',
        checklist: '<path d="M19 3H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2zm-9 14l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z"/>',
        block: '<path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zM4 12c0-4.42 3.58-8 8-8 1.85 0 3.55.63 4.9 1.69L5.69 16.9C4.63 15.55 4 13.85 4 12zm8 8c-1.85 0-3.55-.63-4.9-1.69L18.31 7.1C19.37 8.45 20 10.15 20 12c0 4.42-3.58 8-8 8z"/>',
        calc: '<path d="M19 3H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2zm-5.97 4.06L14.09 6l1.41 1.41L16.91 6l1.06 1.06-1.41 1.41 1.41 1.41-1.06 1.06-1.41-1.4-1.41 1.41-1.06-1.06 1.41-1.41-1.41-1.42zm-6.78.66h5v1.5h-5v-1.5zM11.5 16h-2v2H8v-2H6v-1.5h2v-2h1.5v2h2V16zm6.5 1.25h-5v-1.5h5v1.5zm0-2.5h-5v-1.5h5v1.5z"/>'
    };

    function pickDSIcon(text, allowFallback) {
        var t = (text || "").toLowerCase();
        if (/^summary$|recap/.test(t.trim())) return DS_ICONS.summary;
        if (/further reading|reference|terminology|glossary/.test(t)) return DS_ICONS.reading;
        if (/case stud|production|real system|open-source/.test(t)) return DS_ICONS.case_study;
        if (/end-to-end|lifecycle|hop breakdown|request flow/.test(t)) return DS_ICONS.route;
        if (/simulation|experiment|live .*test|crashsim|replsim|raftsim/.test(t)) return DS_ICONS.science;
        if (/source listing|implementing|workspace|low-level architecture|http server|pure event loop|state machine/.test(t)) return DS_ICONS.code;
        if (/non-goal|out of scope/.test(t)) return DS_ICONS.block;
        if (/non-functional|slo|sla/.test(t)) return DS_ICONS.speed;
        if (/functional requirement/.test(t)) return DS_ICONS.checklist;
        if (/capacity|envelope|back-of-the-envelope|sizing/.test(t)) return DS_ICONS.calc;
        if (/requirement/.test(t)) return DS_ICONS.tune;
        if (/api|wire protocol|data contract|protocol|schema|message/.test(t)) return DS_ICONS.protocol;
        if (/failure|crash|fault|limitation|split-brain|reconcil|conflict|recovery|error taxonomy|backoff|circuit breaker/.test(t)) return DS_ICONS.fault;
        if (/transcod|cmaf|abr|hls|dash|streaming|video/.test(t)) return DS_ICONS.video;
        if (/crawl|politeness|robots\.txt|frontier/.test(t)) return DS_ICONS.globe;
        if (/waiting room|admission control|ticket|booking|seat hold/.test(t)) return DS_ICONS.ticket;
        if (/snowflake|base-62|key allocation|unique id/.test(t)) return DS_ICONS.tag;
        if (/priority lane|notification|pacing|alert/.test(t)) return DS_ICONS.notify;
        if (/batched commit|committer pipeline|group commit|pipelin/.test(t)) return DS_ICONS.bolt;
        if (/measur|physical cost|fsync|latency|throughput|observab|metric|monitor|rate-?limit|gcra|gorilla|ingestion|compression|cardinality/.test(t)) return DS_ICONS.speed;
        if (/consisten|consensus|raft|election|voting|fencing|lock|lease|idempoten|payment|ledger|safety/.test(t)) return DS_ICONS.shield;
        if (/partition|sharding|hash|virtual node|ring lookup|router|routing|redirect|dispatch|fan-out|autocomplete|search/.test(t)) return DS_ICONS.split;
        if (/replicat|follower|leader|quorum|catch-up|sync|crdt|collaborative|chunking|deduplication|merkle/.test(t)) return DS_ICONS.sync;
        if (/in-memory|cache|memtable|trie|stampede|buffer/.test(t)) return DS_ICONS.memory;
        if (/wal|write-ahead|on-disk|durable|storage|persistent|object|erasure|block|compaction|log matching|multipart|garbage collection/.test(t)) return DS_ICONS.storage;
        if (/architecture|control plane|data plane|topology/.test(t)) return DS_ICONS.layers;
        return allowFallback ? DS_ICONS.layers : null;
    }

    function initMaterialSectionIcons() {
        var path = window.location.pathname || "";
        if (/\/(cover|glossary)\.html$/.test(path)) return;
        var main = document.querySelector(".content main");
        if (!main) return;
        main.querySelectorAll("h2, h3").forEach(function (h) {
            if (h.querySelector(".md-sec-icon")) return;
            var svg = pickDSIcon(h.textContent, h.tagName === "H2");
            if (!svg) return;
            var span = document.createElement("span");
            span.className = "md-sec-icon";
            span.setAttribute("aria-hidden", "true");
            span.innerHTML = '<svg viewBox="0 0 24 24">' + svg + "</svg>";
            h.insertBefore(span, h.firstChild);
        });
    }

    function initAll() {
        initMaterialSectionIcons();
        initGlossaryLinks();
    }

    applyThemeAssets(false);
    labelThemeMenu();
    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", initAll);
    } else {
        initAll();
    }

    new MutationObserver(function () {
        applyThemeAssets(false);
    }).observe(document.documentElement, { attributes: true, attributeFilter: ["class"] });

    window.addEventListener("beforeprint", function () { applyThemeAssets(true); });
    window.addEventListener("afterprint", function () { applyThemeAssets(false); });

    document.querySelectorAll('figure > img[src*=".svg"]').forEach(function (diagram) {
        diagram.style.cursor = "zoom-in";
        diagram.title = "Open at full size";
        diagram.addEventListener("click", function () { open(diagram); });
    });
})();
