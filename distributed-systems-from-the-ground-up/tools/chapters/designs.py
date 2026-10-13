#!/usr/bin/env python3
"""Writes the sources of the system design chapters 7 to 16 from the descriptions below.

Every one of these chapters has the same sections in the same order, so the order is
written once, here, and each design supplies its own content.

    python3 tools/chapters/designs.py
"""
import pathlib
import re

HERE = pathlib.Path(__file__).resolve().parent


def table(head, rows):
    lines = ["| " + " | ".join(head) + " |", "|" + "---|" * len(head)]

    return "\n".join(lines + ["| " + " | ".join(str(cell) for cell in row) + " |" for row in rows])


def numbered(head, rows):
    return table(["No."] + head, [[number] + list(row) for number, row in enumerate(rows)])


def parts(d):
    """The sections of a design chapter that are tables, pictures and API examples, by name.
    The prose of a chapter is written by hand in hand/NN.txt and places them with `@part <name>`."""
    made = {}
    made["covers"] = "\n".join(['<div class="covers">', "", "This chapter covers", ""] + ["- " + item for item in d["covers"]] + ["", "</div>"])
    made["use_cases"] = "@figure %s-use-cases :: The actors and what each of them does." % d["slug"]
    made["functional"] = numbered(["Functional requirement"], [[row] for row in d["functional"]])
    made["non_functional"] = numbered(["Property", "Non-functional requirement"], d["non_functional"])
    made["entities"] = "@figure %s-entities :: The core entities and their fields." % d["slug"]
    made["capacity"] = "\n".join([
        '<div class="estimate">', "", '<img class="builder" src="art/crab-builder.svg" alt="A crab in a hard hat, in tears.">', "",
        "**Arithmetic ahead.** " + d["capacity"], "", '<a class="skip" href="#high-level-design">Skip to the high-level design</a>', "",
        "<details>", "<summary>Show the calculation</summary>", "", table(["Quantity", "Calculation", "Result"], d["calculation"]), "", "</details>", "", "</div>"])
    api = []

    for title, request, response, note in d["api"]:
        api += ["**%s**" % title, "", "```http", request, "```", "", "```http", response, "```", "", note, ""]

    made["api"] = "\n".join(api).rstrip("\n")
    made["design"] = "\n".join([
        "@figure %s-design :: The components and the path of a request. The steps are numbered." % d["slug"], "",
        table(["Component", "Role", "State it holds", "When 1 instance fails"], d["components"])])
    made["walk"] = "\n".join(["The steps follow the arrows of figure %s.%s-design." % (d["number"], d["slug"]), ""]
                             + ["%d. %s" % (number + 1, step) for number, step in enumerate(d["walk"])])
    made["mistakes"] = table(["Mistake", "What goes wrong", "What to do"], d["mistakes"])
    made["failures"] = table(["Failure", "What users see", "How the system recovers"], d["failures"])
    made["tradeoffs"] = table(["Decision", "What it gains", "What it costs"], d["tradeoffs"])
    made["sim"] = "@sim %s" % d["program"]
    made["terms"] = table(["Term", "Meaning"], d["terms"])
    made["summary"] = "\n".join(['<div class="summary">', "", "## Summary", ""] + ["- " + item for item in d["summary"]] + ["", "</div>"])

    return made


def by_hand(d, source):
    """A chapter whose prose is written by hand. `@part name` places one of the parts above."""
    made = parts(d)

    return "\n".join(made[line[6:].strip()] if line.startswith("@part ") else line for line in source.split("\n"))


def chapter(d):
    """A chapter assembled from the description alone, for a design that has no hand-written prose yet."""
    made = parts(d)
    out = ["# %s: System Design" % d["title"], "", d["intro"], "", made["covers"], ""]
    out += ["## The idea, with small numbers", "", d["story"].strip("\n"), ""]
    out += ["## Use cases", "", d["use_cases"], "", made["use_cases"], ""]
    out += ["## Functional requirements", "", made["functional"], ""]
    out += ["## Non-functional requirements", "", made["non_functional"], "", d["consistency"], ""]
    out += ["## Core entities", "", made["entities"], "", "## Capacity estimate", "", made["capacity"], ""]
    out += ["## The API", "", d["api_intro"], "", made["api"], ""]
    out += ["## High-level design", "", made["design"], "", "### One request, step by step", "", made["walk"], ""]

    for heading, body in d["sections"]:
        lines = []

        # A system design chapter prints no code. Its simulation lives in the
        # repository, and the chapter shows what the simulation printed.
        for line in body.strip("\n").split("\n"):
            if line.startswith("@code "):
                continue

            if line.startswith("@out "):
                lines += ["The simulation of this design prints the following.", ""]

            lines.append(line)

        out += ["## " + heading, "", re.sub(r"\n{3,}", "\n\n", "\n".join(lines)), ""]

    out += ["## Mistakes to avoid", "", made["mistakes"], "", "## Failures", "", made["failures"], ""]
    out += ["## Trade-offs", "", made["tradeoffs"], "", "## The simulation", "", made["sim"], ""]
    out += ["## Terms introduced in this chapter", "", made["terms"], "", made["summary"], ""]

    return "\n".join(out)


DESIGNS = []

DESIGNS.append(dict(
    number=7, title="Rate Limiter", slug="limiter", program="ratelimit",
    intro="""A *rate limiter* decides, for every request, whether the caller has asked too often. It
protects an API from a client that sends more than its share, whether by mistake, such as
a retry loop without a pause, or on purpose.

In this chapter, we will design a rate limiter that sits in front of an API and gives
each client its own allowance. We have 2 decisions to make: which counting rule to use
and where to keep the counters when the limiter runs on many machines.""",
    covers=["what a limit should allow and refuse", "the token bucket, worked by hand", "the `429` response and its headers",
            "where the counters live when there are many limiter nodes", "what to do when the counter store is down"],
    use_cases="2 actors use the limiter. Clients meet it on every call. Operators set the limits.",
    functional=["Each client has a limit: a number of requests per second, and a burst it may send at once.",
                "A request within the limit passes to the API unchanged.",
                "A request over the limit is answered with `429 Too Many Requests` and the time to wait.",
                "An operator can change a client's limit without a restart."],
    non_functional=[["Latency", "The check adds less than 1 ms to a request."],
                    ["Availability", "If the limiter cannot decide, requests pass. A broken limiter must not take the API down."],
                    ["Consistency", "Eventual. A client may briefly exceed its limit by a few requests when limiter nodes disagree."],
                    ["Scale", "1 million clients and 50000 requests per second."]],
    consistency="""We accept eventual consistency here on purpose. Suppose a limit of 100 requests per second sometimes lets 103 through. It still protects the API. Making every count exact would put a
strongly consistent write on the path of every request, which is the opposite of what a
protective layer should cost.""",
    capacity="The counters for 1 million clients need about 64 MB of memory, so they fit on 1 node, and we run 3 for availability.",
    calculation=[["Memory per bucket", "client id 40 bytes + tokens 8 + time 8 + overhead 8", "64 bytes"],
                 ["Memory for all clients", "1000000 × 64 bytes", "64 MB"], ["Checks per second", "1 per request", "50000"]],
    api_intro="Every response carries 3 extra headers, so that a well-behaved client can slow down before it is refused.",
    api=[("A request within the limit", "GET /v1/orders HTTP/1.1\nHost: api.example\nAuthorization: Bearer client-42",
          "HTTP/1.1 200 OK\nRateLimit-Limit: 5\nRateLimit-Remaining: 3\nRateLimit-Reset: 1",
          "`RateLimit-Remaining` is the number of tokens left in the client's bucket."),
         ("A request over the limit", "GET /v1/orders HTTP/1.1\nHost: api.example\nAuthorization: Bearer client-42",
          "HTTP/1.1 429 Too Many Requests\nRetry-After: 2\nContent-Type: application/problem+json\n\n"
          '{\n  "type": "/problems/rate-limited",\n  "title": "Too many requests",\n  "status": 429,\n  "detail": "5 requests per second are allowed"\n}',
          "`Retry-After` tells the client how many seconds to wait. Clients that honour it see no second `429`.")],
    components=[["API gateway", "asks the limiter before it forwards a request", "none", "another gateway takes its traffic"],
                ["Rate limiter", "keeps a bucket for each client and decides", "none of its own", "requests pass unchecked until it returns"],
                ["Counter store", "holds the buckets, shared by all limiter nodes", "the buckets, in memory", "limiters fall back to a local bucket"]],
    sections=[("The token bucket", """
Picture a bucket that holds up to 10 tokens. 5 new tokens drop in every second, and a
full bucket stays full. Each request takes 1 token. When the bucket is empty, the request is refused.

2 numbers describe the rule, and each has a plain meaning.

| Number | Meaning | In the example |
|---|---|---|
| Rate | the average number of requests per second that a client may send for ever | 5 |
| Capacity | the size of a burst that is still accepted after a quiet period | 10 |

No timer adds the tokens. The bucket only needs the time of the last
request: when the next request arrives, it adds the tokens for the time that has passed.

@code ratelimit/src/main.rs bucket :: A token bucket

@code ratelimit/src/main.rs run :: 3 kinds of traffic against 1 bucket

@out ratelimit

| Output | What it shows |
|---|---|
| 4 per second: all allowed | Traffic below the rate is always allowed. |
| 8 per second: 8, 8, 8, then 5 | The first seconds drain the full bucket. After that, exactly the rate gets through. |
| a burst of 30: 14 allowed | 10 from the full bucket, plus the 4 tokens that dropped in while the burst arrived. |
"""),
              ("Many limiter nodes", """
With 1 limiter node, the bucket lives in its memory. With 3 nodes behind a load balancer,
a client's requests reach all 3, and 3 private buckets would allow 3 times the limit.

| Where the buckets live | Accuracy | Cost per request |
|---|---|---|
| In each limiter node | wrong by a factor of the number of nodes | none |
| In a shared in-memory store | exact, if refill and take happen in 1 step | 1 round trip, under 1 ms |
| In each node, with each node given a share of the limit | approximate | none |

We choose the shared store. "Refill and take in 1 step" matters: if a node reads the
bucket, computes, and writes it back, 2 nodes can read the same value and both allow a
request. For that reason the store has to run the whole update as a single operation.
""")],
    failures=[["The counter store is unreachable", "nothing: requests pass", "limiters use a local bucket with a third of the limit until the store returns"],
              ["A limiter node stops", "nothing", "the gateway uses the other nodes"],
              ["A client ignores `429` and keeps sending", "that client keeps receiving `429`", "the refusals cost almost nothing, which is the point of the limiter"]],
    tradeoffs=[["Token bucket", "allows short bursts, needs 2 numbers of state", "a client can send a burst right after a quiet period"],
               ["Fail open", "the API stays up when the limiter is down", "no protection during that time"],
               ["Eventual consistency", "no strongly consistent write per request", "a limit can be exceeded slightly"]],
    summary=["A token bucket allows an average rate and a bounded burst with 2 numbers of state per client.",
             "The bucket is refilled when a request arrives, from the time that has passed. No timer is needed.",
             "With several limiter nodes, the buckets live in a shared store that updates a bucket in 1 step.",
             "A limiter that cannot decide lets requests pass.",
             "In the run, a burst of 30 requests had 14 allowed: the bucket of 10 and 4 tokens that arrived meanwhile."]))

DESIGNS.append(dict(
    number=8, title="Unique ID Generator", slug="idgen", program="idgen",
    intro="""Every order, message and user needs an id that no other record has. On 1 database a
counter does the job. With many machines, a shared counter means that every new record
waits for 1 machine, and stops when that machine does.

In this chapter, we will design a service that hands out unique 64-bit ids from any number
of nodes, with no communication between them.""",
    covers=["why a shared counter does not scale", "packing time, a node number and a counter into 64 bits",
            "what happens when a clock goes back", "how many ids 1 node can make"],
    use_cases="Services ask for ids. Operators have 1 task: to give each node a number of its own.",
    functional=["Each caller receives an id that no other caller has received or will receive.",
                "Ids fit in 64 bits, so that they can be database keys.",
                "An id made later is larger than an id made earlier, to within a few milliseconds."],
    non_functional=[["Availability", "Any node can make ids while every other node is down."],
                    ["Latency", "Making an id takes microseconds and involves no network call."],
                    ["Consistency", "Uniqueness is absolute. Order between nodes is approximate, limited by how far their clocks differ."],
                    ["Scale", "Up to 1024 nodes, each making 4 million ids per second."]],
    consistency="""In the usual sense, this design needs no consistency model, because the nodes share no
data. Uniqueness comes from the layout of the id, and the only shared fact, the node
number, is assigned once.""",
    capacity="1 node can make 4096 ids per millisecond, and the 41 bits of time last 69 years.",
    calculation=[["Ids per node per millisecond", "2 to the power 12", "4096"], ["Ids per node per second", "4096 × 1000", "4096000"],
                 ["Nodes", "2 to the power 10", "1024"], ["Years of time", "2 to the power 41 ms ÷ (1000 × 60 × 60 × 24 × 365)", "69.7"]],
    api_intro="There is 1 operation. Callers that need many ids usually link the generator as a library and skip the network.",
    api=[("Get an id", "POST /v1/ids HTTP/1.1\nHost: ids.example", 'HTTP/1.1 201 Created\nContent-Type: application/json\n\n{ "id": "8388636672" }',
          "We send the id as a string, because JSON numbers lose precision above 2 to the power 53.")],
    components=[["Id node", "makes ids from its clock, its number and a counter", "its number and the time of its last id", "the others carry on; its number is not reused while it may return"],
                ["Coordinator", "gives each starting node a number that no other node holds", "the numbers in use", "running nodes are unaffected; new nodes cannot start"]],
    sections=[("The layout of an id", """
An id is 3 numbers side by side in 64 bits.

| Part | Bits | Why it makes ids unique |
|---|---|---|
| Time in milliseconds | 41 | Ids from different milliseconds differ here. |
| Node number | 10 | Ids from different nodes in the same millisecond differ here. |
| Counter | 12 | Ids from 1 node in the same millisecond differ here. |

2 ids can only be equal if they come from the same node, in the same millisecond, with
the same counter value, and the generator does not allow that.

@code idgen/src/main.rs generator :: Making an id

@code idgen/src/main.rs main :: 3 nodes, 100 milliseconds, and a clock that goes back

@out idgen

| Output | What it shows |
|---|---|
| 1228800 ids, 1228800 different | No id was made twice, across 3 nodes. |
| 271200 requests refused | Each node was asked for 5000 ids per millisecond and can make 4096. The rest have to wait for the next millisecond. |
| at time 1999: None | A node whose clock has gone back makes no ids until the clock has caught up. |
"""),
              ("When a clock goes back", """
Clocks are corrected from time to time, and a correction can move a clock backwards. After such a step, a new id could repeat the time, node and counter of an earlier id.

To prevent that, the generator remembers the time of its last id and refuses to make one for an earlier
time. Small steps of a few milliseconds are waited out. Larger steps are a fault that an
operator should see, so the node reports itself as unhealthy.
""")],
    failures=[["A node's clock steps back", "that node answers `503` for the length of the step", "the caller asks another node"],
              ["2 nodes are given the same number", "duplicate ids, silently", "prevented by the coordinator; nothing in the id can detect it afterwards"],
              ["The coordinator is down", "nothing", "running nodes keep their numbers"]],
    tradeoffs=[["Ids from local state only", "no network call, no single point of failure", "order between nodes is only as good as the clocks"],
               ["41 bits of time", "ids sort by creation time", "the scheme ends after 69 years"],
               ["12 bits of counter", "4096 ids per millisecond per node", "a busier caller has to wait for the next millisecond"]],
    summary=["A shared counter makes every new record depend on 1 machine.",
             "An id made of time, node number and counter is unique without any communication between nodes.",
             "The only shared fact is the node number, assigned once at startup.",
             "A node refuses to make ids while its clock is behind the time of its last id.",
             "In the run, 3 nodes made 1228800 ids with no duplicate."]))

