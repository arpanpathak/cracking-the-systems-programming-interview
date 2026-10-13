<img class="plate" src="art/ch26.svg?v=8495e880" alt="2 penguins stand beside a sign that reads: cat, chat, cats, chats.">

# Collaborative Editing: System Design

In a collaborative editor, several people work on the same document at once. Each
sees the others' changes appear as they are made, character by character, with a
coloured cursor marking where each person is typing, and nobody has to save, send or
merge anything. The experience is that of several pens writing on a single sheet of
paper.

The previous chapter dealt with 2 devices that had changed the same file, and
resolved the matter by keeping both versions and asking the user to choose. In an
editor that answer is not available. Conflicting changes are here the ordinary
condition, by no means an occasional accident: whenever 2 people type within the same
fraction of a second, each has changed the document without knowledge of the other's
change, and this happens many times a minute. The editor cannot present a conflict
for a human to settle on every keystroke. It has to combine concurrent changes
automatically, in a way that keeps every participant's intention, and it has to do
so in such a manner that everybody ends with exactly the same document.

That last requirement, known as *convergence*, is the difficult one. Each person's
own keystrokes must appear on their own screen at once, since nobody will tolerate
typing into an editor that waits for a server before showing a letter. Every
participant therefore applies their own changes first and the others' afterwards,
which means that different participants apply the same changes in different orders,
and the result must nevertheless be identical for all of them. This chapter explains
why the obvious representation of a change fails that test, and then the 2 families
of solution that are in use.

<div class="covers">

This chapter covers

- why each person's changes must take effect at once on their own screen
- changes described by position, and how 2 of them go wrong
- operational transformation, which adjusts a change for what its author had not seen
- the role of a central server in ordering changes
- conflict-free replicated data types, which give every character a name
- deleting, and why deleted characters cannot disappear
- cursors, presence and working offline
- storing a document as a log of operations with snapshots

</div>

## Changes that take effect at once

The simplest way of building a shared editor would be to treat the document as a
value in a strongly consistent store. A keystroke would be sent to the server, the
server would apply it, and the new document would be returned to everybody. All
participants would see the same thing, because there would be only 1 copy.

It would also be unusable. Every character would appear on the typist's own screen
only after a round trip to the server, some 50 to 200 ms later, and on a poor
connection later still. People notice a delay of that size in their own typing
within a few characters, and find it intolerable.

An editor therefore applies each change to the local copy of the document
immediately, and sends it to the others afterwards. This is the same decision that
chapter 18 took when it displayed a sent message before the server had confirmed it,
and it has a far-reaching consequence. Each participant now holds a copy of the
document that is momentarily ahead of everyone else's in respect of their own
changes, and behind in respect of the others'. The copies are replicas in the full
sense, every one of them accepts writes, and the system is one of replication with
many writers and no possibility of coordination before a write.

## 2 changes by position

A change to a text is most naturally described as an *operation* on a position:
insert this character at position 5, or delete the character at position 9. This is
how a single-user editor works internally, and it is entirely adequate so long as
every operation is applied to the same text that its author was looking at.

With 2 people editing concurrently, that condition fails, and the consequences can
be followed in a small example.

<figure class="steps" data-prefix="figures/steps-edit-positions" data-count="5" data-version="92325ab8">
<img src="figures/steps-edit-positions-01.svg?v=92325ab8" alt="2 changes by position, step 1 of 5. Ada and Bob are both looking at the text &#x27;cat&#x27;. Positions are counted from 0: c is at 0, a at 1, t at 2, and position 3 is the end.">
<figcaption><b>Figure 26.1</b> Ada and Bob each insert a character into "cat" at the same moment, and applying the changes by position gives different results. Use Next and Back to move through the 5 steps.</figcaption>
</figure>

Ada inserted an `h` at position 1, and Bob an `s` at position 3, which at the time
was the end of the word. When Bob's operation reaches Ada, her text has already
changed: her own `h` has moved every later character 1 place to the right, and
position 3 no longer means what it meant to Bob. The operation is applied faithfully
and lands in the wrong place. Ada's operation, arriving at Bob's copy, is unaffected,
since nothing before position 1 has moved. The 2 copies now read `chast` and
`chats`.

