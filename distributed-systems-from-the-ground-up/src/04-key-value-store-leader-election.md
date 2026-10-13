<img class="plate" src="art/ch04.svg?v=56c02505" alt="3 cats sit in boxes numbered 1, 2 and 3. The cat in box 3 wears a small crown, and the other 2 cats each hold up a paper marked with a tick. A ballot box stands between them under a banner that reads term 1.">

# Key-Value Store: Leader Election (Low-Level Design)

In [chapter 3](03-key-value-store-replication.md) the leader of each shard was
appointed by an operator, and when a leader was lost its shard could accept no writes
until somebody promoted a follower by hand. Non-functional requirement 1 of
[chapter 1](01-key-value-store-system-design.md) allows 21.6 minutes of failed
requests in a month, and no procedure that depends on a person noticing a failure,
understanding it and typing commands can be relied upon to stay within such a limit.
The members of a shard have to choose their own leader.

Stated so, the task sounds modest, and it is in fact the hardest problem in this
book. The members must agree on a leader although they can communicate only by
messages that may be lost, although any of them may crash and return at any moment
with whatever it had on disk, and although none of them can tell a crashed member
from one that is merely slow or cut off. The agreement must be such that 2 members
are never leaders at once, since each would then accept writes of which the other
knew nothing. And whoever is chosen must already hold every write that has ever been
acknowledged, since a leader that lacked one would proceed to overwrite it. A group
of machines reaching a decision under these conditions is said to reach *consensus*.

The algorithm used in this chapter is *Raft*, published by Diego Ongaro and John
Ousterhout in 2014 with the stated aim of being understandable, which it is to a
degree that its predecessors were not. Raft combines the replication of chapter 3
with a procedure for voting. We first describe the roles of a member and the rule by
which it votes, and show why that rule guarantees that every new leader holds every
acknowledged record. We then deal with a case that chapter 3 excluded, that of a
member whose log differs from its leader's. Raft is implemented as a library without
any network code, tested by a simulation that crashes members and loses messages at
random, and then run over gRPC as `kvraft`. Finally we measure for how long a shard
of 3 nodes is unavailable when its leader is killed.

<div class="covers">

This chapter covers

- the roles of a member: follower, candidate and leader
- terms, and the state that a member must keep on disk
- election timeouts and the voting rule
- term markers, which record the term of every record without changing the format of the log
- repairing a log that differs from the leader's
- the commit rule for records of earlier terms
- a simulation of 200 random runs with crashes and lost messages
- checking that the simulation would detect a faulty implementation
- `kvraft`: driving Raft with a clock and gRPC
- a measurement of the pause that follows the loss of a leader
- the limitations that remain

</div>

## Overview

Every member of a shard runs the same program and is started in the same way, and
none is configured as the leader. At any moment each member is in 1 of 3 roles.

<figure>
<img src="figures/elect-roles.svg?v=bde23ea5" alt="The 3 roles of a member and the transitions between them. A follower accepts records from a leader. A candidate asks the others for their votes. A leader accepts writes and sends records. Transition 1, follower to candidate: the follower hears nothing from a leader for 1 to 2 seconds. Transition 2, candidate to leader: a majority of the members votes for the candidate. Transition 3, leader to follower: the leader sees a higher term. Transition 4, candidate to follower: the candidate sees a leader of its term, or a higher term.">
<figcaption><b>Figure 4.1</b> The roles of a member and the transitions between them.</figcaption>
</figure>

Time is divided into *terms*, numbered from 1. Every term begins with an election and
has at most 1 leader. When no candidate obtains a majority, the term has no leader,
and another election follows in the next. The implementation keeps the invariants of
chapter 3 and adds 3 more.

5. At most 1 member leads any given term.
6. An elected leader holds every record that was acknowledged in an earlier term.
7. A member removes a record from its log only if the record was not committed.

Invariant 5 holds because every member votes at most once in a term and a candidate
needs the votes of a majority. Any 2 majorities have a member in common, and for 2
candidates to win the same term that member would have had to vote twice. Invariants
6 and 7 are established in the sections on voting and on the repair of logs.

## The messages

Elections add a second call to the protocol of chapter 1, and 2 fields to the
existing `Append` call.

<p class="listing"><img class="mascot" src="art/crab-happy.svg" alt=""><b>Listing 4.1</b> The election service in the schema. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/distributed-systems-from-the-ground-up/code/proto/store.proto">proto/store.proto</a></p>

```protobuf
{{#include ../code/proto/store.proto:election}}
```


<p class="listing"><img class="mascot" src="art/crab-happy.svg" alt=""><b>Listing 4.2</b> The replication service, with fields 6 and 7 added. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/distributed-systems-from-the-ground-up/code/proto/store.proto">proto/store.proto</a></p>

```protobuf
{{#include ../code/proto/store.proto:replication}}
```


`AppendRequest` has gained the fields `previous_term` and `leader`, under the unused
numbers 6 and 7. This is the evolution of a schema as chapter 1 described it. The
existing fields have kept their numbers, `kvnode`, the program of chapter 3, makes no
use of the new ones, and a node built from the earlier schema passes over them when it
decodes a message.

As in chapter 3, the library has message types of its own.

<p class="listing"><img class="mascot" src="art/crab-happy.svg" alt=""><b>Listing 4.3</b> The imports of <code>raft/src/lib.rs</code>. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/distributed-systems-from-the-ground-up/code/raft/src/lib.rs">raft/src/lib.rs</a></p>

```rust
{{#include ../code/raft/src/lib.rs:imports}}
```

<p class="listing"><img class="mascot" src="art/crab-happy.svg" alt=""><b>Listing 4.4</b> The messages of the library. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/distributed-systems-from-the-ground-up/code/raft/src/lib.rs">raft/src/lib.rs</a></p>

```rust
{{#include ../code/raft/src/lib.rs:messages}}
```


## The state of a member

<p class="listing"><img class="mascot" src="art/crab-happy.svg" alt=""><b>Listing 4.5</b> The roles, the election timeout, and the state of a member. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/distributed-systems-from-the-ground-up/code/raft/src/lib.rs">raft/src/lib.rs</a></p>

```rust
{{#include ../code/raft/src/lib.rs:member}}
```


A member holds 3 kinds of state, which differ in whether they have to survive a
restart, and the distinction is among the most important things to understand about
the algorithm.

<figure>
<img src="figures/elect-disk-memory.svg?v=9964293d" alt="The state of a member, divided by where it is kept. On disk, where it must survive a restart: the file kv.log with the records and the term markers, and the file state with the term and the vote. In memory, rebuilt after a restart: records and terms, read from kv.log, and term and voted_for, read from state, and entries and committed, which start empty and at 0, and role and leader, which start as follower with no leader known.">
<figcaption><b>Figure 4.2</b> The state of a member, divided into what is on disk and what is rebuilt.</figcaption>
</figure>

