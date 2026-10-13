<img class="plate" src="art/ch25.svg?v=56b4d2df" alt="A beaver stands beside a sign that reads: based on version 3, now version 4.">

# File Sync: System Design

A file synchronisation service keeps the same folder on several devices. A person
saves a document on a laptop, and a few seconds later the same document, with the
same changes, is on their phone and their desktop computer, without anything having
been copied by hand. If a device is switched off or out of reach at the time, it
receives the changes when it next connects. From the user's side the service is
nearly invisible, a folder that is the same everywhere.

Behind that simplicity lies a problem of replication with a feature that the
replicated stores of earlier chapters were spared. In chapter 3 a single leader
accepted all the writes of a shard, and the followers had only to copy what the
leader decided. Here every device is a place where writes originate, and devices
write while they are disconnected, sometimes for days. A laptop on a flight and a
phone in the mountains may each change the same file, in different ways, with
neither able to learn of the other until both return. No arrangement of leaders can
prevent this, since the devices cannot reach any leader at the time. The service has
to accept that conflicting changes will be made, detect them reliably when they
come to light, and resolve them without destroying anybody's work.

The other half of the design is economy. Files are large, the connections of mobile
devices are slow and often charged by volume, and a service that transferred a whole
file of 500 MB because 1 paragraph of it had changed would be unusable. Much of the
engineering lies in transferring exactly what has changed and nothing else.

<div class="covers">

This chapter covers

- a file as a list of chunks, with the bytes in 1 place and the list in another
- transferring only the chunks that have changed
- why cutting a file at fixed positions fails when a byte is inserted
- cuts that depend on the content
- versions, and detecting that 2 devices have changed the same file
- what to do with a conflict
- how a device learns that something has changed
- how a device catches up after being offline
- deleting, renaming, and the order in which things are uploaded

</div>

## A file as a list of chunks

The service does not store a file as a single object. It follows the practice of the
object store in chapter 16: a file is cut into *chunks* of moderate size, each chunk
is identified by a checksum of its contents, and the file itself is represented by
the list of the checksums of its chunks, in order.

The representation divides the data into 2 parts of very different character. The
chunks are large, immutable and without structure, and are kept in a chunk store,
which is an object store. The lists, together with the names of the files, their
versions and their positions in folders, are the *metadata*. They are small,
frequently changed, and have to be strongly consistent, and they are kept in a
replicated database.

Several properties that the service needs follow from this division with little
further effort. Identical chunks have identical checksums and are stored once,
whether they occur in 2 versions of a file, in 2 files, or in the folders of 2
different users. The previous versions of a file cost almost nothing to retain,
since an old version is merely an old list, most of whose chunks are shared with the
new one. And a transfer that is interrupted can be resumed, since the chunks that
arrived are already in the store and need not be sent again.

## Transferring only what changed

When a file is modified, the device cuts the new contents into chunks, computes
their checksums, and compares the resulting list with the list of the version it
previously held. The chunks whose checksums already appear are in the store and
need not be sent. Only the chunks with new checksums are uploaded, followed by the
new list.

A device that receives the change proceeds in the mirror image. It obtains the new
list, compares it with the chunks it holds locally, downloads those it lacks, and
assembles the new version of the file from old and new chunks together.

If a paragraph is altered in the middle of a document of 100 MB that has been cut
into chunks of 4 MB, 1 chunk of the 25 has changed, and 4 MB are transferred in
place of 100. The scheme has, however, a weakness that depends on how the file is
cut, and it is serious enough to determine the design.

## Where to cut

The obvious way of cutting a file is at fixed positions, after every 4 MB. This
serves well when a file is modified by overwriting some of its bytes in place, and
very badly when bytes are inserted or removed.

Suppose that a single byte is added at the very beginning of a file. Every byte that
follows is now 1 position later than it was. The first chunk consists of the new
byte and the first 4 MB less 1 byte of the old content, the second chunk begins 1
byte earlier in the old content than it used to, and so on to the end. Although the
content is all but unchanged, every chunk contains different bytes from before and
has a different checksum, and the entire file is uploaded again. Inserting text near
the start of a document, which is among the commonest of all edits, defeats the
scheme completely.

