<img class="plate" src="art/ch01.svg?v=76ac1f43" alt="Draft, an owl, stands beside a drawing board. The blueprint on it shows a request passing through a router to a group of 3 nodes, one of them marked as the leader. A crab looks up at the board.">

# Key-Value Store: System Design

A *key-value store* is the simplest database that is of any practical use. It offers 2
operations, to store a value under a key and to return the value that was stored under
a key, and it makes no attempt to understand what the values mean. Simple as it is, it
lies underneath a remarkable number of other systems. A web application keeps its
users' sessions in one. A cluster of machines keeps its configuration in one. A file
system uses one for its directory of files, and an object store for its index of
objects. Most of the larger storage systems in use today contain a key-value store as
their innermost component, and the designs in the later chapters of this book rely on
one repeatedly.

On a single machine, a key-value store is an afternoon's work: a table in memory and a
file on disk. The difficulty, and the subject of this chapter and the 5 that follow,
begins when the store has to outgrow 1 machine and to outlive it. The data may be
larger than any 1 disk. The requests may be more than any 1 processor can answer. And
the machine will certainly fail at some point, by losing power, or its disk, or its
connection to the network, and a store on which other systems depend cannot be
permitted to lose its data or to stop answering on that account. Meeting these demands
means spreading the data across many machines and keeping several copies of every
part of it, and the moment there are several copies, the questions arise that define
the whole field: which copy is right when they differ, who decides, and what happens
when the machines cannot reach each other to agree.

This chapter designs such a store from its requirements. It is the system design, and
it stays at the level of components and the messages between them. Chapters 2 to 6
then build each component in Rust and measure it.

<div class="covers">

This chapter covers

- what the store is for, stated as use cases and as requirements that can be tested
- strong, eventual and tunable consistency, and why this design chooses the first
- the entities of the design, and an estimate of how many machines it needs
- an HTTP API, with conditional writes that prevent 1 client from overwriting another
- the protocol that storage nodes speak among themselves
- the components of the system and the path of a request through them
- dividing keys among machines with consistent hashing and virtual nodes
- how every part of the system learns where a key lives, and what happens when that knowledge is out of date
- keeping 3 copies of every key, with a leader and a majority
- what the system does when a machine, a disk or the network fails
- what the design guarantees, and what it gives up in return

</div>

## Why such a store is needed

Consider a shop whose web site runs on 3 web servers behind a load balancer. A
customer's requests are distributed among the 3, so that the request which adds an
item to the basket may be handled by 1 server and the request which displays the
basket by another. The basket therefore cannot be kept in the memory of any 1 web
server. It has to be held by some service that all 3 can reach.

This arrangement is typical, and it divides the system into parts of 2 very different
characters. The web servers hold nothing that matters. Any of them can be restarted,
replaced or duplicated at any moment without loss, and a component of this kind is
called *stateless*. The shared store is the opposite. Everything of value is in it, a
failure of it is a failure of every web server at once, and it cannot be
restarted on a fresh machine, since a fresh machine would not have the data. The
simplicity of the stateless part of a system is paid for by the difficulty of the
part that holds the state, and this chapter is about that part.

What is demanded of the store follows directly from its position. Each demand has a
consequence for the design, and each consequence is the subject of a later section.

| What is demanded | What the design must therefore do | Where it is treated |
|---|---|---|
| A crash in the middle of a write loses no data that was confirmed | write each change to disk before confirming it | the last section, and chapter 2 |
| The loss of a machine loses no data | keep each change on more than 1 machine | Replication |
| The data may exceed the disk of 1 machine | divide the keys among machines | Sharding |
| The failure of a machine does not stop the service | let another machine take over its work | Failure handling |
| Clients working at the same time do not undo each other's changes | allow a write to state what it was based on | The API |

## Use cases

The store is used by 3 kinds of party. An *application* is any service that keeps its
data in the store, such as the web servers of the shop. An *operator* is whoever looks
after the machines, whether a person or an automated system. And *monitoring* is the
system that watches the health of every machine and raises an alarm when something is
wrong.

<figure>
<img src="figures/use-cases.svg?v=41cb1cb8" alt="A use case diagram of the key-value store with 3 actors. The application, a service that keeps its state in the store, stores a value with PUT /v1/keys/{key}, reads a value with GET, deletes a key with DELETE, writes only if the value is unchanged with PUT and If-Match, and lists keys by prefix with GET /v1/keys. The operator, who changes the set of machines, adds a node, removes a node, and replaces a failed node. Monitoring, which watches every node, checks health with GET /healthz and reads metrics.">
<figcaption><b>Figure 1.1</b> The 3 actors of the store and what each of them does.</figcaption>
</figure>

| Actor | Use case | An example |
|---|---|---|
| Application | store a value | save the basket of customer 41 |
| Application | read a value | load the basket when the customer's next request arrives |
| Application | delete a key | remove the basket once the order has been paid for |
| Application | write only if unchanged | add an item to the basket without discarding an item that another web server has just added |
| Application | list keys by prefix | find all the sessions that belong to user 7 |
| Operator | add a node | increase capacity before a sale |
| Operator | remove a node | take a machine out of service for maintenance |
| Operator | replace a failed node | a machine's disk has failed |
| Monitoring | check health | stop sending requests to a node that is not well |
| Monitoring | read metrics | plot the number of keys on each node |

## Functional requirements

The functional requirements state what the store does. Each is derived from a use case
and is specific enough that a test could establish whether it is met.

| No. | Functional requirement |
|---|---|
| 0 | A client can set the value of a key. A key consists of 1 to 256 characters from `A-Z`, `a-z`, `0-9`, `.`, `_` and `-`. A value is 0 to 1048576 bytes of any content. |
| 1 | A client can read the current value of a key, together with its version. |
| 2 | A client can delete a key. |
| 3 | Every write gives the key a new version. A client can make a write conditional on the version it last read, or on the key's not existing. |
| 4 | A client can list the keys that begin with a given prefix, in sorted order and in pages of limited size. |
| 5 | An operator can add, remove and replace nodes while the store continues to serve requests. |
| 6 | Every node reports whether it is able to serve requests. |

## Non-functional requirements

The non-functional requirements state how well the store must do these things: how
much data, how many requests, how quickly, and through which failures. It is these,
far more than the functional requirements, that determine the architecture. A program
that kept 1 file on 1 machine would satisfy functional requirements 0 to 6 completely,
and would satisfy almost none of what follows.

| No. | Property | Non-functional requirement | Remark |
|---|---|---|---|
| 0 | Durability | An acknowledged write survives the loss of any 1 machine, including its disk. | A write is *acknowledged* when the client has received a successful response to it. |
| 1 | Availability | 99.95% of requests succeed, measured over a month. | A month of 30 days has 43200 minutes, of which 0.05% is 21.6 minutes. |
| 2 | Consistency | Strong: a read that begins after a write was acknowledged returns that write or a later one, whichever node answers. | Explained below, with its 2 alternatives. |
| 3 | Latency | 99% of writes complete within 20 ms and 99% of reads within 5 ms, for clients in the same data centre. | The value below which 99% of measurements fall is the *99th percentile*, written p99. |
| 4 | Scale | 1 billion keys with values of 1 KB on average, 20000 writes per second and 100000 reads per second. | |
| 5 | Elasticity | Capacity can be increased by adding machines while the store is in service. | |

Durability and availability are easily confused and should be kept apart. Durability
concerns data that has already been written, and requires that none of it be lost.
Availability concerns requests that are yet to come, and requires that they be
answered. Data can be perfectly durable and entirely unavailable, as when every copy
of a key is on a machine that has been switched off for an hour and will return
intact. The design provides for the 2 properties by different mechanisms, and they
sometimes pull in opposite directions.

### Which kind of consistency

The word "consistency" has to be given an exact meaning before anything can be
designed to provide it, since storage systems offer 3 quite different things under
that name. They are best distinguished by a single situation: a value has just been
written, 1 of the copies of the data has not yet received the change, and a reader
happens to be answered by that copy.

<figure>
<img src="figures/consistency-models.svg?v=7b8b3e8c" alt="The 3 consistency models, shown with 1 situation. A client writes basket = tea, milk, and the write is acknowledged. Replica 3 has not received the write yet and still holds basket = tea. Another client reads the basket. Under strong consistency the answer is always tea, milk: every read sees the latest acknowledged write, and a read may have to wait or fail during a partition. Under eventual consistency the answer is tea or tea, milk: any replica may answer with what it has, and replicas agree some time after writes stop. Under tunable consistency the answer depends on the request, which names how many replicas must answer. This chapter&#x27;s store is strongly consistent.">
<figcaption><b>Figure 1.2</b> The same write, the same slow copy, and what a reader is told under each of the 3 models.</figcaption>
</figure>

