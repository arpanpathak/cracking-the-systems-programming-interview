<img class="plate" src="art/ch06.svg?v=6137924e" alt="Bundle, a beaver, carries 4 logs tied together with a rope toward a door marked disk, where a single log lies that was carried alone. A crab watches with a stopwatch.">

# Key-Value Store: Group Commit (Low-Level Design)

The capacity estimate of [chapter 1](01-key-value-store-system-design.md) arrived at
24 nodes by assuming that a node stores 20 writes with every wait for its disk.
Without that assumption the same calculation gave 325 nodes. Nothing built so far
does anything of the kind. The storage node of
[chapter 2](02-key-value-store-storage-node.md) waits once for every write, and
reaches its limit at about 180 writes per second however many clients are sending to
it, since each must wait its turn for a disk that confirms 185 times a second.

This chapter adds the missing technique. Under *group commit*, a node stores all the
writes that are waiting at a given moment with a single wait for the disk. The change
is small, some 60 lines in the store and 1 thread in the server, and its effect is
out of all proportion to its size: the measured rate rises from 180 writes per second
to almost 5000 with 64 clients, and beyond 17000 with 256. It is among the best
examples in systems programming of a large gain obtained by rearranging work, with
no part of the work made faster.

<div class="covers">

This chapter covers

- why a single wait for the disk can serve many writes
- a committer thread that forms batches without a timer
- conditional writes within a batch
- measurements with 1, 8, 64 and 256 clients
- a crash in the middle of a batch

</div>

## The idea

A wait for the disk takes about 5.4 ms whether it stores 1 record or 100. Nearly all
of that time is spent by the disk in confirming that the data is safe, and very
little in transferring the data, so that the cost is close to a fixed charge for each
wait and almost independent of how much is written. Writes that arrive while 1 wait
is in progress can therefore share the next.

<figure>
<img src="figures/group-timeline.svg?v=0338736f" alt="5 writes that arrive within 1 millisecond, stored in 2 ways. With 1 wait for each write, there are 5 waits of 5.4 ms, and the last write is answered after 27 ms. With group commit there are 2 waits, and the last write is answered after 10.8 ms. Step 1: the committer takes write 1 and starts to wait for the disk. Step 2: writes 2 to 5 arrive during that wait and queue up. Step 3: the wait ends, and the committer takes all 4 that are waiting. Step 4: it stores them with 1 write and 1 wait, and answers all 4.">
<figcaption><b>Figure 6.1</b> 5 writes stored with 5 waits, and the same 5 writes stored with 2.</figcaption>
</figure>

The design uses no timer, and the point deserves emphasis because the alternative is
common. Some systems hold a write back for a millisecond or so in the hope that
others will arrive to share its wait. This improves throughput under heavy load and
penalises every write under light load, when no others are coming. Here a batch is
formed only from writes that are already waiting. A write that arrives alone is
stored at once, with no delay, and the batches grow of their own accord as the load
grows, since the busier the node is, the more writes accumulate during each wait.
The mechanism adjusts itself to the load without any parameter that an operator has
to tune.

## A batch in the store

`Store::commit` takes a list of writes and returns a result for each of them.

<p class="listing"><img class="mascot" src="art/crab-happy.svg" alt=""><b>Listing 6.1</b> The imports of <code>kv/src/store.rs</code>. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/distributed-systems-from-the-ground-up/code/kv/src/store.rs">kv/src/store.rs</a></p>

```rust
{{#include ../code/kv/src/store.rs:imports}}
```

<p class="listing"><img class="mascot" src="art/crab-happy.svg" alt=""><b>Listing 6.2</b> Storing a batch of writes with a single wait for the disk. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/distributed-systems-from-the-ground-up/code/kv/src/store.rs">kv/src/store.rs</a></p>

```rust
{{#include ../code/kv/src/store.rs:batch}}
```


The method works in 3 passes.

| Pass | What happens |
|---|---|
| Check | The condition of each write is checked, and the writes that are accepted receive the next sequence numbers. |
| Store | All the accepted records go to the log in 1 write, followed by 1 wait for the disk. |
| Apply | The records are applied to the map, and the results are returned. |

Conditional writes need care in the first pass. Suppose that a batch contains 2
writes to `user-1`, each carrying `If-None-Match: *`, which means "create only". The
first ought to succeed and the second to fail, although neither is yet in the map,
and a check against the map alone would accept both. The `pending` map resolves the
difficulty. It records the version that each key will have once the accepted writes
of the batch have been applied, and a later write in the same batch is checked
against it. The batch thus behaves, as far as any client can tell, exactly as if its
writes had been performed in sequence, which is the property that makes batching
invisible.