<figure>
<img src="figures/sync-chunking.svg?v=edf26463" alt="2 rows of 8 chunks after 1 byte is added at the start of a file. With cuts every 1024 bytes, all chunks have changed. With cuts that depend on the content, only the first chunk has changed.">
<figcaption><b>Figure 25.1</b> The chunks that have to be uploaded after 1 byte is added at the start of a file, under 2 ways of cutting.</figcaption>
</figure>

The remedy is to let the content itself determine where the cuts fall. The device
passes a small window, of a few dozen bytes, along the file, computing at each
position a hash of the bytes in the window. Wherever the hash satisfies some fixed
condition, for instance that its lowest 22 bits are all 0, a cut is made. Since the
condition is met on average once in every 4 million positions, the chunks have an
average size of 4 MB, though they vary in length. This technique is called
*content-defined chunking*.

Its value lies in the fact that a cut now depends only on the few bytes around it.
When a byte is inserted at the start of the file, the positions of all later cuts
shift by 1 along with the content, and each still falls between the same 2 pieces of
content as before. The chunks after the first therefore contain exactly the bytes
they contained previously and have the same checksums.

The simulation for this chapter makes the comparison on a file of 64 KB, with small
chunks so that the effect is visible. After 1 byte is added at the start, cuts every
1024 bytes leave all 65 chunks to be uploaded again, and cuts that depend on the
content leave 1 of 62.

The hash of the window has to be computed at every position in the file, and would
be slow if it were calculated from nothing each time. A *rolling hash* is designed so
that when the window advances by 1 byte, the new value is obtained from the old by
removing the contribution of the byte that has left and adding that of the byte that
has entered, in a constant number of operations. Limits are also set on the size of
a chunk in both directions, so that an unlucky stretch of content yields neither a
swarm of tiny chunks nor a single enormous one.

## Versions and conflicts

Every file has a *version*, a number that the metadata store increases by 1 each
time the file is changed. A device records, for each file, the version on which its
local copy is based.

When a device uploads a change, it states that version: "here is a new list of
chunks for this file, which I produced by modifying version 3". The service compares
the stated version with the current one. If the file is still at version 3, nobody
else has changed it in the meantime, and the upload is accepted as version 4. If the
file is by now at version 4 or beyond, some other device has changed it since this
device last looked, and the upload is rejected as a *conflict*.

This is the conditional write of chapter 1, the `If-Match` header under another
name, and it is the foundation on which the correctness of the whole service rests.
Without it, the later of 2 uploads would silently replace the earlier, and one
person's work would vanish with no indication that it had ever existed.

<figure class="steps" data-prefix="figures/steps-sync-conflict" data-count="5" data-version="2e21dbd2">
<img src="figures/steps-sync-conflict-01.svg?v=2e21dbd2" alt="2 devices change the same file, step 1 of 5. The laptop and the phone both hold version 3 of a file. Both go offline: the laptop on a flight, the phone in the mountains.">
<figcaption><b>Figure 25.2</b> A laptop and a phone change the same file while offline, and the second upload is recognised as a conflict. Use Next and Back to move through the 5 steps.</figcaption>
</figure>

The comparison and the update have to be a single atomic operation in the metadata
store. If 2 devices upload within the same instant, exactly 1 must succeed, and this
is the principal reason why the metadata is held in a strongly consistent database.

### What to do with a conflict

Detecting a conflict is a precise matter. Deciding what to do about it is a question
of policy, on which reasonable designs differ.

The simplest policy is that the last writer prevails, the later upload replacing the
earlier. It needs no intervention from the user and silently discards somebody's
work, and it is acceptable only for data whose loss nobody would mind.

The policy adopted by most services for ordinary files is to keep both. The version
that arrived first remains under the original name, and the other is saved beside it
under a name that marks it as a conflicting copy, with the device and the date.
Nothing is lost, and the user, who alone knows what the 2 edits were meant to
achieve, combines them by hand. It is a slightly awkward outcome and an honest one.

For certain kinds of content the 2 changes can be merged automatically. If 2 people
have edited different paragraphs of a text, both edits can be applied. This requires
the service to understand the structure of the content, and is the subject of
chapter 26. A service that synchronises arbitrary files treats them as opaque bytes
and cannot attempt it, since 2 edits to a spreadsheet or an image cannot be combined
by anything that does not know what a spreadsheet or an image is.

## Learning that something changed