Under *strong consistency*, the reader receives the new value. The system behaves, as
far as any client can tell, as though there were only 1 copy of the data, and a write
that has been acknowledged is visible to every subsequent read. The precise form of
this property is called *linearizability*. Its cost is that reads and writes must
involve a leader or a majority of the copies, which makes them slower and means that
they fail when a majority cannot be reached.

Under *eventual consistency*, the reader may receive the old value. The system
promises only that, once writes cease, all copies will in time come to hold the same
value. Any copy can answer any request, which makes the system fast and keeps it
available through almost any failure, and the burden passes to the applications, which
have to cope with stale values and with conflicting ones.

*Tunable consistency* lets each request choose. With N copies, a write waits for W of
them to confirm and a read consults R of them. Whenever R + W is greater than N, the
copies consulted by any read must include at least 1 that took part in the latest
write, and the read sees that write. With 3 copies, the choice of W = 2 and R = 2
behaves strongly, and W = 1 and R = 1 is fast and only eventually consistent. The
flexibility is real, and so is its cost, which is that every caller must choose
correctly for every request.

| Model | What a read returns | What it costs | Where it is used |
|---|---|---|---|
| Strong | the latest acknowledged write | slower requests, and no service on the smaller side of a network split | money, stock levels, locks, anything guarded by a conditional write |
| Eventual | possibly an older value, for a while | applications must tolerate stale and conflicting values | counters of likes, caches, activity feeds |
| Tunable | whatever the request asked for | every caller has to choose correctly | varied workloads on 1 store |

This design chooses strong consistency, and the reason lies in the fourth use case.
"Add an item to the basket, unless somebody else has changed the basket in the
meantime" works only if the version that a client reads is the latest. If reads could
be stale, 2 web servers might each read version 1, each conclude that nobody had
changed the basket, and each write, with 1 of the 2 items lost. This is precisely the
lost update that conditional writes exist to prevent, and a conditional write over
stale reads prevents nothing. What strong consistency costs is set out in the section
on guarantees: during a split of the network, the smaller side stops answering.

## Core entities

The *core entities* are the things that the system stores, together with the things
it stores them on. Naming them at this stage, with their fields, provides a vocabulary
that the API, the protocol and the code of later chapters all share.

<figure>
<img src="figures/entities.svg?v=1c0adae2" alt="The core entities. An Entry has a key, a value and a version. A Record has a sequence, a kind that is put or delete, a key and a value, and the version of an Entry is the sequence of the Record that last wrote it. A Shard has a first and a last token, a term, a leader Node and follower Nodes. A Node has an id, an address, its tokens and a state. Ring has a version, list of Nodes and list of Shards.">
<figcaption><b>Figure 1.3</b> The core entities and their fields.</figcaption>
</figure>

| Entity | What it is | Identified by |
|---|---|---|
| Entry | the current value of a key, and its version | the key |
| Record | 1 change to a key, in the order in which the changes occurred | a sequence number |
| Node | a machine that runs the storage program | a node id |
| Shard | a range of keys, together with the 3 nodes that store it | the last position of its range |
| Ring | the assignment of ranges of keys to nodes | a version number |

The first 2 entities are 2 representations of the same data, and the distinction
between them runs through every chapter that follows. The records are a history: "set
`user-1` to `ada`", "set `user-1` to `ada lovelace`", "delete `user-2`". The entries
are the state that results from applying that history in order. Both are kept, because
they serve different purposes. Records are what is written to disk and copied to other
nodes, since a sequence of changes is easy to append to, to transmit and to compare.
Entries are what reads are answered from, since nobody wishes to replay a history in
order to learn the present value. The version of an entry is the sequence number of
the last record that changed it, which fastens every entry to a definite point in the
history.

## Capacity estimate

<div class="estimate">

<img class="builder" src="art/crab-builder.svg" alt="A crab in a hard hat, in tears.">

**Arithmetic ahead.** This estimate turns non-functional requirement 4 into a number of machines. The result is 24 storage nodes, each holding 138 GB, and nothing else from this section is needed later.

<a class="skip" href="#high-level-design">Skip to the high-level design</a>

<details>
<summary>Show the calculation</summary>

The estimate depends on 1 quantity that has to be measured and cannot be assumed: the
time a disk takes to store a write durably. Chapter 2 measures it with a program
called `synccost`. On an NVMe disk, appending a record and waiting for the disk to
confirm took 5.4 ms, so that a node which waits once for each record stores 185
records per second. Readers can run `synccost` on their own hardware and repeat the
calculation with their own figure.

**Storage.** An entry consists of a key of about 32 bytes, a value of 1024 bytes and
about 44 bytes of bookkeeping, 1100 bytes in all.

| Quantity | Calculation | Result |
|---|---|---|
| Size of 1 copy of the data | 1000000000 × 1100 bytes | 1.1 TB |
| Size of 3 copies, as non-functional requirement 0 demands | 1.1 TB × 3 | 3.3 TB |

**Writes.** Every write is stored on 3 nodes, so that 20000 writes per second become
60000 records per second across the cluster. At 185 records per second for each node,
325 nodes would be needed. The time the disk takes, however, is nearly the same for 1
record as for 20, and a node can therefore gather the records that arrive during 1
wait and store them together. Storing several records with a single wait is called
*group commit*, and it is the subject of chapter 6. With 20 records for each wait on
average, a node stores 185 × 20 = 3700 records per second.

| Quantity | Calculation | Result |
|---|---|---|
| Records to store per second | 20000 writes × 3 copies | 60000 |
| Records per node per second, with 1 wait for each record | 1 ÷ 0.0054 s | 185 |
| Records per node per second, with 20 records for each wait | 185 × 20 | 3700 |
| Nodes required | 60000 ÷ 3700 | 16.2, rounded up to 17 |
| Nodes chosen | | 24 |
| Capacity of 24 nodes | 24 × 3700 | 88800 records per second |
| Data on each node | 3.3 TB ÷ 24 | 138 GB |

We choose 24 nodes. At the required rate of writes, a cluster of that size works at
68% of its capacity, which leaves the surviving nodes room to carry the load of one
that has failed.

<figure>
<img src="figures/capacity.svg?v=17215b66" alt="The capacity estimate as bars. Storage: 1 copy of 1 billion keys at 1.1 KB each is 1.1 TB, 3 copies are 3.3 TB, and each of 24 nodes holds 138 GB. Records stored per second: 1 node that calls fsync for every record stores 185, 1 node that groups 20 records per fsync stores 3700, and 24 nodes store 88800, against a requirement of 60000, which is 20000 writes per second stored on 3 nodes each.">
<figcaption><b>Figure 1.4</b> The capacity estimate, drawn to scale. The dashed line marks the required rate.</figcaption>
</figure>

**Reads.** Reads are answered from memory and do not wait for the disk. Spread over 24
nodes, 100000 reads per second come to about 4200 for each node, far below what a node
can answer from memory. The rate of reads therefore has no influence on the number of
nodes.

</details>

</div>

## The API

Applications reach the store over HTTP. The API follows the style known as *REST*, in
which the things a service holds are presented as *resources*, each identified by a
URL, and the standard methods of HTTP are the operations upon them. Adhering to the
standard meanings of the methods and status codes has a practical reward. Every
existing HTTP client, proxy and cache already understands them, and so handles the
API correctly without knowing anything about key-value stores.

<figure>
<img src="figures/api-resources.svg?v=c4252b81" alt="The resources of the API. For one key, at /v1/keys/{key}: PUT creates or replaces the value and answers 201 or 204, GET reads the value and its version and answers 200, and DELETE removes the key and answers 204. For the collection, GET /v1/keys with prefix, after and limit returns one page of keys in order. For the node, GET /healthz says whether Node can serve.">
<figcaption><b>Figure 1.5</b> The resources of the API and the methods that each accepts.</figcaption>
</figure>

### The rules the API follows

