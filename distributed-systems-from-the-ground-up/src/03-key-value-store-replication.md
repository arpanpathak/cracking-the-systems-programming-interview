<img class="plate" src="art/ch03.svg?v=5d627052" alt="Ledger the tortoise sits at the first of 3 ledgers. 2 pigeons carry copies of its newest line to the other 2 ledgers. The first ledger shows lines 1 to 3 ticked, and the other 2 ledgers show the same lines.">

# Key-Value Store: Replication (Low-Level Design)

The storage node of [chapter 2](02-key-value-store-storage-node.md) keeps every
acknowledged write when its process crashes. Against the loss of the machine itself,
or of its disk, it offers nothing: a log on 1 disk is gone when that disk is gone.
Non-functional requirement 0 of [chapter 1](01-key-value-store-system-design.md)
demands that an acknowledged write survive the loss of any 1 machine, and it follows
that the record of every write has to be stored on at least 2 machines before the
client is answered.

To copy a file from 1 machine to another is easy. What makes replication a subject is
that the copying takes place over a network which loses messages, delays them and
delivers their answers late or not at all, between machines that stop and restart at
arbitrary moments, and that through all of this the copies must remain identical, in
content and in order, record for record. A follower that has missed a message must
not apply the next one as though nothing were missing. A leader that has lost an
answer must not conclude that the follower lacks the record, nor that it has it. And a
machine that was the leader an hour ago and has since been replaced must be prevented
from writing as though it still were.

This chapter implements the replication that chapter 1 specified: a leader that
orders the writes of a shard, and 2 followers that store the same records in the same
order. It turns out that a single small rule on the follower's side handles every one
of the situations listed above. We define the messages and the state of a replica,
derive the rules for followers and leaders, and implement them as a library that
performs no network operations whatever, so that a simulation can subject it to every
possible combination of lost messages. We then build `kvnode`, a storage node that
exchanges the messages over gRPC, and run 3 nodes while stopping followers, removing
the majority, and replacing a lost leader.

<div class="covers">

This chapter covers

- the `Append` message and its answer
- the state of a replica: its log, its committed sequence and its term
- what a follower does with an incoming message
- the rule by which a leader decides that a record is committed
- a simulation of 4096 combinations of lost messages
- `kvnode`: Protocol Buffers, a gRPC service, and the tasks of a leader
- the path of a write and the path of a read in a leader
- experiments with 3 nodes: a stopped follower, a lost majority, a lost leader
- replacing a leader by hand, and how terms protect against a former leader
- the limitations that remain

</div>

## Overview

Every shard has 3 replicas. All writes go to the leader, and the other 2 replicas are
followers. Figure 3.1 shows the nodes of this chapter and the route of a
write among them.

<figure>
<img src="figures/repl-nodes.svg?v=616f3843" alt="The 3 nodes of the chapter and the path of a write. Step 1: the client sends a write to the leader, node 1, over HTTP on port 7001. Step 2: the leader appends the record to its log and waits for the disk. Step 3: it sends the record to both followers, node 2 on port 7102 and node 3 on port 7103, in an Append call over gRPC. Step 4: each follower appends the record, waits for its disk and answers. Step 5: after the first answer, 2 of 3 logs hold the record. Step 6: Leader applies record and answers client.">
<figcaption><b>Figure 3.1</b> The 3 nodes and the path of a write. The steps are numbered from 1 to 6.</figcaption>
</figure>

The implementation maintains 4 invariants.

1. The log of every follower is a prefix of its leader's log: the same records in the same order, and possibly fewer of them.
2. A record is acknowledged to its client only after at least 2 of the 3 logs hold it.
3. A replica applies a record to its entries only after the record is known to be held in at least 2 of the 3 logs.
4. A replica rejects every message from a leader whose term is lower than its own.

The second invariant is non-functional requirement 0 in the form of a rule. The third
ensures that a read returns only data which would survive the loss of a machine. The
fourth prevents a former leader from modifying a shard after it has been replaced.

In this chapter the leader of a shard is chosen by an operator, who starts 1 node in
that role. Automatic election, as chapter 1 described it, is built upon the mechanism
of this chapter and is the subject of [chapter 4](04-key-value-store-leader-election.md).

## The messages

The protocol of chapter 1 defines a single call, `Append`, which a leader sends to
each of its followers.

<p class="listing"><img class="mascot" src="art/crab-happy.svg" alt=""><b>Listing 3.1</b> The replication service in the schema. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/distributed-systems-from-the-ground-up/code/proto/store.proto">proto/store.proto</a></p>

```protobuf
{{#include ../code/proto/store.proto:replication}}
```


The library uses types of its own for these messages, so that it has no dependence on
gRPC, and the conversion between the 2 representations is performed in the node.

<p class="listing"><img class="mascot" src="art/crab-happy.svg" alt=""><b>Listing 3.2</b> The imports of <code>repl/src/lib.rs</code>. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/distributed-systems-from-the-ground-up/code/repl/src/lib.rs">repl/src/lib.rs</a></p>

```rust
{{#include ../code/repl/src/lib.rs:imports}}
```

<p class="listing"><img class="mascot" src="art/crab-happy.svg" alt=""><b>Listing 3.3</b> The message and its answer, as the library uses them. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/distributed-systems-from-the-ground-up/code/repl/src/lib.rs">repl/src/lib.rs</a></p>

```rust
{{#include ../code/repl/src/lib.rs:messages}}
```


| Field | Purpose |
|---|---|
| `term` | identifies the leader's period of leadership, and a follower refuses a message whose term is lower than its own |
| `previous_sequence` | the position in the leader's log immediately before `records`, and the follower appends only if its own log ends there |
| `records` | the records the follower lacks, in order, and empty in a heartbeat |
| `committed_sequence` | the last record that the leader knows to be on a majority, up to which the follower may apply |
| `appended` | whether the follower appended the records |
| `last_sequence` | the end of the follower's log after it has processed the message, whether it appended or refused |

The last field is the one on which the whole protocol turns. A follower never merely
says yes or no. In every answer it reports where its log now ends, and this single
number is enough for a leader to correct any mistaken belief it may hold about that
follower.

## The state of a replica

A replica consists of a log, of the entries that result from applying a part of that
log, and of 3 numbers: the sequence of its last record, the point up to which records
have been applied, and its term.