A device has to find out that a file was changed elsewhere. It could ask the service
at regular intervals, and this is the polling that chapter 18 examined and found
wanting: frequent polling wastes requests and battery when nothing is happening, and
infrequent polling delays every change.

The service therefore uses the remedy of chapter 18. Each device keeps a connection
open to a notification service, and when a change is accepted, the service informs
the other devices of the same account over their connections. The message carries no
content. It says only that something has changed, and the device, on receiving it,
asks the metadata service what.

That question is answered by means of a *cursor*, exactly as in chapter 18. The
metadata store keeps for each account an ordered list of every change, each with a
sequence number: file 7 changed to version 4, file 12 deleted, folder 3 renamed. A
device remembers the number of the last change it has applied and asks for
everything after that. The same request serves a device that was told of a change a
second ago and one that has been switched off for a month, and the service keeps no
record of which device has received what.

The design of chapter 18 thus reappears almost unaltered: a signal to attract
attention, which is permitted to be lost, and a cursor from which the true state is
recovered, which is not. It is among the most reusable patterns in this book.

## Deleting, renaming and order

A few matters of detail cause a disproportionate share of the defects in services of
this kind.

A deletion has to be synchronised like any other change, and it cannot be
represented by the mere absence of a file. Were a device to see only that a file is
missing from the list, it could not distinguish a file that was deleted elsewhere
from a file that it has itself created a moment ago and has yet to upload. A deletion is
therefore recorded as an explicit entry in the list of changes, sometimes called a
*tombstone*, and the file's chunks are retained for a time so that the deletion can
be undone.

A rename should be recorded as a rename, an operation on the metadata alone. If it
were treated as the deletion of one file and the creation of another, every device
would download again a file whose bytes it already held. With chunks identified by
their checksums, even that naive treatment would in fact transfer nothing, since the
"new" file consists of chunks that are already present, which is a further dividend
of content addressing.

The order of an upload matters for the same reason that it did in chapter 16. The
chunks are uploaded first, and the new list is committed to the metadata store last.
The list is what makes the new version exist for other devices, and at that moment
every chunk it refers to must already be in the store. An upload interrupted halfway
leaves a few chunks that nothing refers to, to be collected later as garbage, and
never a version that other devices are told of and cannot assemble.

Finally, a file that is still being written should not be uploaded. An application
saving a large file writes it over several seconds, and a device that began
uploading at the first change would send a partial file, followed at once by
another. Devices wait until a file has been unchanged for a short period before
treating it as modified.

## Use cases

A person changes files on 1 device, sees the changes on another, and occasionally
has to settle a conflict.

<figure>
<img src="figures/sync-use-cases.svg?v=c2bf9d13" alt="A use case diagram of the sync service. Person: change a file on 1 device (PUT /v1/files/{id}), see it on the other (GET /v1/changes?after=), settle a conflict (both versions are kept).">
<figcaption><b>Figure 25.3</b> The actor and what it does.</figcaption>
</figure>

## Functional requirements

| No. | Functional requirement |
|---|---|
| 0 | A change made to a file on 1 device appears on the user's other devices. |
| 1 | A device that was offline receives every change made in its absence when it reconnects. |
| 2 | Only the parts of a file that have changed are transferred. |
| 3 | When 2 devices change the same file independently, neither change is lost. |
| 4 | Earlier versions of a file can be restored for 30 days. |
| 5 | A deleted file can be restored for 30 days. |

## Non-functional requirements

| No. | Property | Non-functional requirement |
|---|---|---|
| 0 | Durability | A file whose upload was confirmed is not lost. |
| 1 | Consistency | Strong for metadata: of 2 uploads based on the same version, exactly 1 is accepted. Eventual between devices. |
| 2 | Latency | A change reaches a connected device within 5 seconds. |
| 3 | Economy | The bytes transferred are proportional to the size of the change and not to the size of the file. |
| 4 | Scale | 100 million users, 10 billion files, 1 EB of content. |

Non-functional requirement 1 sets 2 consistency models side by side, and it is worth
being clear about where each applies. Among the devices, the system is eventually
consistent by necessity, since a device that is switched off cannot possibly have
the latest version. The metadata store that arbitrates among them is strongly
consistent, and it has to be, because the detection of conflicts depends on every
upload being compared with the true current version. The service as a whole can
tolerate devices that are far behind precisely because, at its centre, there is 1
place that is never in doubt about what the latest version is.