| Rule | How it is applied here |
|---|---|
| A URL identifies a resource, and consists of nouns. | `/v1/keys/user-1` identifies the key `user-1`. The API has no URLs such as `/setKey`. |
| The HTTP method expresses the operation. | `GET` reads a resource, `PUT` replaces it and `DELETE` removes it. |
| `GET` has no side effects. | Clients and intermediaries may repeat, cache and retry a `GET` freely. |
| `PUT` and `DELETE` are idempotent. | An operation is *idempotent* if performing it several times has the same effect as performing it once, so that a client may repeat these requests after a lost response. |
| The status code reports the outcome. | `201` for a key that was created, `204` for success with nothing to return, `404` for a key that does not exist, `412` for a condition that did not hold. |
| Errors have a body that a program can read. | Error responses use the `application/problem+json` format defined in RFC 9457. |
| The version of the API is part of the path. | An incompatible future version can be served under `/v2/` beside `/v1/`. |
| Collections are returned in pages. | The `limit` parameter bounds the size of a page, and each response says how to ask for the next. |

### Reference

Each operation is specified below by its request and its possible responses.
`store.example` stands for the address of the load balancer.

**Set the value of a key**

| | |
|---|---|
| Request | `PUT /v1/keys/{key}` |
| Request headers | `Content-Type: application/octet-stream`. Optionally `If-Match: "<version>"` or `If-None-Match: *`. |
| Request body | the value: 0 to 1048576 bytes, stored exactly as sent |
| Success | `201 Created` for a new key, `204 No Content` for a value that was replaced |
| Response headers | `ETag: "<version>"`, the version of the entry after the write |
| Response body | none |
| Errors | `400`, `412`, `413`, `503` |

```http
PUT /v1/keys/user-1 HTTP/1.1
Host: store.example
Content-Type: application/octet-stream
Content-Length: 3

ada
```

```http
HTTP/1.1 201 Created
ETag: "1"
Content-Length: 0
```

**Read the value of a key**

| | |
|---|---|
| Request | `GET /v1/keys/{key}` |
| Request headers | optionally `If-None-Match: "<version>"` |
| Request body | none |
| Success | `200 OK`, or `304 Not Modified` when the entry is still at the version given in `If-None-Match` |
| Response headers | `ETag: "<version>"`, `Content-Type: application/octet-stream` |
| Response body | the value, as it was stored, and empty for `304` |
| Errors | `400`, `404`, `503` |

```http
GET /v1/keys/user-1 HTTP/1.1
Host: store.example
```

```http
HTTP/1.1 200 OK
ETag: "1"
Content-Type: application/octet-stream
Content-Length: 3

ada
```

**Delete a key**

| | |
|---|---|
| Request | `DELETE /v1/keys/{key}` |
| Request headers | optionally `If-Match: "<version>"` |
| Request body | none |
| Success | `204 No Content` |
| Response body | none |
| Errors | `400`, `404`, `412`, `503` |

```http
DELETE /v1/keys/user-2 HTTP/1.1
Host: store.example
If-Match: "3"
```

```http
HTTP/1.1 204 No Content
```

**List keys**

| | |
|---|---|
| Request | `GET /v1/keys` |
| Query parameters | `prefix`: only keys that begin with this text, empty by default. `after`: only keys that sort after this key. `limit`: the largest number of keys to return, from 1 to 1000, 100 by default. |
| Request body | none |
| Success | `200 OK` |
| Response headers | `Content-Type: application/json` |
| Response body | a JSON object with the fields below |
| Errors | `503` |

| Field of the response body | Type | Meaning |
|---|---|---|
| `keys` | array | the keys of this page, in sorted order |
| `keys[].key` | string | the key |
| `keys[].version` | number | the version of the entry |
| `keys[].size` | number | the length of the value in bytes |
| `next_after` | string or `null` | the value to pass as `after` for the next page, and `null` on the last page |

```http
GET /v1/keys?prefix=user-&limit=2 HTTP/1.1
Host: store.example
```

```http
HTTP/1.1 200 OK
Content-Type: application/json

{
  "keys": [
    { "key": "user-1", "version": 2, "size": 12 },
    { "key": "user-2", "version": 3, "size": 5 }
  ],
  "next_after": "user-2"
}
```

**Errors**

Every error response has the content type `application/problem+json` and a body with
these fields.

| Field | Type | Meaning |
|---|---|---|
| `type` | string | identifies the kind of error, and is the field a program should compare |
| `title` | string | a description of the kind of error, the same on every occurrence |
| `status` | number | the HTTP status code, repeated in the body |
| `detail` | string, optional | a description of this particular occurrence |

```http
HTTP/1.1 412 Precondition Failed
Content-Type: application/problem+json

{
  "type": "/problems/condition-failed",
  "title": "The condition on the key's version does not hold",
  "status": 412,
  "detail": "the key is at version 2"
}
```

**Health of a node**

| | |
|---|---|
| Request | `GET /healthz` |
| Success | `200 OK` |
| Response body | a JSON object: `status` (a string), `keys` (the number of keys), `last_sequence` (the sequence number of the last record) |

```http
HTTP/1.1 200 OK
Content-Type: application/json

{ "status": "ok", "keys": 2, "last_sequence": 5 }
```

The sections that follow take up the parts of this reference that embody a decision,
and show each exchange as it was actually performed by the server of chapter 2.

### Writing and reading a key

`PUT` stores the body of the request as the value of the key. Since values are opaque
bytes, the body is sent without any encoding. The first write of a key is answered
with `201 Created`. All the responses in this section were produced by the server of
chapter 2, with its `date` header removed.

```console
$ curl -i -X PUT http://127.0.0.1:7001/v1/keys/user-1 --data-binary 'ada'
HTTP/1.1 201 Created
etag: "1"
content-length: 0
```

The version of an entry is conveyed in the `etag` header. In HTTP, an *entity tag*, or
ETag, identifies 1 particular state of a resource, which is exactly what a version is.
`GET` returns the value together with its tag.

```console
$ curl -i http://127.0.0.1:7001/v1/keys/user-1
HTTP/1.1 200 OK
content-type: application/octet-stream
etag: "1"
content-length: 3

ada
```

### Conditional writes

Functional requirement 3 is directed at a problem called the *lost update*, which
arises when 2 clients read a value, each modify it independently, and each write it
back.

| Step | Web server A | Web server B | Value in the store |
|---|---|---|---|
| 1 | reads the basket: `tea` | | `tea` |
| 2 | | reads the basket: `tea` | `tea` |
| 3 | writes `tea, milk` | | `tea, milk` |
| 4 | | writes `tea, sugar` | `tea, sugar` |

Both writes succeed, and `milk` is missing from the final value. Nothing failed, and
no error was reported to anyone. The write at step 4 was computed from what B read at
step 2, which by then was no longer current, and the store, having been told only to
set the value, set it.

The remedy is to let a write state which version it was based on. HTTP provides the
`If-Match` header for this purpose: the server performs the write only if the present
version of the resource is the version named in the header.

```console
$ curl -i -X PUT http://127.0.0.1:7001/v1/keys/user-1 -H 'If-Match: "1"' --data-binary 'ada lovelace'
HTTP/1.1 204 No Content
etag: "2"
```

The key was at version 1, the condition held, and version 2 resulted. The same request
sent a second time is refused, since version 1 is no longer current.

```console
$ curl -i -X PUT http://127.0.0.1:7001/v1/keys/user-1 -H 'If-Match: "1"' --data-binary 'ada byron'
HTTP/1.1 412 Precondition Failed
content-type: application/problem+json
content-length: 144

{"type":"/problems/condition-failed","title":"The condition on the key's version does not hold","status":412,"detail":"the key is at version 2"}
```

The status `412 Precondition Failed` informs web server B that its copy is out of
date. B reads again, obtains `tea, milk` at version 2, adds the sugar, and writes with
`If-Match: "2"`. The procedure of reading, modifying and writing conditionally,
repeated until the write succeeds, is the general method by which clients of a store
cooperate without locks, and it recurs throughout the later chapters under the name of
compare-and-set.

<figure>
<img src="figures/request-annotated.svg?v=89429437" alt="A conditional write explained line by line. PUT /v1/keys/user-1 names the whole new state of the resource, so sending it twice leaves the same result. The header If-Match with version 1 makes the write happen only if the key is still at the version this client read. The answer 204 No Content means the value was replaced, and the etag header carries the new version 2. The answer 412 Precondition Failed means another client wrote first and nothing was changed.">
<figcaption><b>Figure 1.6</b> A conditional write, and the 2 responses it can receive.</figcaption>
</figure>

