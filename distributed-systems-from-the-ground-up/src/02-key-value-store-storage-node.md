<img class="plate" src="art/ch02.svg?v=ce3188d3" alt="Ledger, a tortoise, writes each change in a long ledger before saying yes. Lightning strikes beside it and a crab jumps in shock, and the ledger still holds every line that was written: put user-1, put user-2, delete user-2.">

# Key-Value Store: Storage Node (Low-Level Design)

The design of [chapter 1](01-key-value-store-system-design.md) distributes a key-value
store over 24 machines, keeps every key on 3 of them, and reasons at length about what
happens when machines fail. All of that reasoning rests on a single assumption about
each individual machine, which chapter 1 stated in its closing section and did not
justify: that a write which a node has acknowledged will still be there after the node
has crashed and been restarted. If 1 node can quietly lose a write it has confirmed,
then a write "stored on 2 of 3 nodes" may be stored on 1, and nothing built on top of
that count can be trusted.

This chapter builds the component that makes the assumption true. A *storage node* is
the program that holds the entries of the store on 1 machine, and its whole difficulty
is concentrated in the few milliseconds during which a write is in progress and the
machine may lose power. We begin by examining what a crash can do to a write at each
stage, which leads to the technique of writing every change to a log before doing
anything else. We then define the format of the log on disk, write the code that
recovers from a damaged log, and build on top of it the store and the HTTP API of
chapter 1. The chapter ends by trying, in 3 different ways, to make the node lose
data: by damaging its log at every possible byte, by killing it under load, and by
killing it under load from another machine.

<div class="covers">

This chapter covers

- what a crash does to a write at each stage
- write-ahead logging, and why the log is written before memory is changed
- a format for records, with a length and a checksum
- recovery: reading a log, and cutting off a damaged end
- the system calls `write` and `fsync`, and what each of them costs
- what to do when the disk reports an error
- a store with entries, versions and conditional writes
- an HTTP server that provides the API of chapter 1
- a simulation that damages a log at every byte
- a test that kills the server under load, on 1 machine and on 2

</div>

## Storing data durably

A storage node keeps its entries in memory, so that a read requires no access to the
disk. Memory is lost when the process stops, and so the node must keep the data on
disk as well, in a form from which the contents of memory can be reconstructed.

The first design that comes to mind keeps a file which mirrors the contents of memory
and, on every write, overwrites the affected part of that file. In the presence of
crashes this is unsafe, and the reason is worth seeing concretely. Suppose that a
value of 1 KB is being replaced by another of the same size, and that the power fails
when half of the new bytes have reached the disk. The file now contains the first
half of the new value followed by the second half of the old. The entry is corrupt,
its former value can no longer be recovered, and, worst of all, nothing in the file
indicates that anything is wrong.

The fault in this design is that an update in place destroys the old state before the
new state is complete, so that there is a moment at which neither exists. The standard
remedy is to give up updating in place altogether. The node appends a description of
each change to the end of a file and modifies the file in no other way. A file used in
this manner is called a *log*. Because every change is entered in the log before it is
applied to any other structure, the technique is known as *write-ahead logging*, and
the file as a *write-ahead log*.

With a file that is only ever appended to, a crash during a write can affect nothing
but the record that was being appended. All the earlier records are intact, since
nothing ever writes to that part of the file again.

<figure>
<img src="figures/node-inside.svg?v=fc67b1c5" alt="The inside of a storage node. The HTTP handler reads the key, the headers and the body, and calls the store, which checks the condition on the version. A write goes first to the log on disk, which holds every change in order and survives a crash, and second to the map in memory, which goes from key to entry, is sorted by key, and is rebuilt at start. A read uses map only.">
<figcaption><b>Figure 2.1</b> The components of a storage node, and the order of the steps of a write.</figcaption>
</figure>

The node maintains 4 *invariants*, conditions that hold at every moment, whatever
requests arrive and wherever a crash occurs.

1. Every change is in the log, and confirmed by the disk, before its client receives a response.
2. Every change is in the log before it is applied to the map in memory.
3. The map is equal to the result of applying all the records of the log in order.
4. The log is modified only by appending. The bytes of a confirmed record are never written again.

Each invariant purchases something specific. The first is durability itself. The
second and third together ensure that the map contains nothing that is absent from the
log, so that the loss of the map loses no data. And the fourth confines the damage
that a crash can do to the end of the file, where recovery knows to look for it.

## Crashes during a write

Given this ordering of steps, the outcome of a crash can be worked out for each stage
of a write.

<figure>
<img src="figures/crash-points.svg?v=254c7a72" alt="The 4 moments at which a node can crash during a write. Before the record is written: nothing is on disk, the client gets no answer, and after restart the write did not happen. In the middle of the record: part of a record is on disk, the client gets no answer, and after restart the part is cut off. After fsync but before the answer: the whole record is on disk, the client gets no answer, and after restart the write happened. After the answer: the whole Record is on disk, client got 201 or 204, and write happened.">
<figcaption><b>Figure 2.2</b> The 4 stages at which a crash can occur, and the state that is found after a restart.</figcaption>
</figure>

The third case requires comment. The record has been stored durably, and the node
crashes before it has sent its response. After the restart the write is present,
although its client was never told that it had succeeded. This does not violate the
guarantee of durability, which covers acknowledged writes and is silent about writes
whose outcome was never reported. From the client's point of view the outcome of such
a write is unknown, which is the lost response that chapter 1 discussed under
retries. The client resolves the uncertainty by sending the request again, and can do
so safely because `PUT` is idempotent. This case is produced deliberately, by a test,
in the section on killing the server.

## The format of a record