<figure>
<img src="figures/repl-state.svg?v=8433bb6c" alt="The state of a replica. Its log holds records 1 to 9. Records 1 to 7 are committed: they are on a majority of the logs and are applied to the entries. Records 8 and 9 are on this log and perhaps on others, are not applied and are not visible to reads. The replica keeps 2 positions, last, the end of the log, and committed, the last record known to be on a majority.">
<figcaption><b>Figure 3.2</b> The log of a replica with 9 records, of which 7 are committed.</figcaption>
</figure>

A record is *committed* when a majority of the replicas has stored it. A committed
record survives the loss of any 1 machine, since any 2 of the 3 replicas include at
least 1 that holds it. A replica keeps uncommitted records in its log without
applying them. The entries therefore reflect committed records only, and no read can
return a value that might yet be lost.

Figure 3.3 shows where each part of this state resides and which
operation carries data from 1 part to another.

<figure>
<img src="figures/repl-replica-struct.svg?v=a00c1c22" alt="The data of a Replica. On disk is the file kv.log with every record in order, which survives a restart and is read once, at open. In memory are records, a vector that holds the whole log with record n at index n minus 1, the numbers committed and term, and entries, a sorted map. Step 1: open reads the log file into records and applies nothing. Step 2: commit(n) applies records up to n to entries. Step 3: get and list read entries, so they see committed data only.">
<figcaption><b>Figure 3.3</b> The data of a replica and the operations that connect its parts.</figcaption>
</figure>

In the code, `records` is a vector that holds record `n` at index `n - 1`, so that its
length is the sequence of its last record. `commit` proceeds from `committed` to the
sequence it is given and passes each record to `apply`, the function of chapter 2
that inserts or removes an entry. Since `commit` is the only caller of `apply`, there
is no path by which an uncommitted record can reach the entries.

<p class="listing"><img class="mascot" src="art/crab-happy.svg" alt=""><b>Listing 3.4</b> The replica, and the application of committed records. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/distributed-systems-from-the-ground-up/code/repl/src/lib.rs">repl/src/lib.rs</a></p>

```rust
{{#include ../code/repl/src/lib.rs:replica}}
```


`Replica::open` sets `committed` to 0 and leaves the entries empty, although the log
may contain records. This may seem wasteful, and it is in fact necessary. After a
restart, a replica cannot tell from its own log which of its records had reached a
majority, since its last few records may exist on its own disk and nowhere else. A
follower learns the committed sequence from its leader, and a leader learns it from
the answers of its followers.

## The follower

A follower applies the same procedure to every message it receives.

| Condition | Action | Answer |
|---|---|---|
| The term of the message is lower than the follower's own. | none | `appended = false`, with the follower's term |
| `previous_sequence` differs from the end of the follower's log. | adopt the term | `appended = false`, with the end of the follower's log |
| `previous_sequence` equals the end of the follower's log. | adopt the term, append the records with 1 wait for the disk, apply records up to `committed_sequence` | `appended = true`, with the new end of the log |

<figure>
<img src="figures/repl-follower-flow.svg?v=6485da97" alt="The decisions of handle_append. First check: is the term of the message at least the follower&#x27;s own term? If no, the follower refuses and reports its term. Second check: does the message start where the follower&#x27;s log ends, that is, does previous_sequence equal the last sequence? If no, the follower refuses and reports its last sequence. If both checks pass, the follower appends the records, applies the committed ones, and answers that it appended, with its new last sequence.">
<figcaption><b>Figure 3.4</b> The 2 checks that a follower applies to a message, in order.</figcaption>
</figure>

`handle_append` is a direct transcription of that figure. Each check that fails
returns by way of a closure named `refuse`, which builds an answer from the follower's
present term and the end of its log. When both checks pass, `append_records` writes
the whole batch with a single wait for the disk, and `commit` then applies whatever
the leader has declared committed. Since `commit` stops at the end of the log, a
committed sequence that lies beyond what this follower holds does no harm.

<p class="listing"><img class="mascot" src="art/crab-happy.svg" alt=""><b>Listing 3.5</b> The follower's handling of a message. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/distributed-systems-from-the-ground-up/code/repl/src/lib.rs">repl/src/lib.rs</a></p>

```rust
{{#include ../code/repl/src/lib.rs:follower}}
```


The second row of the table is what maintains invariant 1, and it deserves to be
looked at closely, since the whole reliability of replication derives from it. A
follower appends records only at the exact position where the leader's message
begins. Its log can therefore never acquire a gap, a duplicate or a record out of
place, whatever has happened to earlier messages. When the positions differ, the
follower attempts no repair of any kind. It reports where its log ends, and the leader
sends a message that begins there.

<figure>
<img src="figures/repl-catchup.svg?v=fa143d06" alt="How a leader and a follower agree on where to continue. The leader&#x27;s log holds records 1 to 9 and the follower&#x27;s records 1 to 7, and the leader believes that the follower&#x27;s log ends at 6. Step 1: the leader sends records 7 to 9 with previous_sequence 6. Step 2: the follower&#x27;s log ends at 7, so it refuses and answers appended false, last_sequence 7. Step 3: the leader sends records 8 and 9 with previous_sequence 7. Step 4: the follower appends them and answers appended true, last_sequence 9.">
<figcaption><b>Figure 3.5</b> A leader with an outdated view of a follower, and the exchange that corrects it.</figcaption>
</figure>

This 1 exchange covers every circumstance in which a follower is behind or the
leader's information is out of date: a follower that was stopped and has restarted, a
message that was lost, an answer that was lost, and a new follower with an empty log.
None of these cases has code of its own. They are all the same case, in which the
leader's belief about the end of the follower's log is wrong and the follower's
answer puts it right.

The records of a message are appended with `Log::append_records`, which writes all of
them and waits for the disk once.

<p class="listing"><img class="mascot" src="art/crab-happy.svg" alt=""><b>Listing 3.6</b> The imports of <code>kv/src/log.rs</code>. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/distributed-systems-from-the-ground-up/code/kv/src/log.rs">kv/src/log.rs</a></p>

```rust
{{#include ../code/kv/src/log.rs:imports}}
```