The header `If-None-Match: *` expresses the complementary condition, that the write
is to be performed only if the key does not exist. With it, several clients may all
attempt to create the same key, and exactly 1 succeeds.

```console
$ curl -i -X PUT http://127.0.0.1:7001/v1/keys/user-1 -H 'If-None-Match: *' --data-binary 'someone else'
HTTP/1.1 412 Precondition Failed
content-type: application/problem+json
content-length: 144

{"type":"/problems/condition-failed","title":"The condition on the key's version does not hold","status":412,"detail":"the key is at version 2"}
```

On a `GET`, `If-None-Match` with a version asks for the value only if it has changed
since that version. If it has not, the server answers `304 Not Modified` with no body,
which spares the transfer of data that the client already holds.

```console
$ curl -i http://127.0.0.1:7001/v1/keys/user-1 -H 'If-None-Match: "2"'
HTTP/1.1 304 Not Modified
etag: "2"
```

### Listing keys

`GET /v1/keys` returns the keys that begin with `prefix`, in sorted order, and no more
than `limit` of them. When more remain, the response carries `next_after`, and the
client obtains the next page by passing that value as `after`.

```console
$ curl -i 'http://127.0.0.1:7001/v1/keys?prefix=user-&limit=1'
HTTP/1.1 200 OK
content-type: application/json
content-length: 71

{"keys":[{"key":"user-1","version":2,"size":12}],"next_after":"user-1"}
```

```console
$ curl -i 'http://127.0.0.1:7001/v1/keys?prefix=user-&limit=1&after=user-1'
HTTP/1.1 200 OK
content-type: application/json
content-length: 66

{"keys":[{"key":"user-2","version":3,"size":5}],"next_after":null}
```

The position in the listing is thus expressed as the last key of the previous page.
A page number would not serve, for a reason that applies to every listing of data that may
change. If a key is inserted ahead of the reader's position between 2 requests, every
later key moves down by 1 place, and a request for "page 2" returns a key that the
reader has already received. A request for the keys after `user-1` is unaffected by
insertions and deletions elsewhere. Chapter 15 meets the same problem in a news feed
and solves it in the same way.

### Deleting a key

```console
$ curl -i -X DELETE http://127.0.0.1:7001/v1/keys/user-2
HTTP/1.1 204 No Content
```

### Errors

A failed request is answered with a status code in the 400s or the 500s and a body in
the format of RFC 9457. The `type` field identifies the category of the error and is
what a client program should test. The `title` is a fixed description of the category,
and `detail`, when present, describes the particular occurrence.

```console
$ curl -i http://127.0.0.1:7001/v1/keys/user-2
HTTP/1.1 404 Not Found
content-type: application/problem+json
content-length: 80

{"type":"/problems/key-not-found","title":"The key does not exist","status":404}
```

| Status | `type` | Condition |
|---|---|---|
| `400 Bad Request` | `/problems/invalid-key` | The key is empty, exceeds 256 characters, or contains a character outside the permitted set. |
| `400 Bad Request` | `/problems/invalid-header` | The `If-Match` or `If-None-Match` header is malformed. |
| `404 Not Found` | `/problems/key-not-found` | A `GET` or `DELETE` names a key that does not exist. |
| `405 Method Not Allowed` | | The resource does not support the method. The `allow` header lists those it does. |
| `412 Precondition Failed` | `/problems/condition-failed` | The condition in `If-Match` or `If-None-Match` does not hold. |
| `413 Payload Too Large` | | The value exceeds 1048576 bytes. |
| `503 Service Unavailable` | `/problems/store-unavailable` | The node is unable to store the write. The client should try again. |

The 2 ranges of status codes call for different behaviour on the part of the client.
A code in the 400s signifies a fault in the request, and sending the same request
again will produce the same error. A code in the 500s signifies that the server was
unable to carry out a valid request, which may well succeed if repeated.

### Retries

Suppose that a client sends a request and loses its connection before any response
arrives. It has no means of knowing whether the operation was performed. This
situation, the lost response, is the most characteristic difficulty of distributed
systems and reappears in nearly every chapter of this book. The API meets it by making
every operation idempotent, so that repeating a request is safe whichever was the
case.

| Request | Effect of repeating it |
|---|---|
| `GET` | None, since `GET` does not change the store. |
| `PUT` without a condition | The key is set to the same value again. The value is unchanged and the version increases. |
| `PUT` with `If-Match` | If the first attempt succeeded, the repetition returns `412`, and a `GET` then shows that the key holds the client's value. |
| `DELETE` | If the first attempt succeeded, the repetition returns `404`, which confirms that the key is absent. |

## The protocol between nodes

The API described so far serves applications. The storage nodes also communicate with
one another. A node sends the records it has written to the nodes that hold the other
copies, and every node obtains the current ring from the coordinator. This internal
traffic has different needs from a public API and uses a protocol of its own.

| | Public API | Internal protocol |
|---|---|---|
| Who calls it | programs in any language, and people with tools such as `curl` | only the store's own programs |
| What matters most | readability, compatibility with HTTP infrastructure, stability over years | compact encoding, low cost of processing, strict types |
| Format | HTTP with JSON and raw bytes | Protocol Buffers over gRPC |

*Protocol Buffers* is a format in which the types of messages are declared in a
schema file and encoded in a compact binary form. *gRPC* is a protocol for remote
procedure calls that carries such messages over HTTP/2. The schema file is the
specification of the internal protocol, and it is written before any implementation.

The `Record` message corresponds to the Record entity.

<p class="listing"><img class="mascot" src="art/crab-happy.svg" alt=""><b>Listing 1.1</b> The Record message. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/distributed-systems-from-the-ground-up/code/proto/store.proto">proto/store.proto</a></p>

```protobuf
{{#include ../code/proto/store.proto:record}}
```


Every field of a message has a number, and it is by the number that the
binary encoding identifies the field. Names occur only in the schema. This
arrangement is what allows nodes running different versions of the software to
communicate, which they must do whenever a cluster is upgraded 1 node after another
without stopping. A newer version may add a field under a number not previously used.
An older node disregards numbers it does not recognise, and a newer node supplies a
default value where a field is missing. The single rule that makes this work is that
a field number, once used, keeps its meaning for ever.

A leader sends records to its followers by means of the `Append` call. The terms
*leader*, *follower* and *term* are defined in the section on replication.

<p class="listing"><img class="mascot" src="art/crab-happy.svg" alt=""><b>Listing 1.2</b> The replication service. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/distributed-systems-from-the-ground-up/code/proto/store.proto">proto/store.proto</a></p>

```protobuf
{{#include ../code/proto/store.proto:replication}}
```


The field `previous_sequence` is what keeps a follower's log identical to its
leader's. A follower appends the records it is sent only if its own log at present
ends at `previous_sequence`. If it does not, the follower answers `appended = false`
together with the actual last sequence number of its log, and the leader sends again
from that point. No follower's log can therefore contain a gap or hold records in a
different order from the leader's.

The coordinator stores the ring as a `Ring` message.

<p class="listing"><img class="mascot" src="art/crab-happy.svg" alt=""><b>Listing 1.3</b> The ring, as the coordinator stores it. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/distributed-systems-from-the-ground-up/code/proto/store.proto">proto/store.proto</a></p>

```protobuf
{{#include ../code/proto/store.proto:ring}}
```


Routers and storage nodes read the ring when they start and thereafter *watch* it. A
watch is a request that the coordinator holds open and answers whenever the stored
value changes, so that every component learns of a new version of the ring within
milliseconds and none of them has to ask repeatedly.

## High-level design

The high-level design names the components of the system, states the role of each,
and traces the path of a request through them. Figure 1.7 shows the
whole. The numbers in the figure are the steps of a write, and they appear again in
its legend and in the text below.

<figure class="wide">
<img src="figures/system-overview.svg?v=2e207001" alt="The high-level design of the key-value store, drawn from left to right, with the path of a write numbered. Applications send requests to a load balancer, which passes each request to 1 of 3 routers. The routers have no data of their own. They hold a copy of the ring, which the coordinator, drawn above them, sends them. On the right are 24 storage nodes. For the key user-1, node-10 is the leader and node-1 and node-6 are the followers, and each has a log on disk. A monitoring system, drawn below the routers, reads the health and the metrics of every node. Step 0: routers hold a copy of the ring, sent by the coordinator. Step 1: an application sends PUT /v1/keys/user-1. Step 2: the load balancer passes it to a healthy router. Step 3: the router hashes the key and finds the leader, node-10. Step 4: node-10 stores the record in its log, on disk. Step 5: node-10 sends the record to node-1 and node-6. Step 6: when 1 of them has stored it, node-10 answers 201 Created. Step 7: the answer returns the way the request came.">
<figcaption><b>Figure 1.7</b> The complete system and the path of a write. The steps are numbered from 0 to 7.</figcaption>
</figure>