| State | Fields | On disk | Why |
|---|---|---|---|
| The log | `log`, `records`, `terms` | yes | The log is the data. |
| The term and the vote | `term`, `voted_for` | yes, in the file `state` | A member that forgot its vote in a restart could vote a second time in the same term, and 2 leaders could then be elected in 1 term. |
| Everything else | `role`, `leader`, `committed`, `entries`, `progress` | no | This state is derived from the log and from messages, and is rebuilt after a restart. |

The second row is easily overlooked. It is natural to think of a vote as a passing
event, of no interest once the election is over. But the whole guarantee of invariant
5 rests on each member voting once, and a member that crashed after voting and
returned with no memory of having done so could give a second vote in the same term
to a different candidate. A vote is therefore a promise, and it is written to disk
before it is sent.

`Member::open` reads both files. From the log it obtains the records and, by means of
the term markers described below, the term of each. From the state file it obtains
the term and the vote. Everything else begins from fixed values: a member that has
been opened is a follower, knows of no leader, and has applied nothing.

<p class="listing"><img class="mascot" src="art/crab-happy.svg" alt=""><b>Listing 4.6</b> Opening a member. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/distributed-systems-from-the-ground-up/code/raft/src/lib.rs">raft/src/lib.rs</a></p>

```rust
{{#include ../code/raft/src/lib.rs:open}}
```


The state file is replaced by writing a new file and renaming it over the old one. On
POSIX file systems, a rename within a directory is atomic, so that after a crash the
file holds either the old state or the new and never a mixture. A member writes this
file before it sends any message that depends on a new term or a new vote.

<p class="listing"><img class="mascot" src="art/crab-happy.svg" alt=""><b>Listing 4.7</b> Reading and writing the term and the vote. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/distributed-systems-from-the-ground-up/code/raft/src/lib.rs">raft/src/lib.rs</a></p>

```rust
{{#include ../code/raft/src/lib.rs:state}}
```


### The term of a record

Raft needs to know in which term each record was written. The record format of
chapter 2 has no field for it, and the implementation records terms without altering
that format, by means of a *term marker*: the first record that a new leader writes
is a `Put` with an empty key and the leader's term as its value. Clients cannot write
an empty key, since the API requires at least 1 character, so that a marker cannot
collide with any client's data. The term of any record is then the term of the most
recent marker at or before it.

<p class="listing"><img class="mascot" src="art/crab-happy.svg" alt=""><b>Listing 4.8</b> Term markers, and the term of each record of a log. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/distributed-systems-from-the-ground-up/code/raft/src/lib.rs">raft/src/lib.rs</a></p>

```rust
{{#include ../code/raft/src/lib.rs:terms}}
```


The markers have a second function, which is described under the commit rule.

## Elections

### The election timeout

A follower expects a message from its leader at least once in every tick of 100 ms.
Having received none for the whole of its *election timeout*, it concludes that the
leader has failed and stands for election.

If all followers used the same timeout, they would all stand at the same moment, each
would vote for itself, and no candidate would obtain a majority. The timeouts are
therefore made to differ. `election_timeout`, in the listing above, computes a value
between 10 and 19 ticks from the id of the member and its term. Within a term, the
members of a shard obtain different values, and each member obtains a different value
in each term, so that 2 members which happen to coincide once do not coincide again.
Raft as published uses random timeouts for this purpose. Timeouts that are computed
make the simulation later in the chapter repeatable.

On reaching its timeout, a member calls `stand`. It increases its term, records a
vote for itself, and stores both on disk before any request leaves. Every
`VoteRequest` carries the end of the candidate's log, which the voting rule below
compares with the log of each voter.

<p class="listing"><img class="mascot" src="art/crab-happy.svg" alt=""><b>Listing 4.9</b> Standing for election. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/distributed-systems-from-the-ground-up/code/raft/src/lib.rs">raft/src/lib.rs</a></p>

```rust
{{#include ../code/raft/src/lib.rs:stand}}
```


<figure>
<img src="figures/elect-steps.svg?v=302a35e4" alt="The first election of a shard, in 8 steps. Step 1: 3 members start as followers in term 0, with election timeouts of 17, 14 and 11 ticks. Step 2: after 11 ticks, member 3 stands for term 1 and stores term 1 and its own vote on disk. Step 3: it sends RequestVote to members 1 and 2 with the end of its log and the term of that record. Step 4: members 1 and 2 grant their votes, each storing the vote on disk before answering. Step 5: member 3 has 3 votes of 3 and leads term 1. Step 6: it appends the marker of term 1 as record 1 and sends it to both followers. Step 7: the followers store record 1 and answer, and record 1 is committed. Step 8: the leader accepts writes, and the first write becomes record 2.">
<figcaption><b>Figure 4.3</b> The first election of a shard. The steps are numbered from 1 to 8.</figcaption>
</figure>

### The voting rule

A member grants its vote to a candidate when 3 conditions are satisfied.

| Condition | Purpose |
|---|---|
| The candidate's term equals the member's term. A request with a higher term first moves the member to that term. | A candidate of an earlier term cannot win. |
| The member has not voted for a different candidate in this term. | At most 1 leader in a term (invariant 5). |
| The candidate's log ends at least as far as the member's own. The terms of the last records are compared first, and the sequences if the terms are equal. | The leader holds every acknowledged record (invariant 6). |

<p class="listing"><img class="mascot" src="art/crab-happy.svg" alt=""><b>Listing 4.10</b> Granting a vote, and counting the votes received. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/distributed-systems-from-the-ground-up/code/raft/src/lib.rs">raft/src/lib.rs</a></p>

```rust
{{#include ../code/raft/src/lib.rs:vote}}
```


<figure>
<img src="figures/elect-vote-rule.svg?v=6889a6eb" alt="The rule for granting a vote, with 3 logs. Member 1 has 4 records, all of term 1. Member 2 has 5 records, the last of term 2. Member 3 has 3 records of term 1. The ends of the logs, as term and sequence, are 1 and 4, 2 and 5, and 1 and 3. If member 2 stands, it receives both votes. If member 1 stands, only member 3 votes for it, and member 2 refuses. If member 3 stands, it receives no vote. A member votes only for a candidate whose log ends at least as Far as its own, and term is compared first, then sequence.">
<figcaption><b>Figure 4.4</b> The voting rule applied to 3 logs.</figcaption>
</figure>