DESIGNS.append(dict(
    number=9, title="Distributed Cache", slug="cache", program="cachesim",
    intro="""A *cache* keeps copies of data that is slow to fetch, so that the next request for it is
fast. Those copies live in memory, on machines that sit between a service and its database.

In this chapter, we will design a cache spread over several nodes. We will decide what to
keep when memory is full, how to find the node that holds a key, and what to do about the
moment a popular entry disappears.""",
    covers=["what a cache may and may not promise", "keeping the most recently used keys", "measured hit rates for 4 cache sizes",
            "finding a key's node with the hash ring of chapter 1", "expiry, invalidation and the stampede"],
    use_cases="Services read through the cache and tell it when data has changed. Operators add and remove nodes.",
    functional=["A service can store a value under a key for a limited time.", "A service can read a value, and learns whether the cache had it.",
                "A service can delete a key when the data behind it changes.", "When memory is full, the cache drops the entries that were used longest ago."],
    non_functional=[["Latency", "A read takes under 1 ms."], ["Availability", "The loss of a cache node loses no data that matters, because every entry is a copy."],
                    ["Consistency", "Eventual. A cached value can be older than the database for as long as its time limit."],
                    ["Scale", "100 GB of entries and 200000 reads per second."]],
    consistency="""By nature, a cache is eventually consistent: for some time after a write, a reader may get
the old value. Each entry's time limit is the bound on that staleness, and choosing
it is the main decision a caller makes.""",
    capacity="100 GB at 16 GB of memory per node needs 7 nodes, and we run 8.",
    calculation=[["Memory needed", "given", "100 GB"], ["Usable memory per node", "16 GB × 0.9", "14.4 GB"], ["Nodes", "100 ÷ 14.4", "6.9, so 7"],
                 ["Reads per node", "200000 ÷ 8", "25000 per second"]],
    api_intro="Values are opaque bytes, as in the key-value store of chapter 1. Its time limit travels in a header.",
    api=[("Store a value for 60 seconds", "PUT /v1/cache/user-42 HTTP/1.1\nHost: cache.example\nCache-Control: max-age=60\nContent-Length: 9\n\nada, 1815",
          "HTTP/1.1 204 No Content", "After 60 seconds the entry is gone, whether or not it was read."),
         ("Read a value that is not cached", "GET /v1/cache/user-43 HTTP/1.1\nHost: cache.example", "HTTP/1.1 404 Not Found",
          "Misses are ordinary answers: the caller reads the database and stores the result.")],
    components=[["Cache library", "hashes a key and talks to the node that holds it", "a copy of the ring", "nothing to recover: it is part of the service"],
                ["Cache node", "keeps entries in memory and drops the least recently used", "entries, in memory only", "its keys miss until they are fetched again"],
                ["Database", "holds the real data", "everything", "outside the scope of the cache"]],
    sections=[("What to keep", """
In normal operation a cache is full, so every insert has to drop something. Dropping the
entry that was used longest ago, *least recently used*, works well because requests are
uneven: a few keys are asked for again and again, and those stay near the front.

@code cachesim/src/main.rs lru :: A cache that keeps the most recently used keys

Each key's last use is kept in 2 maps, 1 by key and 1 by time, so that both
"when was this key used" and "which key is oldest" are fast.

@code cachesim/src/main.rs workload :: 1 million requests in which a few keys are popular

@out cachesim

| Cache size | Requests answered from the cache |
|---|---|
| 1% of the keys | 5.7% |
| 5% of the keys | 24.7% |
| 10% of the keys | 42.2% |
| 25% of the keys | 72.7% |

With a quarter of the keys, the cache answers almost 3 quarters of the requests. That
unevenness is the reason caching works, and the reason to measure it for real traffic
before buying memory.
"""),
              ("Finding the node", """
To find a node, the cache library uses the consistent hash ring of chapter 1, with each cache node on the
ring. When a node is added, about 1 key in 9 moves to it and misses once. With
`hash mod N`, almost every key would move, and the database would receive the whole read
load at once.
"""),
              ("The stampede", """
When a popular entry expires, every request for it misses at the same moment, and all of
them go to the database for the same value.

| Remedy | How it works |
|---|---|
| Let 1 caller fetch | The first caller to miss takes a short lock on the key. The others wait for its result. |
| Spread the expiry | Each entry's time limit is shortened by a small random amount, so that entries stored together do not expire together. |
| Refresh early | A read shortly before expiry triggers a refresh in the background and still returns the old value. |
""")],
    failures=[["A cache node is lost", "slower responses for its share of the keys", "the keys are fetched from the database again"],
              ["The whole cache is empty after a restart", "the database receives the full read load", "start with a limit on the number of concurrent database reads"],
              ["A value changes in the database", "readers may see the old value", "the writer deletes the key; otherwise the time limit ends the staleness"]],
    tradeoffs=[["Memory only", "reads in microseconds", "everything is lost on a restart"],
               ["Least recently used", "keeps the popular keys without configuration", "a scan over many keys can push the popular ones out"],
               ["Time limits", "a bound on staleness without any coordination", "values are stale within the bound"]],
    summary=["Everything in a cache is a copy, so losing an entry costs time and loses no data.",
             "Dropping the least recently used entry keeps the keys that are asked for most.",
             "In the run, a cache holding 25% of the keys answered 72.7% of the requests.",
             "A hash ring decides which node holds a key, so that adding a node moves only its share.",
             "When a popular entry expires, 1 caller should fetch it and the others should wait."]))

DESIGNS.append(dict(
    number=10, title="Distributed Lock", slug="lock", program="locksim",
    intro="""Sometimes exactly 1 worker may do a thing at a time: run the nightly billing, write to a
file that 2 writers would corrupt. On 1 machine a mutex does this. Across machines, the
holder of a lock can crash without releasing it, or stop for a while and wake up after the
lock has passed to someone else.

In this chapter, we will design a lock service for that world. Our design has 2 parts that only work together: a lock that expires by itself, and a token that makes a late holder
harmless.""",
    covers=["why a lock must expire", "why an expiring lock alone is unsafe", "the fencing token",
            "a run in which a paused client wakes up after losing the lock", "what the storage has to do"],
    use_cases="Workers acquire, renew and release locks. Nobody else uses the lock service.",
    functional=["A worker can acquire a named lock. At most 1 worker holds a lock at any time.",
                "A lock is held for a limited time, a *lease*, and the holder can renew it.",
                "A lock whose lease has ended can be acquired by another worker.",
                "Every lease comes with a token that is larger than the token of every earlier lease."],
    non_functional=[["Consistency", "Strong. At any moment, the lock service grants a lock to at most 1 worker."],
                    ["Availability", "The service survives the loss of 1 of its 3 nodes."],
                    ["Latency", "Acquiring a lock takes 1 round trip to a majority, a few milliseconds."]],
    consistency="""Strong consistency is required here, and the lock service gets it the way chapters 3 and 4 do: a
leader, a log, and a majority of 3 nodes. If the service could split into 2 halves that each grant the lock, it would be worse than no lock.""",
    capacity="A lock is about 100 bytes, so a million locks fit in 100 MB, and 3 small nodes are enough.",
    calculation=[["Memory per lock", "name 50 bytes + holder 30 + token 8 + expiry 8", "about 100 bytes"], ["Memory for 1 million locks", "1000000 × 100 bytes", "100 MB"]],
    api_intro="A lock is a resource with a name. Creating it acquires the lock, and the response carries the token.",
    api=[("Acquire a lock for 10 seconds", 'POST /v1/locks/nightly-billing HTTP/1.1\nHost: locks.example\nContent-Type: application/json\n\n{ "holder": "worker-a", "seconds": 10 }',
          'HTTP/1.1 201 Created\nContent-Type: application/json\n\n{ "token": 1, "expires_in": 10 }',
          "Workers have to pass the token on to whatever the lock protects."),
         ("Acquire a lock that is held", 'POST /v1/locks/nightly-billing HTTP/1.1\nHost: locks.example\nContent-Type: application/json\n\n{ "holder": "worker-b", "seconds": 10 }',
          'HTTP/1.1 409 Conflict\nContent-Type: application/problem+json\n\n{\n  "type": "/problems/lock-held",\n  "title": "The lock is held",\n  "status": 409,\n  "detail": "held for 9 more seconds"\n}',
          "`409 Conflict` is the status for a request that is valid but cannot be carried out in the current state.")],
    components=[["Worker", "acquires the lock, then does its work", "the token of its lease", "its lease runs out, and another worker can acquire the lock"],
                ["Lock service", "grants leases and counts tokens", "the locks, replicated on 3 nodes", "the other 2 nodes continue"],
                ["Storage", "the thing the lock protects; checks the token", "the highest token it has accepted", "outside the scope of the lock service"]],
    sections=[("Why a lock expires", """
If a lock were held until its holder released it, a holder that crashed would hold it for
ever. So every lock is a lease: it ends by itself, and a live holder renews it in time.

Expiry creates a new problem. Workers can be paused, by a long pause of the runtime, a
slow disk, or a suspended virtual machine, for longer than its lease. When it wakes up, it
has no way to know that time has passed. It still believes it holds the lock.
"""),
              ("The fencing token", """
We stop trusting what the worker believes. Each lease carries a number that grows
by 1, the *fencing token*. Every write carries the token, and the storage refuses any write whose token is lower than one it has already seen.

@code locksim/src/main.rs lock :: A lock that expires, and the token of each lease

@code locksim/src/main.rs storage :: The storage checks the token

@code locksim/src/main.rs main :: A worker that pauses for longer than its lease

@out locksim

| Time | What it shows |
|---|---|
| t=1 | While the lease is valid, a second client is refused. |
| t=12 | After the lease has ended, the lock passes on, with token 2. |
| t=17 | Client A is wrong about holding the lock, and it does not matter: its token 1 is refused. |

By itself, the lock service could not have prevented the write at t=17. Only the storage sees
both writes, so only the storage can order them. Without a check on the protected resource, a lock service guarantees nothing.
""")],
    failures=[["A worker crashes while holding a lock", "the lock is unavailable until the lease ends", "another worker acquires it afterwards"],
              ["A worker pauses for longer than its lease", "nothing wrong: its late writes are refused", "the worker sees the refusal and stops"],
              ["A lock service node is lost", "nothing", "the remaining 2 nodes form a majority"]],
    tradeoffs=[["Leases", "a crashed holder cannot block others for ever", "work that takes longer than a lease needs renewals"],
               ["Fencing tokens", "a late holder cannot cause damage", "the protected resource has to check tokens"],
               ["A majority of 3 nodes", "at most 1 holder per lock", "acquiring a lock costs a round trip"]],
    summary=["A distributed lock has to expire, because its holder may have crashed for good.",
             "A holder that pauses for longer than its lease does not know that it has lost the lock.",
             "A fencing token grows with every lease, and the protected resource refuses a lower token.",
             "The check has to be made by the resource, because only the resource sees both writers.",
             "In the run, the write of the paused client was refused, and the storage kept the later write."]))

