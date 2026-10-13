<img class="plate" src="art/ch05.svg?v=84b52a42" alt="Switch, an octopus, sits between 2 stacks of boxes marked shard-a and shard-b. It holds a parcel labelled user-1 in one arm and points another arm at shard-a.">

# Key-Value Store: Router (Low-Level Design)

With [chapter 4](04-key-value-store-leader-election.md) complete, we have a shard
that survives the loss of its leader without anybody's help. Measured against the
design of [chapter 1](01-key-value-store-system-design.md), 2 things are still
wanting. A client has to discover for itself which member of the shard is the leader,
as the program `probe` did by trying each node in turn and collecting 51 refusals in
the process. And all the data is in a single shard, whereas the design calls for the
keys to be divided among many.

A single small component supplies both. The *router* stands between the clients and
the shards. Clients send every request to it, and for each request it works out which
shard owns the key and which member of that shard is at present the leader, and
passes the request on. The clients are thereby relieved of all knowledge of the
cluster. They know 1 address, and neither the number of shards nor a change of leader
is visible to them.

The router is the least intricate program in this part of the book, and it contains
1 decision that is easy to get wrong and expensive when it is: what to do when the
member it has asked does not give a clear answer. A router that retries too readily
will perform a write twice, and a router that retries too reluctantly will report
failures that it could have concealed. The chapter builds the router, states the rule
that settles this question, and then repeats the experiment of chapter 4, killing a
leader under load, with the router in front.

<div class="covers">

This chapter covers

- what a router does, and why it holds no data
- a ring file that lists the shards and their members
- finding the shard of a key with the ring of chapter 1
- finding the leader, and the rule that decides when another member may be asked
- 2 shards behind 1 router, measured
- the loss of a leader behind the router, as a client sees it

</div>

## What a router does

<figure>
<img src="figures/route-overview.svg?v=8d2bc7d5" alt="A router in front of 2 shards. Step 1: a client, which knows 1 address, sends every request to the router on port 7000. Step 2: the router hashes the key, and the ring names a shard. Step 3: it forwards the request to that shard&#x27;s leader. Each shard is a group of 3 members, 1 leader and 2 followers, and the other shard never sees the request.">
<figcaption><b>Figure 5.1</b> A request on its way through the router to the shard that owns its key.</figcaption>
</figure>

A router keeps no data. Everything it knows comes from a ring file, read when it
starts, and from what the members tell it in the course of its work. This is the
statelessness that chapter 1 required of routers, and its practical value is
considerable: any number of routers may be run side by side, and any of them may be
stopped or restarted at any time, since a router that has lost its memory rebuilds it
from the first few answers it receives.

## The ring file

```console
$ cat ring.json
{
  "virtual_nodes": 256,
  "shards": [
    { "name": "shard-a", "members": ["http://127.0.0.1:7011", "http://127.0.0.1:7012", "http://127.0.0.1:7013"] },
    { "name": "shard-b", "members": ["http://127.0.0.1:7021", "http://127.0.0.1:7022", "http://127.0.0.1:7023"] }
  ]
}
```

Each shard is a group of 3 `kvraft` members, listed in the order of their ids. In the
design of chapter 1, the ring is held by a coordinator and changes while the system
runs. Here it is a file that the router reads once at startup. That is sufficient for
routing requests, and it leaves changes to the ring, which are a substantial subject
in themselves, outside this chapter.

<p class="listing"><img class="mascot" src="art/crab-happy.svg" alt=""><b>Listing 5.1</b> The imports of <code>kvrouter/src/main.rs</code>. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/distributed-systems-from-the-ground-up/code/kvrouter/src/main.rs">kvrouter/src/main.rs</a></p>

```rust
{{#include ../code/kvrouter/src/main.rs:imports}}
```

<p class="listing"><img class="mascot" src="art/crab-happy.svg" alt=""><b>Listing 5.2</b> The ring file, and what the router keeps for each shard. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/distributed-systems-from-the-ground-up/code/kvrouter/src/main.rs">kvrouter/src/main.rs</a></p>

```rust
{{#include ../code/kvrouter/src/main.rs:config}}
```


For every shard the router remembers a single number, the position in the list of the
member that was the leader when it last asked. This is a guess and nothing more. The
sections that follow show what happens when the guess is wrong, and the important
property of the design is that a wrong guess costs an extra request and never a wrong
result.