When a log is read back, the reader has to determine where each record ends, since
records differ in length. It must also be able to recognise a record that is
incomplete or damaged, since the end of the file may contain the partial output of a
write that a crash interrupted.

Both needs are met by beginning every record with a *frame* of 8 bytes, which holds
the length of the data that follows and a checksum of it. The checksum is a *CRC-32*,
a value of 32 bits computed from the data in such a way that any change to the data
will almost certainly change the value. When a record is read, the checksum is
computed afresh and compared with the one that was stored.

<figure>
<img src="figures/record-layout.svg?v=c4fa56a5" alt="The 28 bytes of the first record of the log. The frame is 8 bytes: the length, 14 00 00 00, which says that the payload is 20 bytes, and the checksum, 8d d3 da 1d, the CRC-32 of those 20 bytes. The payload is the sequence 1 as 8 bytes, the kind 01 for a put, the key length 6 as 2 bytes, the 6 bytes of the key user-1, and the value ada as the Rest of payload.">
<figcaption><b>Figure 2.3</b> The layout of the first record of a log.</figcaption>
</figure>

The following are the first bytes of a log after the 2 writes to `user-1` shown in
chapter 1.

```console
$ xxd data/kv.log | head -4
00000000: 1400 0000 8dd3 da1d 0100 0000 0000 0000  ................
00000010: 0106 0075 7365 722d 3161 6461 1d00 0000  ...user-1ada....
00000020: cefd 7d53 0200 0000 0000 0000 0106 0075  ..}S...........u
00000030: 7365 722d 3161 6461 206c 6f76 656c 6163  ser-1ada lovelac
```

The first 4 bytes, `1400 0000`, encode the length 20 in *little-endian* order, in
which the least significant byte of a number comes first. The 4 bytes of the checksum
follow. Within the payload, the sequence number 1 occupies the first 8 bytes, and is
followed by the kind, `01`, and the length of the key, `0600`. The key and the value
can be read in the right-hand column. At byte 28, which is `0x1c`, the second record
begins with the length `1d00 0000`, or 29.

<p class="listing"><img class="mascot" src="art/crab-happy.svg" alt=""><b>Listing 2.1</b> The imports of <code>kv/src/record.rs</code>. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/distributed-systems-from-the-ground-up/code/kv/src/record.rs">kv/src/record.rs</a></p>

```rust
{{#include ../code/kv/src/record.rs:imports}}
```

<p class="listing"><img class="mascot" src="art/crab-happy.svg" alt=""><b>Listing 2.2</b> The types for a change, a record, and the result of decoding. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/distributed-systems-from-the-ground-up/code/kv/src/record.rs">kv/src/record.rs</a></p>

```rust
{{#include ../code/kv/src/record.rs:types}}
```


`Decoded` has 3 variants because a reader must tell 3 situations apart: a complete
record, data that ends before the record is complete, and data that is complete and
invalid. The distinction between the last 2 is of no consequence to recovery, which
treats them alike, and is valuable when a log is being examined after a fault, since
the one indicates an interrupted write and the other a damaged disk.

<p class="listing"><img class="mascot" src="art/crab-happy.svg" alt=""><b>Listing 2.3</b> Encoding a record. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/distributed-systems-from-the-ground-up/code/kv/src/record.rs">kv/src/record.rs</a></p>

```rust
{{#include ../code/kv/src/record.rs:encode}}
```


Decoding carries out the same steps in order and returns the variant that corresponds
to the first step that fails.

<p class="listing"><img class="mascot" src="art/crab-happy.svg" alt=""><b>Listing 2.4</b> Decoding a record. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/distributed-systems-from-the-ground-up/code/kv/src/record.rs">kv/src/record.rs</a></p>

```rust
{{#include ../code/kv/src/record.rs:decode}}
```


`split_first_chunk` returns the first bytes of a slice as an array of fixed size,
together with the remainder, or `None` if the slice is too short. Every field is
extracted by this means. A payload shorter than its fields therefore yields `None`,
and at no point does the code use a value read from the disk as an index without
first having validated it. A decoder of data from disk must be written on the
assumption that the data may be anything at all, since after a fault it may be.

## What a durable write costs

Invariant 1 requires that the disk has confirmed every record. Writing to a file does
not, by itself, satisfy this requirement, and the difference between the 2 is the most
consequential fact about storage that a programmer has to know.

The system call `write` copies data into a buffer belonging to the kernel and
returns. At some later time, the kernel transfers the buffer to the disk. With the
call `fsync`, a program instructs the kernel to transfer all the buffered data of a
file at once, and the call does not return until the disk has reported success. In
Rust, `File::sync_data` makes this call.

<figure>
<img src="figures/survives.svg?v=66f2d30b" alt="What survives 2 kinds of failure. When the process is killed, the map in the process is lost, bytes given to write are kept, and bytes after fsync are kept. When the power fails, the map is lost, bytes given to write are lost, and bytes after fsync are kept. After write the bytes are in the kernel&#x27;s memory, and the kernel outlives the process, So only a power failure shows difference.">
<figcaption><b>Figure 2.4</b> The data that is lost in each kind of failure.</figcaption>
</figure>

The program `synccost` appends 500 records to a log, first without `fsync` and then
with an `fsync` after every record.

<p class="listing"><img class="mascot" src="art/crab-happy.svg" alt=""><b>Listing 2.5</b> The imports of <code>synccost/src/main.rs</code>. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/distributed-systems-from-the-ground-up/code/synccost/src/main.rs">synccost/src/main.rs</a></p>

```rust
{{#include ../code/synccost/src/main.rs:imports}}
```