DESIGNS.append(dict(
    number=11, title="Message Queue", slug="queue", program="queuesim",
    intro="""A *message queue* lets one service tell others that something happened without waiting
for them. An order service records "order 7 was paid" and moves on. Billing, shipping and
email each read that message when they are ready, and none of them can slow the order
service down or lose the message by being offline.

In this chapter, we will design a queue built on an append-only log, the structure of
chapter 2. We have to settle how messages keep their order, and what a consumer has to do so that a crash neither loses a message nor acts on it twice.""",
    covers=["topics, partitions and offsets", "ordering by key", "consumer groups and committed offsets",
            "a consumer that crashes before it commits", "at-least-once delivery, and making a consumer safe against repeats"],
    use_cases="Producers publish, consumers fetch and commit, and operators size the topics.",
    functional=["A producer can publish a message to a topic. Messages with the same key are delivered in the order they were published.",
                "A consumer can fetch messages starting from an offset.", "A group of consumers shares a topic: each message goes to 1 member of the group.",
                "A consumer can commit an offset, and after a restart it continues from the committed offset.", "Messages are kept for 7 days, whether or not they were read."],
    non_functional=[["Durability", "A published message survives the loss of 1 broker."], ["Consistency", "Strong within a partition: every consumer sees the same messages in the same order."],
                    ["Delivery", "At least once. A message can be delivered again after a consumer crash."], ["Scale", "100000 messages per second of 1 KB each."]],
    consistency="""Order is the consistency property of a queue. Within a partition it is strong: the log
has 1 order, replicated with a leader and a majority as in chapter 3. Across partitions
there is no order at all, which is the price of reading them in parallel.""",
    capacity="7 days of messages are 60 TB for 1 copy and 181 TB for 3, about 46 brokers with 4 TB disks.",
    calculation=[["Bytes per day", "100000 × 1 KB × 86400 s", "8.64 TB"], ["7 days, 1 copy", "8.64 × 7", "60.5 TB"], ["3 copies", "60.5 × 3", "181 TB"],
                 ["Brokers with 4 TB disks", "181 ÷ 4", "45.4, so 46"]],
    api_intro="A topic is a resource, its messages are a collection, and a group's position is a small resource of its own.",
    api=[("Publish a message", 'POST /v1/topics/orders/messages HTTP/1.1\nHost: queue.example\nContent-Type: application/json\n\n{ "key": "order-7", "body": "paid" }',
          'HTTP/1.1 201 Created\nContent-Type: application/json\n\n{ "partition": 1, "offset": 2 }', "Its key chooses the partition, and the response says where the message now lives."),
         ("Commit an offset", 'PUT /v1/topics/orders/partitions/1/offsets/billing HTTP/1.1\nHost: queue.example\nContent-Type: application/json\n\n{ "committed": 6 }',
          "HTTP/1.1 204 No Content", "`PUT` is idempotent, so committing the same offset twice is harmless.")],
    components=[["Broker", "stores partitions as logs and serves fetches", "the logs", "a follower of each partition it led takes over"],
                ["Consumer", "fetches, acts, commits", "none that must survive", "another member of its group takes over its partitions"],
                ["Offset store", "remembers each group's committed offsets", "the offsets, replicated", "consumers keep working and commit later"]],
    sections=[("Partitions and order", """
A topic is split into *partitions*, and each partition is a log. Each message goes to the partition chosen by a hash of its key, so all messages about `order-7` land in 1 log and
keep their order. Messages with different keys may be in different partitions, where
nothing orders them against each other.

Because of this split, a group of consumers can work in parallel: each partition is read by 1
member of the group at a time.
"""),
              ("Offsets and repeats", """
Brokers do not track which messages a consumer has handled. They store 1 number per
group and partition, the *committed offset*, and the consumer moves it forward.

For each batch a consumer acts and then commits, and it can crash between the 2 steps.

| Order of steps | After a crash between them | Called |
|---|---|---|
| Commit, then act | the messages are skipped | at most once |
| Act, then commit | the messages are delivered again | at least once |

Losing messages is rarely acceptable, so consumers act first. They then have to cope with
seeing a message twice.

@code queuesim/src/main.rs topic :: A topic of partitions, and publishing by key

@code queuesim/src/main.rs consumer :: A consumer that remembers what it has acted on

@code queuesim/src/main.rs main :: Producing 6 messages, and a crash before the commit

@out queuesim

| Output | What it shows |
|---|---|
| every message in partition 1 | With these 4 keys, the hash put all of them in the same partition. |
| after the restart: seen before, skipped | The queue delivered all 6 messages again, because the committed offset was still 0. |
| 6 messages, 6 actions | The consumer acted on each message once, because it remembers what it has done. |

Remembering "what I have done" is the consumer's job. In practice it stores the message's
position together with the result of acting on it, in the same database write, so that
the 2 cannot disagree.
""")],
    failures=[["A consumer crashes before it commits", "nothing, if the consumer ignores repeats", "its messages are delivered again"],
              ["A broker is lost", "a pause of about 1 second for its partitions", "followers are elected leaders, as in chapter 4"],
              ["A consumer is too slow", "its messages wait longer", "more partitions and more group members; the log holds the backlog"]],
    tradeoffs=[["Partitions", "parallel consumers and more throughput", "no order across partitions"],
               ["Offsets kept by position", "the broker stores 1 number per group", "a consumer cannot skip 1 bad message without moving past it"],
               ["At-least-once delivery", "no message is lost", "consumers must tolerate repeats"]],
    summary=["A queue is a set of append-only logs. A message's key decides its log, and a log keeps its order.",
             "A group's progress is 1 number per partition, the committed offset.",
             "A consumer that acts before it commits can see a message twice after a crash.",
             "The consumer makes repeats harmless by remembering what it has acted on.",
             "In the run, 6 messages were delivered twice and acted on once."]))

DESIGNS.append(dict(
    number=12, title="Job Scheduler", slug="jobs", program="jobsim",
    intro="""A *job scheduler* runs work that should not happen inside a request: resizing an
uploaded image, sending a monthly report, retrying a payment tomorrow. Services submit a job and return to their user. Workers pick jobs up and run them.

In this chapter, we will design a scheduler in which a job is finished even when the
worker that started it dies half way.""",
    covers=["the states of a job", "leases: lending a job to a worker until a deadline", "a worker that crashes in the middle of a job",
            "why a job can run twice, and what that asks of the job"],
    use_cases="Developers submit jobs and look at their state. Workers take jobs and report results.",
    functional=["A developer can submit a job, to run now or at a later time.", "A worker can take a waiting job. A job is given to 1 worker at a time.",
                "A worker reports success or failure. A failed job is tried again, up to 5 times.", "A job whose worker stops responding is given to another worker.",
                "A developer can read the state and the number of attempts of a job."],
    non_functional=[["Durability", "A submitted job is not lost when a scheduler node fails."], ["Consistency", "Strong for job state: 2 workers are not given the same job at the same time."],
                    ["Delivery", "At least once. A job can be started a second time."], ["Scale", "10 million jobs per day."]],
    consistency="""Job state is strongly consistent, stored with a leader and a majority as in chapter 3,
because handing 1 job to 2 workers is the failure this system exists to prevent. Even so, a
job can *run* twice, for the reason the lock chapter gave: a worker can outlive its lease
without knowing it.""",
    capacity="10 million jobs per day are 116 per second on average, which 1 replicated job store handles.",
    calculation=[["Jobs per second, average", "10000000 ÷ 86400", "116"], ["Jobs per second, at a peak of 10 times the average", "116 × 10", "1160"],
                 ["Storage for 30 days", "10000000 × 30 × 1 KB", "300 GB"]],
    api_intro="Every path names a resource: a job, a lease, a result. Taking a job has no verb in its path. The worker creates a lease, and the lease says which job it covers.",
    api=[("Submit a job", 'POST /v1/jobs HTTP/1.1\nHost: jobs.example\nContent-Type: application/json\n\n{ "kind": "resize-image", "payload": { "image": "cat.jpg" }, "run_at": "2026-10-14T09:00:00Z" }',
          'HTTP/1.1 201 Created\nLocation: /v1/jobs/8231\nContent-Type: application/json\n\n{ "id": 8231, "state": "waiting", "attempts": 0 }',
          "`Location` gives the URL of the new job, as HTTP expects after a `201`."),
         ("Take a job: create a lease", 'POST /v1/leases HTTP/1.1\nHost: jobs.example\nContent-Type: application/json\n\n{ "worker": "worker-2", "seconds": 30 }',
          'HTTP/1.1 201 Created\nLocation: /v1/leases/771\nContent-Type: application/json\n\n'
          '{ "lease": 771, "job": { "id": 8231, "kind": "resize-image", "payload": { "image": "cat.jpg" } }, "expires_in": 30 }',
          "A worker takes a job by creating a lease, so the path names a thing and the method says what happens to it. "
          "The scheduler picks the job. When no job is waiting, the answer is `204 No Content`."),
         ("Report the result", 'PUT /v1/jobs/8231/result HTTP/1.1\nHost: jobs.example\nContent-Type: application/json\n\n{ "lease": 771, "outcome": "succeeded" }',
          "HTTP/1.1 204 No Content", "The lease number proves that this worker still holds the job. A report with an expired lease is answered `409 Conflict`.")],
    components=[["Scheduler", "accepts jobs and hands out leases", "none of its own", "another scheduler node serves the API"],
                ["Job store", "holds every job and its state", "the jobs, replicated", "a follower takes over, as in chapter 4"],
                ["Worker", "takes a job, runs it, reports", "none that must survive", "its jobs return to the queue when their leases end"],
                ["Reclaimer", "returns jobs with expired leases to the queue", "none", "leases are reclaimed late, by the next reclaimer run"]],
    sections=[("Leases", """
From the outside, a slow worker and a dead one look the same. Our scheduler therefore
lends each job for a fixed time. Workers that need longer renew the lease, and a worker
that says nothing loses the job when the deadline passes.

| State | Meaning | Next state |
|---|---|---|
| waiting | in the queue | running, when a worker takes it |
| running | lent to a worker until a deadline | done on success, waiting on failure or when the deadline passes |
| done | finished | none |

@code jobsim/src/main.rs scheduler :: Jobs, leases, and reclaiming a job whose worker went silent

@code jobsim/src/main.rs main :: 3 workers and 6 jobs, with 1 worker that crashes

@out jobsim

| Output | What it shows |
|---|---|
| t=0: worker 1 takes job 1 | Worker 1 crashes at t=2 and does not finish it. |
| t=3: job 1 is back in the queue | Its lease of 3 seconds ran out with no report. |
| t=4: worker 0 takes job 1 | Another worker runs it. |
| 6 of 6 done, attempts 1 2 1 1 1 1 | Every job finished, and job 1 needed 2 attempts. |
"""),
              ("A job can run twice", """
Suppose worker 1 had not crashed but only stalled, and finished job 1 at t=5, after the
scheduler had given it to worker 0. Its late report is refused, because worker 1 no longer holds the lease. Even so, the
work was done twice.

Every job therefore has to be safe to repeat. Resizing an image is: the second run writes the
same file. Charging a card is not, unless the charge carries a key that the payment
provider uses to recognise the repeat. Designing jobs this way is the price of a scheduler
that does not lose them.
""")],
    failures=[["A worker crashes during a job", "the job finishes later", "its lease ends and another worker takes the job"],
              ["A worker stalls and finishes late", "nothing, if the job is safe to repeat", "its late report is refused"],
              ["A job fails every time", "the job stops after 5 attempts", "it is marked failed for a person to inspect"]],
    tradeoffs=[["Leases with deadlines", "no job is stuck with a dead worker", "a slow worker can cause a second run"],
               ["Workers pull jobs", "a worker takes work only when it has room", "a job waits until some worker asks"],
               ["At-least-once execution", "no job is lost", "jobs must be safe to repeat"]],
    summary=["A scheduler lends a job to a worker until a deadline, and takes it back when the deadline passes in silence.",
             "Job state is strongly consistent, so a job has 1 holder at a time.",
             "A job can still run twice, when its first worker was slow and not dead.",
             "Jobs therefore have to be safe to repeat.",
             "In the run, a worker crashed with job 1, and job 1 was finished by another worker on its second attempt."]))

DESIGNS.append(dict(
    number=13, title="Notification Service", slug="notify", program="notifysim",
    intro="""A *notification service* delivers messages to people: an email that an order has
shipped, a text message with a login code, a push message on a phone. It sends them
through outside providers, which are slow at times and fail at times.

In this chapter, we will design a service that keeps trying when a provider fails and
still sends each notification once.""",
    covers=["why sending goes through a queue", "retries with growing pauses", "an idempotency key against duplicate requests",
            "setting aside what cannot be delivered"],
    use_cases="Services ask for notifications to be sent. Users choose which channels they accept.",
    functional=["A service can ask for a notification to a user on a channel: email, text message or push.",
                "A request carries a key. A second request with the same key sends nothing.",
                "A failed send is tried again, up to 5 times, with a longer pause each time.", "A notification that fails 5 times is set aside and reported.",
                "A user's choice of channels is respected."],
    non_functional=[["Delivery", "At least once to the provider, and once per key from the caller's point of view."], ["Latency", "A notification leaves within 5 seconds of the request when the provider is healthy."],
                    ["Consistency", "Strong for the set of keys already seen. Eventual for delivery state."], ["Scale", "50 million notifications per day."]],
    consistency="""Only 1 piece of state needs strong consistency: the set of keys that have been accepted.
If 2 API nodes disagreed about whether a key was seen, a user would get the same message
twice. Everything after that point can be eventual.""",
    capacity="50 million notifications per day are 580 per second on average, and the queue absorbs peaks of 10 times that.",
    calculation=[["Per second, average", "50000000 ÷ 86400", "579"], ["Per second, peak", "579 × 10", "5790"], ["Senders, at 50 sends per second each", "5790 ÷ 50", "116"]],
    api_intro="Callers invent the key. Good keys name the event, such as `order-7-shipped`, so that a retry of the same event repeats the same key.",
    api=[("Send a notification", 'POST /v1/notifications HTTP/1.1\nHost: notify.example\nIdempotency-Key: order-7-shipped\nContent-Type: application/json\n\n'
          '{ "user": "user-42", "channel": "email", "body": "Your order has shipped." }',
          'HTTP/1.1 202 Accepted\nLocation: /v1/notifications/5512\nContent-Type: application/json\n\n{ "id": 5512, "state": "queued" }',
          "`202 Accepted` says that the request was taken and the work will happen later."),
         ("The same request again", 'POST /v1/notifications HTTP/1.1\nHost: notify.example\nIdempotency-Key: order-7-shipped\nContent-Type: application/json\n\n'
          '{ "user": "user-42", "channel": "email", "body": "Your order has shipped." }',
          'HTTP/1.1 200 OK\nContent-Type: application/json\n\n{ "id": 5512, "state": "sent" }', "Our service returns the same id and sends nothing.")],
    components=[["API", "accepts requests and drops repeats by key", "the keys seen, replicated", "another API node serves requests"],
                ["Queue", "holds notifications until a sender takes them", "the messages, as in chapter 11", "a follower broker takes over"],
                ["Sender", "calls the provider and retries", "none", "its message is delivered again to another sender"],
                ["Provider", "an outside email, text or push service", "outside our control", "senders retry, then set the message aside"]],
    sections=[("Why a queue sits in the middle", """
Providers may take 2 seconds to answer, or be down for 10 minutes. If the API called the
provider directly, every caller would wait that long, and a provider outage would become
an outage of every service that sends notifications. With a queue between them, the API
answers in milliseconds and the senders work through the backlog at the provider's pace.
"""),
              ("Retries with growing pauses", """
Failed sends are tried again, and the pause before each try doubles: 1, 2, 4, 8 seconds.
Short pauses first, because most failures are brief. Longer pauses later, so that a
provider in trouble is not flooded by its own callers.

@code notifysim/src/main.rs retry :: Trying up to 5 times, with a pause that doubles

@code notifysim/src/main.rs main :: 5 requests: a repeat, some failures, and one that cannot be delivered

@out notifysim

| Output | What it shows |
|---|---|
| order-8: sent on try 3, after 3 seconds | 2 failures cost pauses of 1 and 2 seconds. |
| order-7, second request: not sent again | The key was seen before. |
| order-9: sent on try 5, after 15 seconds | The pauses 1, 2, 4 and 8 add up to 15. |
| order-10: set aside | After 5 tries the service stops, so that 1 bad message cannot be retried for ever. |

In a real deployment each pause also gets a small random addition. Without it, thousands
of messages that failed together would all retry at the same instant.
""")],
    failures=[["The provider is down", "notifications arrive late", "senders retry with growing pauses; the queue holds the backlog"],
              ["A sender crashes after the provider accepted a message", "the user may get that message twice", "the queue redelivers; providers that accept a key drop the repeat"],
              ["A caller retries its request", "nothing", "the idempotency key identifies the repeat"]],
    tradeoffs=[["A queue between API and provider", "callers are not slowed by the provider", "delivery is no longer immediate"],
               ["Retries", "brief failures are invisible", "a message can be sent twice without a key on the provider's side"],
               ["Setting aside after 5 tries", "a bad message does not block the others", "someone has to look at what was set aside"]],
    summary=["Sending goes through a queue, so that a slow provider does not slow its callers.",
             "A failed send is retried with pauses that double, and set aside after 5 tries.",
             "An idempotency key from the caller makes a repeated request send nothing.",
             "In the run, a notification that failed 4 times was sent on try 5, 15 seconds after the first."]))