The order of the passes preserves invariant 1 of chapter 2. No result leaves `commit`
before the wait for the disk has ended, and so no client is answered early.

## The committer

A single thread, the *committer*, owns the store. The handlers of requests do not
touch the store at all. Each hands its write to the committer through a channel and
waits for the result.

<p class="listing"><img class="mascot" src="art/crab-happy.svg" alt=""><b>Listing 6.3</b> The imports of <code>kvgroup/src/main.rs</code>. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/distributed-systems-from-the-ground-up/code/kvgroup/src/main.rs">kvgroup/src/main.rs</a></p>

```rust
{{#include ../code/kvgroup/src/main.rs:imports}}
```

<p class="listing"><img class="mascot" src="art/crab-happy.svg" alt=""><b>Listing 6.4</b> The options, and a write on its way to the committer. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/distributed-systems-from-the-ground-up/code/kvgroup/src/main.rs">kvgroup/src/main.rs</a></p>

```rust
{{#include ../code/kvgroup/src/main.rs:options}}
```


<p class="listing"><img class="mascot" src="art/crab-happy.svg" alt=""><b>Listing 6.5</b> The committer thread. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/distributed-systems-from-the-ground-up/code/kvgroup/src/main.rs">kvgroup/src/main.rs</a></p>

```rust
{{#include ../code/kvgroup/src/main.rs:committer}}
```


This loop is the whole of group commit. `recv` blocks until a write arrives.
`try_iter` then yields every write that is already in the channel, without waiting
for more, up to a limit of 256 for the batch. While `commit` is waiting for the disk,
new writes accumulate in the channel, and the next turn of the loop takes all of
them.

Giving the store to 1 thread has a further merit. Since no other thread touches it,
the store needs no lock, and the question of what 2 concurrent writers might do to
the map does not arise. Concurrency has been confined to the channel, where it is
handled by a well-tested library, and the logic of the store remains sequential.

<p class="listing"><img class="mascot" src="art/crab-happy.svg" alt=""><b>Listing 6.6</b> Handing a write to the committer, and the HTTP handlers. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/distributed-systems-from-the-ground-up/code/kvgroup/src/main.rs">kvgroup/src/main.rs</a></p>

```rust
{{#include ../code/kvgroup/src/main.rs:handlers}}
```


<p class="listing"><img class="mascot" src="art/crab-happy.svg" alt=""><b>Listing 6.7</b> Starting the committer and the server. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/distributed-systems-from-the-ground-up/code/kvgroup/src/main.rs">kvgroup/src/main.rs</a></p>

```rust
{{#include ../code/kvgroup/src/main.rs:main}}
```


## Measurements

`kvbench` runs a number of clients simultaneously. Each client sends its writes in
succession and waits for every answer before sending the next.

<p class="listing"><img class="mascot" src="art/crab-happy.svg" alt=""><b>Listing 6.8</b> The imports of <code>kvbench/src/main.rs</code>. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/distributed-systems-from-the-ground-up/code/kvbench/src/main.rs">kvbench/src/main.rs</a></p>

```rust
{{#include ../code/kvbench/src/main.rs:imports}}
```

<p class="listing"><img class="mascot" src="art/crab-happy.svg" alt=""><b>Listing 6.9</b> Writing from several clients at once. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/distributed-systems-from-the-ground-up/code/kvbench/src/main.rs">kvbench/src/main.rs</a></p>

```rust
{{#include ../code/kvbench/src/main.rs:bench}}
```


```console
$ ./target/release/kvd --data /var/tmp/kvd &
$ ./target/release/kvbench --server http://127.0.0.1:7001 --clients 64 --writes 12 --acked acked.txt
64 clients: 768 writes acknowledged in 4.27 s, 180 writes per second

$ ./target/release/kvgroup --data /var/tmp/kvgroup &
$ ./target/release/kvbench --server http://127.0.0.1:7001 --clients 64 --writes 400 --acked acked.txt
64 clients: 25600 writes acknowledged in 5.13 s, 4993 writes per second
25535 writes in 800 batches, 31.9 writes per batch
```

<figure>
<img src="figures/group-results.svg?v=4cce2822" alt="Writes per second without and with group commit. With 1 client: 167 without and 165 with, at 1.0 writes per batch. With 8 clients: 181 without and 712 with, at 4.0 writes per batch. With 64 clients: 180 without and 4993 with, at 31.9 writes per batch. With 256 clients: 17218 with group commit, at 119.9 writes per batch. Without group commit the rate stays near 180 whatever the load, and with it the rate grows with the number of clients.">
<figcaption><b>Figure 6.2</b> Writes per second without and with group commit, for 4 numbers of clients.</figcaption>
</figure>