<p class="listing"><img class="mascot" src="art/crab-happy.svg" alt=""><b>Listing 3.7</b> Appending a batch of records that another node has numbered. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/distributed-systems-from-the-ground-up/code/kv/src/log.rs">kv/src/log.rs</a></p>

```rust
{{#include ../code/kv/src/log.rs:replicate}}
```


## The leader

A leader has 3 responsibilities: to accept writes, to send each follower whatever
records it lacks, and to determine which records are committed.

### Proposing a record

`propose` checks the condition of a write against the entries and appends the record
to the leader's own log. The record is not yet applied, since at this point only 1
replica holds it.

A leader accepts a new write only when `is_settled` is true, which is to say when
every record in its log is committed. The reason lies in conditional writes. A
condition is checked against the entries, and the entries do not include uncommitted
records. If the leader were to accept a second write while an earlier record was
still uncommitted, the condition of the second would be evaluated against a state
that lacked its predecessor, and a conditional write could succeed when it ought to
have failed. Requiring a settled log guarantees that every condition is evaluated
against all earlier writes. The price is that the writes of a shard are processed
strictly in sequence. Production systems evaluate conditions against a speculative
state and process writes in batches, which is considerably more intricate and is not
attempted here, although chapter 6 recovers much of the lost throughput by another
means.

Within `propose`, the present version of the key is read from the entries, a `Delete`
of a key that does not exist is rejected, and `check` evaluates the condition. Only
then is the record appended. On return, the record is in the leader's log and in
`records`, and the entries are unchanged.

<p class="listing"><img class="mascot" src="art/crab-happy.svg" alt=""><b>Listing 3.8</b> Checking the condition of a write and appending its record. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/distributed-systems-from-the-ground-up/code/repl/src/lib.rs">repl/src/lib.rs</a></p>

```rust
{{#include ../code/repl/src/lib.rs:propose}}
```


### Building a message for a follower

For every follower, the leader remembers the last sequence that the follower
reported. `append_for` takes that number and returns a message containing every later
record. For a follower that is up to date, the slice of records is empty and the
message is a heartbeat. A reported sequence that lies beyond the end of the leader's
own log is limited to that end, a situation that can arise when a leader has itself
been replaced and restarted with a shorter log.

<p class="listing"><img class="mascot" src="art/crab-happy.svg" alt=""><b>Listing 3.9</b> The message that brings 1 follower up to date. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/distributed-systems-from-the-ground-up/code/repl/src/lib.rs">repl/src/lib.rs</a></p>

```rust
{{#include ../code/repl/src/lib.rs:append_for}}
```


### The commit rule

The leader knows where its own log ends and what last sequence each follower has
reported. If these numbers are sorted, the one in the middle is the highest sequence
that a majority has stored.

<figure>
<img src="figures/repl-commit-rule.svg?v=dc5d2c21" alt="How the leader computes the committed sequence. The leader&#x27;s log ends at 10, the log of follower 1 at 7 and the log of follower 2 at 9. Sorted with the highest first, the values are 10, 9 and 7. The value in the middle is 9, so at least 2 of the 3 replicas hold every record up to 9, and the leader commits up to 9. Record 10 is on 1 log and stays uncommitted.">
<figcaption><b>Figure 3.6</b> The commit rule applied to logs that end at 10, 7 and 9.</figcaption>
</figure>

`majority_sequence` implements the rule for any number of replicas, by taking the
element at index `n / 2` of the values sorted in descending order. For 3 replicas
that is the second value, and for 5 the third.

<p class="listing"><img class="mascot" src="art/crab-happy.svg" alt=""><b>Listing 3.10</b> The commit rule. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/distributed-systems-from-the-ground-up/code/repl/src/lib.rs">repl/src/lib.rs</a></p>

```rust
{{#include ../code/repl/src/lib.rs:majority}}
```


## Simulating lost messages

Because the library performs no network operations, a test can carry the messages
between replicas itself and decide the fate of every exchange. This is the reason for
writing the rules as a library in the first place. Faults in a real network occur
rarely and unrepeatably, and a protocol that has only been tested on a real network
has scarcely been tested against faults at all.

`replsim` creates a leader and 2 followers in a single process. For each exchange it
chooses 1 of 3 outcomes: the message is delivered and answered, the message is lost,
or the message is processed and its answer is lost.

<p class="listing"><img class="mascot" src="art/crab-happy.svg" alt=""><b>Listing 3.11</b> The imports of <code>replsim/src/main.rs</code>. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/distributed-systems-from-the-ground-up/code/replsim/src/main.rs">replsim/src/main.rs</a></p>

```rust
{{#include ../code/replsim/src/main.rs:imports}}
```

<p class="listing"><img class="mascot" src="art/crab-happy.svg" alt=""><b>Listing 3.12</b> A cluster in 1 process, with control over every exchange. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/distributed-systems-from-the-ground-up/code/replsim/src/main.rs">replsim/src/main.rs</a></p>

```rust
{{#include ../code/replsim/src/main.rs:cluster}}
```


The first part of the simulation runs the cases discussed above.

<p class="listing"><img class="mascot" src="art/crab-happy.svg" alt=""><b>Listing 3.13</b> The cases of the chapter, run in order. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/distributed-systems-from-the-ground-up/code/replsim/src/main.rs">replsim/src/main.rs</a></p>

```rust
{{#include ../code/replsim/src/main.rs:cases}}
```


The second part runs 3 writes under every combination of outcomes. Each write involves
2 exchanges, and each exchange is assigned 2 bits of a pattern, which gives 4096
patterns. After each pattern, `replsim` verifies invariants 1 and 2, then delivers all
messages and verifies that the 3 logs become equal.

<p class="listing"><img class="mascot" src="art/crab-happy.svg" alt=""><b>Listing 3.14</b> Every combination of lost messages over 3 writes. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/distributed-systems-from-the-ground-up/code/replsim/src/main.rs">replsim/src/main.rs</a></p>

```rust
{{#include ../code/replsim/src/main.rs:exhaustive}}
```


<p class="listing"><img class="mascot" src="art/crab-happy.svg" alt=""><b>Listing 3.15</b> Running the simulation. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/distributed-systems-from-the-ground-up/code/replsim/src/main.rs">replsim/src/main.rs</a></p>

```rust
{{#include ../code/replsim/src/main.rs:main}}
```