DESIGNS.append(dict(
    number=14, title="URL Shortener", slug="shortener", program="shortener",
    intro="""A *URL shortener* turns a long address into a short one, such as `sho.rt/4C92`, and
sends anyone who opens the short address on to the long one. It is a small system with an
uneven load: a link is created once and may be opened millions of times.

In this chapter, we will design it from parts that earlier chapters built: the key-value
store, the id generator and the cache.""",
    covers=["making a short code: a counter in base 62, or part of a hash", "measured collisions of both methods",
            "a read path that is served from a cache", "the choice between redirect status `301` and `302`"],
    use_cases="Authors create links and read their click counts. Visitors open links, and they are the bulk of the traffic.",
    functional=["An author can create a short link for a URL and receives a code of 7 characters.", "Opening a short link redirects the visitor to the URL.",
                "A code, once given out, always leads to the same URL.", "An author can read how often a link was opened."],
    non_functional=[["Availability", "99.99% for redirects. A link that does not open is the worst failure."], ["Latency", "A redirect takes under 10 ms."],
                    ["Consistency", "Strong for creating a link: each code belongs to exactly 1 URL. Eventual for click counts."],
                    ["Scale", "100 million new links per month, and 100 redirects for every new link."]],
    consistency="""Creating links and counting clicks need different guarantees. Creating a link must be strongly
consistent, since 1 code for 2 URLs sends visitors to the wrong place for ever. Nobody is harmed by a click count that is a few seconds behind, so counting is eventual and cheap.""",
    capacity="5 years of links are 6 billion codes and 3 TB, and redirects average 3900 per second.",
    calculation=[["Links in 5 years", "100000000 × 12 × 5", "6 billion"], ["Codes of 7 characters", "62 to the power 7", "3.5 trillion"],
                 ["Storage for links", "6 billion × 500 bytes", "3 TB"], ["New links per second", "100000000 ÷ (30 × 86400)", "39"], ["Redirects per second", "39 × 100", "3900"]],
    api_intro="Creating a link is an ordinary `POST`. Opening one is a plain `GET` on the shortest possible path.",
    api=[("Create a link", 'POST /v1/links HTTP/1.1\nHost: sho.rt\nContent-Type: application/json\n\n{ "url": "https://example.com/a/very/long/address?with=parameters" }',
          'HTTP/1.1 201 Created\nLocation: /v1/links/4C92\nContent-Type: application/json\n\n{ "code": "4C92", "short_url": "https://sho.rt/4C92" }', "Its code is the base 62 form of the link's id."),
         ("Open a link", "GET /4C92 HTTP/1.1\nHost: sho.rt", "HTTP/1.1 301 Moved Permanently\nLocation: https://example.com/a/very/long/address?with=parameters\nCache-Control: max-age=86400",
          "Browsers follow `Location` by themselves.")],
    components=[["Web server", "creates links and answers redirects", "none", "the load balancer uses the others"],
                ["Cache", "holds the most opened links", "copies, in memory", "its links are read from the store once more"],
                ["Key-value store", "maps a code to its URL", "every link, replicated", "a follower takes over, as in chapter 4"],
                ["Id generator", "gives each new link a number", "see chapter 8", "another id node is asked"]],
    sections=[("Making the code", """
A code is 7 characters from 62: the digits and the letters in both cases. That gives 3.5
trillion codes, about 600 times what 5 years need.

| Method | How | Problem |
|---|---|---|
| Part of a hash | hash the URL and keep the first characters | 2 URLs can receive the same code |
| A counter | give each link the next number, written in base 62 | needs a source of unique numbers |

Chapter 8 built that source, so we use the counter. Our simulation measures what the hash method would have cost.

@code shortener/src/main.rs base62 :: Writing a number in base 62, and reading it back

@code shortener/src/main.rs main :: 2 million URLs with both methods

@out shortener

| Output | What it shows |
|---|---|
| 1000000 is `4C92` | A million links in, codes are still 4 characters long. |
| counter: 0 collisions | Different numbers always give different codes. |
| hash, 6 characters: 97 collisions | Among 2 million URLs, 97 pairs would have shared a code. Each needs a check and a second try. |

Codes from a counter have 1 drawback: they can be guessed in order. Services that must
hide their links from guessing mix the bits of the id before encoding it.
"""),
              ("The read path", """
100 of every 101 requests are redirects, and a few links receive most of them. Chapter 9
measured that a cache holding a quarter of the keys answers about 3 quarters of the
requests, so the web servers ask the cache first and the store second.

Links do not change, which removes the hard part of caching: a cached link is correct for
as long as it is kept.
"""),
              ("301 or 302", """
| Status | Browser behaviour | Effect |
|---|---|---|
| `301 Moved Permanently` | remembers the redirect | repeat visits skip our servers, so load is lower and clicks go uncounted |
| `302 Found` | asks again every time | every visit is counted, and load is higher |

We answer `301` with a time limit of 1 day, which counts each visitor about once a day.
""")],
    failures=[["The cache is lost", "redirects are slower for a few minutes", "links are read from the store and cached again"],
              ["The id generator is unreachable", "new links cannot be created; redirects work", "another id node is used"],
              ["A store leader fails", "about 1 second without new links for its shard", "a follower is elected"]],
    tradeoffs=[["Codes from a counter", "no collisions and no retry", "codes can be guessed in order"],
               ["Cache in front of the store", "most redirects avoid the store", "more memory"], ["`301` with a time limit", "fewer requests reach us", "click counts are approximate"]],
    summary=["A short code is a link's number written in base 62. 7 characters give 3.5 trillion codes.",
             "A counter gives each link its own code. Part of a hash gave 97 collisions among 2 million URLs.",
             "Redirects outnumber new links by 100 to 1 and are served from a cache.",
             "Links do not change, so a cached link stays correct.",
             "The redirect status decides whether repeat visits are counted."]))

DESIGNS.append(dict(
    number=15, title="News Feed", slug="feed", program="feedsim",
    intro="""A *news feed* shows each member the recent posts of the accounts they follow, newest
first. Building 1 feed is easy. Building them for millions of members, where 1 account can
have millions of followers, is a question of when to do the work: when a post is written,
or when a feed is read.

In this chapter, we will count the work of both and arrive at the mixture that large feeds
use.""",
    covers=["copying a post to followers when it is written", "collecting posts when a feed is read",
            "the account with 2 million followers", "a mixture of both, with the work counted"],
    use_cases="Members are the only actors: they post, follow and read.",
    functional=["A member can publish a post.", "A member can follow and unfollow an account.",
                "A member can read a feed of recent posts from followed accounts, newest first, in pages.", "A new post appears in followers' feeds within 5 seconds."],
    non_functional=[["Latency", "Reading a feed takes under 200 ms."], ["Availability", "99.9% for reading feeds."],
                    ["Consistency", "Eventual. Followers may see a post a few seconds apart, and in slightly different order."], ["Scale", "10 million members, 20 feed reads for every post."]],
    consistency="""Feeds are the textbook case for eventual consistency. Nobody is harmed if a post reaches
1 follower 3 seconds before another, and accepting that lets the copying happen in the
background.""",
    capacity="A feed entry is 16 bytes, so the newest 500 entries for 10 million members are 80 GB of cache.",
    calculation=[["Feed entry", "post id 8 bytes + time 8 bytes", "16 bytes"], ["Entries kept per member", "the newest 500", "500"],
                 ["Feed cache", "10000000 × 500 × 16 bytes", "80 GB"], ["Posts per day", "10000000 members × 2", "20 million"]],
    api_intro="Members read the feed in pages with a cursor, for the reason given in chapter 1: new posts arrive while a member scrolls.",
    api=[("Publish a post", 'POST /v1/posts HTTP/1.1\nHost: feed.example\nContent-Type: application/json\n\n{ "body": "Shipped the new release." }',
          'HTTP/1.1 201 Created\nLocation: /v1/posts/90210\nContent-Type: application/json\n\n{ "id": 90210, "time": "2026-10-14T09:00:00Z" }', "We store the post before the response and copy it to followers afterwards."),
         ("Read a page of the feed", "GET /v1/feed?limit=2 HTTP/1.1\nHost: feed.example",
          'HTTP/1.1 200 OK\nContent-Type: application/json\n\n{\n  "posts": [\n    { "id": 90210, "author": "ada", "body": "Shipped the new release." },\n    { "id": 90188, "author": "grace", "body": "Found the bug." }\n  ],\n  "next_after": "90188"\n}',
          "`next_after` is the id of the last post on the page.")],
    components=[["Post service", "stores a post and queues the copying", "posts, in the key-value store", "another instance serves requests"],
                ["Fan-out workers", "add a post to each follower's list", "none", "their tasks are delivered again, as in chapter 11"],
                ["Feed cache", "1 list of recent post ids per member", "lists, in memory", "lists are rebuilt from the posts on the next read"],
                ["Feed service", "reads a member's list and fetches the posts", "none", "another instance serves requests"]],
    sections=[("2 ways to build a feed", """
| | Copy on write | Collect on read |
|---|---|---|
| When a post is written | it is added to every follower's list | nothing more happens |
| When a feed is read | the member's list is ready | the posts of every followed account are fetched and merged |
| Cost of a post | 1 list update per follower | 1 |
| Cost of a read | 1 | 1 fetch per followed account |

Feeds are read far more often than posts are written, so copying on write looks right:
pay once per post, and every read is cheap. It fails for 1 kind of account.

@code feedsim/src/main.rs accounts :: 1000 ordinary accounts and 1 with 2 million followers

@code feedsim/src/main.rs cost :: Counting the work of each method

@out feedsim

| Method | Work per day |
|---|---|
| Copy on write for everyone | 20.4 million list updates, of which 20 million are for the 1 large account |
| Collect on read for everyone | 4 million fetches |
| Mixture | 400000 list updates and 20005 fetches |

98% of the copying is caused by the 1 account with 2 million followers. Each of its 10 daily
posts means 2 million list updates.
"""),
              ("The mixture", """
Our mixture treats the 2 kinds of account differently. Posts by ordinary accounts are
copied to their followers' lists. Posts by accounts above a threshold, 10000 followers
here, are left where they are, and a reader's feed merges them in when it is read.

Readers follow only a handful of such accounts, so the merge adds a few fetches to a
read, where copying would have added millions of updates to a write.
""")],
    failures=[["Fan-out workers fall behind", "posts appear in feeds late", "the queue holds the tasks; more workers are added"],
              ["The feed cache is lost", "the first read of each feed is slow", "lists are rebuilt by collecting on read"],
              ["A member unfollows an account", "old posts of that account may remain in the list briefly", "they are filtered out when the feed is read"]],
    tradeoffs=[["Copy on write", "reads are 1 lookup", "an account with many followers makes writes expensive"],
               ["Collect on read", "writes cost nothing extra", "every read fetches from many accounts"],
               ["A mixture with a threshold", "both costs stay small", "2 code paths, and a threshold to tune"]],
    summary=["A feed can be built when a post is written or when the feed is read.",
             "Copying on write makes reads cheap, and makes a post by a large account very expensive.",
             "In the count, 1 account of 1001 caused 98% of the copying.",
             "A mixture copies the posts of ordinary accounts and collects those of large accounts at read time.",
             "Feeds are eventually consistent, which lets the copying happen in the background."]))