| Clients | Without | With group commit | Writes in a batch |
|---|---|---|---|
| 1 | 167 | 165 | 1.0 |
| 8 | 181 | 712 | 4.0 |
| 64 | 180 | 4993 | 31.9 |
| 256 | not measured | 17218 | 119.9 |

Several things can be read from the table. A single client gains nothing, since it
sends its next write only when the previous one has been answered, and there is
consequently never a second write with which a wait could be shared. Group commit
improves throughput under concurrency and does nothing for the latency of an
individual write, which remains 1 wait for the disk.

The size of a batch is about half the number of clients: 4 of 8, 32 of 64, 120 of
256. The explanation is that the clients fall into 2 groups that alternate. While 1
half is waiting in the batch that is being stored, the other half has just been
answered and is sending its next writes, which form the following batch.

And the assumption of chapter 1 is confirmed with something to spare. The estimate
supposed 20 writes for each wait and 3700 writes per second. With 64 clients the node
achieved 31.9 writes for each wait and 4993 writes per second.

## A crash in the middle of a batch

The server is killed while 64 clients are writing. The program `kvd` of chapter 2
then opens the same data directory, which incidentally demonstrates that the 2
programs use the same format for the log.

```console
$ ./target/release/kvgroup --data /var/tmp/kvgroup &
$ ./target/release/kvbench --server http://127.0.0.1:7001 --clients 64 --writes 2000 --acked acked.txt &
$ sleep 2; kill -9 <pid of kvgroup>
64 clients: 9341 writes acknowledged in 2.74 s, 3412 writes per second
$ ./target/release/kvd --data /var/tmp/kvgroup &
recovered 9366 keys from 9366 records, cut 0 bytes from the end of the log
$ ./target/release/kvctl verify --server http://127.0.0.1:7001 --acked acked.txt
9341 acknowledged, 9341 found, 0 missing
```

Every one of the 9341 acknowledged writes is present. The log contains 25 more, which
are the batch that had reached the disk when the process was killed and whose
answers had not yet been sent. These are the durable and unacknowledged writes of
chapter 2, the third case of its figure of crash points, now occurring 25 together.
Group commit has not altered the guarantee in any respect. It has enlarged the
number of writes that may be in that uncertain state at the moment of a crash from 1
to the size of a batch, and each of the 25 clients concerned resolves the uncertainty
in the usual way, by repeating its request.

## What is still missing

| Missing | Effect |
|---|---|
| `kvgroup` serves writes only. | Reads need access to the map, which the committer thread owns. A shared view of the map for reading would provide it. |
| The replicated nodes of chapters 3 and 4 still store 1 write for each round trip. | Their leaders could send a whole batch in 1 `Append`, which the protocol already permits, and the followers already store the records of a message with 1 wait. |

## The complete programs

`Store::commit` is part of `kv/src/store.rs`, which is listed in full in chapter 2.

<p class="listing"><img class="mascot" src="art/crab-cute.svg" alt=""><b>Listing 6.10</b> The complete <code>kvgroup/src/main.rs</code>. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/distributed-systems-from-the-ground-up/code/kvgroup/src/main.rs">kvgroup/src/main.rs</a></p>

```rust
{{#include ../code/kvgroup/src/main.rs}}
```


<p class="listing"><img class="mascot" src="art/crab-cute.svg" alt=""><b>Listing 6.11</b> The complete <code>kvbench/src/main.rs</code>. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/distributed-systems-from-the-ground-up/code/kvbench/src/main.rs">kvbench/src/main.rs</a></p>

```rust
{{#include ../code/kvbench/src/main.rs}}
```


## Further reading

- D. DeWitt and others, "Implementation Techniques for Main Memory Database Systems", SIGMOD 1984, which introduced group commit.
- J. Gray and A. Reuter, *Transaction Processing: Concepts and Techniques*, Morgan Kaufmann, 1992.

<div class="summary">

## Summary

- A wait for the disk costs nearly the same for 1 record as for 100, so that the writes which arrive during a wait can share the next.
- The committer thread takes every write that is waiting and stores them together. It uses no timer, and a write that arrives alone is not delayed.
- Within a batch, every conditional write is checked against the writes that precede it, so that a batch behaves as its writes would in sequence.
- With 64 clients the node stored 4993 writes per second, against 180 without group commit, and with 256 clients it stored 17218.
- After being killed under load, the node held all 9341 acknowledged writes, and 25 more that had reached the disk without being acknowledged.

</div>