The third condition establishes invariant 6, by the argument that chapter 1 gave in
outline. An acknowledged record is stored on a majority of the members, and a
candidate needs the votes of a majority. Since 2 majorities share at least 1 member,
some voter holds the record. That voter grants its vote only to a candidate whose log
ends at least as far as its own, and such a candidate holds the record as well. A
candidate that lacks an acknowledged record therefore cannot collect a majority. The
choice that an operator made in chapter 3, by reading 2 numbers and promoting the
follower with the longer log, is here made by the members themselves, each refusing
its vote to anyone who knows less than it does.

In `on_vote`, the 3 conditions are `request.term == self.term`, `free` and
`complete`. Tuples in Rust are compared by their first elements, with the second
consulted only in a tie, so that `(last_term, last_sequence) >= (...)` is precisely
the comparison that the rule requires. A vote that is granted is written to disk
before any answer is returned. `on_voted` counts the votes for a candidate, and the
vote that completes a majority triggers `lead`.

Terms are compared before sequences because a longer log is not necessarily a more
complete one. In figure 4.4, a member that had been isolated might have
accumulated several uncommitted records of term 1, and its log would then be longer
than that of member 2. A record of term 2 at the end of member 2's log shows that
member 2 has received records from a later leader, and its log takes precedence.

### Becoming the leader

`lead` does 3 things. For every follower it records where to begin sending, namely at
the end of its own log, as a first guess that a refusal will correct. It then appends
the marker of its term, and finally sends its first messages.

<p class="listing"><img class="mascot" src="art/crab-happy.svg" alt=""><b>Listing 4.11</b> Becoming the leader. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/distributed-systems-from-the-ground-up/code/raft/src/lib.rs">raft/src/lib.rs</a></p>

```rust
{{#include ../code/raft/src/lib.rs:lead}}
```


### Returning to follower

Every message carries the term of its sender. On seeing, in any message, a term
higher than its own, a member calls `step_down`: it adopts that term, clears its
vote, since the vote belonged to an earlier term, and continues as a follower. For a
leader, this is how the arrival of a successor makes itself known.

<p class="listing"><img class="mascot" src="art/crab-happy.svg" alt=""><b>Listing 4.12</b> Adopting a higher term. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/distributed-systems-from-the-ground-up/code/raft/src/lib.rs">raft/src/lib.rs</a></p>

```rust
{{#include ../code/raft/src/lib.rs:step_down}}
```


## Repairing a log that differs

In chapter 3 the log of a follower was always a prefix of its leader's, and a former
leader had to rejoin with an empty log. With elections, a member can hold records
that its present leader lacks. This comes about when a leader appends a record and
fails before sending it. The record exists on 1 member only and was never
acknowledged, and the new leader writes a different record at the same sequence.

`Append` detects such a difference through the field `previous_term`. A follower
appends records only if its own record at `previous_sequence` has the term
`previous_term`. The check is sufficient on account of a single property: if 2 logs
contain a record with the same sequence and the same term, the 2 logs are identical
up to that record. The property holds because each term has 1 leader, a leader writes
each sequence once, and the check is applied on every append, so that agreement at 1
position has always been built upon agreement at the position before.

<figure>
<img src="figures/elect-repair.svg?v=5de06754" alt="How a member whose log differs from the leader&#x27;s is repaired. The leader has 6 records: 4 of term 1 and 2 of term 2. Member 3 has 5 records of term 1, and its record 5 was written in term 1 and never committed. Step 1: the leader sends record 6 with previous sequence 5 and term 2. Step 2: member 3 finds that its record 5 is of term 1, refuses, and answers that the leader should continue from 4. Step 3: the leader sends records 5 and 6 with previous sequence 4 and term 1, which matches. Step 4: member 3 compares its record 5 with the leader&#x27;s, finds that they differ, and removes its record 5. Step 5: member 3 appends the leader&#x27;s records 5 and 6, and both logs are equal.">
<figcaption><b>Figure 4.5</b> The repair of a member that holds a record which the leader does not have.</figcaption>
</figure>

On the follower's side, the handling of `Append` consists of 3 checks followed by the
repair itself.

<figure>
<img src="figures/elect-append-flow.svg?v=21d1107d" alt="The decisions of on_append. First check: is the term of the message at least the member&#x27;s own? If no, refuse and report the end of the log. Second check: does the member have a record at previous_sequence? If no, refuse and report the end of the log. Third check: is the member&#x27;s record at that sequence of the term previous_term? If no, refuse and report the sequence before it. If all 3 checks pass, the member stores the records, applies the committed ones and answers that it appended. Passing the first check also makes the member a follower of the sender and restarts its election timeout.">
<figcaption><b>Figure 4.6</b> The checks that a member applies to an `Append` message, in order.</figcaption>
</figure>

The third check carries a hint for the leader. When its record at `previous_sequence`
has a different term, the member answers with `previous_sequence - 1`, and the leader
begins its next message 1 record earlier. By repeating this, the leader moves
backwards through its log until it arrives at a record on which the 2 logs agree.

<p class="listing"><img class="mascot" src="art/crab-happy.svg" alt=""><b>Listing 4.13</b> The checks of <code>Append</code>. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/distributed-systems-from-the-ground-up/code/raft/src/lib.rs">raft/src/lib.rs</a></p>

```rust
{{#include ../code/raft/src/lib.rs:on_append}}
```


Once all the checks have passed, the 2 logs are known to be equal up to
`previous_sequence`, and `store` makes the member's log equal to the leader's for
every record that follows.

<figure>
<img src="figures/elect-store-example.svg?v=b7fb4e60" alt="An example of the method store. The member holds d, e, x and y at sequences 4 to 7. The leader sends e, f, g and h for sequences 5 to 8, with previous_sequence 4, where both logs hold d in the same term. Step 1: record 5 is e in both logs with the same term, so it is skipped. Step 2: record 6 is x in the member&#x27;s log and f from the leader, so the member removes x and y. Step 3: it appends f, g and h in 1 write, and the log is d, e, f, g, h.">
<figcaption><b>Figure 4.7</b> The method `store` applied to a log that differs from the leader's at record 6.</figcaption>
</figure>

<p class="listing"><img class="mascot" src="art/crab-happy.svg" alt=""><b>Listing 4.14</b> Skipping equal records, removing differing ones, and appending the rest. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/distributed-systems-from-the-ground-up/code/raft/src/lib.rs">raft/src/lib.rs</a></p>

```rust
{{#include ../code/raft/src/lib.rs:store}}
```


For each incoming record, `store` computes a term from `previous_term` and from the
markers among the incoming records, exactly as `terms_of` does for a whole log. 2
records count as equal only if both their terms and their contents agree.

<p class="listing"><img class="mascot" src="art/crab-happy.svg" alt=""><b>Listing 4.15</b> Removing uncommitted records. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/distributed-systems-from-the-ground-up/code/raft/src/lib.rs">raft/src/lib.rs</a></p>