<p class="listing"><img class="mascot" src="art/crab-happy.svg" alt=""><b>Listing 2.6</b> Measuring the cost of an append with and without <code>fsync</code>. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/distributed-systems-from-the-ground-up/code/synccost/src/main.rs">synccost/src/main.rs</a></p>

```rust
{{#include ../code/synccost/src/main.rs:measure}}
```


```console
$ cargo run --release -p synccost -- /var/tmp/synccost
without fsync: 500 records in      1.4 ms, 0.003 ms per record, 366991 records per second
with fsync   : 500 records in   2697.5 ms, 5.395 ms per record,    185 records per second
```

<figure>
<img src="figures/sync-cost.svg?v=0bf92cb7" alt="The cost of fsync on an NVMe disk. Appending 1 record takes 0.003 ms with write only and 5.395 ms with write followed by fsync. That is 366991 records per second against 185. write copies the bytes into the kernel&#x27;s memory and returns, and fsync waits until the disk reports that the bytes are stored.">
<figcaption><b>Figure 2.5</b> The 2 measurements, drawn to scale.</figcaption>
</figure>

On an NVMe disk, a durable append took 5.4 ms, about 1900 times as long as an append
that merely copies data into the kernel's buffer. This is the figure from which
chapter 1 derived its 185 records per second. Because the cost is so high, storage
systems commonly make the behaviour configurable, and `kvd` has an option `--no-sync`
under which the node responds after `write` alone. In that mode the node keeps every
acknowledged write if its process crashes, and may lose the most recent writes if the
machine loses power. Whether that is an acceptable bargain depends on the data, and it
is a decision that ought to be made knowingly, since the default behaviour of a great
many programs makes it silently.

## Design overview

<div class="lld">

Low-level design: the storage node

**Crates**

| Crate | Kind | Contents |
|---|---|---|
| `kv` | library | `record` (the format of a record), `log` (the log file), `store` (the map and the conditions on writes) |
| `kvd` | library and program | `api` (errors and conditional headers, shared with later chapters) and the HTTP server |
| `kvctl` | program | a client that generates load and verifies acknowledged writes |
| `crashsim` | program | a simulation that damages a log at every position |
| `synccost` | program | the measurement of `fsync` |

**Types**

| Type | Fields | Purpose |
|---|---|---|
| `Change` | `Put { key, value }` or `Delete { key }` | the modification that a write requests |
| `Record` | `sequence`, `change` | a change and its position in the log |
| `Log` | `file`, `sync`, `next`, `failed` | appends records and reads them back |
| `Entry` | `value`, `version` | the current state of a key |
| `Condition` | `Always`, `Absent`, `Version(n)` | the state of the key that a write requires |
| `Store` | `entries: BTreeMap<String, Entry>`, `log` | applies changes and answers reads |

**Operations**

| Operation | Steps | Cost |
|---|---|---|
| `Store::put` | check the condition, `Log::append`, apply to the map | 1 `fsync` |
| `Store::delete` | check that the key exists, check the condition, `Log::append`, apply | 1 `fsync` |
| `Store::get` | look the key up in the map | O(log n), with no access to the disk |
| `Store::list` | iterate over the map from a starting key | O(log n + size of the page), with no access to the disk |
| `Store::open` | `Log::open`, then apply every record | proportional to the size of the log |

**Failure policy**

| Event | Response |
|---|---|
| The log ends with an incomplete or damaged record | The file is cut off after the last valid record. |
| A write to the log fails | The node returns `503` and rejects every later write until it is restarted. |

</div>

The manifest of the workspace declares the edition of Rust, the minimum version of
the compiler, and the dependencies that its crates share.

<p class="listing"><img class="mascot" src="art/crab-cute.svg" alt=""><b>Listing 2.7</b> The complete <code>Cargo.toml</code>. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/distributed-systems-from-the-ground-up/code/Cargo.toml">Cargo.toml</a></p>

```toml
{{#include ../code/Cargo.toml}}
```


| Dependency | Purpose |
|---|---|
| `axum`, `tokio` | the HTTP server and the asynchronous runtime |
| `clap` | parsing the options of the command line |
| `crc32fast` | the checksum of a record |
| `parking_lot` | a mutex whose `lock` method returns the guard directly |
| `serde` | JSON encoding of the list response and of error bodies |
| `thiserror` | deriving `Display` and `From` for the store's error type |
| `ureq` | the HTTP client used by `kvctl` |
| `xxhash-rust` | the hash function of the ring described in chapter 1 |

## The log

`Log` owns the log file. It offers 2 operations: opening, which includes recovery, and
appending a record.

<p class="listing"><img class="mascot" src="art/crab-happy.svg" alt=""><b>Listing 2.8</b> The imports of <code>kv/src/log.rs</code>. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/distributed-systems-from-the-ground-up/code/kv/src/log.rs">kv/src/log.rs</a></p>

```rust
{{#include ../code/kv/src/log.rs:imports}}
```

<p class="listing"><img class="mascot" src="art/crab-happy.svg" alt=""><b>Listing 2.9</b> The log, and the result of opening it. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/distributed-systems-from-the-ground-up/code/kv/src/log.rs">kv/src/log.rs</a></p>

```rust
{{#include ../code/kv/src/log.rs:types}}
```


### Recovery

Opening a log reads the entire file and decodes records from the beginning until one
fails to decode. Since `Record::decode` already distinguishes every possible outcome,
the loop is short. Recovery treats an incomplete record and a corrupt one alike: in
either case the record before it becomes the last record of the log.

<p class="listing"><img class="mascot" src="art/crab-happy.svg" alt=""><b>Listing 2.10</b> Decoding records until one is incomplete or corrupt. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/distributed-systems-from-the-ground-up/code/kv/src/log.rs">kv/src/log.rs</a></p>