| Component | Role | State it holds | When 1 instance fails |
|---|---|---|---|
| Load balancer | accepts connections from clients and passes each to a healthy router | none | a standby takes over the service address |
| Router | finds the node responsible for a key and forwards the request to it | a copy of the ring | the load balancer stops using it |
| Storage node | stores the replicas of the shards assigned to it | a log on disk, and the entries in memory | the shards it led elect new leaders |
| Coordinator | stores the ring and the present leader of every shard | the ring | the remaining 2 of its 3 machines continue to serve |
| Monitoring | reads the health and the metrics of every node | time series | requests are unaffected, and alerts are unavailable |

The *coordinator* is a small replicated store for configuration. It runs on 3
machines, keeps a complete copy of its data on each, and remains available as long as
a majority of them is running. It may seem odd that a key-value store should depend
on a second, smaller store, and the reason is a circularity that cannot otherwise be
escaped. The ring is what tells every component where a key is to be found, and the
store cannot keep the ring within itself, since the ring would be needed in order to
find it. The ring is therefore kept in a separate system at a fixed address that
every component knows. Chapter 4 shows how a group of 3 machines agrees on a value,
which is what the coordinator does.

A write to the key `user-1` passes through the following steps.

0. Before any request arrives, every router holds a copy of the ring, and the coordinator informs the routers of every change to it.
1. An application sends `PUT /v1/keys/user-1` to the load balancer.
2. The load balancer forwards the request to a router that passed its most recent health check.
3. The router hashes `user-1`, looks up the resulting position in its copy of the ring, finds that the leader of the shard is `node-10`, and forwards the request there.
4. `node-10` appends a record to its log and waits for its disk to confirm.
5. `node-10` sends the record to both followers, `node-1` and `node-6`.
6. As soon as 1 follower has confirmed, `node-10` applies the record and answers `201 Created`.
7. The response returns to the application by way of the router and the load balancer.

A read follows steps 1 to 3 and is then answered by `node-10` from memory, with steps
4 to 6 omitted.

2 features of this arrangement deserve to be drawn out, since they are deliberate.

The routers are stateless. A component without state can be run in any number of
instances, added and removed at will, and replaced after a failure without any
procedure of recovery. The design confines all lasting state to the storage nodes and
the coordinator, so that those are the only components which require replication and
the careful treatment of failure that occupies the rest of this chapter.

And, as step 0 indicates, the coordinator takes no part in the handling of requests.
If it becomes unreachable, reads and writes continue undisturbed on the copies of the
ring that the routers already hold. Only changes to the ring are suspended: a change
of leader cannot be recorded and a node cannot be added until the coordinator
returns. A component that every request had to consult would be both a bottleneck and
a single point of failure, and keeping the coordinator off the path of requests avoids
both.

## Sharding

*Sharding* is the division of the data into parts that are stored on different nodes,
each part being a *shard*. With sharding, the total volume of data can exceed the
capacity of any 1 node, and the load of requests is distributed among all of them. The
central question is by what function a key is assigned to a node, and the obvious
answer turns out to have a serious flaw.

### Hashing modulo the number of nodes

The obvious method hashes the key and takes the remainder on division by the number
of nodes, `node = hash(key) mod N`. Provided that the hash function distributes its
output evenly, every node receives an equal share of the keys, and any component that
knows N can locate any key by a single calculation.

The flaw appears when N changes. A key stays where it is only if its hash leaves the
same remainder under the old number of nodes and the new. The following table shows,
for a few hash values, what happens when N increases from 4 to 5.

| `hash(key)` | `mod 4` | `mod 5` | Does the key move |
|---|---|---|---|
| 0 | 0 | 0 | no |
| 1 | 1 | 1 | no |
| 4 | 0 | 4 | yes |
| 5 | 1 | 0 | yes |
| 9 | 1 | 4 | yes |
| 10 | 2 | 0 | yes |

Of any 20 consecutive hash values, only 4 leave the same remainder modulo 4 and
modulo 5. The addition of a fifth node therefore relocates 80% of all keys, although
the new node has need of only 20% of them, and the other 60% merely change places
among the existing nodes to nobody's advantage. During such a relocation the cluster
expends a large part of its capacity on copying data, at exactly the time when a node
was added because capacity was short.

### Consistent hashing

*Consistent hashing* is a method of assignment under which a change in the set of
nodes relocates only the keys that have to move. The range of the hash function is
regarded as a circle, called the *ring*, on which the largest value is followed by the
smallest. Every node is given a position on the ring, called its *token*. A key is
hashed to a position by the same function, and it belongs to the node whose token is
the first at or after that position, proceeding clockwise.

<figure>
<img src="figures/ring.svg?v=d49cc6f6" alt="A hash ring with positions 0 to 99. Node A has the token 12, B has 37, C has 62 and D has 87. Step 1: hash the key, and user-1 lands on position 20. Step 2: walk clockwise from 20 to the next token. Step 3: the next token is 37, which belongs to B, so B owns the key. Step 4: the next 2 different nodes, C and D, hold the other copies. B owns Every position from 13 to 37, because 12 is token before it.">
<figcaption><b>Figure 1.8</b> A ring of 100 positions with 4 nodes. The key at position 20 belongs to node B.</figcaption>
</figure>

In figure 1.8 the ring has only 100 positions, to keep the arithmetic easy. Node B
has the token 37, and the token before it is 12, so that B owns the positions 13 to
37. A key that hashes to position 20 belongs to B. A key that hashes to 90 lies beyond
the last token, passes the end of the range, continues from 0, and belongs to A at
position 12.

The gain of the method is seen when a node is added.

<figure>
<img src="figures/ring-add.svg?v=d2443ae3" alt="The same ring after node E joins with the token 50. Before, positions 38 to 62 belonged to C. E takes positions 38 to 50. 13 of the 100 positions change owner, all of them from C to E, and the keys on A, B and D and the keys at 51 to 62 on C stay in place. With hash mod N, going from 4 to 5 nodes moves 80 of 100.">
<figcaption><b>Figure 1.9</b> Node E joins the ring. Only the positions 38 to 50 change their owner.</figcaption>
</figure>

Node E is given the token 50, which lies between the token of B and that of C. E takes
over the positions 38 to 50, which formerly belonged to C, and every other position
keeps its owner. The addition has relocated 13% of the positions, and every relocated
key has gone to E. The removal of a node has the reverse effect: its positions pass to
its clockwise neighbour, and no other key is touched.

| | `hash mod N` | Consistent hashing |
|---|---|---|
| Keys relocated when a node is added to N nodes | about N ÷ (N + 1) of all keys | about 1 ÷ (N + 1) of all keys |
| Where the relocated keys go | to every node | to the new node only |
| What is needed in order to locate a key | the number of nodes | the tokens of all the nodes |

The last row is the price. Under the first method a component needs to know 1 number,
and under the second it needs the whole ring. How every component comes to have the
ring, and what happens when its copy is out of date, is taken up below.

### Virtual nodes

With a single token for each node, the size of a node's range depends on where its own
token and its predecessor's happen to fall, and the ranges can differ enormously.
Furthermore, when a node is removed its entire range passes to 1 neighbour, which then
carries a double load.

Both defects are removed by giving every node many tokens. The tokens of a node are
called its *virtual nodes*. Each node then owns many small ranges scattered around the
ring. Its total share is the sum of many random range sizes, which varies far less
than any single one of them, and the ranges of a removed node pass to many different
neighbours.

The program `ringsim` measures the effect. It places 100000 keys on a ring of 24
nodes, with 1, 8, 64 and 256 tokens for each node, and reports the smallest and the
largest share of keys held by any node. It then adds a node and counts the keys whose
owner has changed.