The simulation for this chapter runs exactly this case and prints the 2 different
results. The copies have *diverged*, and the fault will never correct itself, since
each later operation is applied to 2 different texts and can only compound the
difference.

The root of the trouble is that a position is not a stable way of referring to a
place in a text. It is meaningful only relative to a particular state of the
document, and an operation that travels to another replica arrives at a different
state. The 2 families of solution correspond to the 2 possible remedies. One may
keep positions and correct them on arrival, or one may abandon positions for
something that does not go out of date.

## Adjusting a change for what its author had not seen

The first remedy is called *operational transformation*, usually abbreviated OT.
Before an operation that was made concurrently with others is applied, it is
transformed so as to take account of them.

In the example, Bob's insertion at position 3 was made without knowledge of Ada's
insertion at position 1. Ada's character was placed before position 3 and so
displaced it by 1. The transformed operation is therefore an insertion at position
4, and applied to Ada's text it yields `chats`. Ada's operation is transformed
against Bob's in turn. Bob's character was placed after position 1 and displaced
nothing before it, so Ada's operation is unchanged, and Bob's text becomes `chats` as
well. The last step of the picture above shows the outcome, and the simulation
confirms it.

For insertions the rule is short. An insertion is moved 1 place to the right for
every concurrent insertion that was made at an earlier position. A further rule is
needed for the case in which 2 people insert at the very same position, where some
fixed convention, such as giving precedence to the participant with the smaller
identifier, must decide which character comes first, and must decide it identically
on every replica.

Deletions add further cases. An insertion after a concurrently deleted character
moves 1 place to the left. 2 participants who both delete the same character must
between them delete it once. An insertion in the middle of a range that somebody
else is deleting must survive. For each pair of kinds of operation there is a
transformation, and the difficulty of OT lies in the number of these cases and in
the requirement that they agree with one another: whichever order a replica happens
to receive 2 concurrent operations in, transforming and applying them must lead to
the same text. Published algorithms have been found, years afterwards, to violate
this requirement in obscure combinations.

### What a central server contributes

The difficulty is greatly reduced by a decision about architecture. If participants
exchanged operations directly with one another, each might see the operations in a
different order, and the transformations would have to be correct for every possible
order among any number of participants. Nearly all practical systems avoid this by
routing every operation through a central server.

The server gives the document a single, agreed history. It maintains a *revision*
number, which counts the operations applied so far. A participant sends each
operation together with the revision of the document on which it was based. The
server compares that revision with its current one. If others have been applied
since, the server transforms the incoming operation against each of them in order,
applies the result, assigns it the next revision number, and sends the transformed
operation to all the other participants. Each participant, meanwhile, transforms the
operations it receives from the server against any of its own that the server has
not yet acknowledged.

With this arrangement, every transformation involves only 2 sequences: what the
server has applied, and what 1 client has pending. The server is the single place at
which order is decided, exactly as the leader of a shard was in chapter 3 and the
message store was in chapter 18, and the general lesson holds here too, that a
problem of ordering among many parties becomes tractable when 1 of them is appointed
to decide the order.

The price is the usual one. The server must be reachable for collaboration to
proceed. A participant who is offline can continue to type, and the operations
accumulate locally, but they are merged only on reconnection, by transformation
against everything that has happened in the meantime.

## A name for every character

The second remedy removes the cause of the trouble. If positions go out of date,
characters can be referred to by something that does not.

In this approach every character is given, at the moment it is typed, a unique
identifier that it keeps for ever. The identifiers are chosen so that they can be
ordered, and the text is defined as the characters arranged in the order of their
identifiers. An insertion no longer says "at position 3". It says "a new character
with this identifier", and the identifier is chosen to fall between those of the 2
characters where the author placed it.