```rust
{{#include ../code/kv/src/log.rs:scan}}
```


<figure>
<img src="figures/recovery-scan.svg?v=debdc2db" alt="Recovery of a log of 63 bytes after a crash. Record 1 occupies bytes 0 to 27 and record 2 bytes 28 to 57, and 5 bytes of a third record follow. The scan reads a frame at 0 that says 20 bytes and whose checksum matches: record 1. At 28 the frame says 22 bytes and the checksum matches: record 2. At 58 only 5 bytes are left and a frame needs 8, so the record is incomplete and the scan stops. The file is cut to 58 bytes, and the next record will have sequence 3.">
<figcaption><b>Figure 2.6</b> The recovery of a log that was cut off in the middle of its third record.</figcaption>
</figure>

<p class="listing"><img class="mascot" src="art/crab-happy.svg" alt=""><b>Listing 2.11</b> Opening the log and cutting off a damaged end. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/distributed-systems-from-the-ground-up/code/kv/src/log.rs">kv/src/log.rs</a></p>

```rust
{{#include ../code/kv/src/log.rs:open}}
```


The call to `set_len` removes the damaged end of the file before any new record is
appended, and the correctness of the whole log depends on this step. If the damaged
bytes were left where they are, the next record would be written after them, a later
recovery would stop at the damage, and the new record would be lost although the node
had acknowledged it. A recovery procedure that reads correctly and fails to repair
has merely postponed the loss.

Both calls to `sync_all` are necessary, one to make the new length of the file
durable and the other for its directory. Synchronising a file makes its contents
durable, but the existence of the file is recorded in the directory that contains it,
and that is a separate object. A newly created file whose directory has not been
synchronised may be absent after a power failure, contents and all. The log therefore
synchronises its directory when it is opened.

### Appending

<p class="listing"><img class="mascot" src="art/crab-happy.svg" alt=""><b>Listing 2.12</b> Appending a record. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/distributed-systems-from-the-ground-up/code/kv/src/log.rs">kv/src/log.rs</a></p>

```rust
{{#include ../code/kv/src/log.rs:append}}
```


The field `failed` implements a policy known as *fail-stop*, under which a component
that meets an error it cannot handle safely ceases to operate. If `write_all` or
`sync_data` returns an error, the state of the file is unknown: the record may be
absent, partly written, or complete. A log that went on accepting records could append
a valid record after a damaged one, where recovery would never reach it.

It might be thought that the node could call `fsync` again. This is unsafe as
well, and for a reason that has surprised the authors of several well-known
databases. After a failed `fsync`, the kernel may already have discarded the data it
was unable to write, and a second call may then report success although nothing has
reached the disk. A success after a failure therefore proves nothing. The log
accordingly rejects all further appends. From that moment its node answers `503` to
writes, continues to serve reads from memory, and has to be restarted or replaced by
an operator. In the design of chapter 1, the followers of all the affected shards
elect new leaders at this point, and the fault of 1 disk is absorbed by the cluster.

## The store

`Store` contains the map and the log, and every modification of either passes through
it.

<p class="listing"><img class="mascot" src="art/crab-happy.svg" alt=""><b>Listing 2.13</b> The imports of <code>kv/src/store.rs</code>. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/distributed-systems-from-the-ground-up/code/kv/src/store.rs">kv/src/store.rs</a></p>

```rust
{{#include ../code/kv/src/store.rs:imports}}
```

<p class="listing"><img class="mascot" src="art/crab-happy.svg" alt=""><b>Listing 2.14</b> Opening the store by applying the records of the log. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/distributed-systems-from-the-ground-up/code/kv/src/store.rs">kv/src/store.rs</a></p>

```rust
{{#include ../code/kv/src/store.rs:open}}
```


Recovery and the path of a write share a single function, `apply`, for modifying the
map. Invariant 3 is a consequence of this arrangement. What a record does to the map
is defined in exactly 1 place, which is used both when a record is first written and
whenever a log is read back, so that the 2 cannot come to differ.

<p class="listing"><img class="mascot" src="art/crab-happy.svg" alt=""><b>Listing 2.15</b> Conditional writes: check, append, apply. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/distributed-systems-from-the-ground-up/code/kv/src/store.rs">kv/src/store.rs</a></p>

```rust
{{#include ../code/kv/src/store.rs:write}}
```


`put` and `delete` perform the same 3 steps in the same order. The condition is
evaluated first, against the map, so that a write which is refused produces no
record. `append` then returns when the record is durable, or returns an error, in
which case the `?` operator leaves the function before `apply` is reached. The map is
modified last. The order of these steps is the order of the invariants, and the code
has been arranged so that it cannot be otherwise.

<div class="crab crab-happy">

The version of an entry is the sequence number of its record. The store keeps no separate counter of versions that could come to disagree with the log after a crash.

</div>

Reads use the map alone.

<p class="listing"><img class="mascot" src="art/crab-happy.svg" alt=""><b>Listing 2.16</b> Reading a key, and listing a page of keys. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/distributed-systems-from-the-ground-up/code/kv/src/store.rs">kv/src/store.rs</a></p>

```rust
{{#include ../code/kv/src/store.rs:read}}
```


A `BTreeMap` keeps its keys in sorted order, so that a listing is an iteration from
some starting position, which is implemented in a function named `page`. Its call to
`range` begins at the prefix or immediately after the cursor, and `take_while` ends
the iteration at the first key that lacks the prefix. By looking for 1 item beyond the
page, `page` learns whether a further page exists without having to count the
remaining keys.

## The HTTP server