```console
$ cargo run --release -p replsim
3 writes, every message delivered: logs end at [3, 3, 3], committed 3
3 writes while follower 1 is unreachable: logs end at [6, 3, 6], committed 6
follower 1 returns, 1 exchange: logs end at [6, 6, 6], committed 6
3 writes while the answers of follower 1 are lost: logs end at [9, 7, 9], committed 9
  the leader believes that the log of follower 1 ends at 6
  next exchange: the leader sends records 7 to 9, follower 1 refuses and reports 7
  the exchange after it: logs end at [9, 9, 9], committed 9
1 write while both followers are unreachable: acknowledged false, logs end at [10, 9, 9], committed 9
  the leader reads j as None
  the leader accepts another write: false
follower 2 returns: logs end at [10, 9, 10], committed 10
  the leader reads j as Some(10)
a replica at term 2 receives a message of term 1: appended false, its term 2
4096 patterns of lost messages over 3 writes:
  every acknowledged record was in at least 2 of the 3 logs
  every follower's log was the beginning of the leader's log
  after the losses stopped, the 3 logs were equal and every record was committed
  0 of 3 writes acknowledged: 1024 patterns
  1 of 3 writes acknowledged: 1024 patterns
  2 of 3 writes acknowledged: 704 patterns
  3 of 3 writes acknowledged: 1344 patterns
```

| Output | What it shows |
|---|---|
| 3 writes while follower 1 is unreachable: logs end at [6, 3, 6], committed 6 | Writes are committed with 1 follower, as invariant 2 allows. |
| follower 1 returns, 1 exchange: logs end at [6, 6, 6] | A single message brings the follower up to date, because the leader knew where its log ended. |
| answers of follower 1 are lost: the leader believes its log ends at 6 | The follower stored record 7 and the leader was not told. |
| leader sends records 7 to 9, follower 1 refuses and reports 7 | The follower detects that the message does not begin at the end of its log, and the leader continues from the position reported. |
| 1 write while both followers are unreachable: acknowledged false, committed 9 | A record in 1 log is not acknowledged and is not visible to reads. |
| leader accepts another write: false | The leader accepts no write while a record is uncommitted. |
| follower 2 returns: committed 10, leader reads j as Some(10) | The uncommitted record is committed as soon as a second replica stores it, although its client had received an error. |
| a replica at term 2 receives a message of term 1: appended false | Invariant 4 holds. |
| 4096 patterns: every acknowledged record was in at least 2 of 3 logs | Invariant 2 holds for every combination of lost messages and lost answers. |

The seventh row shows something that every client of a replicated store has to take
into account. A write that was answered with an error may nevertheless take effect
later. The record was in the leader's log, and it was committed when a follower
became reachable again. For a client, therefore, an error from a leader signifies an
unknown outcome, exactly as a lost connection does, and is to be resolved by reading
the key or by repeating an idempotent request. An error does not mean that nothing
happened.

## Design overview

<div class="lld">

Low-level design: replication

**Crates**