```rust
{{#include ../code/raft/src/lib.rs:truncate}}
```


`truncate` refuses to remove a committed record and returns an error. By invariant 6
the situation cannot arise, since a leader holds every committed record and its log
cannot differ from a follower's at a committed position. The check is there
nonetheless, and for a good reason. Should the invariant ever be violated, through a
defect in this code or a fault in a disk, the result without the check would be
acknowledged data silently destroyed, and with it the member stops. A program that
verifies what it believes to be impossible converts its own undiscovered defects from
corruption into failures that somebody will notice.

In order to truncate its file, a member needs the byte offset at which the last
record to be kept ends. It computes that offset by encoding the records that are kept
and summing their lengths, which avoids storing an offset for every record.

The log of chapter 2 gains a method for removing records from its end.

<p class="listing"><img class="mascot" src="art/crab-happy.svg" alt=""><b>Listing 4.16</b> The imports of <code>kv/src/log.rs</code>. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/distributed-systems-from-the-ground-up/code/kv/src/log.rs">kv/src/log.rs</a></p>

```rust
{{#include ../code/kv/src/log.rs:imports}}
```

<p class="listing"><img class="mascot" src="art/crab-happy.svg" alt=""><b>Listing 4.17</b> Removing records from the end of the log. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/distributed-systems-from-the-ground-up/code/kv/src/log.rs">kv/src/log.rs</a></p>

```rust
{{#include ../code/kv/src/log.rs:truncate}}
```


This method qualifies invariant 4 of chapter 2, which stated that the log is modified
only by appending. Stated exactly, no committed record is ever modified. Records
beyond the committed sequence may be removed, and invariant 7 of this chapter ensures
that only such records are.

### The leader's view of a follower

For every follower, the leader keeps 2 sequences. `next` is where its next message
will begin, and it moves backwards on a refusal. `matched` is the highest sequence
that the follower has confirmed, and it only ever increases. The commit rule uses
`matched`, since `next` is a guess. `on_appended` updates both from an answer, applies
the commit rule, and returns a further message when the follower is still behind.

<p class="listing"><img class="mascot" src="art/crab-happy.svg" alt=""><b>Listing 4.18</b> Processing the answer of a follower. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/distributed-systems-from-the-ground-up/code/raft/src/lib.rs">raft/src/lib.rs</a></p>

```rust
{{#include ../code/raft/src/lib.rs:on_appended}}
```


## The commit rule

<p class="listing"><img class="mascot" src="art/crab-happy.svg" alt=""><b>Listing 4.19</b> Applying committed records, and the leader's commit rule. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/distributed-systems-from-the-ground-up/code/raft/src/lib.rs">raft/src/lib.rs</a></p>

```rust
{{#include ../code/raft/src/lib.rs:commit}}
```


The commit rule of chapter 3 committed a record as soon as a majority had stored it.
`advance` adds a condition, that the record at the majority position must belong to
the leader's own term, and the reason for it is the subtlest point in Raft. A record
of an earlier term can still be replaced even when a majority holds it, if a member
that lacks it comes to be elected by members that lack it too, which remains possible
for as long as no record of the current term is stored on a majority. Counting
replicas is therefore safe only for records of the current term. Records of earlier
terms are committed indirectly, at the moment when a record of the current term at a
later sequence is committed.

It is here that the markers perform their second function. A new leader appends a
marker as the first record of its term, and as soon as a majority has stored it, the
marker and every record before it are committed together. Without markers, the
records inherited from earlier terms would remain uncommitted until the first write
of a client in the new term happened to arrive.

## The clock and the messages

The library reads no clock and opens no connection. Its caller invokes `tick` at a
fixed interval and `handle` for every incoming message, and sends whatever messages
either method returns. As in chapter 3, this separation is what makes the algorithm
testable, since a test can then supply the clock and the network itself.

<p class="listing"><img class="mascot" src="art/crab-happy.svg" alt=""><b>Listing 4.20</b> The clock: heartbeats for a leader, the election timeout for the others. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/distributed-systems-from-the-ground-up/code/raft/src/lib.rs">raft/src/lib.rs</a></p>

```rust
{{#include ../code/raft/src/lib.rs:tick}}
```


<p class="listing"><img class="mascot" src="art/crab-happy.svg" alt=""><b>Listing 4.21</b> Dispatching a message. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/distributed-systems-from-the-ground-up/code/raft/src/lib.rs">raft/src/lib.rs</a></p>

```rust
{{#include ../code/raft/src/lib.rs:handle}}
```


<p class="listing"><img class="mascot" src="art/crab-happy.svg" alt=""><b>Listing 4.22</b> The operations for client requests. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/distributed-systems-from-the-ground-up/code/raft/src/lib.rs">raft/src/lib.rs</a></p>

```rust
{{#include ../code/raft/src/lib.rs:client}}
```


`can_read` permits a read when the member is the leader, when the marker of its term
is committed, and when a majority of the members has answered within the last 10
ticks. The second of these conditions ensures that the entries reflect every record
that was committed in earlier terms.

## Simulating crashes and lost messages

Because the library is free of clocks and connections, a test has control of all of
them. `raftsim` runs 3 members in a single process. It decides when the clock of each
member ticks, which message is delivered next, which messages are lost, and when a
member crashes and restarts.

<p class="listing"><img class="mascot" src="art/crab-happy.svg" alt=""><b>Listing 4.23</b> The imports of <code>raftsim/src/main.rs</code>. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/distributed-systems-from-the-ground-up/code/raftsim/src/main.rs">raftsim/src/main.rs</a></p>

```rust
{{#include ../code/raftsim/src/main.rs:imports}}
```

<p class="listing"><img class="mascot" src="art/crab-happy.svg" alt=""><b>Listing 4.24</b> A repeatable source of pseudo-random numbers. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/distributed-systems-from-the-ground-up/code/raftsim/src/main.rs">raftsim/src/main.rs</a></p>

```rust
{{#include ../code/raftsim/src/main.rs:random}}
```


<p class="listing"><img class="mascot" src="art/crab-happy.svg" alt=""><b>Listing 4.25</b> The cluster: members, messages in transit, and writes. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/distributed-systems-from-the-ground-up/code/raftsim/src/main.rs">raftsim/src/main.rs</a></p>

```rust
{{#include ../code/raftsim/src/main.rs:cluster}}
```


After every step, `raftsim` checks 3 properties.

<p class="listing"><img class="mascot" src="art/crab-happy.svg" alt=""><b>Listing 4.26</b> The properties checked after every step. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/distributed-systems-from-the-ground-up/code/raftsim/src/main.rs">raftsim/src/main.rs</a></p>

```rust
{{#include ../code/raftsim/src/main.rs:check}}
```