## Core entities

<figure>
<img src="figures/sync-entities.svg?v=c4f8a0fd" alt="The core entities. File has the fields id u64, path string, version u64, chunks checksum[]. Chunk has the fields checksum u64, bytes in object store. Device has the fields id string, cursor last change seen. A File is a list of chunks and a version. A Device remembers how far it has read in the list of changes.">
<figcaption><b>Figure 25.4</b> The core entities and their fields.</figcaption>
</figure>

## Capacity estimate

<div class="estimate">

<img class="builder" src="art/crab-builder.svg" alt="A crab in a hard hat, in tears.">

**Arithmetic ahead.** 1 EB of content in chunks of 4 MB is 250 billion chunks, and the metadata for 10 billion files comes to about 5 TB.

<a class="skip" href="#high-level-design">Skip to the high-level design</a>

<details>
<summary>Show the calculation</summary>

| Quantity | Calculation | Result |
|---|---|---|
| Chunks | 1 EB ÷ 4 MB | 250 billion |
| Metadata per file | name, version, folder, and 25 checksums of 16 bytes on average | about 500 bytes |
| Metadata for all files | 10 billion × 500 bytes | 5 TB |
| Open connections | 100 million users × 2 devices × 20% online | 40 million |
| Changes per second | 100 million users × 20 changes a day ÷ 86400 | about 23000 |

</details>

</div>

## The API

A device first learns which chunks the store lacks, uploads those, and then commits
the new version, stating the version it started from.

**Ask which chunks are missing**

```http
POST /v1/chunk-queries HTTP/1.1
Host: sync.example
Content-Type: application/json

{ "checksums": ["9f2c", "41aa", "c07e"] }
```

```http
HTTP/1.1 200 OK
Content-Type: application/json

{ "missing": ["c07e"] }
```

The resource created is a query, which is why the request is a `POST` to a
collection of queries and the answer comes back at once. Only the chunk `c07e` has
to be uploaded.

**Upload a chunk**

```http
PUT /v1/chunks/c07e HTTP/1.1
Host: sync.example
Content-Type: application/octet-stream
Content-Length: 4194304

(4194304 bytes)
```

```http
HTTP/1.1 201 Created
```

The address of a chunk is its checksum, so that uploading the same chunk twice is
harmless and `PUT` is the proper method.

**Commit a new version of a file**

```http
PUT /v1/files/7 HTTP/1.1
Host: sync.example
If-Match: "3"
Content-Type: application/json

{ "path": "notes.txt", "chunks": ["9f2c", "41aa", "c07e"] }
```

```http
HTTP/1.1 200 OK
ETag: "4"
Content-Type: application/json

{ "id": 7, "version": 4 }
```

**The same commit from a device that is behind**

```http
PUT /v1/files/7 HTTP/1.1
Host: sync.example
If-Match: "3"
Content-Type: application/json

{ "path": "notes.txt", "chunks": ["9f2c", "77b0", "c07e"] }
```

```http
HTTP/1.1 412 Precondition Failed
Content-Type: application/problem+json

{
  "type": "/problems/version-conflict",
  "title": "The file has been changed by another device",
  "status": 412,
  "current_version": 4
}
```

**Fetch the changes since a cursor**

```http
GET /v1/changes?after=5120 HTTP/1.1
Host: sync.example
```

```http
HTTP/1.1 200 OK
Content-Type: application/json

{
  "changes": [
    { "number": 5121, "file": 7, "kind": "modified", "version": 4, "chunks": ["9f2c", "41aa", "c07e"] },
    { "number": 5122, "file": 12, "kind": "deleted" }
  ],
  "next_after": 5122
}
```

## High-level design

<figure class="wide">
<img src="figures/sync-design.svg?v=24cf85ac" alt="Syncing a file between 2 devices. The components are Laptop, Sync service, Metadata store, Chunk store, Notifier, Phone. Step 1: The laptop uploads the chunks the store does not have. Step 2: It sends the chunk list and the version it started from. Step 3: The file is updated if that version is still current. Step 4: The service tells the notifier. Step 5: The phone is told, and fetches what changed.">
<figcaption><b>Figure 25.5</b> The components and the path of a change. The steps are numbered.</figcaption>
</figure>