| Crate | Kind | Contents |
|---|---|---|
| `repl` | library | the messages, `Replica`, the follower's rule, the leader's operations, the commit rule |
| `replsim` | program | the simulation of lost messages |
| `kvnode` | program | a storage node that replicates over gRPC: `rpc` (the service), `node` (the leader's tasks, writes and reads), `main` (the HTTP API) |

**State of a node**

| Field | Type | Purpose |
|---|---|---|
| `replica` | `Mutex<Replica>` | the log, the entries, the committed sequence and the term |
| `peers` | `Vec<Peer>` | for a leader, the address of each follower, the last sequence it reported, and the time of its last answer |
| `turn` | `tokio::sync::Mutex<()>` | makes writes take turns |
| `committed` | `watch::Sender<u64>` | informs waiting writes when the committed sequence advances |
| `appended` | `Notify` | wakes the follower tasks when the leader has appended a record |
| `deposed` | `AtomicBool` | set when a follower answers with a higher term |

**Timing**

| Constant | Value | Meaning |
|---|---|---|
| `HEARTBEAT` | 100 ms | the interval between messages to a follower when there are no new records |
| `ANSWER` | 500 ms | the time the leader waits for the answer to 1 message |
| `COMMIT` | 1 s | the time a write waits for a majority, and also the period within which a majority must have answered for the leader to serve reads |

**Responses of a node**

| Situation | Status |
|---|---|
| A write or a read is sent to a follower | `421 Misdirected Request` |
| A write is sent to a leader that has learned of a higher term | `421 Misdirected Request` |
| A record does not reach a majority within 1 second | `503 Service Unavailable` |
| A read is sent to a leader that no majority has answered within 1 second | `503 Service Unavailable` |

</div>

## The node

`kvnode` combines a replica with a gRPC service for replication and the HTTP API of
chapter 1.

<p class="listing"><img class="mascot" src="art/crab-happy.svg" alt=""><b>Listing 3.16</b> The imports of <code>kvnode/src/main.rs</code>. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/distributed-systems-from-the-ground-up/code/kvnode/src/main.rs">kvnode/src/main.rs</a></p>

```rust
{{#include ../code/kvnode/src/main.rs:imports}}
```

<p class="listing"><img class="mascot" src="art/crab-happy.svg" alt=""><b>Listing 3.17</b> The options of the command line. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/distributed-systems-from-the-ground-up/code/kvnode/src/main.rs">kvnode/src/main.rs</a></p>

```rust
{{#include ../code/kvnode/src/main.rs:options}}
```


### The gRPC service

The Rust types, the client code and the server code for `Append` are generated from
the schema when the program is built. Building requires `protoc`, the compiler for
Protocol Buffers, which is available as the package `protobuf-compiler` on Debian and
Ubuntu.

<p class="listing"><img class="mascot" src="art/crab-cute.svg" alt=""><b>Listing 3.18</b> The complete <code>kvnode/build.rs</code>. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/distributed-systems-from-the-ground-up/code/kvnode/build.rs">kvnode/build.rs</a></p>

```rust
{{#include ../code/kvnode/build.rs}}
```


<p class="listing"><img class="mascot" src="art/crab-happy.svg" alt=""><b>Listing 3.19</b> The imports of <code>kvnode/src/rpc.rs</code>. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/distributed-systems-from-the-ground-up/code/kvnode/src/rpc.rs">kvnode/src/rpc.rs</a></p>

```rust
{{#include ../code/kvnode/src/rpc.rs:imports}}
```

<p class="listing"><img class="mascot" src="art/crab-happy.svg" alt=""><b>Listing 3.20</b> Including the generated code. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/distributed-systems-from-the-ground-up/code/kvnode/src/rpc.rs">kvnode/src/rpc.rs</a></p>

```rust
{{#include ../code/kvnode/src/rpc.rs:generated}}
```


The generated types are converted to the types of `kv` and `repl` at the boundary of
the service. A `Record` message that has no `change` field is rejected with the gRPC
status `InvalidArgument`.

<p class="listing"><img class="mascot" src="art/crab-happy.svg" alt=""><b>Listing 3.21</b> Conversion between the generated types and the library's types. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/distributed-systems-from-the-ground-up/code/kvnode/src/rpc.rs">kvnode/src/rpc.rs</a></p>

```rust
{{#include ../code/kvnode/src/rpc.rs:convert}}
```


Followers run the server side of the service. The handler passes each message to
`Replica::handle_append`. Since that method waits for the disk, the call is wrapped in
`block_in_place`, which informs the asynchronous runtime that the current thread is
about to block.

<p class="listing"><img class="mascot" src="art/crab-happy.svg" alt=""><b>Listing 3.22</b> The server side of <code>Append</code>. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/distributed-systems-from-the-ground-up/code/kvnode/src/rpc.rs">kvnode/src/rpc.rs</a></p>

```rust
{{#include ../code/kvnode/src/rpc.rs:service}}
```


### The leader's tasks

Figure 3.7 shows the parts of a leader and the order in which a write
passes through them. Each box corresponds to a function or a field in the listings
that follow.

<figure>
<img src="figures/repl-leader-parts.svg?v=fbddd76a" alt="The parts of a leader in kvnode. The HTTP handler, Node::write, holds the turn, which 1 write holds at any moment. Step 1: the handler calls propose on the Replica, which is behind a mutex, and the record is appended to the leader&#x27;s log. Step 2: both follower tasks are woken, and each calls append_for to learn what its follower lacks and sends it over gRPC. Step 3: an answer arrives, and the function record stores the follower&#x27;s last sequence and applies the commit rule, majority_sequence of the 3 last sequences. Step 4: the committed sequence is published on a watch channel, where the handler waits for its sequence, and the handler answers.">
<figcaption><b>Figure 3.7</b> The parts of a leader, and the path of a write between them.</figcaption>
</figure>

<p class="listing"><img class="mascot" src="art/crab-happy.svg" alt=""><b>Listing 3.23</b> The imports of <code>kvnode/src/node.rs</code>. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/distributed-systems-from-the-ground-up/code/kvnode/src/node.rs">kvnode/src/node.rs</a></p>

```rust
{{#include ../code/kvnode/src/node.rs:imports}}
```

<p class="listing"><img class="mascot" src="art/crab-happy.svg" alt=""><b>Listing 3.24</b> The state of a node. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/distributed-systems-from-the-ground-up/code/kvnode/src/node.rs">kvnode/src/node.rs</a></p>

```rust
{{#include ../code/kvnode/src/node.rs:types}}
```


A leader starts 1 task for each follower. The task repeats a single exchange: it
builds a message that begins where the follower's log is believed to end, sends it,
and processes the answer. When the follower is up to date, the task waits until the
leader appends a record or until the heartbeat interval has elapsed. When the answer
shows that records are still missing, the task continues at once.

`follow` runs for the lifetime of the node, and its loop has 3 phases. It first locks
the replica for no longer than it takes to build a message. It then releases the lock and
waits for the answer, for at most 500 ms. Finally it passes the answer to `record`. If
`record` reports that the follower is still behind, the loop continues immediately.
Otherwise the task sleeps until `appended` is signalled or the heartbeat interval
elapses, whichever occurs first.

<p class="listing"><img class="mascot" src="art/crab-happy.svg" alt=""><b>Listing 3.25</b> The task that keeps a follower up to date. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/distributed-systems-from-the-ground-up/code/kvnode/src/node.rs">kvnode/src/node.rs</a></p>

```rust
{{#include ../code/kvnode/src/node.rs:follow}}
```


A point of design here has a large effect on how the node behaves under faults. No
task holds the lock of the replica while it waits for the network. It takes the lock
to build a message and again to process an answer, and releases it in between. An
unreachable follower therefore delays its own task and nothing else, neither the task
of the other follower nor any request from a client. Had the lock been held across
the network call, a single slow follower would have stopped the whole shard, which
would have defeated the purpose of waiting only for a majority.

`record` is called with every answer. It first compares the term of the answer with
the leader's own. A higher term shows that a newer leader exists, and the node ceases
to accept writes. Otherwise it stores the sequence reported, applies the commit rule
to the 3 last sequences, and publishes the new committed sequence through a `watch`
channel, where the waiting writes observe it.

<p class="listing"><img class="mascot" src="art/crab-happy.svg" alt=""><b>Listing 3.26</b> Processing an answer, and committing. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/distributed-systems-from-the-ground-up/code/kvnode/src/node.rs">kvnode/src/node.rs</a></p>

```rust
{{#include ../code/kvnode/src/node.rs:record}}
```


### Writes

<figure>
<img src="figures/repl-write-path.svg?v=0226fb60" alt="The steps of a write in the leader. Step 1: the handler takes its turn, since writes are processed 1 after another. Step 2: it waits until every earlier record is committed. Step 3: propose checks the condition, appends the record and waits for the disk. Step 4: it wakes the 2 follower tasks, and each sends its follower what it lacks. Step 5: a follower answers, and the task records the follower&#x27;s last sequence. Step 6: the commit rule gives a new committed sequence, and the record is applied to the entries. Step 7: the handler sees its sequence committed and answers 201 or 204 with the version. Step 8: if 1 second passes without a majority, it answers 503, and the record stays In log.">
<figcaption><b>Figure 3.8</b> The steps of a write in the leader.</figcaption>
</figure>

<p class="listing"><img class="mascot" src="art/crab-happy.svg" alt=""><b>Listing 3.27</b> The write path of the leader. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/distributed-systems-from-the-ground-up/code/kvnode/src/node.rs">kvnode/src/node.rs</a></p>

```rust
{{#include ../code/kvnode/src/node.rs:write}}
```


The handlers send no messages themselves. A handler appends a record, wakes both
follower tasks, and waits for the committed sequence to reach the sequence of its
record. A `watch` channel holds the most recent committed sequence, and `wait_for`
returns as soon as that value satisfies its condition, including the case in which
it already does.

If no majority stores the record within 1 second, the handler answers `503`. The
record remains in the leader's log. The follower tasks go on sending it, and it is
committed when a follower becomes reachable, as the simulation showed.

### Reads

<p class="listing"><img class="mascot" src="art/crab-happy.svg" alt=""><b>Listing 3.28</b> The read path of the leader. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/distributed-systems-from-the-ground-up/code/kvnode/src/node.rs">kvnode/src/node.rs</a></p>

```rust
{{#include ../code/kvnode/src/node.rs:read}}
```


A leader that has been separated from its followers by a network partition cannot
know whether another leader has been appointed in the meantime, and its entries may
therefore be out of date. `must_serve_reads` accordingly requires that a majority of
the replicas, counting the leader itself, has answered within the last second. The
check limits to 1 second the time for which a former leader could return outdated
data, on the condition that no new leader is appointed sooner than that after the old
one becomes unreachable. Stricter implementations confirm their leadership with a
majority for every read, at the cost of a network round trip for each.

A second check concerns a leader that has been restarted. Its log may contain
committed records that have not yet been applied, since `committed` begins at 0. Such
a leader serves reads once every record that its log held at startup has been
committed again.

### The HTTP API

The handlers reuse the error type and the header parsing of chapter 2, from
`kvd::api`. They differ from the handlers of chapter 2 in passing writes to
`Node::write` and reads to `Node::get`.

<p class="listing"><img class="mascot" src="art/crab-happy.svg" alt=""><b>Listing 3.29</b> The handlers for <code>PUT</code>, <code>DELETE</code> and <code>GET</code>. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/distributed-systems-from-the-ground-up/code/kvnode/src/main.rs">kvnode/src/main.rs</a></p>

```rust
{{#include ../code/kvnode/src/main.rs:handlers}}
```


<p class="listing"><img class="mascot" src="art/crab-happy.svg" alt=""><b>Listing 3.30</b> Listing keys, and the health of the node. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/distributed-systems-from-the-ground-up/code/kvnode/src/main.rs">kvnode/src/main.rs</a></p>

```rust
{{#include ../code/kvnode/src/main.rs:list}}
```


<p class="listing"><img class="mascot" src="art/crab-happy.svg" alt=""><b>Listing 3.31</b> Starting a leader or a follower. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/distributed-systems-from-the-ground-up/code/kvnode/src/main.rs">kvnode/src/main.rs</a></p>

```rust
{{#include ../code/kvnode/src/main.rs:main}}
```


## Running 3 nodes

The followers are started first, each with an address for HTTP and another for
replication. The leader is then started with the replication addresses of both
followers.

```console
$ ./target/release/kvnode --role follower --listen 127.0.0.1:7002 --replication 127.0.0.1:7102 --data /var/tmp/n2 &
term 1, log ends at 0
accepting records on 127.0.0.1:7102
listening on 127.0.0.1:7002
$ ./target/release/kvnode --role follower --listen 127.0.0.1:7003 --replication 127.0.0.1:7103 --data /var/tmp/n3 &
$ ./target/release/kvnode --role leader --listen 127.0.0.1:7001 --data /var/tmp/n1 \
      --follower http://127.0.0.1:7102 --follower http://127.0.0.1:7103 &
term 1, log ends at 0
listening on 127.0.0.1:7001
```

A write to the leader is stored by all 3 nodes, and a request to a follower is refused
with the status that chapter 1 specifies for a request sent to the wrong node.

```console
$ curl -i -X PUT http://127.0.0.1:7001/v1/keys/user-1 --data-binary 'ada'
HTTP/1.1 201 Created
etag: "1"
content-length: 0

$ curl -i -X PUT http://127.0.0.1:7002/v1/keys/user-1 --data-binary 'x'
HTTP/1.1 421 Misdirected Request
content-type: application/problem+json
content-length: 117

{"type":"/problems/not-leader","title":"This node is not the leader","status":421,"detail":"this node is a follower"}
$ for port in 7001 7002 7003; do curl http://127.0.0.1:$port/healthz; echo; done
{"role":"leader","term":1,"last_sequence":1,"committed":1,"followers":[1,1]}
{"role":"follower","term":1,"last_sequence":1,"committed":1,"followers":[]}
{"role":"follower","term":1,"last_sequence":1,"committed":1,"followers":[]}
$ cmp /var/tmp/n1/kv.log /var/tmp/n2/kv.log && cmp /var/tmp/n1/kv.log /var/tmp/n3/kv.log && echo identical
identical
```

The health response of the leader lists the last sequence reported by each follower.
The 3 log files are identical byte for byte, which is invariant 1 in the strongest
form it could take.

## Experiments

All the nodes in these experiments run on 1 machine and share its disk. On separate
machines, each node has a disk of its own and the nodes do not compete for it.
Nothing else changes: each node is started with the addresses of its peers in place
of `127.0.0.1`.

### The cost of replication

```console
$ time ./target/release/kvctl load --server http://127.0.0.1:7001 --count 300 --acked acked.txt
300 writes acknowledged
3.89 s, 77 writes per second
```

The replicated shard completes 77 writes per second, against 185 for the single node
of chapter 2 on the same disk. Each write now waits for 2 disks in succession, the
leader's and then a follower's, and for a network round trip. Chapter 1 allowed for
this in its capacity estimate by counting 3 stored records for every write.

### A follower stops

A follower is killed while a load is running.

```console
$ ./target/release/kvctl load --server http://127.0.0.1:7001 --count 400 --acked acked.txt &
$ kill -9 <pid of the node on port 7002>
$ curl http://127.0.0.1:7001/healthz
{"role":"leader","term":1,"last_sequence":435,"committed":434,"followers":[417,434]}
400 writes acknowledged
$ curl http://127.0.0.1:7001/healthz
{"role":"leader","term":1,"last_sequence":700,"committed":700,"followers":[417,700]}

$ ./target/release/kvnode --role follower --listen 127.0.0.1:7002 --replication 127.0.0.1:7102 --data /var/tmp/n2 &
term 1, log ends at 417
$ curl http://127.0.0.1:7001/healthz
{"role":"leader","term":1,"last_sequence":700,"committed":700,"followers":[700,700]}
$ cmp /var/tmp/n1/kv.log /var/tmp/n2/kv.log && echo identical
identical
```

| Output | What it shows |
|---|---|
| 400 writes acknowledged | Writes continued without interruption after the follower stopped. The leader and the remaining follower form a majority. |
| `"followers":[417,700]` | The leader retains the last position that the stopped follower reported. |
| term 1, log ends at 417 | After its restart, the follower's log contains the records it had stored before it was killed. |
| `"followers":[700,700]`, identical | The follower task sent the 283 missing records, and the logs are equal again. |

Apart from restarting the process, no action by an operator was required.

### The majority is lost

Both followers are killed.

```console
$ kill -9 <pid of the node on port 7002> <pid of the node on port 7003>
$ curl -o /dev/null -w '%{http_code} in %{time_total} s\n' -X PUT http://127.0.0.1:7001/v1/keys/alone --data-binary 'x'
503 in 1.011346 s
$ curl -X PUT http://127.0.0.1:7001/v1/keys/alone2 --data-binary 'x'
{"type":"/problems/store-unavailable","title":"The node cannot serve the request","status":503,"detail":"record 701 is not on a majority of the replicas"}
$ curl http://127.0.0.1:7001/v1/keys/key-000001
{"type":"/problems/store-unavailable","title":"The node cannot serve the request","status":503,"detail":"this leader cannot reach a majority of the replicas"}
$ curl http://127.0.0.1:7001/healthz
{"role":"leader","term":1,"last_sequence":701,"committed":700,"followers":[700,700]}

$ ./target/release/kvnode --role follower --listen 127.0.0.1:7003 --replication 127.0.0.1:7103 --data /var/tmp/n3 &
$ curl http://127.0.0.1:7001/healthz
{"role":"leader","term":1,"last_sequence":701,"committed":701,"followers":[700,701]}
$ curl -o /dev/null -w '%{http_code}\n' http://127.0.0.1:7001/v1/keys/alone
200
$ curl -o /dev/null -w '%{http_code}\n' -X PUT http://127.0.0.1:7001/v1/keys/after --data-binary 'x'
201
```

| Output | What it shows |
|---|---|
| 503 in 1.01 s | The leader appended record 701, could not store it on a second replica, and reported failure after the commit timeout. |
| record 701 is not on a majority | The second write was not accepted, because record 701 was still uncommitted. |
| this leader cannot reach a majority | Reads are refused as well, since the leader can no longer confirm that it is the current leader. |
| `"last_sequence":701,"committed":700` | The record is in the leader's log and has not been applied. |
| after 1 follower returns: `"committed":701`, `GET alone` returns 200 | The record was committed without any new request from the client. |

This is exactly the behaviour that chapter 1 specified for the minority side of a
partition. The leader remains consistent and becomes unavailable, and it would be
easy, and wrong, to regard its refusal to serve as a defect. A leader that went on
answering in this condition would be answering from data that it cannot know to be
current.

### The leader is lost

In this experiment a leader is killed under load and its data directory is moved
away, which simulates the loss of a machine together with its disk.

<figure>
<img src="figures/repl-promote.svg?v=c7c6023b" alt="Replacing a lost leader by hand, in 7 steps. Step 1: the leader&#x27;s machine is lost with its disk, after 228 writes had been acknowledged. Step 2: the operator reads the health of both followers, and both logs end at 228. Step 3: the follower with the longest log is chosen, because it holds every acknowledged record. Step 4: it is restarted as leader with term 2. Step 5: the other follower receives a message of term 2, adopts the term and follows the new leader. Step 6: a new, empty node is added as a follower, and the leader sends it all 228 records. Step 7: a message of term 1 is refused from now on, so the lost leader cannot disturb the shard if it returns.">
<figcaption><b>Figure 3.9</b> The procedure for replacing a lost leader by hand.</figcaption>
</figure>

```console
$ ./target/release/kvctl load --server http://127.0.0.1:7001 --count 2000 --acked acked.txt &
$ kill -9 <pid of the leader>
write 229 failed: io: Peer disconnected
228 writes acknowledged
$ mv /var/tmp/n1 /var/tmp/n1.lost
$ for port in 7002 7003; do curl http://127.0.0.1:$port/healthz; echo; done
{"role":"follower","term":1,"last_sequence":228,"committed":227,"followers":[]}
{"role":"follower","term":1,"last_sequence":228,"committed":227,"followers":[]}

$ kill -9 <pid of the node on port 7003>
$ ./target/release/kvnode --role follower --listen 127.0.0.1:7001 --replication 127.0.0.1:7101 --data /var/tmp/n1 &
$ ./target/release/kvnode --role leader --term 2 --listen 127.0.0.1:7003 --data /var/tmp/n3 \
      --follower http://127.0.0.1:7102 --follower http://127.0.0.1:7101 &
term 2, log ends at 228
listening on 127.0.0.1:7003
$ for port in 7003 7002 7001; do curl http://127.0.0.1:$port/healthz; echo; done
{"role":"leader","term":2,"last_sequence":228,"committed":228,"followers":[228,228]}
{"role":"follower","term":2,"last_sequence":228,"committed":228,"followers":[]}
{"role":"follower","term":2,"last_sequence":228,"committed":228,"followers":[]}
$ ./target/release/kvctl verify --server http://127.0.0.1:7003 --acked acked.txt
228 acknowledged, 228 found, 0 missing
```

| Output | What it shows |
|---|---|
| 228 writes acknowledged | the client's record of acknowledged writes, kept outside the cluster |
| both followers: `"last_sequence":228,"committed":227` | Both followers hold all 228 records. They had not yet been told that record 228 was committed, because the leader stopped before its next message. |
| term 2, log ends at 228 | The promoted node starts as leader with a higher term. |
| all 3 nodes: term 2, `"committed":228` | The remaining follower adopted the new term, and the empty replacement node received the complete log. |
| 228 acknowledged, 228 found, 0 missing | Non-functional requirement 0 is met: every acknowledged write survived the loss of the leader and its disk. |

The second row illustrates why the committed sequence is not stored on disk. What a
follower knows to be committed always lags behind its leader, and after a leader has
been lost, the committed sequence is established afresh from the logs: a new leader
commits a record as soon as a majority has reported it.

For the promotion, the follower with the longer log must be chosen. By invariant 2,
every acknowledged record is on at least 1 of the 2 followers, though not necessarily
on both. If their logs differ in length, the longer contains every acknowledged
record, and the shorter may lack some of the most recent. To promote the shorter
would be to discard acknowledged writes, and this choice, made here by a person
reading 2 numbers, is the one that chapter 4 has to teach the nodes to make for
themselves.

### The former leader returns

Suppose that a former leader was not lost after all and begins to send messages
again, as it might when a network partition ends. A leader with term 1 is started
against the 2 followers.

```console
$ ./target/release/kvnode --role leader --term 1 --listen 127.0.0.1:7009 --data /var/tmp/n9 \
      --follower http://127.0.0.1:7102 --follower http://127.0.0.1:7101 &
$ curl -i -X PUT http://127.0.0.1:7009/v1/keys/stale --data-binary 'x'
HTTP/1.1 421 Misdirected Request
content-type: application/problem+json
content-length: 125

{"type":"/problems/not-leader","title":"This node is not the leader","status":421,"detail":"a leader of a newer term exists"}
$ curl http://127.0.0.1:7002/healthz
{"role":"follower","term":2,"last_sequence":228,"committed":228,"followers":[]}
$ curl -o /dev/null -w '%{http_code}\n' -X PUT http://127.0.0.1:7003/v1/keys/fresh --data-binary 'x'
201
```

Both followers are at term 2 and refuse messages of term 1. Each of their answers
carries the higher term, so that the old leader records that it has been replaced and
rejects writes with `421`. The shard meanwhile continues to accept writes through its
leader of term 2. Terms are what make a change of leader safe, since a leader that
has been replaced cannot add a record to any follower.

## Limitations

| Limitation | Consequence |
|---|---|
| The leader is appointed by an operator. | After the loss of a leader, the shard is unavailable for writes until a person or a script promotes a follower. |
| A former leader must not rejoin with its old log. | Its log may contain records that were appended and never committed, at positions where the new leader has written different records. The implementation compares positions only, so a former leader has to rejoin with an empty data directory. |
| Writes are processed 1 after another. | The write rate of a shard is limited to 1 write for each round trip. Group commit, which the capacity estimate of chapter 1 assumed, is not implemented. |
| Every replica holds all its records in memory. | The memory used by a node grows with the length of its log. |
| A leader serves reads for up to 1 second after losing its majority. | Non-functional requirement 2, consistency, depends on no new leader being appointed within that second. |

The first 2 limitations are removed in chapter 4, and the third in chapter 6.

## The complete programs

The log and the store are listed in chapter 2. Those listings include
`Log::append_records` as well as `apply`, `check` and `page`, which this chapter uses.

<p class="listing"><img class="mascot" src="art/crab-cute.svg" alt=""><b>Listing 3.32</b> The complete <code>repl/src/lib.rs</code>. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/distributed-systems-from-the-ground-up/code/repl/src/lib.rs">repl/src/lib.rs</a></p>

```rust
{{#include ../code/repl/src/lib.rs}}
```


<p class="listing"><img class="mascot" src="art/crab-cute.svg" alt=""><b>Listing 3.33</b> The complete <code>replsim/src/main.rs</code>. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/distributed-systems-from-the-ground-up/code/replsim/src/main.rs">replsim/src/main.rs</a></p>

```rust
{{#include ../code/replsim/src/main.rs}}
```


<p class="listing"><img class="mascot" src="art/crab-cute.svg" alt=""><b>Listing 3.34</b> The complete <code>kvnode/Cargo.toml</code>. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/distributed-systems-from-the-ground-up/code/kvnode/Cargo.toml">kvnode/Cargo.toml</a></p>

```toml
{{#include ../code/kvnode/Cargo.toml}}
```


<p class="listing"><img class="mascot" src="art/crab-cute.svg" alt=""><b>Listing 3.35</b> The complete <code>kvnode/src/rpc.rs</code>. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/distributed-systems-from-the-ground-up/code/kvnode/src/rpc.rs">kvnode/src/rpc.rs</a></p>

```rust
{{#include ../code/kvnode/src/rpc.rs}}
```


<p class="listing"><img class="mascot" src="art/crab-cute.svg" alt=""><b>Listing 3.36</b> The complete <code>kvnode/src/node.rs</code>. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/distributed-systems-from-the-ground-up/code/kvnode/src/node.rs">kvnode/src/node.rs</a></p>

```rust
{{#include ../code/kvnode/src/node.rs}}
```


<p class="listing"><img class="mascot" src="art/crab-cute.svg" alt=""><b>Listing 3.37</b> The complete <code>kvnode/src/main.rs</code>. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/distributed-systems-from-the-ground-up/code/kvnode/src/main.rs">kvnode/src/main.rs</a></p>

```rust
{{#include ../code/kvnode/src/main.rs}}
```


<div class="summary">

## Summary

- The leader of a shard sends each follower the records it lacks, in an `Append` message that states the position at which those records begin.
- A follower appends only if its log ends at that position, and otherwise reports where its log ends, upon which the leader continues from there. This 1 rule deals with restarted followers, lost messages, lost answers and empty followers.
- A record is committed when a majority of the replicas has stored it, and the leader computes the committed sequence as the middle value of the sorted last sequences.
- A replica applies committed records only, so that no read returns data which could be lost with 1 machine.
- A write that was answered with an error may still be committed later, and a client has to treat an error as an unknown outcome.
- For 4096 combinations of lost messages and answers, the simulation verified that every acknowledged record was held in at least 2 of the 3 logs.
- With 3 nodes on 1 disk, the replicated shard completed 77 writes per second, against 185 for a single node.
- After the loss of a leader and its disk, promoting the follower with the longer log preserved all 228 acknowledged writes.
- A term identifies the current leader, and followers refuse messages with a lower term, so that a replaced leader cannot modify its shard.

</div>