`kvd` presents the store through the API of chapter 1.

<p class="listing"><img class="mascot" src="art/crab-happy.svg" alt=""><b>Listing 2.17</b> The imports of <code>kvd/src/main.rs</code>. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/distributed-systems-from-the-ground-up/code/kvd/src/main.rs">kvd/src/main.rs</a></p>

```rust
{{#include ../code/kvd/src/main.rs:imports}}
```

<p class="listing"><img class="mascot" src="art/crab-happy.svg" alt=""><b>Listing 2.18</b> The options of the command line, and the shared state. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/distributed-systems-from-the-ground-up/code/kvd/src/main.rs">kvd/src/main.rs</a></p>

```rust
{{#include ../code/kvd/src/main.rs:options}}
```


### Errors

Each kind of failure of a request is a variant of `ApiError`, in the module
`kvd::api`, and a single function converts a variant into a status code and a response
body in the format of RFC 9457. Handlers return `Result<_, ApiError>` and use `?`. The
conversion from `StoreError` is the 1 place that maps a failed condition to `412` and a
failure of the log to `503`.

<p class="listing"><img class="mascot" src="art/crab-happy.svg" alt=""><b>Listing 2.19</b> The imports of <code>kvd/src/api.rs</code>. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/distributed-systems-from-the-ground-up/code/kvd/src/api.rs">kvd/src/api.rs</a></p>

```rust
{{#include ../code/kvd/src/api.rs:imports}}
```

<p class="listing"><img class="mascot" src="art/crab-happy.svg" alt=""><b>Listing 2.20</b> The errors of the API and their responses. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/distributed-systems-from-the-ground-up/code/kvd/src/api.rs">kvd/src/api.rs</a></p>

```rust
{{#include ../code/kvd/src/api.rs:errors}}
```


### Conditions

<p class="listing"><img class="mascot" src="art/crab-happy.svg" alt=""><b>Listing 2.21</b> Parsing the <code>If-Match</code> and <code>If-None-Match</code> headers. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/distributed-systems-from-the-ground-up/code/kvd/src/api.rs">kvd/src/api.rs</a></p>

```rust
{{#include ../code/kvd/src/api.rs:headers}}
```


`write_condition` accepts the combinations of headers that are meaningful for a write
and answers `400` to all others, such as `If-Match: *`. The server thus rejects a
condition that it cannot interpret. The alternative, to ignore it, would mean
performing an unconditional write on behalf of a client that had asked for a
conditional one, which is exactly the lost update that the condition was sent to
prevent.

### Blocking calls in an asynchronous server

The server uses an asynchronous runtime, in which a small pool of threads serves all
the connections and switches among them whenever one has to wait for the network. To
block such a thread, as an `fsync` of 5 ms does, would delay every connection that the
thread serves. `spawn_blocking` runs a closure on a separate pool of threads intended
for operations that block, and the handler awaits the result without occupying a
thread of the runtime.

<p class="listing"><img class="mascot" src="art/crab-happy.svg" alt=""><b>Listing 2.22</b> Running a write on a thread that is permitted to block. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/distributed-systems-from-the-ground-up/code/kvd/src/main.rs">kvd/src/main.rs</a></p>

```rust
{{#include ../code/kvd/src/main.rs:blocking}}
```


<p class="listing"><img class="mascot" src="art/crab-happy.svg" alt=""><b>Listing 2.23</b> The handlers for <code>PUT</code> and <code>DELETE</code>. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/distributed-systems-from-the-ground-up/code/kvd/src/main.rs">kvd/src/main.rs</a></p>

```rust
{{#include ../code/kvd/src/main.rs:put}}
```


`PUT` answers `201 Created` when it creates a key and `204 No Content` when it
replaces a value. Both responses carry the new version in the `ETag` header.

### Reads

<p class="listing"><img class="mascot" src="art/crab-happy.svg" alt=""><b>Listing 2.24</b> The handler for <code>GET</code> on a single key. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/distributed-systems-from-the-ground-up/code/kvd/src/main.rs">kvd/src/main.rs</a></p>

```rust
{{#include ../code/kvd/src/main.rs:get}}
```


A read holds the lock of the store only while an entry is being copied, and performs
no access to the disk. It can therefore run directly on a thread of the runtime.

<p class="listing"><img class="mascot" src="art/crab-happy.svg" alt=""><b>Listing 2.25</b> The handlers for listing keys and for the health check. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/distributed-systems-from-the-ground-up/code/kvd/src/main.rs">kvd/src/main.rs</a></p>

```rust
{{#include ../code/kvd/src/main.rs:list}}
```


<p class="listing"><img class="mascot" src="art/crab-happy.svg" alt=""><b>Listing 2.26</b> Opening the store and starting the server. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/distributed-systems-from-the-ground-up/code/kvd/src/main.rs">kvd/src/main.rs</a></p>

```rust
{{#include ../code/kvd/src/main.rs:main}}
```


## Running the node

```console
$ cd code
$ cargo build --release
$ ./target/release/kvd --listen 127.0.0.1:7001 --data /var/tmp/kvd
recovered 0 keys from 0 records, cut 0 bytes from the end of the log
listening on 127.0.0.1:7001
```

All the responses shown in chapter 1 came from this program. A further 3 complete the
set: a key containing a character outside the permitted set, a method that a resource
does not support, and a health check.

```console
$ curl -i -X PUT 'http://127.0.0.1:7001/v1/keys/bad%20key' --data-binary 'x'
HTTP/1.1 400 Bad Request
content-type: application/problem+json
content-length: 153

{"type":"/problems/invalid-key","title":"The key is not valid","status":400,"detail":"a key is 1 to 256 characters from A-Z, a-z, 0-9, '.', '_' and '-'"}
```