<figure class="steps" data-prefix="figures/steps-edit-names" data-count="4" data-version="9b47c6d9">
<img src="figures/steps-edit-names-01.svg?v=9b47c6d9" alt="A name for every character, step 1 of 4. In the second approach, a character is never referred to by its position. Each has a name of its own, a number that does not change, and the text is the characters in the order of their names.">
<figcaption><b>Figure 26.2</b> Every character has an identifier that fixes its place, so that insertions can be applied in any order. Use Next and Back to move through the 4 steps.</figcaption>
</figure>

An operation of this form has a remarkable property. It refers to nothing that
another operation can alter, and applying it consists merely in adding 1 element to
a sorted collection. 2 such operations can be applied in either order with the same
result, and an operation applied twice has the same effect as once. No
transformation is required, and no server is needed to decide an order, since order
is irrelevant.

A data structure whose operations can be applied in any order, any number of times,
with every replica arriving at the same state, is called a *conflict-free replicated
data type*, or CRDT. In the simulation, the same 2 insertions are applied in both
orders to a text represented in this way, and both replicas read `chats`. When both
participants insert at the same place, the identifiers are distinguished by the
identity of the device, and both replicas read `carnt`, with the characters in the
same order on each.

The identifiers have to satisfy 2 conditions. They must be unique, which is arranged
by including the identity of the device in each. And it must always be possible to
create a new identifier between any 2 existing ones, however close together. Whole
numbers do not suffice, since nothing lies between 1500 and 1501. Practical schemes
use sequences of numbers of variable length, compared as the entries of a dictionary
are, so that between any 2 a longer one can be found, or else define each character's
place by reference to the identifier of the character it was typed after.

### The cost of a name

The simplicity of the operations is bought with metadata. A plain text of 10000
characters occupies 10000 bytes. The same text as a CRDT carries an identifier for
every character, which may be 10 or 20 times the size of the character itself, and
identifiers of the dictionary kind grow longer wherever a great deal of text has
been inserted in the same place. Much of the engineering in CRDT libraries is
devoted to compressing this, for instance by storing a run of characters typed in
succession by 1 person as a single unit with 1 identifier and a length.

Automatic merging has a further limit, which applies to both families and which no
algorithm can remove. Convergence guarantees that all replicas end with the same
text. It does not guarantee that the text is what anybody meant. If 2 people correct
the same misspelt word simultaneously, each by deleting it and typing it again, the
merged document contains the corrected word twice. The result is consistent and
wrong, and what collaborative editors rely upon in practice is that people can see
each other's cursors, and tend not to edit the same word at the same moment.

## Deleting

Deletion presents a difficulty of its own in a CRDT. Suppose that Ada deletes a
character at the same moment that Bob inserts a new one immediately after it, his
operation saying in effect "after the character with identifier 2000". If Ada's
replica had removed that character altogether, Bob's operation would arrive
referring to something that no longer exists there.

A deleted character is therefore not removed. It is marked as deleted and hidden
from view, and its identifier remains in the structure to serve as a point of
reference. Such a marker is the *tombstone* of chapter 25. The consequence is that a
document which has been heavily edited contains far more tombstones than visible
characters, and they can be discarded only when it is certain that no replica
anywhere still holds an operation that refers to them, which, with participants who
may be offline for weeks, is difficult to establish.

## The 2 approaches compared

| | Operational transformation | CRDT |
|---|---|---|
| How an operation refers to a place | by position | by the identifier of a character |
| What makes replicas converge | transforming operations against concurrent ones | operations that give the same result in any order |
| Central server | required, to fix the order | not required |
| Working offline, or peer to peer | awkward: everything is transformed on return | natural: operations are merged whenever they meet |
| Size of the document | close to the plain text | several times the plain text, with tombstones |
| Where the complexity lies | in the transformation rules | in the identifiers and their compaction |

Services in which a server is always in the path, and in which documents are large
and long-lived, have mostly used operational transformation. Applications that must
work offline for long periods, or without any central server, have mostly used
CRDTs. The design in the remainder of this chapter uses a central server with
operational transformation.

## Around the text

A collaborative editor conveys more than the text. Each participant sees where the
others' cursors and selections are, and who is present in the document. This
information is *ephemeral*: it is forwarded to the other participants as it changes
and is stored nowhere, since a cursor position that is lost is replaced by the next
one a moment later. It is the presence of chapter 18, with the same loose
guarantees.