A write counts as acknowledged under exactly the condition that the node itself
applies: the member that accepted it has committed its record while still leading the
same term.

<p class="listing"><img class="mascot" src="art/crab-happy.svg" alt=""><b>Listing 4.27</b> A scripted election, a crashed leader, and the repair of its log. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/distributed-systems-from-the-ground-up/code/raftsim/src/main.rs">raftsim/src/main.rs</a></p>

```rust
{{#include ../code/raftsim/src/main.rs:cases}}
```


<p class="listing"><img class="mascot" src="art/crab-happy.svg" alt=""><b>Listing 4.28</b> 200 random runs, and the recovery at the end of each. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/distributed-systems-from-the-ground-up/code/raftsim/src/main.rs">raftsim/src/main.rs</a></p>

```rust
{{#include ../code/raftsim/src/main.rs:runs}}
```


Each run takes 600 random steps. A step ticks the clock of a member (40%), delivers a
message (42%), loses a message (5%), crashes a member (3%), restarts a member (4%) or
sends a write (6%). At the end of a run, all members are started, all messages are
delivered, and `raftsim` verifies that the members agree on a leader and on a log, and
that the leader returns every acknowledged write.

<p class="listing"><img class="mascot" src="art/crab-happy.svg" alt=""><b>Listing 4.29</b> Running the simulation. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/distributed-systems-from-the-ground-up/code/raftsim/src/main.rs">raftsim/src/main.rs</a></p>

```rust
{{#include ../code/raftsim/src/main.rs:main}}
```


```console
$ cargo run --release -p raftsim
start:            1: Follower term 0 log 0 | 2: Follower term 0 log 0 | 3: Follower term 0 log 0
after 11 ticks:   1: Follower term 1 log 1 | 2: Follower term 1 log 1 | 3: Leader term 1 log 1
after 3 writes:   1: Follower term 1 log 4 | 2: Follower term 1 log 4 | 3: Leader term 1 log 4, 3 acknowledged
leader 3 appends record 5 and crashes: 1: Follower term 1 log 4 | 2: Follower term 1 log 4 | 3: down
after 10 ticks:   1: Leader term 2 log 5 | 2: Follower term 2 log 5 | 3: down
after 1 write:    1: Leader term 2 log 6 | 2: Follower term 2 log 6 | 3: down, 4 acknowledged
member 3 returns: 1: Leader term 2 log 6 | 2: Follower term 2 log 6 | 3: Follower term 1 log 5
after 2 ticks:    1: Leader term 2 log 6 | 2: Follower term 2 log 6 | 3: Follower term 2 log 6
member 3 discarded 1 record that was never committed, and holds the leader's records in its place
200 runs of 600 random steps:
  480 leaders were elected, and no term had 2 leaders
  504 writes were acknowledged, and every one was present after recovery
  18 uncommitted records were discarded by members whose log differed from a leader's
  the highest term reached in a run was 8
```

| Output | What it shows |
|---|---|
| after 11 ticks: member 3 is Leader of term 1, all logs at 1 | Member 3 has the shortest timeout in term 0. Record 1 is the term marker. |
| leader 3 appends record 5 and crashes: the others have 4 records | Record 5 exists on member 3 only and was not acknowledged. |
| after 10 ticks: member 1 is Leader of term 2, logs at 5 | Member 1 was elected by itself and member 2. Its record 5 is the marker of term 2. |
| member 3 returns: Follower, term 1, log 5 | Member 3 holds a record 5 that differs from the leader's record 5. |
| after 2 ticks: member 3 at term 2, log 6; it discarded 1 record | The repair removed the uncommitted record and installed the leader's records. |
| 480 leaders were elected, and no term had 2 leaders | Invariant 5 held at every step of every run. |
| 504 writes were acknowledged, and every one was present after recovery | Invariant 6 held. |
| 18 uncommitted records were discarded | The runs produced logs that differed, and the repair resolved them without the loss of an acknowledged write. |

### Checking the simulation

A simulation that reports no failure is informative only if it would have reported
one for an incorrect implementation, and this is a question that can be put to the
test. We disabled 3 rules of Raft in turn and ran the simulation against each
modified library.

| Rule disabled | Result |
|---|---|
| A member votes only for a candidate whose log is at least as complete as its own. | detected: `member 2 lost acknowledged write of key-1` |
| A member votes at most once in a term. | detected: `members 1 and 3 both lead term 4` |
| The leader commits by counting only for records of its own term. | not detected: all 200 runs passed |

The third result has to be stated with care. The correctness of Raft requires this
condition, and the implementation contains it. With 3 members and 200 runs, however,
the simulation did not produce a sequence of events in which the absence of the
condition leads to an error. In the paper on Raft, such a sequence involves 5 members
and several successive failures of leaders at particular moments. The simulation
therefore provides evidence for the voting rules and for the repair of logs, and
provides none for this condition. It would have been easy to report "200 runs passed"
and to leave the reader with the impression that everything had been verified, and
the difference between what a test exercises and what it merely fails to contradict
is one that this book tries to keep in view.

## Design overview

<div class="lld">

Low-level design: leader election

**Crates**

| Crate | Kind | Contents |
|---|---|---|
| `raft` | library | `Member`: roles, voting, the repair of logs, the commit rule, with no network and no clock |
| `raftsim` | program | the simulation |
| `kvraft` | program | a node: `rpc` (both gRPC services), `node` (the clock, sending messages, writes and reads), `main` (the HTTP API) |
| `probe` | program | a client that measures the longest pause between acknowledged writes |

**Rules of a member**

| Event | Action |
|---|---|
| Any message with a higher term | adopt the term, clear the vote, become a follower |
| `Append` with a lower term | refuse, and report the member's own term |
| `Append` whose `previous_sequence` is beyond the end of the log | refuse, and report the end of the log |
| `Append` whose `previous_term` differs from the term of the member's record at that sequence | refuse, and report the sequence before it |
| `Append` that matches | skip identical records, remove the first differing record and everything after it, append the rest, apply up to the committed sequence |
| `RequestVote` | grant if the term is current, no other vote was given in this term, and the candidate's log ends at least as far |
| No message from a leader for the election timeout | increase the term, vote for itself, send `RequestVote` to all members |
| Votes from a majority | become the leader, append the term marker, send `Append` to all members |

**Timing**

| Quantity | Value |
|---|---|
| Tick | 100 ms |
| Heartbeat interval of a leader | 1 tick |
| Election timeout | 10 to 19 ticks, computed from the member's id and term |
| Time a write waits for its record to be committed | 1 s |

</div>

## The node

`kvraft` connects the library to a clock, to a network and to an HTTP API. All
members are started with the same options, apart from their ids and addresses.