```console
$ curl -i -X POST http://127.0.0.1:7001/v1/keys/user-1 --data-binary 'x'
HTTP/1.1 405 Method Not Allowed
allow: GET,HEAD,PUT,DELETE
content-length: 0
```

Both the `405` and its `allow` header are produced by `axum`, whose router knows
which methods are registered for each path.

```console
$ curl -i http://127.0.0.1:7001/healthz
HTTP/1.1 200 OK
content-type: application/json
content-length: 42

{"status":"ok","keys":2,"last_sequence":5}
```

## Simulating crashes

The log is intended to recover exactly its complete records, wherever a crash occurs.
A claim of this kind is not established by a few examples, and `crashsim` verifies it
exhaustively, for a log of 5 records, by damaging copies of the log in every possible
position.

<p class="listing"><img class="mascot" src="art/crab-happy.svg" alt=""><b>Listing 2.27</b> The imports of <code>crashsim/src/main.rs</code>. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/distributed-systems-from-the-ground-up/code/crashsim/src/main.rs">crashsim/src/main.rs</a></p>

```rust
{{#include ../code/crashsim/src/main.rs:imports}}
```

<p class="listing"><img class="mascot" src="art/crab-happy.svg" alt=""><b>Listing 2.28</b> Building the test log. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/distributed-systems-from-the-ground-up/code/crashsim/src/main.rs">crashsim/src/main.rs</a></p>

```rust
{{#include ../code/crashsim/src/main.rs:build}}
```


<p class="listing"><img class="mascot" src="art/crab-happy.svg" alt=""><b>Listing 2.29</b> Opening a damaged copy, and the expected result of recovery. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/distributed-systems-from-the-ground-up/code/crashsim/src/main.rs">crashsim/src/main.rs</a></p>

```rust
{{#include ../code/crashsim/src/main.rs:recover}}
```


A crash during a write leaves a file that is shorter than was intended. `cuts` creates
every such file, 1 for each possible length, and checks the result of recovering each.

<p class="listing"><img class="mascot" src="art/crab-happy.svg" alt=""><b>Listing 2.30</b> Cutting the log short at every byte. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/distributed-systems-from-the-ground-up/code/crashsim/src/main.rs">crashsim/src/main.rs</a></p>

```rust
{{#include ../code/crashsim/src/main.rs:cuts}}
```


Storage devices are also capable of returning data that differs from what was
written. `flips` inverts 1 bit in each byte of the log, in a separate run for every
byte. With a bit inverted, the affected record fails its checksum, and recovery is
expected to return all the records before it.

<p class="listing"><img class="mascot" src="art/crab-happy.svg" alt=""><b>Listing 2.31</b> Inverting 1 bit in every byte. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/distributed-systems-from-the-ground-up/code/crashsim/src/main.rs">crashsim/src/main.rs</a></p>

```rust
{{#include ../code/crashsim/src/main.rs:flips}}
```


<p class="listing"><img class="mascot" src="art/crab-happy.svg" alt=""><b>Listing 2.32</b> Running the simulation. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/distributed-systems-from-the-ground-up/code/crashsim/src/main.rs">crashsim/src/main.rs</a></p>

```rust
{{#include ../code/crashsim/src/main.rs:main}}
```


```console
$ cargo run -p crashsim
a log of 5 records and 152 bytes, with records ending at 28, 58, 95, 120, 152
cut at every length from 0 to 152: each recovery returned the complete records
  lengths   0 to  27: 0 records
  lengths  28 to  57: 1 records
  lengths  58 to  94: 2 records
  lengths  95 to 119: 3 records
  lengths 120 to 151: 4 records
  length  152       : 5 records
1 bit flipped in each of 152 bytes: each recovery returned the records before the damage
after a cut at 63: 2 records recovered, and the next record has sequence 3
```

| Output | What it shows |
|---|---|
| lengths 28 to 57: 1 record | A record is recovered only if every one of its bytes is present. With 29 of the 30 bytes of record 2 on disk, record 2 is not recovered. |
| each recovery returned complete records | No cut causes recovery to return a partial record, a wrong record, or records out of order. |
| 1 bit flipped in each of 152 bytes | Corruption at any position in a record, the length field included, is detected, and the preceding records are returned. |
| after a cut at 63, the next record has sequence 3 | The damaged end was removed, and the log continues after the last valid record with no gap in its sequence numbers. |

The test with inverted bits also discloses a limitation. When a bit is inverted in
record 2, recovery stops there and discards records 3 to 5, although they are intact.
For damage at the end of the file, which is what an interrupted write produces, this
behaviour is correct. Damage in the middle of the file is a different matter: it
means that the disk has lost data which was acknowledged, and a single node has no
means of repairing such a loss. In the design of chapter 1, the record is recovered
from the other replicas, and this is the first of several points at which a
limitation of 1 node is the reason for something in the larger design.

## Killing the server under load

The simulation exercises the log in isolation. The next test covers a complete node:
the HTTP server, the store, the log and the disk. The command `kvctl load` writes keys
in sequence and records each key in a local file once the server has answered with
success.

<p class="listing"><img class="mascot" src="art/crab-happy.svg" alt=""><b>Listing 2.33</b> The imports of <code>kvctl/src/main.rs</code>. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/distributed-systems-from-the-ground-up/code/kvctl/src/main.rs">kvctl/src/main.rs</a></p>

```rust
{{#include ../code/kvctl/src/main.rs:imports}}
```