```console
$ cargo run --release -p ringsim
100000 keys on 24 nodes, ideal share 4.17%
     1 tokens per node: smallest share  0.16%, largest share 11.26%
     8 tokens per node: smallest share  1.42%, largest share  7.83%
    64 tokens per node: smallest share  3.35%, largest share  5.07%
   256 tokens per node: smallest share  3.86%, largest share  4.73%
adding node 25 to a ring with 256 tokens per node, ideal movement 4.00%
  on the ring: 4332 keys changed owner (4.33%), 4332 of them to the new node
  hash mod N : 96001 keys changed owner (96.00%)
replicas of user-1: node-10, node-1, node-6
position of user-1: 0x7c7615c11438e5c9
```

<figure>
<img src="figures/ring-spread.svg?v=be915fbb" alt="The share of 100000 keys held by the emptiest and the fullest of 24 nodes, for 4 numbers of tokens per node, against an ideal share of 4.17 percent. With 1 token per node the shares run from 0.16 to 11.26 percent. With 8 tokens, from 1.42 to 7.83. With 64 tokens, from 3.35 to 5.07. With 256 tokens, from 3.86 to 4.73.">
<figcaption><b>Figure 1.10</b> The range of shares across 24 nodes, for each number of tokens.</figcaption>
</figure>

| Output | What it shows |
|---|---|
| 1 token: shares from 0.16% to 11.26% | With 1 token for each node, the most heavily loaded node holds 70 times as many keys as the least. |
| 256 tokens: shares from 3.86% to 4.73% | With 256 tokens, every node is within 14% of the ideal share of 4.17%. |
| 4332 keys changed owner, all to the new node | Adding a 25th node relocated 4.33% of the keys, close to the ideal of 4.00%, and no key moved between existing nodes. |
| `hash mod N`: 96001 keys changed owner | The same change relocates 96% of the keys when the node is chosen by remainder. |

We use 256 tokens for each node. With 24 nodes, the ring contains 6144 tokens, and
each range between adjacent tokens holds about 180 MB on average. A larger number of
tokens would improve the balance further, at the cost of a larger ring to store and
to distribute.

The ring uses a 64-bit hash function, xxHash3, for tokens and keys alike. The token of
a virtual node is the hash of the name of its node followed by a number, as in
`node-7#12`. Since the tokens are derived from the names, every router and node that
knows the names of all the nodes computes an identical ring, and no table of tokens
has to be transmitted.

The tokens are kept in a sorted map. To find the owner of a key, a lookup takes the
tokens from the key's position to the end of the map, followed by those from its
beginning, which is clockwise order on the ring. The cost is logarithmic in the number
of tokens.

### Shards on the ring

Each range between adjacent tokens is a shard. The replicas of a shard are placed on
the first 3 distinct nodes encountered going clockwise from its range. The node that
owns the range is the preferred leader of the shard, and the other 2 are its
followers. For the key `user-1`, `ringsim` reports `node-10`, `node-1` and `node-6`,
and these 3 nodes serve as the example in every chapter that follows.

The word "distinct" matters. Consecutive tokens on the ring may belong to the same
physical node, since each node has 256 of them, and 2 replicas placed on 1 machine
would give no protection against the loss of that machine. Tokens of a node already
chosen are therefore passed over.

### The ring in a running system

The ring has so far been described as a data structure. It remains to describe how the
components of a running cluster obtain it, use it and change it, and it is here that
most of the practical difficulty lies.

**Where the ring is kept.** There is a single authoritative copy, the `Ring` message
held by the coordinator. It contains the name, address and tokens of every node, and
the present leader of every shard. Every change increases its version number by 1.
Routers and storage nodes hold a copy in memory and keep it current by means of a
watch.

**How a request is routed.** Routing requires no communication with the coordinator or
with other routers. A router hashes the key and performs a binary search in its sorted
list of tokens, which with 6144 tokens takes 13 comparisons.

<figure>
<img src="figures/ring-route.svg?v=3a871bdd" alt="How the ring is used for a request, in 8 steps numbered from 0. Step 0: the coordinator holds the ring at version 7, with the tokens of every node and the leader of each shard. Step 1: each router keeps a copy and watches the coordinator, which sends version 8 as soon as it exists. Step 2: a request arrives and the router hashes the key. Step 3: it searches its sorted tokens for the next one, a binary search of 13 steps over 6144 tokens. Step 4: it sends the request to that shard&#x27;s leader with the ring version it used. Step 5: the node compares versions and serves the request if they are the same. Step 6: if the router&#x27;s ring is old, the node refuses and answers that the ring is at version 8. Step 7: the router fetches version 8 and sends again, and the client sees 1 slower request and no error.">
<figcaption><b>Figure 1.11</b> The use of the ring for a request, including the case of a ring that is out of date.</figcaption>
</figure>

**What happens when a ring is out of date.** A router may forward a request an instant
before a new version of the ring reaches it, and the request then arrives at a node
that is no longer responsible for the key. If that node were to answer, it might
return a stale value or accept a write that belongs elsewhere, and strong consistency
would be lost through nothing more than a delayed notification. Routers therefore
attach the version of their ring to every forwarded request, in a `Ring-Version`
header. A node that holds a newer ring and is not responsible for the key refuses the
request with the status `421 Misdirected Request`, which HTTP defines for a request
sent to a server that cannot answer for the resource. On receiving it, the router
waits for the newer ring and forwards again, and the client observes nothing but a
slightly slower response. The principle, that a component acting on possibly stale
information should declare which version it is acting on so that the recipient can
check, reappears in this book wherever stale knowledge is dangerous.

**How a node joins.** A new node cannot assume ownership of its ranges at once, since
it does not yet hold their data. Ownership is therefore transferred range by range,
each after its data has been copied.

<figure>
<img src="figures/ring-join.svg?v=10f34d21" alt="How a node joins the ring, in 7 steps. Step 1: the operator starts node-25 and gives it the address of the coordinator. Step 2: node-25 registers in the coordinator as joining, with 256 tokens computed from its name. Step 3: the coordinator publishes ring version 8, in which node-25 owns no keys yet. Step 4: each current owner copies 1 range to node-25 and still serves the range meanwhile. Step 5: node-25 confirms that a range is complete. Step 6: the coordinator moves that range to node-25 in version 9, and routers send its keys to node-25 from now on. Step 7: the old owner deletes its copy of the range, and steps 3 to 6 repeat for every range.">
<figcaption><b>Figure 1.12</b> The procedure by which a node joins a running cluster.</figcaption>
</figure>

**How a node leaves.** When an operator removes a node, the procedure runs in reverse.
The departing node copies each of its ranges to the node that will own it, and the
coordinator reassigns a range when its copy is complete. When a node fails without
warning, there is no opportunity to copy. Its ranges are still held by the other 2
replicas of each shard, the shards it led elect new leaders, and a replacement node is
supplied with the data by the surviving replicas.

**Gossip as an alternative.** Some systems distribute the ring without any
coordinator. Each node holds a copy, and the nodes exchange their copies in pairs,
each repeatedly choosing another at random and comparing versions, so that a change
spreads through the cluster as a rumour does through a crowd.

<figure>
<img src="figures/gossip.svg?v=787c5563" alt="How a gossip protocol spreads a new ring among 8 nodes without a coordinator. At the start, 1 node has ring version 8 and 7 have version 7. After round 1, 2 nodes have version 8. After round 2, 4 nodes. After round 3, all 8. Once per second, every node picks another node at random and the 2 compare ring versions, and the one with the older ring takes the newer. The number of nodes that know doubles each round, so 24 nodes need about 5 rounds and 1000 nodes about 10.">
<figcaption><b>Figure 1.13</b> The spread of a new version of the ring among 8 nodes by gossip.</figcaption>
</figure>

A *gossip protocol* removes the dependence on a coordinator and scales to very large
clusters, since no node has to communicate with more than a few others. Its
disadvantage is that for some seconds after a change, different nodes hold different
versions of the ring and may direct the same key to different nodes. Designs founded
on gossip have to tolerate such disagreement, and accordingly tend to be those that
offer eventual consistency. We use a coordinator, since a single authoritative ring is
far easier to reason about when strong consistency is the aim, and a cluster of 24
nodes has no need of the scalability of gossip.

### The cost of sharding

An operation on a single key involves a single shard. An operation on many keys may
involve many. Listing keys by prefix, functional requirement 4, is of the second kind,
because hashing deliberately destroys the order of keys: keys with a common prefix
hash to unrelated positions and are scattered over all the nodes. A router has to send
such a request to every node and merge their sorted results, so that a listing takes
time proportional to the number of nodes.