DESIGNS.append(dict(
    number=16, title="Object Store", slug="objects", program="objectsim",
    intro="""An *object store* keeps files of any size under a name: photos, videos, backups. Unlike
the key-value store of chapter 1, its values do not fit in memory or in a single request,
and some are larger than a disk.

In this chapter, we will design a store that cuts every object into chunks, keeps each
chunk on 3 nodes, and notices and repairs a chunk that a disk has damaged.""",
    covers=["cutting objects into chunks", "naming a chunk by its checksum", "separating names from bytes",
            "a damaged copy, found and repaired on read", "replication and its cost"],
    use_cases="Applications upload, download and list. Operators replace failed disks and nodes.",
    functional=["An application can upload an object of up to 5 TB under a name in a bucket.", "An application can download an object, or a range of its bytes.",
                "An application can list the objects of a bucket by prefix.", "An object that was stored is returned unchanged, or the store reports an error. It does not return damaged bytes."],
    non_functional=[["Durability", "An object survives the loss of any 2 of the 3 nodes that hold a chunk, and damage on a disk."], ["Availability", "99.9% for uploads and downloads."],
                    ["Consistency", "Strong for names: after an upload completes, a download returns the new object. Chunks do not change at all."],
                    ["Scale", "1 billion objects and 100 PB of data."]],
    consistency="""Consistency is simple here because of a design choice: a chunk is named by the checksum
of its bytes, so a chunk with a given name has only 1 possible content and is written
once. Only 1 thing changes: the small record that maps an object's name to its
list of chunks, and that record lives in a strongly consistent store like the one of
chapter 1.""",
    capacity="100 PB in 3 copies is 300 PB, about 21000 disks of 16 TB, with 25 billion chunks to keep track of.",
    calculation=[["Raw storage", "100 PB × 3 copies", "300 PB"], ["Disks of 16 TB, 90% full", "300 PB ÷ 14.4 TB", "20834"],
                 ["Chunks of 4 MB", "100 PB ÷ 4 MB", "25 billion"], ["Metadata", "1 billion objects × 1 KB", "1 TB"]],
    api_intro="Objects are addressed as `bucket/key`. Request and response bodies are the object itself.",
    api=[("Upload an object", "PUT /v1/buckets/holiday/video.mp4 HTTP/1.1\nHost: objects.example\nContent-Type: video/mp4\nContent-Length: 10485760\n\n(10485760 bytes)",
          'HTTP/1.1 201 Created\nETag: "crc32:9a3f11c2-3"', "Clients can compare the `ETag`, which names the content, with their own checksum."),
         ("Download part of an object", "GET /v1/buckets/holiday/video.mp4 HTTP/1.1\nHost: objects.example\nRange: bytes=0-1048575",
          "HTTP/1.1 206 Partial Content\nContent-Range: bytes 0-1048575/10485760\nContent-Length: 1048576\n\n(1048576 bytes)", "With a range, a video player fetches only the part it is about to show.")],
    components=[["API server", "cuts uploads into chunks and puts downloads together", "none", "another API server is used"],
                ["Metadata store", "maps an object's name to its chunks", "the names, replicated", "a follower takes over, as in chapter 4"],
                ["Storage node", "keeps chunks on its disks", "chunks", "every chunk it held has 2 other copies"],
                ["Repair worker", "finds chunks with fewer than 3 good copies", "none", "repairs wait for the next run"]],
    sections=[("Chunks", """
Uploads are cut into chunks of 4 MB. Each chunk is stored separately, on 3 nodes.

| Reason to chunk | What it gives |
|---|---|
| An object can be larger than a disk | its chunks are spread over many disks |
| A failed upload can continue | only the missing chunks are sent again |
| A download can start anywhere | a byte range maps to a few chunks |
| Equal chunks have equal names | the same bytes are stored once |
"""),
              ("Checksums", """
Disks sometimes return bytes that differ from what was written, without reporting an
error. For that reason the store keeps a checksum for every chunk and verifies it on every
read. Using the checksum as the chunk's name makes the check free: a node asked for chunk
`9a3f11c2` reads the bytes, computes their checksum, and knows at once whether they are
intact.

@code objectsim/src/main.rs store :: Storing an object as chunks on 3 nodes, and reading it back with a check

@code objectsim/src/main.rs main :: A 10 MB object, a second copy of it, and a damaged chunk

@out objectsim

| Output | What it shows |
|---|---|
| 3 chunks written | 10 MB is 2 chunks of 4 MB and 1 of 2 MB. |
| the copy: 0 written, 3 already there | The same bytes have the same chunk names, so the copy takes no space. |
| 1 byte damaged, read back equal, 1 copy repaired | The damaged copy failed its check. The read used another copy and replaced the damaged one. |

Like the log of chapter 2, this simulation uses a CRC-32. Real object stores use a
cryptographic hash such as SHA-256 for chunk names, because with 25 billion chunks 2
different chunks would otherwise share a 32-bit name.
"""),
              ("Names apart from bytes", """
Listing a bucket and renaming an object should not involve the storage nodes. We keep 2 kinds of data in 2 places: small, changing records of names in a strongly
consistent metadata store, and large, unchanging chunks on the storage nodes. Uploads write the chunks first and the name last, so every name points at chunks that exist.
""")],
    failures=[["A disk returns damaged bytes", "nothing", "the checksum fails, another copy is used, and the bad copy is replaced"],
              ["A storage node is lost", "nothing", "the repair worker makes a third copy of each of its chunks on other nodes"],
              ["An upload stops half way", "the object does not appear", "its chunks have no name pointing at them and are removed later"]],
    tradeoffs=[["3 copies of every chunk", "simple, and fast to repair", "3 times the disk space; erasure coding needs about half of that"],
               ["Chunks named by checksum", "damage is detected, and equal data is stored once", "a chunk cannot be changed in place"],
               ["Names in a separate store", "listing and renaming are cheap", "2 systems to keep in step"]],
    summary=["An object store cuts objects into chunks and keeps each chunk on 3 nodes.",
             "A chunk is named by the checksum of its bytes, so damage shows up on every read.",
             "Names live in a small, strongly consistent store. Bytes live on storage nodes and do not change.",
             "An upload writes chunks first and the name last.",
             "In the run, a damaged copy was detected, the object was read correctly from another copy, and the damaged copy was replaced."]))


DESIGNS.append(dict(
    number=17, title="Video Streaming", slug="stream", program="streamsim",
    intro="""A *video streaming* service lets a creator upload 1 file and lets millions of viewers
watch it, on phones and televisions, over connections that are fast in 1 minute and slow
in the next. The video should start within a second or 2 and should not stop to load.

In this chapter, we will design the 2 halves of such a service: preparing a video after
upload, and playing it. Both rest on 1 idea, which is to cut the video into short pieces
and to offer each piece in several qualities.""",
    covers=["why a video is cut into pieces of a few seconds", "encoding 1 upload into several qualities", "the manifest: the list a player follows",
            "choosing the quality of each piece from the speed of the last download", "why the pieces are served from a CDN"],
    story="""
Imagine reading a long book to a friend over a bad phone line. Reading the whole book in 1
call is hopeless: the line drops and you start again. So you read 1 page per call. A
dropped call costs 1 page.

Now suppose you have 3 editions of every page: the full text, a shortened version, and a
1-line summary. On a good line you read the full page. When the line turns bad, you
switch to the summary for the next page, so that your friend is not left waiting. When
the line recovers, you go back to the full text.

| Page | Line quality | Edition you read | Your friend waits? |
|---|---|---|---|
| 1 | good | full | no |
| 2 | good | full | no |
| 3 | bad | full, chosen before the line turned | a little |
| 4 | bad | summary | no |
| 5 | good | summary, chosen while the line was bad | no |
| 6 | good | full | no |

A page is a piece of 4 seconds of video. The editions are the same 4 seconds at
different qualities. The choice is always 1 page behind the line, which is why pages 3 and
5 look wrong, and why a player keeps some video in reserve.
""",
    use_cases="Viewers play videos, which is almost all of the traffic. Creators upload them.",
    functional=["A creator can upload a video file of up to 10 GB.", "After processing, the video can be played on any device.",
                "Playback starts within 2 seconds.", "The quality adapts to the viewer's connection while the video plays.", "A viewer can jump to any point of the video."],
    non_functional=[["Availability", "99.95% for playback."], ["Latency", "The first piece arrives within 1 second of pressing play."],
                    ["Consistency", "Eventual. A new video may take minutes to appear, and that is acceptable."], ["Scale", "10 million viewers at the same time, and 500 hours of video uploaded per minute."]],
    consistency="""Nothing in playback needs strong consistency. A piece of video, once encoded, does not
change, so every copy of it is correct for ever. That is what makes it possible to keep
copies in thousands of places.""",
    capacity="10 million viewers at an average of 2500 kbit/s need 25000 Gbit/s, far more than 1 site can send, so pieces are served from a CDN.",
    calculation=[["Outgoing traffic", "10000000 viewers × 2500 kbit/s", "25000 Gbit/s"], ["Storage per hour of video, 4 qualities", "(400 + 1200 + 2500 + 5000) kbit/s × 3600 s", "4.1 GB"],
                 ["New storage per day", "500 hours × 60 × 24 × 4.1 GB", "2.95 PB"], ["Pieces per hour of video", "3600 ÷ 4 × 4 qualities", "3600"]],
    api_intro="The player needs 2 kinds of request: 1 for the manifest, and then 1 per piece. Pieces are plain files with stable URLs, so any HTTP cache can serve them.",
    api=[("Get the manifest of a video", "GET /v1/videos/8842/manifest HTTP/1.1\nHost: video.example",
          "HTTP/1.1 200 OK\nContent-Type: application/json\n\n{\n  \"piece_seconds\": 4,\n  \"pieces\": 450,\n  \"qualities\": [\n    { \"kbit\": 400,  \"url\": \"https://cdn.example/8842/400/piece-{n}.ts\" },\n    { \"kbit\": 1200, \"url\": \"https://cdn.example/8842/1200/piece-{n}.ts\" },\n    { \"kbit\": 2500, \"url\": \"https://cdn.example/8842/2500/piece-{n}.ts\" },\n    { \"kbit\": 5000, \"url\": \"https://cdn.example/8842/5000/piece-{n}.ts\" }\n  ]\n}",
          "The manifest tells the player which qualities exist and how to build the URL of any piece."),
         ("Get 1 piece", "GET /8842/1200/piece-17.ts HTTP/1.1\nHost: cdn.example", "HTTP/1.1 200 OK\nContent-Type: video/mp2t\nCache-Control: max-age=31536000, immutable\nContent-Length: 600000\n\n(600000 bytes)",
          "`immutable` tells every cache that this piece will not change, so it can be kept for a year.")],
    components=[["Upload service", "receives the source file and stores it", "none", "the creator's upload resumes on another instance"],
                ["Encoders", "turn the source into pieces at 4 qualities", "none", "the task is delivered again, as in chapter 11"],
                ["Object store", "keeps the source and every piece", "everything, see chapter 16", "chunks have 3 copies"],
                ["Video API", "returns the manifest", "video records", "another instance answers"],
                ["CDN", "keeps copies of pieces close to viewers", "copies only", "viewers are served from the next nearest site"]],
    walk=["A creator uploads the source file. Large uploads are sent in parts, so that a broken upload continues where it stopped.",
          "The upload service stores the source in the object store and puts 1 task on the queue.",
          "An encoder takes the task and produces the video at 4 qualities, each cut into pieces of 4 seconds.",
          "Each piece is stored as its own object. When all are stored, the video is marked ready.",
          "A viewer presses play. The player asks the video API for the manifest.",
          "The player fetches pieces from the CDN, 1 after another. A CDN site that does not have a piece fetches it from the object store once and keeps it."],
    sections=[("Pieces and qualities", """
A video file is not sent as 1 long download, for 3 reasons.

| Reason | With 1 long file | With pieces of 4 seconds |
|---|---|---|
| The viewer jumps to minute 40 | the player has to work out a byte position | it asks for piece 600 |
| The connection slows down | the quality is fixed for the whole video | the next piece can be smaller |
| A cache keeps the video | it holds all of it or none | it holds the pieces people watch |

Each piece exists in 4 qualities. All 4 show the same 4 seconds, so the player can switch
between them at any piece boundary without a visible jump.
"""),
              ("Choosing the quality", """
The player measures how fast the last piece arrived and picks the best quality that fits
into 80% of that speed. The spare 20% is a safety margin.

@code streamsim/src/main.rs choose :: Choosing the quality of the next piece

@code streamsim/src/main.rs play :: Playing 10 pieces over a connection that slows down and recovers

@out streamsim

| Piece | What it shows |
|---|---|
| 1 | The player knows nothing yet and starts with the lowest quality, so the video begins after 0.3 seconds. |
| 2 and 3 | The connection is fast, and the player moves up to 2500. |
| 4 | The speed has dropped to 1500, but the choice was made before the player knew. The piece takes 6.7 seconds, and the buffer shrinks from 8.7 to 6.0 seconds. |
| 5 to 7 | The player steps down, first to 1200 and then to 400. |
| 6 | The buffer was 6.8 seconds and the download took 6.9: the video paused for 0.1 seconds. |
| 9 | The speed has recovered and the player is back at 2500. |

The buffer is what turns a late decision into a small problem. Without several seconds of
video in reserve, piece 4 alone would have stopped playback for almost 3 seconds.
"""),
              ("Why a CDN", """
A *content delivery network* is a set of caches in many cities. A viewer in Madrid
fetches pieces from a site in Madrid.

| | From 1 central site | From a CDN |
|---|---|---|
| Distance to the viewer | up to half the planet | a few milliseconds |
| Traffic the origin carries | all of it | each piece once per CDN site |
| When the origin is unreachable | nobody can watch | pieces already cached keep playing |

Pieces suit a CDN perfectly because they do not change. Chapter 9 warned that cached
values can be stale. A piece cannot be: its URL names 1 video, 1 quality and 1 piece
number for ever.
""")],
    reading=dict(choose=["`QUALITIES` is sorted from lowest to highest.", "`rfind` searches from the end, so it returns the highest quality that passes the test.",
                         "The test keeps 20% of the measured speed in reserve.", "With no quality that fits, the player takes the lowest. A poor picture is better than a stopped one."],
                 play=["`measured` is the speed of the previous download. The first value, 1000, is a cautious guess.",
                       "`download` is the time to fetch 4 seconds of video at the chosen quality and the real speed.",
                       "While a piece downloads, the player plays from its buffer. `stalled` counts the time when the buffer was empty."]),
    mistakes=[["Offering 1 quality", "Viewers on slow connections wait, and viewers on fast ones get a poor picture.", "Encode several qualities and let the player choose."],
              ["Choosing a quality once, at the start", "A connection that slows down stops the video.", "Choose again for every piece."],
              ["Serving pieces from the origin", "The origin carries every viewer's traffic.", "Give pieces stable URLs and a long cache lifetime, and serve them from a CDN."]],
    failures=[["An encoder crashes during a video", "the video is ready later", "the task returns to the queue and another encoder takes it"],
              ["A CDN site fails", "a short pause, then playback continues", "the player's requests go to another site"],
              ["The viewer's connection slows down", "the picture gets less sharp", "the player picks a lower quality for the next piece"]],
    tradeoffs=[["Pieces of 4 seconds", "quick reaction to speed changes, cheap seeking", "many small files per video"],
               ["4 qualities", "smooth playback on most connections", "4 times the encoding work and storage"],
               ["A CDN", "short distance to viewers, low load on the origin", "cost, and a new video takes time to spread"]],
    terms=[["Piece (segment)", "a few seconds of video, stored as its own file"], ["Bitrate", "the number of bits used for each second of video"], ["Rendition", "the whole video at 1 quality"],
           ["Manifest", "the list of qualities and pieces that a player follows"], ["Adaptive bitrate", "choosing the quality of each piece from the measured speed"], ["CDN", "caches in many places, each close to some of the viewers"]],
    summary=["A video is cut into pieces of a few seconds, and each piece is encoded at several qualities.",
             "The player reads a manifest and fetches the pieces in order, choosing a quality for each from the speed of the last download.",
             "A buffer of several seconds covers the moments when the choice was wrong.",
             "Pieces do not change, so they can be cached for a long time in many places.",
             "In the run, the speed fell from 6000 to 700 kbit/s, the player stepped from 2500 down to 400, and the video paused for 0.1 seconds."]))