<p class="listing"><img class="mascot" src="art/crab-happy.svg" alt=""><b>Listing 4.30</b> The imports of <code>kvraft/src/main.rs</code>. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/distributed-systems-from-the-ground-up/code/kvraft/src/main.rs">kvraft/src/main.rs</a></p>

```rust
{{#include ../code/kvraft/src/main.rs:imports}}
```

<p class="listing"><img class="mascot" src="art/crab-happy.svg" alt=""><b>Listing 4.31</b> The options of the command line. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/distributed-systems-from-the-ground-up/code/kvraft/src/main.rs">kvraft/src/main.rs</a></p>

```rust
{{#include ../code/kvraft/src/main.rs:options}}
```


<p class="listing"><img class="mascot" src="art/crab-happy.svg" alt=""><b>Listing 4.32</b> The imports of <code>kvraft/src/rpc.rs</code>. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/distributed-systems-from-the-ground-up/code/kvraft/src/rpc.rs">kvraft/src/rpc.rs</a></p>

```rust
{{#include ../code/kvraft/src/rpc.rs:imports}}
```

<p class="listing"><img class="mascot" src="art/crab-happy.svg" alt=""><b>Listing 4.33</b> Conversion between the generated types and the library's messages. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/distributed-systems-from-the-ground-up/code/kvraft/src/rpc.rs">kvraft/src/rpc.rs</a></p>

```rust
{{#include ../code/kvraft/src/rpc.rs:convert}}
```


Each gRPC call delivers 1 message to a member, and the member's answer is returned as
the response to the call.

<p class="listing"><img class="mascot" src="art/crab-happy.svg" alt=""><b>Listing 4.34</b> The server side of <code>Append</code> and <code>RequestVote</code>. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/distributed-systems-from-the-ground-up/code/kvraft/src/rpc.rs">kvraft/src/rpc.rs</a></p>

```rust
{{#include ../code/kvraft/src/rpc.rs:service}}
```


Around the member, a node consists of a small loop, which is shown in figure
4.elect-node-loop.

<p class="listing"><img class="mascot" src="art/crab-happy.svg" alt=""><b>Listing 4.35</b> The imports of <code>kvraft/src/node.rs</code>. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/distributed-systems-from-the-ground-up/code/kvraft/src/node.rs">kvraft/src/node.rs</a></p>

```rust
{{#include ../code/kvraft/src/node.rs:imports}}
```

<p class="listing"><img class="mascot" src="art/crab-happy.svg" alt=""><b>Listing 4.36</b> The state of a node. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/distributed-systems-from-the-ground-up/code/kvraft/src/node.rs">kvraft/src/node.rs</a></p>

```rust
{{#include ../code/kvraft/src/node.rs:types}}
```


<figure>
<img src="figures/elect-node-loop.svg?v=4f8fba54" alt="How kvraft drives a member. A clock task, every 100 ms, and an HTTP handler, for a write, call the member, which is behind a mutex. Step 1: the clock or a handler calls the member under the lock. Step 2: the member returns the messages that have to be sent. Step 3: dispatch sends each message as a gRPC call, Append or RequestVote, in its own task and with a time limit of 500 ms. Step 4: the response is a message too, and it goes back to the member, which may return more messages.">
<figcaption><b>Figure 4.8</b> The loop that connects a member to the clock and to the other members.</figcaption>
</figure>

`with_member` is the single point of entry to the member. It takes the lock, runs the
operation it is given, and publishes the committed sequence afterwards, so that no
operation can change that sequence without the waiting writes being informed.

<p class="listing"><img class="mascot" src="art/crab-happy.svg" alt=""><b>Listing 4.37</b> Running an operation on the member. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/distributed-systems-from-the-ground-up/code/kvraft/src/node.rs">kvraft/src/node.rs</a></p>

```rust
{{#include ../code/kvraft/src/node.rs:with_member}}
```


`dispatch` starts 1 task for each message, and `send` performs a gRPC call with a
time limit. Each response is converted into the corresponding answer message and
handed to `deliver`, which passes it to the member and dispatches whatever the member
returns. A call that fails or times out produces no message at all, which Raft
tolerates without any special provision, since the next tick sends a new message to
the same member.

<p class="listing"><img class="mascot" src="art/crab-happy.svg" alt=""><b>Listing 4.38</b> Sending a message and delivering the answer. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/distributed-systems-from-the-ground-up/code/kvraft/src/node.rs">kvraft/src/node.rs</a></p>

```rust
{{#include ../code/kvraft/src/node.rs:send}}
```


`run_clock` calls `tick` every 100 ms. `answer` serves the gRPC handlers: an incoming
request is 1 message for the member, which returns exactly 1 answer to it.

<p class="listing"><img class="mascot" src="art/crab-happy.svg" alt=""><b>Listing 4.39</b> The clock, and answering a request from another member. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/distributed-systems-from-the-ground-up/code/kvraft/src/node.rs">kvraft/src/node.rs</a></p>

```rust
{{#include ../code/kvraft/src/node.rs:clock}}
```


<p class="listing"><img class="mascot" src="art/crab-happy.svg" alt=""><b>Listing 4.40</b> Writes and reads. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/distributed-systems-from-the-ground-up/code/kvraft/src/node.rs">kvraft/src/node.rs</a></p>

```rust
{{#include ../code/kvraft/src/node.rs:write}}
```


The write path has the structure of chapter 3, with 1 addition after the wait. If a
member loses its leadership while a write is waiting, its uncommitted record may be
replaced by a record of the new leader at the same sequence, and the committed
sequence may then pass that position without the write having been stored at all. A
handler therefore acknowledges a write only if its member still leads the term in
which the record was appended. Otherwise it answers `503`, and the outcome of the
write is unknown to its client, to be resolved as chapter 3 described.

Any member that is not the leader answers `421 Misdirected Request` and names the
leader it knows of in the `detail` field.

<p class="listing"><img class="mascot" src="art/crab-happy.svg" alt=""><b>Listing 4.41</b> The HTTP handlers and the health of a node. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/distributed-systems-from-the-ground-up/code/kvraft/src/main.rs">kvraft/src/main.rs</a></p>

```rust
{{#include ../code/kvraft/src/main.rs:handlers}}
```


<p class="listing"><img class="mascot" src="art/crab-happy.svg" alt=""><b>Listing 4.42</b> Starting a node. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/distributed-systems-from-the-ground-up/code/kvraft/src/main.rs">kvraft/src/main.rs</a></p>

```rust
{{#include ../code/kvraft/src/main.rs:main}}
```


## Running 3 nodes