Cursors are nonetheless subject to the central problem of this chapter. A cursor is
a position in the text, and when another participant inserts characters before it,
it has to move. A cursor is therefore transformed against incoming operations in
the way that an operation would be, or, in a CRDT, is attached to the
identifier of a character, which does not move.

Undo also needs rethinking. In an editor for 1 person, undo reverses the most recent
change. In a shared document the most recent change may be somebody else's, and to
reverse it would be bewildering. Undo is accordingly made to reverse the most recent
change of the person who invokes it, which requires the inverse of an operation that
is no longer the latest and has to be transformed against everything that came
after.

## Storing the document

The server retains every operation, in order, in a log, each with its revision
number. The document at any revision is the result of applying the operations up to
that point, so that the log is the authoritative record and the current text is
derived from it. This is the relation between records and entries from chapter 1,
and it yields the complete history of the document, by which an author can see what
it contained at any earlier moment and who changed what.

To replay the whole log each time a document is opened would grow slower with every
keystroke ever made. The server therefore saves a *snapshot* of the text at
intervals, every few hundred operations, and a document is opened by loading the
latest snapshot and applying the operations that follow it. The operations before a
snapshot are kept as long as history is wanted and are not needed for opening.

Each document is served, at any moment, by a single server process, which holds its
current text in memory and decides the order of its operations. Documents are
assigned to servers by hashing their identifiers, and every participant in a
document is connected, through a gateway of the kind described in chapter 18, to
that document's server. The operation is appended to the log before it is
acknowledged and broadcast, so that if the process fails, another can take over the
document from the log without losing anything that was confirmed.

## Use cases

An author types in a shared document, sees what the others type, and may continue
while offline.

<figure>
<img src="figures/edit-use-cases.svg?v=0353eb6a" alt="A use case diagram of the editing service. Author: change the text (an operation, over an open connection), see what others type (their operations, pushed), continue offline (operations wait, then are sent).">
<figcaption><b>Figure 26.3</b> The actor and what it does.</figcaption>
</figure>

## Functional requirements

| No. | Functional requirement |
|---|---|
| 0 | Several authors can edit the same document at the same moment. |
| 1 | An author's own change appears on their screen immediately. |
| 2 | A change by another author appears within 200 ms. |
| 3 | When all changes have been delivered, every author sees the same document. |
| 4 | An author sees the cursors of the other authors. |
| 5 | An author who is offline can continue to edit, and the changes are merged on reconnection. |
| 6 | The history of a document can be viewed, and an earlier state restored. |

## Non-functional requirements

| No. | Property | Non-functional requirement |
|---|---|---|
| 0 | Convergence | All replicas reach the same state once every operation has been delivered, in whatever order they were applied locally. |
| 1 | Durability | An operation that the server has acknowledged is not lost. |
| 2 | Consistency | Eventual between authors. Strong for the order of operations in the server's log. |
| 3 | Latency | A local change takes effect in under 16 ms, and a remote one within 200 ms. |
| 4 | Scale | 10 million documents open at once, with up to 100 authors in a document. |

Non-functional requirement 2 has the form that has now appeared in several chapters.
The replicas that people look at are eventually consistent, each running ahead with
its own changes. At the centre is a log whose order is strongly consistent and never
in dispute, and the eventual consistency of the edges is made safe by the certainty
of the centre. Convergence, non-functional requirement 0, is the precise statement
of what "eventual" promises here.

## Core entities

<figure>
<img src="figures/edit-entities.svg?v=98f0a9d2" alt="The core entities. Document has the fields id u64, revision u64, text at that revision. Operation has the fields document u64, author string, based_on revision, change insert|delete. An Operation says what was changed and which revision its author was looking at. The revision counts operations applied.">
<figcaption><b>Figure 26.4</b> The core entities and their fields.</figcaption>
</figure>

## Capacity estimate

<div class="estimate">

<img class="builder" src="art/crab-builder.svg" alt="A crab in a hard hat, in tears.">