DESIGNS.append(dict(
    number=18, title="Chat", slug="chat", program="chatsim",
    intro="""A *chat service* delivers a message from 1 phone to another within a fraction of a
second when both are online, and holds it when the receiver is not. Phones lose their
connection all the time: in a lift, on a train, when the screen is locked.

In this chapter, we will design message delivery that survives those gaps. Every message
arrives, once, and in the order it was sent.""",
    covers=["why a phone keeps a connection open", "numbering the messages of a conversation", "catching up after being offline",
            "duplicates and gaps, and how a number handles both", "finding which server holds a member's connection"],
    story="""
A lecturer hands out numbered sheets: 1, 2, 3, 4. A student who steps out for a moment
misses some. On returning, the student does not ask "what did I miss?", which nobody can
answer. The student says "my last sheet is number 1", and receives 2, 3 and 4.

The number does 2 more jobs.

| What happens | What the student sees | What the student does |
|---|---|---|
| Sheet 4 is handed over while 2 and 3 are missing | 4 does not follow 1 | waits, and asks for everything after 1 |
| Sheet 3 is handed over a second time | 3 is not after 4 | puts it aside: already have it |

With 1 number per sheet, the student can tell a gap from a repeat and knows exactly what
to ask for. A chat conversation works the same way: the server numbers every message, and
each phone remembers the last number it has shown.
""",
    use_cases="A chat service has 1 kind of actor, the member, who sends, reads and reconnects.",
    functional=["A member can send a message to a conversation of 2 or more members.", "A member who is online receives a message within 500 ms.",
                "A member who was offline receives every missed message after reconnecting.", "Messages in a conversation are shown in the same order to every member.",
                "A message is shown once, even when it is delivered more than once."],
    non_functional=[["Durability", "A message that the sender saw as sent is not lost."], ["Consistency", "Strong within a conversation: 1 order of messages. Presence is eventual."],
                    ["Availability", "99.95% for sending and receiving."], ["Scale", "50 million members online, and 20 billion messages per day."]],
    consistency="""Order is what members notice, so each conversation has a single, strongly consistent
sequence of messages, kept the way chapter 3 keeps a log. Whether a contact is shown as
online is allowed to lag by a few seconds.""",
    capacity="50 million open connections need about 500 gateway servers, and 20 billion messages per day are 230000 per second.",
    calculation=[["Connections per gateway", "given", "100000"], ["Gateways", "50000000 ÷ 100000", "500"], ["Messages per second", "20000000000 ÷ 86400", "231000"],
                 ["Storage per day", "20 billion × 200 bytes", "4 TB"]],
    api_intro="Sending and catching up are ordinary HTTP requests. Live delivery uses a WebSocket, a connection that stays open so that the server can send without being asked.",
    api=[("Send a message", 'POST /v1/conversations/301/messages HTTP/1.1\nHost: chat.example\nIdempotency-Key: phone-a-000512\nContent-Type: application/json\n\n{ "text": "are you coming?" }',
          'HTTP/1.1 201 Created\nContent-Type: application/json\n\n{ "number": 1, "time": "2026-10-14T09:00:00Z" }', "The server chooses the number. The key lets the phone send again after a lost answer without creating a second message."),
         ("Catch up after being offline", "GET /v1/conversations/301/messages?after=1 HTTP/1.1\nHost: chat.example",
          'HTTP/1.1 200 OK\nContent-Type: application/json\n\n{\n  "messages": [\n    { "number": 2, "sender": "bob", "text": "hello?" },\n    { "number": 3, "sender": "bob", "text": "we are starting" },\n    { "number": 4, "sender": "bob", "text": "table 4" }\n  ]\n}',
          "`after=1` is the phone's cursor: the last number it has shown.")],
    components=[["Gateway", "holds the open connections of many phones", "connections, in memory", "its phones reconnect to another gateway and catch up"],
                ["Chat service", "numbers and stores messages, and forwards them", "none", "another instance takes the requests"],
                ["Message store", "keeps every conversation's messages in order", "messages, replicated", "a follower takes over, as in chapter 4"],
                ["Session store", "remembers which gateway each online member is connected to", "sessions, in memory", "phones re-register when they reconnect"]],
    walk=["The sender's phone sends the message over the connection it keeps open to gateway A.",
          "Gateway A passes the message to the chat service.",
          "The chat service asks the message store to append it. The store gives it the next number of the conversation, and the sender is told that the message is sent.",
          "The chat service looks up the receiver in the session store, finds gateway B, and forwards the message there. A receiver who is offline is skipped: the message waits in the store.",
          "Gateway B pushes the message down the receiver's open connection."],
    sections=[("An open connection", """
With ordinary HTTP, only the client can start a conversation. A phone would have to ask
"anything new?" every second, which wastes battery and still delays messages. A chat app
therefore opens 1 connection and keeps it. The server can send on it at any moment.

| | Asking every second | 1 open connection |
|---|---|---|
| Delay of a message | up to 1 second | a few milliseconds |
| Requests when nothing happens | 1 per second per phone | none |
| What the server must hold | nothing | 1 connection per online phone |

The last row is the cost: servers that hold millions of connections, the *gateways*, and
a session store that says which gateway a member is on.
"""),
              ("Numbers, gaps and repeats", """
@code chatsim/src/main.rs server :: A conversation on the server

@code chatsim/src/main.rs phone :: A phone that knows the last number it has shown

@code chatsim/src/main.rs main :: A phone that goes offline while 3 messages are sent

@out chatsim

| Output | What it shows |
|---|---|
| phone ignores 4: message 2 is missing | A message that arrives ahead of earlier ones is not shown, so the order on screen is the order on the server. |
| the phone reports that it has message 1 | After reconnecting, the phone names its position, and the server sends 2, 3 and 4. |
| phone ignores 3: already shown | A repeated message is recognised by its number. |
| 4 on the server, 4 on the phone | Every message arrived once, in order. |
"""),
              ("Groups", """
A conversation with 200 members works the same way: 1 sequence of numbers, and 1 cursor
per member. Delivery is a fan-out, as in chapter 15: the chat service looks up the
gateway of every online member and forwards the message to each. Members who are offline
catch up later from their cursor.
""")],
    reading=dict(server=["The number of a message is its position in the vector, counted from 1.", "`after(received)` skips the first `received` messages and returns the rest with their numbers."],
                 phone=["`deliver` accepts exactly 1 number: the one after the last it has shown.", "A lower number is a repeat. A higher number means a gap.", "`sync` is what a phone does on every reconnect."]),
    mistakes=[["Ordering messages by the phone's clock", "Phone clocks differ, and messages appear in the wrong order.", "Let the server number the messages of each conversation."],
              ["Sending only new messages after a reconnect", "Messages sent during the gap are lost.", "Have the phone report its last number, and send everything after it."],
              ["Showing whatever arrives", "A message delivered twice appears twice.", "Show a message only if its number follows the last one shown."]],
    failures=[["The receiver is offline", "the message arrives later", "it waits in the message store until the phone reports its cursor"],
              ["A gateway crashes", "its phones show 'connecting' for a moment", "they reconnect elsewhere and catch up from their cursors"],
              ["The answer to a send is lost", "the sender's phone sends again", "the idempotency key returns the same message number"]],
    tradeoffs=[["Open connections", "messages arrive at once", "servers hold 1 connection per online phone"],
               ["Numbers per conversation", "order, gaps and repeats are handled by 1 mechanism", "every message goes through the store that assigns numbers"],
               ["Storing every message", "offline members catch up", "storage grows with every message"]],
    terms=[["WebSocket", "a connection that stays open and lets both sides send"], ["Gateway", "a server whose job is to hold many open connections"], ["Cursor", "the number of the last message a device has received"],
           ["Presence", "whether a member is online"], ["Fan-out", "delivering 1 message to many receivers"]],
    summary=["A phone keeps 1 connection open, so that the server can deliver a message at once.",
             "The server gives every message the next number of its conversation.",
             "A phone shows a message only if its number follows the last one shown. That rule handles repeats and gaps.",
             "After being offline, a phone reports its last number and receives everything after it.",
             "In the run, 3 messages sent while the phone was offline arrived in order after it reconnected, and a repeat was ignored."]))

DESIGNS.append(dict(
    number=19, title="Payment System", slug="pay", program="paysim",
    intro="""A *payment system* moves money from a customer to a shop. It is unlike the other
systems in this book in 1 respect: its mistakes cannot be shrugged off. A charge that
happens twice, or money that leaves 1 account without arriving in another, is a real loss
to a real person.

In this chapter, we will design the core of such a system around 2 rules: a request that
is repeated has no second effect, and every movement of money is written as 2 entries
that cancel out.""",
    covers=["why a payment request must be safe to repeat", "the idempotency key", "double-entry bookkeeping: 2 entries per payment",
            "a ledger in which the total cannot change", "what to do when the outside bank is slow or silent"],
    story="""
You pay 40 at a market stall. The stallholder writes 2 lines in a book, never 1.

| Line | Account | Amount |
|---|---|---|
| 1 | customer | -40.00 |
| 2 | stall | +40.00 |
| | Total | 0.00 |

Each payment adds 2 lines that sum to 0. If the book ever fails to sum to 0, a line is
missing or wrong, and the stallholder knows it at once. That is *double entry*, and it is
several hundred years old.

Now the customer taps a card, the reader shows "error", and the customer taps again. Did
the first tap work? If each tap made a payment, the customer may have paid twice. So the
reader attaches the same receipt number to both taps, and the stallholder, seeing a
receipt number that is already in the book, writes nothing new. That is the *idempotency
key*.
""",
    use_cases="Shops charge and refund. Accountants read the ledger to check that it balances.",
    functional=["A shop can charge a customer an amount.", "A request that is sent again with the same key has no second effect and returns the first result.",
                "A shop can refund a payment, in full or in part.", "Every payment is recorded as entries in a ledger, and the entries of a payment add up to 0.",
                "An accountant can list the entries of any account."],
    non_functional=[["Consistency", "Strong. Both entries of a payment are written, or neither."], ["Durability", "A recorded payment is not lost under any single failure."],
                    ["Availability", "99.99%. When in doubt, the system refuses a payment and does not guess."], ["Scale", "1000 payments per second."]],
    consistency="""This is the chapter in which consistency wins every argument. The 2 entries of a payment
are written in 1 transaction on a strongly consistent store, and a request that cannot be
completed safely is refused. An unavailable payment system loses a sale. An inconsistent
one loses money and trust.""",
    capacity="1000 payments per second are 86 million per day and about 35 GB of ledger entries per day.",
    calculation=[["Payments per day", "1000 × 86400", "86.4 million"], ["Entries per day", "86.4 million × 2", "172.8 million"], ["Storage per day", "172.8 million × 200 bytes", "34.6 GB"]],
    api_intro="A charge is a new resource, so it is created with `POST`. `POST` is not idempotent by itself, which is exactly why this API requires a key.",
    api=[("Charge a customer", 'POST /v1/payments HTTP/1.1\nHost: pay.example\nIdempotency-Key: order-7\nContent-Type: application/json\n\n{ "from": "ada", "to": "shop", "amount": 4000, "currency": "EUR" }',
          'HTTP/1.1 201 Created\nLocation: /v1/payments/9001\nContent-Type: application/json\n\n{ "id": 9001, "state": "done", "amount": 4000, "currency": "EUR" }',
          "Amounts are whole numbers of cents. Fractions of a currency are not stored as floating-point numbers, which cannot represent 0.10 exactly."),
         ("The same request again", 'POST /v1/payments HTTP/1.1\nHost: pay.example\nIdempotency-Key: order-7\nContent-Type: application/json\n\n{ "from": "ada", "to": "shop", "amount": 4000, "currency": "EUR" }',
          'HTTP/1.1 200 OK\nContent-Type: application/json\n\n{ "id": 9001, "state": "done", "amount": 4000, "currency": "EUR" }',
          "The same payment comes back with `200`, and no money moves."),
         ("A charge without enough money", 'POST /v1/payments HTTP/1.1\nHost: pay.example\nIdempotency-Key: order-8\nContent-Type: application/json\n\n{ "from": "ada", "to": "shop", "amount": 9000, "currency": "EUR" }',
          'HTTP/1.1 422 Unprocessable Content\nContent-Type: application/problem+json\n\n{\n  "type": "/problems/insufficient-funds",\n  "title": "The account does not hold this amount",\n  "status": 422\n}',
          "`422` is the status for a request that is well formed and cannot be carried out.")],
    components=[["Payment API", "checks the key and the request", "none", "another instance answers"],
                ["Key store", "remembers the result of every key", "keys, replicated", "a follower takes over; until then payments are refused"],
                ["Ledger", "writes the 2 entries of a payment in 1 transaction", "every entry, replicated", "a follower takes over; until then payments are refused"],
                ["Card network", "moves money between banks", "outside our control", "the payment stays pending and is checked again"]],
    walk=["A shop sends `POST /v1/payments` with the key `order-7`.",
          "The API looks up `order-7` in the key store. If a result is stored, it is returned and nothing else happens.",
          "For a new key, the ledger checks the balance and writes 2 entries, minus 4000 for the customer and plus 4000 for the shop, together with the key's result, in 1 transaction.",
          "The card network is asked to move the money between the banks. Its answer can take seconds, so the payment is first *pending* and becomes *done* when the answer arrives."],
    sections=[("A ledger that cannot lose money", """
@code paysim/src/main.rs ledger :: A ledger with an idempotency key for every transfer

@code paysim/src/main.rs main :: 5 requests, 2 of them repeats

@out paysim

| Output | What it shows |
|---|---|
| order-7 twice: ada has 6000 both times | The second request found the key and moved nothing. |
| order-8: Refused | 9000 is more than the 6000 that ada holds. The refusal is stored under the key too. |
| order-9 twice: ada has 0 | Again 1 transfer for 2 requests. |
| total 10000 at the start and at the end | Money moved between accounts. None appeared or vanished. |

The stored result matters as much for a refusal as for a success. A shop that retries a
refused charge must get the same refusal, even if the customer's balance has changed in
between.
"""),
              ("When the bank does not answer", """
Our ledger is under our control. The card network is not. A request to it can time out,
and then nobody on our side knows whether the money moved.

| Wrong reaction | Why it is wrong |
|---|---|
| Tell the shop the payment failed | The money may have moved, and the customer was charged for nothing. |
| Send the request to the bank again | Without a key on the bank's side, the customer may be charged twice. |

The right reaction is to leave the payment *pending*, and to ask the bank about that
payment, by its reference, until the bank gives a definite answer. Every evening, a
*reconciliation* job compares our ledger with the bank's statement and reports any
payment that appears in 1 and not the other.
""")],
    reading=dict(ledger=["`transfers` maps a key to the outcome of its transfer. `balances` holds each account in cents, as whole numbers.",
                         "The first thing `transfer` does is look up the key. A known key returns its stored outcome.",
                         "The 2 lines that change balances are the 2 entries: the same amount leaves 1 account and enters the other.",
                         "The outcome is stored under the key in every case, refused included."],
                 main=["The requests repeat `order-7` and `order-9` to play the part of a shop that retries."]),
    mistakes=[["A charge without an idempotency key", "A retry after a lost answer charges the customer twice.", "Require a key, and store the result of every key."],
              ["Updating 1 balance, then the other", "A crash between the 2 updates destroys or creates money.", "Write both entries in 1 transaction."],
              ["Amounts as floating-point numbers", "0.10 + 0.20 is not 0.30, and cents go missing over millions of payments.", "Store amounts as whole numbers of the smallest unit."]],
    failures=[["The answer to a charge is lost", "the shop retries", "the key returns the first result"],
              ["The card network times out", "the payment shows as pending", "the system asks the network about that payment until it gets a definite answer"],
              ["The ledger's leader fails", "payments are refused for about 1 second", "a follower is elected, as in chapter 4"]],
    tradeoffs=[["Strong consistency everywhere", "money is not lost or duplicated", "payments are refused during a failover"],
               ["A key on every request", "retries are safe", "the result of every key has to be stored"],
               ["Entries, with balances computed from them", "every balance can be explained and checked", "more data than 1 number per account"]],
    terms=[["Ledger", "the list of all entries, which is the record of where money went"], ["Double entry", "writing every movement of money as 2 entries that add up to 0"],
           ["Idempotency key", "a name the caller gives a request, so that a repeat has no second effect"], ["Pending", "a payment whose outcome is not known yet"],
           ["Reconciliation", "comparing 2 records of the same payments to find differences"]],
    summary=["A payment request carries a key, and a repeated key returns the first result without moving money.",
             "Every payment is 2 ledger entries that add up to 0, written in 1 transaction.",
             "Amounts are whole numbers of cents.", "When an outside bank does not answer, the payment stays pending until its outcome is known.",
             "In the run, 5 requests made 2 transfers and 1 refusal, and the total stayed at 10000."]))