<p class="listing"><img class="mascot" src="art/crab-happy.svg" alt=""><b>Listing 2.34</b> Writing keys, and recording each acknowledged key. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/distributed-systems-from-the-ground-up/code/kvctl/src/main.rs">kvctl/src/main.rs</a></p>

```rust
{{#include ../code/kvctl/src/main.rs:load}}
```


<p class="listing"><img class="mascot" src="art/crab-happy.svg" alt=""><b>Listing 2.35</b> Reading back every acknowledged key. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/distributed-systems-from-the-ground-up/code/kvctl/src/main.rs">kvctl/src/main.rs</a></p>

```rust
{{#include ../code/kvctl/src/main.rs:verify}}
```


While the load is running, the server is terminated with signal 9, `SIGKILL`, which
stops a process at once and allows it to complete nothing that is in progress.

```console
$ ./target/release/kvd --data /var/tmp/kvd &
recovered 0 keys from 0 records, cut 0 bytes from the end of the log
listening on 127.0.0.1:7001
$ ./target/release/kvctl load --server http://127.0.0.1:7001 --count 5000 --acked acked.txt &
$ sleep 3; pkill -9 -x kvd
write 495 failed: io: Peer disconnected
494 writes acknowledged
$ ./target/release/kvd --data /var/tmp/kvd &
recovered 495 keys from 495 records, cut 0 bytes from the end of the log
listening on 127.0.0.1:7001
$ ./target/release/kvctl verify --server http://127.0.0.1:7001 --acked acked.txt
494 acknowledged, 494 found, 0 missing
```

| Output | What it shows |
|---|---|
| 494 writes acknowledged, 494 found, 0 missing | Every acknowledged write was recovered after the process was killed. |
| recovered 495 keys | The log contains 1 more write than the client had recorded. |
| cut 0 bytes | The process was not in the middle of appending a record when it was killed. |

Write 495 is an instance of the third case in figure 2.2. Its record was
stored durably, and the process was killed before any response was sent. From the
client's side the write failed, although the store contains it, and a client that
needs a definite outcome sends its `PUT` again.

### The limits of this test

The same test, run with `--no-sync`, also recovers every acknowledged write.

```console
$ ./target/release/kvd --data /var/tmp/kvd --no-sync &
$ ./target/release/kvctl load --server http://127.0.0.1:7001 --count 200000 --acked acked.txt &
$ sleep 1.5; pkill -9 -x kvd
write 8595 failed: io: Connection reset by peer (os error 104)
8594 writes acknowledged
$ ./target/release/kvd --data /var/tmp/kvd --no-sync &
recovered 8594 keys from 8594 records, cut 0 bytes from the end of the log
$ ./target/release/kvctl verify --server http://127.0.0.1:7001 --acked acked.txt
8594 acknowledged, 8594 found, 0 missing
```

It would be a serious error to conclude from this that `fsync` is unnecessary. When a
process is killed, its own memory is lost, but the data it had passed to `write` is
in the kernel's buffers. The kernel continues to run, and writes that data to the disk
shortly afterwards. Only a failure that stops the kernel, such as a loss of power,
loses data that was written without `fsync`. A test that kills a process therefore
succeeds with and without `fsync`, and provides no evidence whatever about durability
under a loss of power. Many systems have been declared durable on the strength of
exactly this test.

## Running the test on 2 machines

The server and the client are separate programs that communicate over HTTP, and can
therefore run on different machines without any change. In the following session, the
server runs on a machine named `node-b` at the address 10.0.0.2, and the client on
`node-a`. A binary can be copied between machines of the same architecture and
operating system, and is otherwise built on each.

<figure>
<img src="figures/two-machines.svg?v=073ee750" alt="The test on 2 machines. On node-a, kvctl load sends PUT requests and writes each acknowledged key to acked.txt. On node-b, kvd listens on port 7001 and writes kv.log. kvctl writes keys and notes each one the server answered. After 3 seconds kvd is killed with signal 9. kvd is started again and reads its log. kvctl reads every noted key, and 1107 of 1107 are there.">
<figcaption><b>Figure 2.7</b> The client and the server on separate machines.</figcaption>
</figure>

```console
node-a$ scp target/release/kvd node-b:/tmp/kvd
node-b$ /tmp/kvd --listen 0.0.0.0:7001 --data /tmp/kvd-data &
recovered 0 keys from 0 records, cut 0 bytes from the end of the log
listening on 0.0.0.0:7001

node-a$ ./target/release/kvctl load --server http://10.0.0.2:7001 --count 5000 --acked acked.txt &
node-b$ pkill -9 -x kvd
write 1108 failed: io: Connection reset by peer (os error 104)
1107 writes acknowledged

node-b$ /tmp/kvd --listen 0.0.0.0:7001 --data /tmp/kvd-data &
recovered 1107 keys from 1107 records, cut 0 bytes from the end of the log
node-a$ ./target/release/kvctl verify --server http://10.0.0.2:7001 --acked acked.txt
1107 acknowledged, 1107 found, 0 missing
node-a$ curl http://10.0.0.2:7001/healthz
{"status":"ok","keys":1107,"last_sequence":1107}
```

The client's file of acknowledged keys is held on a machine that no fault affected,
and is on that account an independent record of what the server acknowledged. Tests
of faults follow this structure quite generally. A component outside the system under
test records what was acknowledged, a fault is injected, and the record is compared
with the state of the system after it has recovered. Chapters 3 and 4 test replication
and elections in the same way.

The test can be run in several configurations.

| Configuration | Server | Client |
|---|---|---|
| 1 machine | `kvd --listen 127.0.0.1:7001` | `kvctl ... --server http://127.0.0.1:7001` |
| 2 machines on a local network | `kvd --listen 0.0.0.0:7001` on machine B | `kvctl ... --server http://<address of B>:7001` on machine A |
| 2 cloud instances | as above, with port 7001 permitted between the instances | as above, using the private address of the server |