**Arithmetic ahead.** 10 million open documents with 2 authors typing in each produce about 10 million operations per second at the peak, and far fewer in practice, since people pause.

<a class="skip" href="#high-level-design">Skip to the high-level design</a>

<details>
<summary>Show the calculation</summary>

| Quantity | Calculation | Result |
|---|---|---|
| Authors typing at any moment | 10 million documents × 2 authors × 10% actually typing | 2 million |
| Operations per second | 2 million × 5 keystrokes per second | 10 million |
| Size of an operation in the log | document, author, revision, position, character | about 30 bytes |
| Log growth | 10 million × 30 bytes | 300 MB per second at the peak |
| Memory for open documents | 10 million × 50 KB | 500 GB, across the session servers |

</details>

</div>

In practice operations are sent in small batches, several keystrokes together, which
reduces the number of messages by a large factor without any perceptible delay.

## The API

A document is opened with an ordinary request, which returns the text and its
revision. From then on, operations travel in both directions over an open
connection.

**Open a document**

```http
GET /v1/documents/8812 HTTP/1.1
Host: docs.example
```

```http
HTTP/1.1 200 OK
Content-Type: application/json

{ "id": 8812, "revision": 4410, "text": "cat" }
```

**An operation sent by a client, over the open connection**

```json
{ "document": 8812, "client_id": "ada-17", "based_on": 4410, "insert": { "at": 1, "text": "h" } }
```

`based_on` is the revision that the author was looking at. `client_id` identifies
the operation, so that if it is sent a second time after a lost acknowledgement, the
server recognises it.

**The server's acknowledgement to the sender**

```json
{ "document": 8812, "client_id": "ada-17", "revision": 4412 }
```

**The same operation as broadcast to the other authors**

```json
{ "document": 8812, "author": "ada", "revision": 4412, "insert": { "at": 1, "text": "h" } }
```

The operation broadcast is the transformed one, and its revision is the position it
was given in the log. Revision 4411 belonged to an operation by another author that
reached the server first.

**Read the history of a document**

```http
GET /v1/documents/8812/operations?after=4400&limit=100 HTTP/1.1
Host: docs.example
```

```http
HTTP/1.1 200 OK
Content-Type: application/json

{
  "operations": [
    { "revision": 4411, "author": "bob", "insert": { "at": 3, "text": "s" } },
    { "revision": 4412, "author": "ada", "insert": { "at": 1, "text": "h" } }
  ],
  "next_after": 4412
}
```

## High-level design

<figure class="wide">
<img src="figures/edit-design.svg?v=79da8749" alt="2 authors in 1 document. The components are Author A, Session server, Operation log, Author B, Snapshots. Step 1: An author&#x27;s change travels to the session server. Step 2: The server adjusts it, numbers it and logs it. Step 3: The adjusted change is sent to every other author. Step 4: The text is saved now and then, to shorten the log.">
<figcaption><b>Figure 26.5</b> The components and the path of an operation. The steps are numbered.</figcaption>
</figure>

| Component | Role | State it holds | When 1 instance fails |
|---|---|---|---|
| Client | applies the author's changes at once, and transforms incoming ones | its copy of the document, and operations not yet acknowledged | it reopens the document and sends its pending operations again |
| Session server | orders the operations of a document, transforms them, and broadcasts | the current text of each of its documents, in memory | another server loads the document from its snapshot and log |
| Operation log | every operation of every document, in order | the log, replicated | a follower is elected |
| Snapshots | the text of a document at intervals | snapshots, in an object store | as in chapter 16 |

### One operation, step by step

The steps follow the arrows of figure 26.5.

1. Author A types a character. The client applies it to its own copy at once, and sends the operation to the session server with the revision on which it was based.
2. The session server transforms the operation against every operation applied since that revision, appends the result to the log under the next revision number, and acknowledges it to A.
3. The server sends the transformed operation to author B, whose client transforms it against any operations of its own that the server has not yet acknowledged, and applies it.
4. Every few hundred operations, the current text is saved as a snapshot.

## Mistakes to avoid