EXTRA = {}

EXTRA[7] = dict(
    story="""
Imagine a turnstile with a small tray of tokens beside it. The tray holds 10 tokens. A
machine drops 5 new tokens into the tray every second, and stops when the tray is full.
To pass, a person takes 1 token. With an empty tray, nobody passes.

| What happens | Tokens before | Passes? | Tokens after |
|---|---|---|---|
| The tray starts full | 10 | | 10 |
| 10 people arrive together | 10 | all 10 | 0 |
| An 11th person arrives in the same instant | 0 | no | 0 |
| 1 second passes, 5 tokens drop in | 0 | | 5 |
| 3 people arrive | 5 | all 3 | 2 |

2 things follow from the tray. Over a long time, at most 5 people per second get
through, because that is how fast tokens arrive. After a quiet spell, up to 10 can pass
at once, because the tray was allowed to fill. A rate limiter is this turnstile, with a
tray for every client.
""",
    walk=["A client sends `GET /v1/orders` with its credentials. The gateway reads the client id, `client-42`, from them.",
          "The gateway asks the rate limiter: may `client-42` make 1 request now?",
          "The limiter loads the bucket of `client-42` from the counter store, adds the tokens for the time since its last request, and tries to take 1. This happens as 1 operation in the store.",
          "With a token taken, the gateway forwards the request to an API server. With the bucket empty, the gateway answers `429` itself, and the API server sees nothing."],
    reading=dict(bucket=["`tokens` is a fraction. Half a second at 5 tokens per second adds 2.5 tokens, and rounding that away would cheat the client.",
                         "`allow` first works out how much time has passed and adds `elapsed * rate` tokens. `.min(self.capacity)` is the full tray: extra tokens are thrown away.",
                         "Only after the refill does it look for a token. A bucket with less than 1 token refuses.",
                         "`updated` is set on every call, allowed or refused, so the same stretch of time is not paid out twice."],
                 run=["`run` receives the number of requests for each second and spreads them evenly inside that second.",
                      "For every request it calls `allow` with a time in milliseconds and counts the ones that pass."]),
    mistakes=[["Counting requests per calendar second", "A client sends a full allowance at the end of 1 second and another at the start of the next: twice the limit in a moment.", "Use a token bucket, which has no boundaries between seconds."],
              ["Reading and writing the bucket in 2 steps", "2 limiter nodes read the same value and both allow a request.", "Refill and take in a single operation inside the store."],
              ["Refusing requests when the limiter is broken", "A fault in the protective layer takes the whole API down.", "Let requests pass, and raise an alert."]],
    terms=[["Rate limiter", "a component that refuses requests from a caller that has sent too many"], ["Token bucket", "a counting rule with a refill rate and a capacity"],
           ["Burst", "several requests sent at the same moment"], ["`429 Too Many Requests`", "the HTTP status for a request refused by a limit"],
           ["Fail open", "to let requests pass when the check itself cannot be made"]])

EXTRA[8] = dict(
    story="""
Think of 3 clerks who each hand out numbered tickets, at 3 different counters, without
talking to each other. No 2 customers may receive the same number.

A shared roll of tickets would work, and the clerks would queue for it. So each clerk
writes a ticket from 3 things they already have: the time on the wall clock, the number
of their own counter, and a tally that starts again every minute.

| Clerk | Clock | Counter | Tally this minute | Ticket |
|---|---|---|---|---|
| A | 09:15 | 1 | 0 | 0915-1-0 |
| A | 09:15 | 1 | 1 | 0915-1-1 |
| B | 09:15 | 2 | 0 | 0915-2-0 |
| A | 09:16 | 1 | 0 | 0916-1-0 |

Rows 1 and 2 share a clock and a counter and differ in the tally. Rows 1 and 3 share a
clock and a tally and differ in the counter. Every pair of tickets differs somewhere, and
no clerk asked another. The id generator does the same in 64 bits, with milliseconds for
minutes.
""",
    walk=["When an id node starts, it asks the coordinator for a node number. The coordinator gives out each number once. This is the only time a node needs anyone else.",
          "A service sends `POST /v1/ids` to any id node. The node reads its clock, takes the next counter value for that millisecond, and joins time, node number and counter into 1 number."],
    reading=dict(generator=["`NODE_BITS` and `COUNTER_BITS` fix the layout. `COUNTER_MAX` is 4095, the largest value that fits in 12 bits.",
                            "`next` handles 3 cases in order: the clock went back, the same millisecond as the last id, and a new millisecond.",
                            "In the same millisecond the counter goes up by 1. At 4095 the millisecond is full and the node answers `None`.",
                            "The last line shifts the time left by 22 bits and the node number by 12, which places the 3 parts side by side."],
                 main=["The first loop asks each of 3 nodes for 5000 ids in every millisecond, more than a node can make, on purpose.",
                       "Every id goes into a set. A duplicate would make the set smaller than the number of ids made.",
                       "The second part calls 1 node by hand to show the 3 cases of `next`."]),
    mistakes=[["Giving 2 nodes the same number", "Both make the same ids, and nothing reports it.", "Let 1 coordinator hand out numbers, and keep a number reserved while its node may return."],
              ["Trusting the clock", "After the clock is set back, a node repeats ids it has already made.", "Remember the time of the last id and refuse to go below it."],
              ["Sending ids as JSON numbers", "JavaScript rounds numbers above 2 to the power 53, and 2 ids become equal in the browser.", "Send ids as strings."]],
    terms=[["Unique id", "a value that identifies 1 record and no other"], ["Node number", "a small number that belongs to exactly 1 generator node"],
           ["Counter", "the count of ids a node has made in the current millisecond"], ["Clock step", "a correction that moves a machine's clock, possibly backwards"]])

EXTRA[9] = dict(
    story="""
A librarian keeps the 5 most requested books on the desk. Every other book is in the
basement, a 2-minute walk away.

A reader asks for a book. If it is on the desk, the answer takes a second. That is a
*hit*. If it is in the basement, the librarian fetches it and puts it on the desk for
next time. That is a *miss*. The desk is now 1 book too full, so the book that has not
been asked for the longest goes back downstairs.

| Request | On the desk before | Result | Leaves the desk |
|---|---|---|---|
| Atlas | Atlas, Bible, Cook, Dune, Emma | hit | |
| Faust | Atlas, Bible, Cook, Dune, Emma | miss, 2 minutes | Bible, unused the longest |
| Atlas | Atlas, Cook, Dune, Emma, Faust | hit | |
| Bible | Atlas, Cook, Dune, Emma, Faust | miss, 2 minutes | Cook |

Most requests are for a few popular books, so most requests are hits, although the desk
holds a tiny part of the library. A cache is the desk, the database is the basement, and
this chapter measures how large the desk has to be.
""",
    walk=["A service asks the cache library for `user-42`.", "The library hashes the key on its ring and asks the 1 cache node that owns it. That node answers with the value, or with `404`.",
          "On `404`, the service reads `user-42` from the database, which is slower.", "The service stores the value in the cache with a time limit, so that the next reader gets a hit."],
    reading=dict(lru=["`used` answers \"when was this key last used?\". `order` answers \"which key was used longest ago?\". They hold the same keys.",
                      "`get` raises the clock, records the key's new time in `used`, and removes its old time from `order`. An old time existed only if the key was cached, which is exactly what a hit means.",
                      "When there are more keys than `capacity`, `pop_first` takes the smallest time from `order`, and that key is dropped from `used`."],
                 workload=["`popular_key` multiplies 3 random fractions. The product is usually small, so low key numbers come up far more often.",
                           "`main` runs the same 1 million requests against caches of 4 sizes and counts the hits."]),
    mistakes=[["Treating the cache as the place where data lives", "A restart of the cache loses data.", "Keep the real data in the database. The cache holds copies only."],
              ["Giving every entry the same time limit", "Entries stored together expire together, and the database is hit by all of them at once.", "Shorten each limit by a small random amount."],
              ["Updating the cache when the database changes", "2 writers can update in opposite orders, and the cache keeps the older value.", "Delete the key on a write, and let the next reader fetch the new value."]],
    terms=[["Hit", "a request that the cache could answer"], ["Miss", "a request for a key that the cache does not hold"], ["Least recently used", "the rule that drops the entry that was used longest ago"],
           ["Time to live (TTL)", "how long an entry stays before it is dropped"], ["Stampede", "many requests fetching the same missing key at the same moment"]])

EXTRA[10] = dict(
    story="""
An office has 1 meeting room and a key at the front desk. Whoever holds the key may use
the room.

Ada takes the key, then is called away to a long phone call with the key in her pocket.
The front desk has a rule: a key that is not shown again within 10 minutes is cancelled,
and a new one is issued. After 10 minutes Bob gets a new key and starts his meeting.

Ada's call ends. As far as she knows, she holds the key. She walks to the room. Without
1 more rule, 2 meetings now happen in 1 room.

| Time | Front desk | Ada | Bob |
|---|---|---|---|
| 0 | issues key number 1 to Ada | holds key 1 | |
| 2 | | on the phone | |
| 12 | cancels key 1, issues key number 2 to Bob | still on the phone | holds key 2 |
| 13 | | | opens the door with key 2 |
| 17 | | tries the door with key 1 | |

The rule that saves the room is on the door: the lock remembers the highest key number it
has seen and opens for nothing lower. Key 1 no longer works. The front desk is the lock
service, the key number is the fencing token, and the door is the storage.
""",
    walk=["A worker sends `POST /v1/locks/nightly-billing`. The lock service, a group of 3 nodes that agree by majority, records the worker as holder for 10 seconds and returns token 1.",
          "The worker does its protected work and sends token 1 with every write to the storage. The storage compares the token with the highest it has accepted."],
    reading=dict(lock=["`holder` is who holds the lock and until when. `token` is the number given with the last lease.",
                       "`acquire` refuses only in 1 case: someone else holds the lock and their lease has not ended yet.",
                       "Otherwise it raises the token by 1 and records the new holder. Tokens therefore grow for ever and are not reused."],
                 storage=["`write` rejects a token below the highest one seen. An equal token is accepted, so 1 holder can write many times.",
                          "The storage knows nothing about locks, holders or time. It compares 2 numbers."],
                 main=["The program plays out the story above with the times as plain numbers.",
                       "Client A keeps its first token while it is paused, and uses it at t=17."]),
    mistakes=[["A lock without an expiry", "A holder that crashes keeps the lock for ever.", "Make every lock a lease that ends by itself."],
              ["An expiring lock without tokens", "A paused holder wakes up and writes after someone else has taken the lock.", "Issue a growing token with every lease."],
              ["Checking the token in the worker", "The worker is the part that is wrong about the lock.", "Check the token in the storage, which sees every write."]],
    terms=[["Lock", "the right to be the only one doing something"], ["Lease", "a lock that ends by itself after a fixed time"], ["Fencing token", "a number that grows with every lease and is checked by the protected resource"],
           ["Pause", "a stretch of time in which a program does not run, without knowing it"]])