This is the general price of hashing, and systems whose work consists largely of
range queries choose differently. They divide the key space into contiguous ranges of
keys, without hashing, so that neighbouring keys remain on the same node and a range
query touches few nodes. In exchange they must actively move the boundaries of the
ranges in order to keep the load even, since nothing in an unhashed key space
guarantees that keys are evenly spread.

## Replication

*Replication* is the keeping of copies of the same data on several nodes, each copy
being a *replica*. Non-functional requirement 0 lays down that an acknowledged write
survives the loss of any 1 machine, from which it follows that a write must be stored
on at least 2 machines before it is acknowledged.

### Replication with a leader

If every replica accepted writes independently, 2 clients might write different
values for the same key to 2 replicas at the same moment, and the replicas would then
hold conflicting data, to be reconciled afterwards by some rule that is bound to
discard one client's work. This design avoids such conflicts by appointing 1 replica
of every shard as its *leader*. All writes to the shard go to the leader, which
assigns each the next sequence number, so that the writes have a single agreed order,
and sends the resulting record to the other replicas, the *followers*. A follower
applies the records in the order of their sequence numbers and thereby arrives at the
leader's state.

### Acknowledgement by a majority

The leader acknowledges a write as soon as its record is stored in 2 of the 3 logs,
its own and that of 1 follower. It does not wait for the second follower.

<figure>
<img src="figures/replicated-write.svg?v=f374131d" alt="A write to a shard of 3 replicas. The leader on node-10 and the follower on node-1 hold records 41 and 42, and the slow follower on node-6 holds only record 41. Step 1: the leader appends record 42 to its log and waits for its disk. Step 2: it sends the record to both followers in parallel. Step 3: node-1 appends it, waits for its disk and answers. Step 4: 2 of 3 logs hold the record, so it is committed, and the leader applies it and answers the client. Step 5: node-6 receives it later.">
<figcaption><b>Figure 1.14</b> Record 42 is acknowledged although 1 follower has not yet received it.</figcaption>
</figure>

The rule has 2 consequences, both of them wanted. The record is on 2 machines at the
moment the client receives its acknowledgement, as non-functional requirement 0
demands. And the response time of a write is governed by the faster of the 2
followers, so that a follower which is slow, restarting or unreachable delays
nothing, which is what keeps the p99 latency within the bound of non-functional
requirement 3.

Any set containing more than half of the replicas is called a *majority*. With 3
replicas, a majority consists of 2. The whole importance of majorities derives from a
single property: any 2 majorities of the same shard have at least 1 node in common.

<figure>
<img src="figures/majority.svg?v=54418d41" alt="Why a majority is enough. Record 42 was written to node-10 and node-1 while node-6 was slow and its log ends at record 41, and the write was acknowledged. Then node-10 is lost, and node-1 still has the record. node-1 and node-6 elect a leader, and node-1 has the longer log, so it becomes the leader. A write needs 2 of 3 nodes and an election needs 2 of 3 nodes, and 2 groups of 2 out of 3 always share a node, so every election includes a node that holds every acknowledged record.">
<figcaption><b>Figure 1.15</b> The node common to both majorities holds the acknowledged record.</figcaption>
</figure>

To see what this property accomplishes, consider what happens when the leader of a
shard fails. Its followers elect a new leader, and a candidate requires the votes of a
majority. The majority that stored record 42 and the majority that elects the new
leader share at least 1 node, and that node holds record 42. By the rule of the
election, a node votes only for a candidate whose log is at least as complete as its
own. The node holding record 42 therefore refuses its vote to any candidate that
lacks it, and such a candidate cannot assemble a majority. Every newly elected leader
consequently holds every acknowledged record, and no acknowledged write is lost in a
change of leader. Chapter 4 implements this argument and tests it.

| Replicas | Majority | Failures tolerated | Storage required |
|---|---|---|---|
| 1 | 1 | 0 | 1× |
| 2 | 2 | 0 | 2× |
| 3 | 2 | 1 | 3× |
| 4 | 3 | 1 | 4× |
| 5 | 3 | 2 | 5× |

The table shows that an even number of replicas tolerates no more failures than the
odd number below it, while costing more. We therefore use 3 replicas. A deployment
that must survive 2 simultaneous failures uses 5.

### Asynchronous replication

In *asynchronous replication*, the leader acknowledges a write as soon as its own log
holds the record and sends it to the followers afterwards. Writes are faster, since
they wait for 1 disk and for no network round trip. But if the leader's machine is
lost immediately after an acknowledgement, no other machine has the record, and a
write that was acknowledged is gone. Asynchronous replication is therefore
incompatible with non-functional requirement 0, and this design uses acknowledgement
by a majority. Later chapters adopt the asynchronous form where its risk is
acceptable, as in the cache of chapter 9, and reject it where it is not, as in the
lock service of chapter 10.

## Failure handling

A distributed system is defined as much by what it does when its parts fail as by what
it does when they work. This section takes each kind of failure in turn and states how
it is detected, what clients observe, and how the system recovers.

### Failure of a leader

A leader sends an `Append` call to each of its followers every 100 ms. When there are
no new records, the call is empty and is known as a *heartbeat*, a periodic message
whose arrival shows that its sender is running. A follower that receives no `Append`
for 1 second concludes that its leader has failed.

<figure>
<img src="figures/failover.svg?v=40bdf1a6" alt="What happens when a leader fails, in 6 steps. Step 1: node-10, a leader, stops, and its followers stop receiving heartbeats. Step 2: after 1 second, node-1 stands for election and raises the term from 4 to 5. Step 3: node-6 votes for node-1, because its own log is no longer than node-1&#x27;s. Step 4: the coordinator records the new leader, term 5, leader node-1, as a new ring version. Step 5: routers receive the new ring, and writes to the shard succeed again. Step 6: node-10 returns and becomes a follower, because term 5 is newer than its own term 4.">
<figcaption><b>Figure 1.16</b> The election of a new leader after the failure of `node-10`.</figcaption>
</figure>

Every election opens a new *term*, identified by a number that increases by 1. Terms
are how nodes tell the present leader from a former one. In figure 1.16,
`node-10` still regards itself as the leader of term 4 when it returns. The first
message it receives carries term 5. Since that is higher than its own, `node-10` gives
up its leadership and continues as a follower. Every `Append` call carries the term of
its sender so that the receiver can make this comparison, and a returning leader that
has been superseded is thereby prevented from doing any harm.

### Network partition

A *network partition* is a failure of the network that divides the nodes into groups
which cannot communicate with each other, while every node continues to run. Seen from
inside one group, a partition is indistinguishable from the failure of all the nodes
in the other, and no node can discover which has occurred.

<figure>
<img src="figures/partition.svg?v=9ae933c8" alt="A network partition splits a shard. On one side is node-10 alone, the leader of term 4. On the other side are nodes 1 and 11. A write that reaches node-10 is in 1 log, is never committed, and the client gets an error. The side with 2 nodes elects node-1 as leader of term 5 and commits writes. At most 1 side can hold 2 of 3 nodes, so at most 1 side accepts writes, and the side with 1 node refuses writes: it gives up availability to keep the data consistent.">
<figcaption><b>Figure 1.17</b> During a partition, only the group that contains a majority accepts writes.</figcaption>
</figure>

In figure 1.17, `node-10` is isolated and still regards itself as the leader.
It accepts a write and appends a record to its own log, but it cannot send the record
to a follower. Since no majority holds the record, `node-10` does not acknowledge, and
its client receives an error. Meanwhile 2 of the 3 replicas are in the other group,
which elects a new leader and continues to process writes.

The rule of the majority thus resolves, without any further mechanism, the danger that
a partition presents, namely 2 leaders each accepting writes that the other knows
nothing of. At most 1 group can contain a majority of a shard's replicas, so at most 1
leader can acknowledge writes, and no node is required to determine why it has lost
contact with the others.

### Summary of failures