```console
$ ./target/release/kvraft --id 1 --listen 127.0.0.1:7001 --replication 127.0.0.1:7101 --data /var/tmp/m1 \
      --peer 2=http://127.0.0.1:7102 --peer 3=http://127.0.0.1:7103 &
member 1, term 0, log ends at 0
listening on 127.0.0.1:7001
$ ./target/release/kvraft --id 2 --listen 127.0.0.1:7002 --replication 127.0.0.1:7102 --data /var/tmp/m2 \
      --peer 1=http://127.0.0.1:7101 --peer 3=http://127.0.0.1:7103 &
$ ./target/release/kvraft --id 3 --listen 127.0.0.1:7003 --replication 127.0.0.1:7103 --data /var/tmp/m3 \
      --peer 1=http://127.0.0.1:7101 --peer 2=http://127.0.0.1:7102 &
$ for port in 7001 7002 7003; do curl http://127.0.0.1:$port/healthz; echo; done
{"id":1,"role":"follower","term":1,"leader":3,"last_sequence":1,"committed":1}
{"id":2,"role":"follower","term":1,"leader":3,"last_sequence":1,"committed":1}
{"id":3,"role":"leader","term":1,"leader":3,"last_sequence":1,"committed":1}
```

All 3 members were started without any indication of who should lead. Within 2
seconds, member 3 had been elected in term 1. Every log contains 1 record, the marker
of term 1.

```console
$ curl -i -X PUT http://127.0.0.1:7003/v1/keys/user-1 --data-binary 'ada'
HTTP/1.1 201 Created
etag: "2"
content-length: 0

$ curl -i -X PUT http://127.0.0.1:7001/v1/keys/user-1 --data-binary 'x'
HTTP/1.1 421 Misdirected Request
content-type: application/problem+json
content-length: 116

{"type":"/problems/not-leader","title":"This node is not the leader","status":421,"detail":"the leader is member 3"}
```

The first write of a client receives version 2, since record 1 is the term marker.
Versions remain strictly increasing, which is all that a client is entitled to rely
upon.

## Experiments

As in chapter 3, the 3 nodes run on 1 machine and share its disk.

### The leader is lost

`probe` writes keys continuously for a fixed time. When a node refuses a write or
fails to respond, `probe` sends the write to the next node. It records every
acknowledged key, and the longest interval between 2 consecutive acknowledged writes.

<p class="listing"><img class="mascot" src="art/crab-happy.svg" alt=""><b>Listing 4.43</b> The imports of <code>probe/src/main.rs</code>. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/distributed-systems-from-the-ground-up/code/probe/src/main.rs">probe/src/main.rs</a></p>

```rust
{{#include ../code/probe/src/main.rs:imports}}
```

<p class="listing"><img class="mascot" src="art/crab-happy.svg" alt=""><b>Listing 4.44</b> Measuring the longest pause between acknowledged writes. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/distributed-systems-from-the-ground-up/code/probe/src/main.rs">probe/src/main.rs</a></p>

```rust
{{#include ../code/probe/src/main.rs:probe}}
```


The leader is killed 6 seconds into a run of 20 seconds.

```console
$ ./target/release/probe --seconds 20 --acked acked.txt \
      --server http://127.0.0.1:7001 --server http://127.0.0.1:7002 --server http://127.0.0.1:7003 &
$ sleep 6; kill -9 <pid of member 3, the leader>
$ sleep 3; for port in 7001 7002 7003; do curl http://127.0.0.1:$port/healthz; echo; done
{"id":1,"role":"leader","term":2,"leader":1,"last_sequence":610,"committed":609}
{"id":2,"role":"follower","term":2,"leader":1,"last_sequence":611,"committed":610}
curl: (7) Failed to connect to 127.0.0.1 port 7003
1443 writes acknowledged in 20 seconds, 51 attempts refused
the longest pause between 2 acknowledged writes was 1.05 s, ending 7.1 s after the start
$ ./target/release/kvctl verify --server http://127.0.0.1:7001 --acked acked.txt
1443 acknowledged, 1443 found, 0 missing
```

<figure>
<img src="figures/elect-probe.svg?v=10430968" alt="A timeline of 20 seconds of writes against 3 members. The leader is killed at 6 seconds, and writes resume at 7.1 seconds. 1443 writes were acknowledged, and all were found afterwards. The longest pause between 2 acknowledged writes was 1.05 seconds: the election timeout of the follower that stood, followed by 1 round of votes and 1 round of records. No operator took part.">
<figcaption><b>Figure 4.9</b> The run of 20 seconds, with the pause caused by the loss of the leader.</figcaption>
</figure>

| Output | What it shows |
|---|---|
| member 1: leader, term 2 | A new leader was elected without any action by an operator. |
| longest pause was 1.05 s | Writes were unavailable for about 1 second, which is the election timeout of member 1 in term 1 (10 ticks) together with the exchange of votes and of the term marker. |
| 51 attempts refused | During the pause, `probe` tried the nodes in turn and was refused until member 1 had been elected. |
| 1443 acknowledged, 1443 found, 0 missing | No acknowledged write was lost. |

The measured pause can be set against the availability allowance of chapter 1. For
the shards led by 1 node of 24, a pause of 1 second consumes about 0.04 seconds of a
monthly allowance of 1296. The promotion by hand of chapter 3 would have consumed
minutes.

### The former leader returns

The member that was killed is started again with its data directory intact, which
chapter 3 did not permit.

```console
$ ./target/release/kvraft --id 3 --listen 127.0.0.1:7003 --replication 127.0.0.1:7103 --data /var/tmp/m3 \
      --peer 1=http://127.0.0.1:7101 --peer 2=http://127.0.0.1:7102 &
$ for port in 7001 7002 7003; do curl http://127.0.0.1:$port/healthz; echo; done
{"id":1,"role":"leader","term":2,"leader":1,"last_sequence":1447,"committed":1447}
{"id":2,"role":"follower","term":2,"leader":1,"last_sequence":1447,"committed":1447}
{"id":3,"role":"follower","term":2,"leader":1,"last_sequence":1447,"committed":1447}
$ cmp /var/tmp/m1/kv.log /var/tmp/m2/kv.log && cmp /var/tmp/m1/kv.log /var/tmp/m3/kv.log && echo identical
identical
$ cat /var/tmp/m1/state
2 1
```

It rejoined as a follower of term 2 and received the records it lacked. The 3 logs
are identical, and the state file of member 1 contains `2 1`: term 2, and a vote for
member 1, which it gave to itself when it stood for election.

### A member is left alone

The leader and 1 follower are killed, so that a single member remains.