| Component | Role | State it holds | When 1 instance fails |
|---|---|---|---|
| Device | watches a folder, cuts files into chunks, uploads and downloads | the files, and a cursor | it catches up from its cursor when it returns |
| Chunk store | keeps chunks by checksum | every chunk, as in chapter 16 | as in chapter 16 |
| Sync service | compares versions and commits changes | none | another instance serves the request |
| Metadata store | holds files, versions, chunk lists and the list of changes | all metadata, replicated | a follower is elected |
| Notifier | holds a connection to every online device | connections, in memory | devices reconnect and fetch from their cursors |

### One change, step by step

The steps follow the arrows of figure 25.5.

1. The laptop notices that a file has changed and has been still for 2 seconds. It cuts the file into chunks, asks which of them the store lacks, and uploads those.
2. It sends the new list of chunks to the sync service, together with the version on which its change was based.
3. The sync service asks the metadata store to replace the list if the file is still at that version. The store does so, increases the version, and appends an entry to the account's list of changes.
4. The sync service tells the notifier that the account has a change.
5. The notifier passes the signal to the phone over its open connection. The phone asks for the changes after its cursor, downloads the chunks it lacks from the chunk store, assembles the file, and moves its cursor forward.

## The design, deployed

<figure class="wide">
<img src="figures/sync-deploy.svg?v=a21c394c" alt="The sync service, deployed. Devices: Devices (40 million online), laptops and phones. Services, in 3 zones: Load balancers (x 12), by kind of request, Sync service (x 100), compares versions, Notifiers (x 400), 1 connection per device. Storage: Metadata store (x 90), 30 shards x 3 replicas, Chunk store (1 EB), see chapter 16.">
<figcaption><b>Figure 25.6</b> The sync service as it is deployed, with the bytes travelling directly between devices and the chunk store.</figcaption>
</figure>

The deployment separates 3 kinds of traffic that have nothing in common. Small
requests about metadata go through load balancers to the 100 instances of the sync
service and from there to the metadata store, which is sharded by account with 3
replicas of each shard. Long-lived connections, 1 for every online device, are held
by 400 notifiers, a tier of the same kind as the gateways of chapter 18. And the
bytes of the files travel directly between the devices and the chunk store, without
passing through either of the other tiers, which is what keeps them small.

## How real systems do it

Dropbox has described the protocol of its service, and it matches the outline of
this chapter closely. A file is divided into blocks of 4 MB, each named by a
cryptographic hash of its contents, and the list of those hashes identifies the
contents of the file. To upload, a client sends the list to a metadata server. If
the server lacks some of the blocks, it says which, the client sends them to a
separate block server, and the commit is then repeated and recorded in a journal of
changes for the account, which is the ordered list of changes from which other
clients read with a cursor.

In 1 respect the published design differs from the recommendation of this chapter,
and the difference should be stated plainly. Dropbox's blocks are of fixed size.
Cutting at positions determined by the content, which this chapter presents as the
remedy for insertions, is the method of the Low-Bandwidth File System, a research
system of 2001, and it is used today mainly by backup programs, for which
deduplication across many versions matters most. A fixed block size is simpler, and
a service can limit the damage of an insertion by other means, notably by
transferring within a changed block only the differences from its previous version.
That technique comes from rsync, whose rolling checksum is the original of the
rolling hash described above.

The cost of the rolling hash has itself been reduced. A method published in 2016
replaces the traditional fingerprint by a much cheaper one and adjusts the
condition for a cut so as to avoid very small and very large chunks, and reports
chunking several times faster with nearly the same deduplication.

For the storage of the blocks, Dropbox built its own system of the kind described
in chapter 16, holding exabytes, and has described rewriting its client's
synchronisation engine after concluding that the hardest part of the problem is
the client, which has to reconcile the server's view with a local file system that
other programs are changing all the time.

## Mistakes to avoid