## Finding the shard

Each shard is placed on the ring of chapter 1 with 256 tokens. To look up a key then
takes 2 steps: the ring is asked for the name of the owner, and the shard of that
name is fetched.

<p class="listing"><img class="mascot" src="art/crab-happy.svg" alt=""><b>Listing 5.3</b> Building the ring, and finding the shard of a key. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/distributed-systems-from-the-ground-up/code/kvrouter/src/main.rs">kvrouter/src/main.rs</a></p>

```rust
{{#include ../code/kvrouter/src/main.rs:load}}
```


## Finding the leader

The router sends the request to the member that it believes to be the leader. Usually
the belief is correct. When it is not, the answer of the member tells the router what
to do next.

<figure>
<img src="figures/route-attempts.svg?v=ef4ace25" alt="What a member can answer and what the router does. Any other status, such as 200, 201, 204, 404 or 412, means the leader served the request, and the router passes the response to the client. 421 with the text the leader is member 1 comes from a follower that changed nothing, and the router asks member 1. 503 of type no-leader means an election is running and nothing was changed, and the router asks the next member after a pause. A refused connection means the process is down and nothing was changed, and the router asks the next member. 503 of another type, or a timeout, means the write may or may not have happened, and the router answers 503 so that the client decides.">
<figcaption><b>Figure 5.2</b> The answers a member can give, and the router's reaction to each.</figcaption>
</figure>

All the cases are decided by a single rule: the router asks another member only if
the first attempt has certainly changed nothing. A follower that answers `421` did
not touch its log. Nor did a member that reports that the shard is electing a leader,
nor one whose process is not running and whose connection was refused. In all 3
cases, to ask another member is safe, since whatever that member does will be the
only effect of the request.

A timeout is a different matter altogether. The leader may have appended the record,
and even committed it, before the connection failed, and the router cannot know. If
it were to send the request to another member, a write might be performed twice, and
a conditional write that had succeeded might be reported as failed. The router
therefore answers `503` and leaves the decision to the client, which is the only
party that knows whether its request is safe to repeat. This is the lost response of
chapter 1 once again, and the router's rule is a refusal to guess about it on
somebody else's behalf.

In the code, the possible outcomes of asking a member are the variants of an enum.

<p class="listing"><img class="mascot" src="art/crab-happy.svg" alt=""><b>Listing 5.4</b> The 3 outcomes of asking a member. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/distributed-systems-from-the-ground-up/code/kvrouter/src/main.rs">kvrouter/src/main.rs</a></p>

```rust
{{#include ../code/kvrouter/src/main.rs:attempt}}
```


`ask` sends the request to 1 member and classifies what comes back as 1 of the
outcomes.

<p class="listing"><img class="mascot" src="art/crab-happy.svg" alt=""><b>Listing 5.5</b> Asking 1 member. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/distributed-systems-from-the-ground-up/code/kvrouter/src/main.rs">kvrouter/src/main.rs</a></p>

```rust
{{#include ../code/kvrouter/src/main.rs:ask}}
```


`forward` is the loop around it. A refusal moves the guess to the member that the
refusal named, or failing that to the next in the list. When every member has refused
once, an election must be in progress, and the router then waits 150 ms between
further attempts, so that it does not flood a shard which is busy choosing a leader.

<p class="listing"><img class="mascot" src="art/crab-happy.svg" alt=""><b>Listing 5.6</b> Trying members until one serves the request. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/distributed-systems-from-the-ground-up/code/kvrouter/src/main.rs">kvrouter/src/main.rs</a></p>

```rust
{{#include ../code/kvrouter/src/main.rs:forward}}
```


<p class="listing"><img class="mascot" src="art/crab-happy.svg" alt=""><b>Listing 5.7</b> The HTTP handlers, and the start of the program. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/distributed-systems-from-the-ground-up/code/kvrouter/src/main.rs">kvrouter/src/main.rs</a></p>

```rust
{{#include ../code/kvrouter/src/main.rs:handlers}}
```


## 2 shards behind 1 router

We start 6 `kvraft` members in 2 groups of 3, then the router, and write 400 keys
through it.