| Mistake | What goes wrong | What to do |
|---|---|---|
| Waiting for the server before showing a keystroke | Typing feels delayed and becomes unusable on a slow connection. | Apply every local change at once, and reconcile afterwards. |
| Applying operations by position as they arrive | Replicas diverge, and never recover. | Transform them, or use identifiers in place of positions. |
| Exchanging operations between clients directly | Every client sees a different order, and the transformations must be right for all of them. | Route every operation through a server that fixes the order. |
| No fixed rule for 2 insertions at the same place | Replicas order the 2 characters differently. | Break the tie by a rule that every replica applies alike. |
| Removing deleted characters from a CRDT | A concurrent operation refers to a character that is gone. | Keep a tombstone. |
| Acknowledging an operation before logging it | A crash loses an edit that the author believes is saved. | Append to the log first. |
| Replaying the whole log to open a document | Opening grows slower with every edit ever made. | Save snapshots, and replay from the latest. |
| Storing cursors durably | A flood of writes for information that is worthless a second later. | Forward cursors, and store nothing. |
| Undo that reverses the latest operation | An author undoes somebody else's work. | Undo the author's own latest operation, transformed against what followed. |
| Assuming that convergence means correctness | 2 simultaneous corrections of 1 word leave it doubled. | Show cursors, so that people avoid editing the same place. |

## Failures

| Failure | What authors see | How the system recovers |
|---|---|---|
| An author's connection drops | their own typing continues, and others' changes stop arriving | on reconnection, pending operations are sent and missed ones fetched from the log |
| The acknowledgement of an operation is lost | nothing | the client sends it again, and the server recognises its identifier |
| A session server fails | a pause of a second or 2 | another server loads the snapshot and the log, and the clients reconnect to it |
| An author is offline for a day | their copy and the shared one differ | every local operation is transformed against the day's operations and merged |
| 2 authors edit the same word | a result that neither intended, the same on both screens | the authors see it and correct it |

## Trade-offs

| Decision | What it gains | What it costs |
|---|---|---|
| Local changes applied at once | typing with no delay | replicas that differ for a moment, and the whole problem of merging |
| A central server | a single order, and far simpler transformation | no collaboration without the server |
| Operational transformation | documents close to the size of their text | intricate rules that are hard to get right |
| A log with snapshots | full history, and fast opening | storage that grows with every keystroke |
| Automatic merging | no conflict is ever put to the author | results that are consistent and sometimes unintended |

## The simulation

<div class="simulation">

**Simulation in the repository.** The program [`code/editsim`](https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/distributed-systems-from-the-ground-up/code/editsim/src/main.rs) simulates this design. To run it, clone the repository and type `cargo run --release -p editsim` in the `code` directory.

</div>

## Terms introduced in this chapter

| Term | Meaning |
|---|---|
| Operation | a description of 1 change to a document |
| Concurrent | made without knowledge of each other |
| Convergence | all replicas reaching the same state once every operation has been delivered |
| Divergence | replicas that hold different states and will not come together |
| Operational transformation, OT | adjusting an operation to take account of concurrent ones |
| Revision | the number of operations that the server has applied to a document |
| Conflict-free replicated data type, CRDT | a data structure whose operations give the same result in any order |
| Tombstone | a deleted element that is kept, hidden, as a point of reference |
| Ephemeral | forwarded and not stored |
| Snapshot | the state of a document at 1 revision, saved so that earlier operations need not be replayed |

<div class="summary">

## Summary

- Each author's changes are applied to their own copy at once, so that every copy is a replica that accepts writes without coordination.
- An operation described by position is wrong on a replica where earlier concurrent changes have moved the text, and the replicas diverge.
- Operational transformation adjusts each operation for the concurrent ones its author had not seen.
- A central server fixes a single order of operations, which reduces transformation to a manageable problem.
- A CRDT gives every character an unchanging identifier, so that operations can be applied in any order and no server is needed.
- Deleted characters are kept as tombstones, since concurrent operations may refer to them.
- Convergence makes all copies equal, and does not make the result what anybody intended.
- The document is a log of operations with periodic snapshots, served for each document by a single process.

</div>