| Mistake | What goes wrong | What to do |
|---|---|---|
| Uploading whole files | A small edit to a large file transfers all of it. | Cut files into chunks and upload only the new ones. |
| Cutting at fixed positions | An insertion near the start changes every chunk. | Let the content determine the cuts. |
| Accepting an upload without its base version | The later of 2 edits silently replaces the earlier. | Require the version the change was based on, and compare it atomically. |
| Resolving conflicts by letting the last writer prevail | Somebody's work is discarded without notice. | Keep both versions, and let the user decide. |
| Committing the list before the chunks | Other devices are told of a version they cannot assemble. | Upload the chunks first and commit the list last. |
| Polling for changes | Battery and requests are wasted, or changes arrive late. | Signal over an open connection, and fetch from a cursor. |
| Trusting the signal to carry the change | A lost signal is a lost change. | Treat the signal as a hint, and recover from the cursor. |
| Representing a deletion by absence | A device cannot tell a deleted file from one it has just created. | Record deletions as explicit entries. |
| Treating a rename as delete and create | The history of the file is broken, and work may be repeated. | Record a rename as a change to metadata. |
| Uploading a file while it is being written | Partial files are synchronised, followed by more partial files. | Wait until the file has been still for a moment. |
| Deleting chunks as soon as a file is deleted | Chunks shared with other files or needed for restoring are lost. | Collect unreferenced chunks later, after a period of grace. |

## Failures

| Failure | What users see | How the system recovers |
|---|---|---|
| A device loses its connection during an upload | the file shows as still synchronising | the chunks already uploaded are kept, and the upload resumes with the rest |
| 2 devices change the same file | a second file marked as a conflicting copy | both versions are kept |
| The signal of a change is lost | the change appears a little later | the device also fetches from its cursor at intervals and on reconnecting |
| A device is offline for a month | nothing, until it reconnects | it fetches every change after its cursor |
| The reply to a commit is lost | the device tries again | the retry finds the file already at the new version with the same chunks, and treats it as success |
| The metadata store's leader fails | commits fail for about 1 second | a follower is elected |

## Trade-offs

| Decision | What it gains | What it costs |
|---|---|---|
| Chunks identified by checksum | small transfers, shared storage, cheap old versions | metadata for every chunk, and garbage to collect |
| Cuts that depend on the content | insertions change 1 chunk | chunks of uneven size, and a hash at every byte |
| Strong consistency for metadata | conflicts are always detected | commits wait for a majority |
| Keeping both versions in a conflict | nothing is lost | the user has to combine them |
| A signal and a cursor | prompt delivery that survives lost signals | a connection for every online device |

## The simulation

<div class="simulation">

**Simulation in the repository.** The program [`code/syncsim`](https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/distributed-systems-from-the-ground-up/code/syncsim/src/main.rs) simulates this design. To run it, clone the repository and type `cargo run --release -p syncsim` in the `code` directory.

</div>

## References

- N. Koorapati, "Streaming File Synchronization", Dropbox tech blog, 2014.
- A. Muthitacharoen, B. Chen and D. Mazieres, "A Low-bandwidth Network File System", SOSP 2001.
- A. Tridgell and P. Mackerras, "The rsync algorithm", Australian National University technical report, 1996.
- W. Xia and others, "FastCDC: A Fast and Efficient Content-Defined Chunking Approach for Data Deduplication", USENIX ATC 2016.
- Dropbox tech blog, "Rewriting the heart of our sync engine", 2020.

## Terms introduced in this chapter

| Term | Meaning |
|---|---|
| Synchronisation | bringing copies of the same data on several devices into agreement |
| Chunk | a piece of a file, identified by a checksum of its contents |
| Metadata | the names, versions, folders and chunk lists of files |
| Content-defined chunking | cutting a file where its content satisfies a condition |
| Rolling hash | a hash of a moving window that is updated in constant time as the window advances |
| Version | a number that increases with every change to a file |
| Conflict | 2 changes to the same file, each made without knowledge of the other |
| Conflicting copy | the second of 2 conflicting versions, kept under another name |
| Cursor | the number of the last change a device has applied |
| Tombstone | an explicit record that something was deleted |

<div class="summary">

## Summary

- A file is a list of chunks identified by checksum, with the chunks in an object store and the lists in a strongly consistent metadata store.
- A device uploads only the chunks that the store does not already hold.
- Cuts at fixed positions make an insertion change every chunk, and cuts that depend on the content confine the change to 1.
- Every upload states the version it was based on, and an upload based on an old version is a conflict.
- In a conflict both versions are kept, since the service cannot know which edit the user would prefer.
- Devices are signalled over an open connection and fetch changes from a cursor, so that a lost signal delays a change and loses nothing.
- Chunks are uploaded before the list that refers to them, and deletions are recorded explicitly.

</div>