```console
$ ./target/release/kvrouter --listen 127.0.0.1:7000 --ring ring.json &
routing to 2 shards
listening on 127.0.0.1:7000
$ ./target/release/kvctl load --server http://127.0.0.1:7000 --count 400 --acked acked.txt
400 writes acknowledged
$ for port in 7013 7023; do curl http://127.0.0.1:$port/healthz; echo; done
{"id":3,"role":"leader","term":1,"leader":3,"last_sequence":206,"committed":206}
{"id":3,"role":"leader","term":1,"leader":3,"last_sequence":196,"committed":196}
$ ./target/release/kvctl verify --server http://127.0.0.1:7000 --acked acked.txt
400 acknowledged, 400 found, 0 missing
```

| Output | What it shows |
|---|---|
| logs end at 206 and 196 | The 400 keys were divided 205 to 195. Each log also contains 1 term marker. |
| 400 found, 0 missing | A read through the router reaches the shard that holds the key. |

The client used a single address throughout. It never learned how many shards exist,
or which members lead them.

## A leader is lost behind the router

`probe`, from chapter 4, is now given the router's address and no other. While it is
writing, the leader of `shard-a` is killed.

```console
$ ./target/release/probe --seconds 12 --acked acked.txt --server http://127.0.0.1:7000 &
$ sleep 4; kill -9 <pid of member 3 of shard-a, its leader>
780 writes acknowledged in 12 seconds, 0 attempts refused
the longest pause between 2 acknowledged writes was 1.08 s, ending 5.2 s after the start
$ curl http://127.0.0.1:7000/healthz
{"shards":[{"leader":"http://127.0.0.1:7011","name":"shard-a"},{"leader":"http://127.0.0.1:7023","name":"shard-b"}],"status":"ok"}
$ ./target/release/kvctl verify --server http://127.0.0.1:7000 --acked acked.txt
780 acknowledged, 780 found, 0 missing
```

| Output | What it shows |
|---|---|
| 0 attempts refused | The client saw no error of any kind. In chapter 4, without a router, the same experiment produced 51 refusals. |
| longest pause 1.08 s | Requests for `shard-a` waited inside the router while the shard elected a leader. |
| leader of `shard-a` is now member 1 | The router found the new leader by asking, and remembered it. |
| 780 found, 0 missing | No acknowledged write was lost. |

The comparison with chapter 4 shows what the router contributes. The election took
as long as it did before, about a second, since the router does nothing to hasten it.
What has changed is what the client experiences. A second of refusals, which every
client would have had to be written to handle, has become a second of waiting, which
requires nothing of the client at all.

Writes to `shard-b` were at no time affected. `probe` sends its keys in turn, and so
it waited behind the 1 request for `shard-a` that was being held. Independent clients
writing to `shard-b` would have noticed nothing.

## What is still missing

| Missing | Effect |
|---|---|
| The ring is a file read at startup. | To add a shard, the router has to be restarted, and existing keys do not move to the new shard. |
| Members do not check which shard a key belongs to. | A router with a wrong ring file could write a key to the wrong shard. Chapter 1 prevents this by sending the version of the ring with every request. |
| Listing keys by prefix is not routed. | The router would have to ask every shard and merge the answers. |

## The complete program

<p class="listing"><img class="mascot" src="art/crab-cute.svg" alt=""><b>Listing 5.8</b> The complete <code>kvrouter/Cargo.toml</code>. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/distributed-systems-from-the-ground-up/code/kvrouter/Cargo.toml">kvrouter/Cargo.toml</a></p>

```toml
{{#include ../code/kvrouter/Cargo.toml}}
```


<p class="listing"><img class="mascot" src="art/crab-cute.svg" alt=""><b>Listing 5.9</b> The complete <code>kvrouter/src/main.rs</code>. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/distributed-systems-from-the-ground-up/code/kvrouter/src/main.rs">kvrouter/src/main.rs</a></p>

```rust
{{#include ../code/kvrouter/src/main.rs}}
```


<div class="summary">

## Summary

- A router hashes the key, finds the shard on the ring, and forwards the request to the leader of that shard, and it holds no data of its own.
- The router keeps a guess at the leader of each shard and corrects the guess from the answers it receives.
- It asks another member only when the first attempt certainly changed nothing: after a follower's `421`, after a `503` that reports no leader, or after a refused connection.
- After a timeout it answers `503`, since the write may have been performed, and only the client knows whether the request is safe to repeat.
- With 2 shards, 400 keys were divided 205 to 195, and every key was found again through the router.
- When a leader was killed, clients behind the router experienced a pause of 1.08 seconds and no errors.

</div>