| Failure | How it is detected | What clients observe | Recovery |
|---|---|---|---|
| The process of a storage node stops | `Append` calls to or from the node go unanswered | nothing for the shards it follows, and an election for the shards it leads | The process restarts, rebuilds its state from its log, and receives the records it missed. |
| A leader fails | its followers receive no heartbeat for 1 second | writes to the shard fail for a few seconds, and other shards are unaffected | The followers elect a new leader. |
| A follower fails | the leader's `Append` calls go unanswered | nothing, since 2 of 3 replicas remain | The follower returns and receives the missing records from the leader. |
| A disk is lost | the node cannot start, or cannot write | the same as for a stopped node | The operator replaces the node, and the leaders copy the affected shards to it. |
| The network is partitioned | each group ceases to receive messages from the other | requests to the majority group succeed, and requests to the minority group fail | When the partition ends, the nodes of the minority group continue as followers. |
| A router fails | the load balancer's health check fails | open connections to it are broken, and retried requests reach another router | A new router is started and obtains the ring. |
| The coordinator is unreachable | routers and nodes cannot connect to it | nothing, unless a leader fails during the outage | The coordinator runs on 3 machines and needs 2 of them. |
| 2 of the 3 replicas of a shard are lost | no majority can be formed | the shard is unavailable | A replica is restored from the surviving node. |

The last row marks the limit of the design. With 3 replicas, the store tolerates the
loss of any 1 machine and remains consistent under any partition of the network. A
shard that has lost a majority of its replicas is unavailable, and has to be so, since
the single surviving replica cannot know whether it holds every acknowledged write.

## Guarantees and trade-offs

During a network partition, a distributed store cannot offer both consistency and
availability. It must either refuse some requests in order to keep all its answers
consistent, or accept all requests and allow the 2 groups to diverge. This result is
known as the *CAP theorem*, and it is less a theorem to be proved than an observation
that follows directly from the previous section: a node that cannot reach the others
must choose between answering from what it has, which may be out of date, and
declining to answer. This design gives priority to consistency.

| Property | Provided | By what means, or why not |
|---|---|---|
| An acknowledged write survives the loss of 1 machine (non-functional requirement 0) | yes | The record is in 2 of 3 logs before it is acknowledged. |
| A read returns the latest acknowledged write (non-functional requirement 2) | yes | Reads are served by the leader, and a leader that cannot reach a majority stops serving. |
| Requests succeed while 1 machine is down (non-functional requirement 1) | yes, after an election lasting a few seconds | A new leader is elected by a majority. |
| Requests succeed in the minority group of a partition | no | The minority group cannot store a record on a majority. |
| A write completes without a network round trip | no | Acknowledgement by a majority is required for non-functional requirement 0. |
| Listing by prefix costs the same as a read | no | Hashing distributes adjacent keys over all the nodes. |

The availability allowed by non-functional requirement 1 can be related to elections
by a short calculation. An allowance of 21.6 minutes a month is 1296 seconds. If an
election takes 5 seconds and the failed node led 1/24 of all the shards, the election
causes 1/24 of all writes to fail for 5 seconds and consumes about 0.2 seconds of the
allowance. Several thousand such failures a month would be within it. In practice,
therefore, the requirement is not threatened by the failures of individual machines,
which this design absorbs, and is limited by events that affect many nodes together,
such as a faulty release of the software or the loss of a segment of the network.

## Mistakes to avoid

| Mistake | What goes wrong | What to do |
|---|---|---|
| Assigning keys by `hash mod N` | Adding 1 node moves nearly every key. | Use consistent hashing, so that only the new node's share moves. |
| 1 token for each node | Shares differ by a factor of 70, and a removed node doubles 1 neighbour's load. | Give each node many tokens. |
| Placing a shard's replicas on the next 3 tokens | 2 replicas can land on the same machine. | Take the next 3 distinct nodes. |
| Answering a request with an outdated ring | A node that no longer owns a key serves stale data or accepts a misplaced write. | Send the ring's version with each request, and refuse with `421` when it is behind. |
| Acknowledging before a second copy exists | The loss of the leader loses an acknowledged write. | Acknowledge only when a majority holds the record. |
| Waiting for every replica | 1 slow or failed follower delays or blocks every write. | Wait for a majority only. |
| An even number of replicas | More storage, and no additional failure tolerated. | Use 3 or 5. |
| Letting any node with data answer reads | A follower that is behind returns an old value. | Serve reads from the leader, which must be able to reach a majority. |
| Putting the coordinator on the path of requests | Every request depends on it, and its outage stops the store. | Let routers hold copies of the ring, and consult the coordinator for changes only. |
| Writing without a condition after reading | 2 clients overwrite each other's changes. | Send `If-Match` with the version that was read. |
| Paging by page number | Insertions shift the pages, and keys are repeated or skipped. | Page by the last key received. |
| Reusing a field number in the protocol | Old and new nodes interpret the same bytes differently. | Keep the meaning of every number for ever. |

## A first look at the low-level design

Every guarantee stated above rests on an assumption that has so far been taken for
granted: that a record which a node has reported as stored is still in that node's
log after the node has crashed and restarted. If a node could lose such a record, a
record counted as stored on 2 of 3 nodes might in truth be stored on 1, and the whole
argument from majorities would be without foundation. A storage node justifies the
assumption by observing 2 rules.

1. Every change is appended to a log on disk, and the node waits for the disk to confirm, before the change is applied in memory and before any response is sent.
2. On starting, a node rebuilds its state in memory by reading its log from beginning to end.

Chapter 2 implements a storage node on these 2 rules: a format for records on disk, a
log with its procedure of recovery, and an HTTP server that provides the API of this
chapter. It includes a simulation that cuts a log short at every possible byte and
verifies that recovery returns exactly the records that were complete. The entities
of this chapter appear in its code under the same names.

## The simulation of the ring

<div class="simulation">

**Simulation in the repository.** The program [`code/ringsim`](https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/distributed-systems-from-the-ground-up/code/ringsim/src/main.rs) simulates this design. To run it, clone the repository and type `cargo run --release -p ringsim` in the `code` directory.

</div>

## Terms introduced in this chapter

| Term | Meaning |
|---|---|
| Key-value store | a database that stores a value under a key and returns it on request |
| Stateless | holding no data whose loss would matter |
| Acknowledged | confirmed to the client by a successful response |
| Durability | the property that acknowledged data is not lost |
| Availability | the property that requests are answered |
| Strong consistency, linearizability | every read returns the latest acknowledged write |
| Eventual consistency | all copies come to agree once writes cease |
| Tunable consistency | each request chooses how many copies must take part |
| Entry | the current value of a key, with its version |
| Record | 1 change to a key, with a sequence number |
| Idempotent | having the same effect whether performed once or several times |
| Lost update | a change overwritten by a write that was based on an older value |
| Conditional write, compare-and-set | a write performed only if the version is the one expected |
| Sharding | dividing the data among nodes |
| Shard | 1 part of the data, here a range of the ring |
| Consistent hashing | assigning keys to nodes so that a change of nodes moves few keys |
| Ring | the hash range regarded as a circle, with the nodes' tokens on it |
| Token, virtual node | a position on the ring that belongs to a node |
| Coordinator | a small replicated store that holds the ring |
| Watch | a request that is answered when a stored value changes |
| Gossip protocol | spreading information by repeated exchanges between pairs of nodes |
| Replication | keeping copies of the data on several nodes |
| Leader, follower | the replica that orders writes, and a replica that copies it |
| Majority | more than half of the replicas |
| Heartbeat | a periodic message showing that its sender is running |
| Term | the number of an election, by which a current leader is told from a former one |
| Network partition | a failure that divides the nodes into groups that cannot communicate |
| CAP theorem | during a partition, a store cannot be both consistent and available |

<div class="summary">

## Summary

- The non-functional requirements determine the architecture: durability under the loss of a machine demands replication, the volume of data demands sharding, and the availability target limits how long an election may take.
- Strong consistency is chosen because conditional writes are meaningless over stale reads, and its price is that the minority side of a partition stops answering.
- The capacity estimate starts from a measured disk latency of 5.4 ms, which gives 185 records per second for a node that waits for each record and 3700 with group commit, and arrives at 24 nodes.
- The API uses the standard meanings of HTTP methods and status codes, every operation is idempotent, and `If-Match` prevents lost updates.
- Nodes communicate in Protocol Buffers, whose numbered fields allow different versions of the software to work together.
- Consistent hashing places nodes and keys on a ring: adding a node to 24 relocated 4.33% of the keys in the measurement, against 96% for `hash mod N`.
- With 256 tokens for each node, every node's measured share lay between 3.86% and 4.73%, against an ideal of 4.17%.
- Routers hold copies of the ring and send its version with every request, so that a node can refuse a request based on an outdated ring.
- Each shard has a leader that orders writes and 2 followers, and a write is acknowledged when 2 of the 3 logs hold its record.
- Any 2 majorities share a node, from which it follows that a new leader holds every acknowledged record and that at most 1 group in a partition accepts writes.

</div>