```console
$ kill -9 <pid of member 2, the leader> <pid of member 3>
$ sleep 5; curl http://127.0.0.1:7001/healthz
{"id":1,"role":"candidate","term":6,"leader":null,"last_sequence":1449,"committed":1449}
$ curl -X PUT http://127.0.0.1:7001/v1/keys/alone --data-binary 'x'
{"type":"/problems/store-unavailable","title":"The node cannot serve the request","status":503,"detail":"the shard has no leader at the moment"}
$ sleep 3; curl http://127.0.0.1:7001/healthz
{"id":1,"role":"candidate","term":8,"leader":null,"last_sequence":1449,"committed":1449}

$ (members 2 and 3 are started again)
$ sleep 4; for port in 7001 7002 7003; do curl http://127.0.0.1:$port/healthz; echo; done
{"id":1,"role":"leader","term":9,"leader":1,"last_sequence":1450,"committed":1450}
{"id":2,"role":"follower","term":9,"leader":1,"last_sequence":1450,"committed":1450}
{"id":3,"role":"follower","term":9,"leader":1,"last_sequence":1450,"committed":1450}
```

| Output | What it shows |
|---|---|
| candidate, term 6, then term 8 | The remaining member stands for election again and again. It cannot obtain a second vote, and every attempt increases its term. |
| the shard has no leader at the moment | Writes and reads are refused. 1 member of 3 cannot determine whether the other 2 have failed or have elected a leader between themselves. |
| after the others return: leader of term 9 | The shard resumed in a term above those that the isolated member had reached. |

This is the minority side of a partition once more, seen from the inside. The lone
member behaves exactly as it would if the other 2 were running and unreachable, as
from its own position it must, since it has no means of telling the 2 situations
apart.

## Limitations

| Limitation | Consequence |
|---|---|
| An isolated member increases its term at every attempt at election. | When it reconnects, its higher term obliges the current leader to step down and causes an unnecessary election. Implementations of Raft avoid this with a preliminary vote that does not increase the term. |
| The set of members is fixed when a node starts. | Adding or replacing a member requires all nodes to be restarted with new options. The procedure of chapter 1 for a node joining the ring is not implemented. |
| Writes are processed in turn. | As in chapter 3, the write rate is 1 write for each round trip: 72 writes per second in the run above. Chapter 6 addresses this. |
| Every member holds all its records in memory, and the log grows without limit. | The time to restart and the memory used grow with the age of the shard. |
| Clients must find the leader for themselves. | `probe` tries each node in turn. The router of chapter 5 does this on the clients' behalf. |
| The commit condition for records of earlier terms is not covered by the simulation. | The condition is implemented, and its absence was not detected by the test. |

## The complete programs

<p class="listing"><img class="mascot" src="art/crab-cute.svg" alt=""><b>Listing 4.45</b> The complete <code>raft/src/lib.rs</code>. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/distributed-systems-from-the-ground-up/code/raft/src/lib.rs">raft/src/lib.rs</a></p>

```rust
{{#include ../code/raft/src/lib.rs}}
```


<p class="listing"><img class="mascot" src="art/crab-cute.svg" alt=""><b>Listing 4.46</b> The complete <code>raftsim/src/main.rs</code>. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/distributed-systems-from-the-ground-up/code/raftsim/src/main.rs">raftsim/src/main.rs</a></p>

```rust
{{#include ../code/raftsim/src/main.rs}}
```


<p class="listing"><img class="mascot" src="art/crab-cute.svg" alt=""><b>Listing 4.47</b> The complete <code>kvraft/Cargo.toml</code>. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/distributed-systems-from-the-ground-up/code/kvraft/Cargo.toml">kvraft/Cargo.toml</a></p>

```toml
{{#include ../code/kvraft/Cargo.toml}}
```


<p class="listing"><img class="mascot" src="art/crab-cute.svg" alt=""><b>Listing 4.48</b> The complete <code>kvraft/src/rpc.rs</code>. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/distributed-systems-from-the-ground-up/code/kvraft/src/rpc.rs">kvraft/src/rpc.rs</a></p>

```rust
{{#include ../code/kvraft/src/rpc.rs}}
```


<p class="listing"><img class="mascot" src="art/crab-cute.svg" alt=""><b>Listing 4.49</b> The complete <code>kvraft/src/node.rs</code>. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/distributed-systems-from-the-ground-up/code/kvraft/src/node.rs">kvraft/src/node.rs</a></p>

```rust
{{#include ../code/kvraft/src/node.rs}}
```


<p class="listing"><img class="mascot" src="art/crab-cute.svg" alt=""><b>Listing 4.50</b> The complete <code>kvraft/src/main.rs</code>. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/distributed-systems-from-the-ground-up/code/kvraft/src/main.rs">kvraft/src/main.rs</a></p>

```rust
{{#include ../code/kvraft/src/main.rs}}
```


<p class="listing"><img class="mascot" src="art/crab-cute.svg" alt=""><b>Listing 4.51</b> The complete <code>probe/src/main.rs</code>. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/distributed-systems-from-the-ground-up/code/probe/src/main.rs">probe/src/main.rs</a></p>

```rust
{{#include ../code/probe/src/main.rs}}
```


## Further reading

- D. Ongaro and J. Ousterhout, "In Search of an Understandable Consensus Algorithm", USENIX ATC 2014.
- D. Ongaro, *Consensus: Bridging Theory and Practice*, doctoral dissertation, Stanford University, 2014.
- L. Lamport, "Paxos Made Simple", ACM SIGACT News, 2001.
- T. Chandra, R. Griesemer and J. Redstone, "Paxos Made Live: An Engineering Perspective", PODC 2007.
- M. Fischer, N. Lynch and M. Paterson, "Impossibility of Distributed Consensus with One Faulty Process", Journal of the ACM, 1985.
- K. Kingsbury, the Jepsen analyses, jepsen.io.

<div class="summary">

## Summary

- Every member starts as a follower, and a follower that hears nothing from a leader for its election timeout becomes a candidate and asks all the others for their votes.
- A member votes at most once in a term, so that a term has at most 1 leader, and the term and the vote are stored on disk before any answer that depends on them is sent.
- A member votes only for a candidate whose log ends at least as far as its own, with terms compared before sequences, from which it follows that an elected leader holds every acknowledged record.
- A term marker, the first record of a leader, records the term of every record without changing the format of the log, and commits the records of earlier terms.
- `Append` carries the term of the record that precedes its new records. A follower whose record at that position has a different term refuses, the leader steps back, and the follower replaces its differing records with the leader's.
- Only uncommitted records are ever removed from a log.
- In 200 simulated runs with crashes and lost messages, 480 leaders were elected with no term having 2, and all 504 acknowledged writes were present after recovery.
- The simulation detected 2 disabled voting rules, and did not detect a disabled commit condition for earlier terms.
- With 3 nodes, killing the leader interrupted writes for 1.05 seconds, and none of 1443 acknowledged writes was lost.

</div>