EXTRA[11] = dict(
    story="""
A restaurant kitchen has a rail where the waiter clips order slips, left to right. Cooks
read the slips from the left. Nobody removes a slip: a cook puts a peg on the rail after
the last slip they have finished.

| Event | Rail, left to right | Peg after |
|---|---|---|
| The waiter clips 3 orders | soup, steak, salad | nothing yet |
| A cook makes the soup and the steak | soup, steak, salad | still nothing: the cook has not moved the peg |
| The cook faints | soup, steak, salad | nothing |
| A second cook takes over and reads from the peg | soup, steak, salad | nothing |

The second cook starts from the peg, so soup and steak are on the list again. The rail did
its job: no order was lost. The price is that 2 orders came up twice, and the second cook
needs a way to see that they are already on the pass.

The rail is a partition, a slip is a message, the position of the peg is the committed
offset, and "cook, then move the peg" is at-least-once delivery.
""",
    walk=["A producer sends a message with the key `order-7`. A hash of the key picks partition 0, and the request goes to the broker that leads it.",
          "The leader appends the message to the partition's log and copies it to a follower, as in chapter 3. Then it answers with the offset.",
          "A consumer asks the leader for messages from its committed offset onward.",
          "The consumer acts on each message. When the batch is done, it stores the new offset in the offset store."],
    reading=dict(topic=["A partition is a `Vec` of messages. The offset of a message is its index in that vector.",
                        "`produce` hashes the key and takes the remainder by the number of partitions. The same key therefore always lands in the same partition."],
                 consumer=["`committed` is the peg. `done` is the consumer's own memory of what it has acted on.",
                           "`poll` reads from `committed` to the end. `insert` returns `false` for a message that is already in `done`, and the consumer skips it.",
                           "With `commit` false, the peg does not move. That is the crash."]),
    mistakes=[["Committing before acting", "A crash between the 2 steps skips messages for good.", "Act first, then commit."],
              ["Assuming a message arrives once", "After a crash the same message is acted on twice: 2 emails, 2 charges.", "Record what was done together with its result, and skip repeats."],
              ["Expecting order across a whole topic", "Messages in different partitions arrive in any order.", "Give messages that must stay in order the same key."]],
    terms=[["Topic", "a named stream of messages"], ["Partition", "1 append-only log of a topic"], ["Offset", "the position of a message in its partition"],
           ["Consumer group", "consumers that share the messages of a topic between them"], ["At-least-once delivery", "every message is delivered, and some may be delivered again"]])

EXTRA[12] = dict(
    story="""
A library lends each book for 3 days. A borrower who needs longer renews the loan. A book
that is not back and not renewed after 3 days is treated as lost by that borrower, and
the next person on the list may have it.

| Day | Event | Who has the right to the book |
|---|---|---|
| 0 | Ann borrows the book until day 3 | Ann |
| 2 | Ann falls ill and forgets the book | Ann |
| 3 | The loan runs out | nobody |
| 4 | Ben borrows it until day 7 | Ben |
| 6 | Ben returns it, read | nobody: the book is done |

The library did not need to know why Ann went quiet. The date on the loan decided. A job
scheduler lends jobs in the same way: the job is the book, the worker is the borrower, and
the loan with its date is a lease.
""",
    walk=["A developer sends `POST /v1/jobs`. The scheduler checks the request and gives the job an id.",
          "The scheduler writes the job to the job store in the state *waiting*. The store keeps it on a majority of its nodes, as in chapter 3.",
          "A worker sends `POST /v1/leases`. The scheduler picks a waiting job, marks it *running* with this worker and a deadline, and returns it.",
          "Every few seconds the reclaimer looks for running jobs whose deadline has passed and sets them back to *waiting*."],
    reading=dict(scheduler=["`State::Running` carries the worker and the deadline. That pair is the lease.",
                            "`reclaim` is the librarian checking dates: a running job past its deadline goes back to `Waiting`.",
                            "`take` finds the first waiting job, lends it for 3 seconds and counts the attempt.",
                            "`finish` marks a job done only if the worker that reports is the worker that holds the lease."],
                 main=["Each turn of the loop is 1 second. The scheduler reclaims first, then every worker finishes and takes work.",
                       "Worker 1 skips its turn from t=2 on, which is the crash."]),
    mistakes=[["Giving a job to a worker with no deadline", "A worker that dies keeps its job for ever.", "Lend every job with a deadline, and reclaim it afterwards."],
              ["Accepting any worker's report", "A slow worker overwrites the result of the worker that replaced it.", "Accept a report only with the current lease."],
              ["Writing jobs that cannot be repeated", "A job that ran twice charges a card twice.", "Make every job safe to repeat, with a key that marks its effect as done."]],
    terms=[["Job", "a piece of work to be done outside a request"], ["Worker", "a program that takes jobs and runs them"], ["Lease", "the loan of a job to a worker until a deadline"],
           ["Reclaim", "to take back a job whose lease has run out"], ["Attempt", "1 try at running a job"]])

EXTRA[13] = dict(
    story="""
You ring a friend and get no answer. You try again a minute later, then after 2 minutes,
then after 4. Trying every second would be rude and would not help. Giving up after the
first try would be too soon. After a handful of tries you stop and leave a note.

| Try | Wait before it | Time since the first try | Result |
|---|---|---|---|
| 1 | none | 0 s | no answer |
| 2 | 1 s | 1 s | no answer |
| 3 | 2 s | 3 s | no answer |
| 4 | 4 s | 7 s | no answer |
| 5 | 8 s | 15 s | answered |

1 more thing can go wrong. Your friend picks up, the line drops, and you are not sure the
message got through, so you call again. A friend who remembers "you already told me about
the party" hears it once. That memory is the idempotency key.
""",
    walk=["A service sends `POST /v1/notifications` with the header `Idempotency-Key: order-7-shipped`.",
          "The API looks the key up. A key it has seen gets the earlier answer and nothing else happens. A new key is recorded, and the notification goes into the queue.",
          "A sender takes the notification from the queue.",
          "The sender calls the provider. On failure it waits and tries again, with a pause that doubles.",
          "After 5 failed tries the sender moves the notification to a separate list for a person to look at."],
    reading=dict(retry=["`pause_before(attempt)` is `1 << (attempt - 2)`: 1 for try 2, 2 for try 3, 4 for try 4, 8 for try 5.",
                        "`deliver` loops over the tries and adds up the pauses. `failures` says how many times the provider fails before it works.",
                        "Leaving the loop without a success returns `SetAside`."],
                 main=["`accepted` is the set of keys seen. `insert` returns `false` for a key that is already there, and that request sends nothing."]),
    mistakes=[["Calling the provider inside the request", "A slow provider makes every caller slow.", "Accept the request, queue it, and send from the queue."],
              ["Retrying at a fixed short interval", "A provider that is struggling receives even more traffic.", "Double the pause after each failure, and add a small random part."],
              ["Retrying for ever", "1 undeliverable message is tried for days and hides real problems.", "Stop after a fixed number of tries and set the message aside."]],
    terms=[["Provider", "an outside service that delivers email, text or push messages"], ["Retry", "another try after a failure"], ["Backoff", "waiting longer before each retry"],
           ["Idempotency key", "a name the caller gives a request, so that a repeat is recognised"], ["Dead letter", "a message set aside after its retries are used up"]])

EXTRA[14] = dict(
    story="""
A cloakroom gives every coat a numbered tag. The first coat gets tag 1, the next tag 2.
To get a coat back, you hand over the tag. Nobody has to search, and no 2 coats can share
a tag, because every tag is the next number.

A short link is a cloakroom tag for a long address. The only twist is the way the number
is written. With the 10 digits, a million needs 7 characters: 1000000. With 62 symbols,
the digits and both cases of the alphabet, it needs 4.

| Number | In base 10 | In base 62 |
|---|---|---|
| 61 | 61 | z |
| 62 | 62 | 10 |
| 1000000 | 1000000 | 4C92 |
| 3521614606207 | 3521614606207 | zzzzzzz |

7 characters of base 62 count up to 3.5 trillion. Shorter codes for the same number of
links is the whole reason for base 62.
""",
    walk=["A visitor's browser sends `GET /4C92`.", "The load balancer passes the request to a web server.",
          "The web server asks the cache for `4C92`. Popular links are found here.", "On a miss, it reads `4C92` from the key-value store and puts the answer in the cache.",
          "When an author creates a link, the web server takes the next number from the id generator and writes it in base 62.", "The visitor receives `301` with the long address in `Location`, and the browser goes there."],
    reading=dict(base62=["`DIGITS` lists the 62 symbols in order. The position of a symbol is its value.",
                         "`encode` takes the remainder by 62 to get the last symbol, divides by 62, and repeats. The symbols come out last first, so the result is reversed.",
                         "`decode` goes the other way: for each symbol, multiply what you have by 62 and add the symbol's value."],
                 main=["The counter method encodes the numbers 0 to 1999999. The hash method hashes each URL and keeps 6 characters.",
                       "Both sets are counted. A set that is smaller than 2 million means that 2 URLs received the same code."]),
    mistakes=[["Using part of a hash as the code", "2 addresses can receive the same code, and each new link needs a check and sometimes a second try.", "Use a counter, which gives every link its own number."],
              ["Sending every redirect to the database", "The database does 100 reads for every write.", "Put a cache in front. Links do not change, so cached links stay correct."],
              ["Counting clicks in the redirect itself", "Every redirect waits for a write.", "Record clicks to a queue and count them in the background."]],
    terms=[["Short code", "the few characters that stand for a long address"], ["Base 62", "writing numbers with 62 symbols: the digits and both cases of the alphabet"],
           ["Collision", "2 different inputs that receive the same code"], ["Redirect", "an answer that sends the browser to another address"]])

EXTRA[15] = dict(
    story="""
A school has a notice board in every classroom. When the head teacher has an announcement,
there are 2 ways to get it to the pupils.

A helper can walk to every classroom and pin a copy on each board. Pupils then read their
own board, which is quick. With 20 classrooms that is 20 copies per announcement.

Or the announcement can be pinned once, outside the head teacher's office. Pupils who want
news walk to every office they care about and read each door. No copies are made, and
every pupil walks further.

| | Copy to every board | Pin once, pupils walk |
|---|---|---|
| Work per announcement | 1 copy per classroom | 1 |
| Work per pupil who reads | 1 board | 1 walk per office |
| Good when | there are few classrooms, and many readers | there are thousands of classrooms |

Now picture a national broadcaster with 2 million classrooms to reach. Copying each
announcement 2 million times is too much. A news feed uses both methods: copies for the
ordinary senders, and 1 pinned notice for the very large ones.
""",
    walk=["An author sends `POST /v1/posts`.", "The post service stores the post once and puts a small task on the queue: \"post 90210 by ada\".",
          "A fan-out worker takes the task and looks up ada's followers.", "For each follower, the worker adds the post's id to that follower's list in the feed cache.",
          "A reader sends `GET /v1/feed`.", "The feed service reads the reader's list, merges in recent posts of any very large accounts the reader follows, and fetches the posts themselves."],
    reading=dict(accounts=["Each account has 4 numbers: followers, accounts it follows, posts per day and feed reads per day.", "`accounts` builds 1000 ordinary accounts and 1 very large one."],
                 cost=["`on_write` adds up posts times followers, for accounts at or below a follower limit. That is the number of list updates per day.",
                       "`on_read` adds up reads times the number of accounts whose posts must be fetched at read time.",
                       "`main` computes 3 cases: copy for everyone, collect for everyone, and the mixture with a limit of 10000 followers."]),
    mistakes=[["Copying every post to every follower", "1 post by a very large account means millions of writes.", "Leave posts of very large accounts where they are, and merge them in at read time."],
              ["Collecting every feed at read time", "Each read fetches from hundreds of accounts and is slow.", "Keep a ready list for each reader."],
              ["Storing whole posts in each reader's list", "The same post is stored millions of times.", "Store the post once, and keep only its id in the lists."]],
    terms=[["Feed", "the recent posts of the accounts a member follows, newest first"], ["Fan-out", "delivering 1 post to many followers"], ["Fan-out on write", "copying a post to followers when it is written"],
           ["Fan-out on read", "collecting posts when a feed is read"]])

EXTRA[16] = dict(
    story="""
You are moving house and have a bookcase that does not fit through the door. You take it
apart into shelves, label each shelf, carry the shelves through, and keep a list: shelf 1,
shelf 2, shelf 3. At the other end, the list tells you how to put the bookcase together.

An object store treats a large file the same way.

| Step | With the bookcase | With a 10 MB file |
|---|---|---|
| Cut | take it apart into shelves | cut it into chunks of 4 MB: 4 + 4 + 2 |
| Label | write a label on each shelf | name each chunk by the checksum of its bytes |
| Store | put each shelf in the van | store each chunk on 3 storage nodes |
| List | keep the list of shelves | keep the object's list of chunk names |

The labels do 1 more job. A checksum is computed from the bytes, so a chunk whose bytes
have changed no longer matches its own name. Whoever reads the chunk can tell at once
that it is damaged, and can ask another node for a good copy.
""",
    walk=["An application sends `PUT /v1/buckets/holiday/video.mp4` with the file as the body.",
          "The API server reads the body 4 MB at a time. It computes each chunk's checksum and stores the chunk on 3 storage nodes.",
          "When every chunk is stored, the API server writes 1 record to the metadata store: the object's name and its list of chunk names.",
          "In the background, the repair worker checks that every chunk still has 3 good copies, and makes a new copy where 1 is missing."],
    reading=dict(store=["A `Node` is a map from a chunk's checksum to its bytes. `objects` maps an object's name to its list of checksums.",
                        "`homes` picks 3 nodes in a row, starting from the checksum. A real store would use the hash ring of chapter 1.",
                        "`put` cuts the data with `chunks(CHUNK)`. A chunk whose checksum is already on its first node is counted as present and is not written again.",
                        "`get` looks for a copy whose bytes still match the checksum, replaces any copy that does not, and joins the chunks in order."],
                 main=["The same 10 MB are stored under 2 names. The second upload writes nothing.",
                       "`chunk[1000] ^= 0xff` flips every bit of 1 byte in 1 copy, which is what a faulty disk does."]),
    mistakes=[["Storing an object as 1 piece", "A large object does not fit on 1 disk, and a failed upload starts again from zero.", "Cut objects into chunks."],
              ["Trusting what a disk returns", "A damaged chunk is served to the user as if it were good.", "Verify the checksum on every read."],
              ["Writing the name before the chunks", "A reader can find a name whose chunks are not there yet.", "Write the chunks first and the name last."]],
    terms=[["Object", "a file of any size, stored under a name"], ["Bucket", "a named collection of objects"], ["Chunk", "a piece of an object, at most 4 MB here"],
           ["Checksum", "a short value computed from bytes, which changes when the bytes change"], ["Metadata", "data about an object: its name, its size, its list of chunks"]])

for design in DESIGNS:
    design.update(EXTRA.get(design["number"], {}))

TITLES = {7: "rate-limiter", 8: "unique-id-generator", 9: "distributed-cache", 10: "distributed-lock", 11: "message-queue",
          12: "job-scheduler", 13: "notification-service", 14: "url-shortener", 15: "news-feed", 16: "object-store"}

if __name__ == "__main__":
    for design in DESIGNS:
        # Chapter 7 is written by hand in 07.txt.
        if design["number"] == 7:
            continue

        path = HERE / ("%02d.txt" % design["number"])
        hand = HERE / "hand" / path.name
        path.write_text(by_hand(design, hand.read_text()) if hand.exists() else chapter(design))
        print(path.name, design["title"], "(by hand)" if hand.exists() else "")