## The limits of a single node

| Limitation | Consequence | What chapter 1 provides against it |
|---|---|---|
| The log is on a single disk. | The loss of the disk loses all the data. | 3 replicas of every shard |
| The node is a single process. | Every request fails while the process is not running. | the election of a new leader |
| Every write performs its own `fsync`. | The node stores 185 records per second on the disk measured. | group commit, and the distribution of writes over 24 nodes |
| The log grows without limit. | The time to restart and the disk space used increase continually. | periodic snapshots of the map, after which older records are deleted |
| All entries are held in memory. | The data cannot exceed the memory of 1 machine. | sharding |

Within these limits, the node retains every acknowledged write when its process is
killed, when its log is cut short at any byte, and when a bit is corrupted in its last
record. That is the assumption on which chapter 1 was built, and chapter 3 now builds
replication upon it.

## The complete programs

<p class="listing"><img class="mascot" src="art/crab-cute.svg" alt=""><b>Listing 2.36</b> The complete <code>kv/src/lib.rs</code>. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/distributed-systems-from-the-ground-up/code/kv/src/lib.rs">kv/src/lib.rs</a></p>

```rust
{{#include ../code/kv/src/lib.rs}}
```


<p class="listing"><img class="mascot" src="art/crab-cute.svg" alt=""><b>Listing 2.37</b> The complete <code>kv/src/record.rs</code>. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/distributed-systems-from-the-ground-up/code/kv/src/record.rs">kv/src/record.rs</a></p>

```rust
{{#include ../code/kv/src/record.rs}}
```


<p class="listing"><img class="mascot" src="art/crab-cute.svg" alt=""><b>Listing 2.38</b> The complete <code>kv/src/log.rs</code>. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/distributed-systems-from-the-ground-up/code/kv/src/log.rs">kv/src/log.rs</a></p>

```rust
{{#include ../code/kv/src/log.rs}}
```


<p class="listing"><img class="mascot" src="art/crab-cute.svg" alt=""><b>Listing 2.39</b> The complete <code>kv/src/store.rs</code>. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/distributed-systems-from-the-ground-up/code/kv/src/store.rs">kv/src/store.rs</a></p>

```rust
{{#include ../code/kv/src/store.rs}}
```


<p class="listing"><img class="mascot" src="art/crab-cute.svg" alt=""><b>Listing 2.40</b> The complete <code>kvd/src/lib.rs</code>. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/distributed-systems-from-the-ground-up/code/kvd/src/lib.rs">kvd/src/lib.rs</a></p>

```rust
{{#include ../code/kvd/src/lib.rs}}
```


<p class="listing"><img class="mascot" src="art/crab-cute.svg" alt=""><b>Listing 2.41</b> The complete <code>kvd/src/api.rs</code>. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/distributed-systems-from-the-ground-up/code/kvd/src/api.rs">kvd/src/api.rs</a></p>

```rust
{{#include ../code/kvd/src/api.rs}}
```


<p class="listing"><img class="mascot" src="art/crab-cute.svg" alt=""><b>Listing 2.42</b> The complete <code>kvd/src/main.rs</code>. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/distributed-systems-from-the-ground-up/code/kvd/src/main.rs">kvd/src/main.rs</a></p>

```rust
{{#include ../code/kvd/src/main.rs}}
```


<p class="listing"><img class="mascot" src="art/crab-cute.svg" alt=""><b>Listing 2.43</b> The complete <code>kvctl/src/main.rs</code>. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/distributed-systems-from-the-ground-up/code/kvctl/src/main.rs">kvctl/src/main.rs</a></p>

```rust
{{#include ../code/kvctl/src/main.rs}}
```


<p class="listing"><img class="mascot" src="art/crab-cute.svg" alt=""><b>Listing 2.44</b> The complete <code>crashsim/src/main.rs</code>. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/distributed-systems-from-the-ground-up/code/crashsim/src/main.rs">crashsim/src/main.rs</a></p>

```rust
{{#include ../code/crashsim/src/main.rs}}
```


<p class="listing"><img class="mascot" src="art/crab-cute.svg" alt=""><b>Listing 2.45</b> The complete <code>synccost/src/main.rs</code>. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/distributed-systems-from-the-ground-up/code/synccost/src/main.rs">synccost/src/main.rs</a></p>

```rust
{{#include ../code/synccost/src/main.rs}}
```


<div class="summary">

## Summary

- A storage node keeps its entries in memory for reads and a log on disk for durability, and every write is appended to the log and confirmed by the disk before it is applied in memory.
- With a log that is only appended to, a crash can damage nothing but the last record, whereas an update in place can destroy data that was already stored.
- Every record carries its length and a CRC-32 checksum, by which a reader distinguishes a complete record from one that is incomplete or corrupt.
- Recovery decodes records until one fails, keeps all that precede it, and cuts the file off before anything new is appended.
- `write` hands data to the kernel, and `fsync` waits until the disk has stored it. A durable append took 5.4 ms, which is 185 records per second.
- The directory entry of a new file becomes durable only when the directory is synchronised.
- After a failed write or `fsync`, the log accepts no further records, since a repeated `fsync` can report success for data that is not on the disk.
- A write can be durable without having been acknowledged, when the node crashes between the disk's confirmation and the response, and the client then repeats its request.
- Killing a process does not test durability under a loss of power, because the kernel keeps what the process had written.
- A test of faults records what was acknowledged outside the system under test, and compares that record with the state of the system afterwards.

</div>
