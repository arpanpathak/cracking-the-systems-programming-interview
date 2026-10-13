<img class="plate" src="art/ch28.svg?v=a4f03ad7" alt="A hare stands beside a sign that reads: happened at 7, arrived at 13, counted at 7.">

# Click Aggregation: System Design

An advertiser pays for each click on an advertisement, and wishes to know, minute by
minute, how many clicks there have been. A system that answers this question takes
in a stream of events, each recording that somebody clicked on something at some
moment, and turns it continuously into counts: 412 clicks on advertisement 7 between
10:00 and 10:01, 398 in the minute after. The counts feed dashboards that people
watch, budgets that stop an advertisement when its money is spent, and, at the end
of the month, invoices.

Counting sounds like the easiest task a computer could be given, and for events that
arrived promptly, once each and in order, it would be. The events of a real system
do none of those things. A click is recorded on a phone that may be in a tunnel, and
reaches the service seconds or hours after it happened. Events that were sent in 1
order arrive in another. A browser that received no acknowledgement sends the same
click again. And the machines that do the counting fail in the middle of their work,
after they have counted some events and before they have recorded that they did so.
Since money changes hands on the strength of the totals, a count that is 2% too high
is an advertiser overcharged, and one that is 2% too low is revenue lost.

A system that computes results continuously from an unending stream of events is
said to do *stream processing*, and the counting of clicks is its standard example.
The ideas of this chapter apply equally to counting page views, summing sales,
detecting fraud and computing the metrics of chapter 24.

<div class="covers">

This chapter covers

- counting once a day, and why that is too slow
- the 2 times of every event: when it happened, and when it arrived
- windows, and which window an event belongs to
- watermarks, which decide when a window is finished
- events that arrive after their window has been closed
- counting each click once, although it is delivered more than once
- recovering from a failure without counting anything twice
- keeping every raw event, so that the counts can be made again
- a key that receives far more events than the others

</div>

## Counting once a day

The oldest way of producing such counts makes no attempt at continuity. Every click
is appended to a file, and once a day a job reads the day's file from beginning to
end, counts the clicks for each advertisement, and writes the totals. This is *batch
processing*, and it has virtues that should not be underrated. It is simple. It sees
all the data at once, so that late and disordered events present no difficulty
provided they arrived before the job ran. And if the job is found to contain a
defect, it is corrected and run again on the same file.

Its failing is delay. The count for a click made just after midnight is available
some 24 hours later. An advertiser cannot see during the day how a campaign is
performing, and a budget of 1000 that was exhausted by 9 in the morning goes on
being spent until the following night.

Stream processing aims to produce the same counts within seconds, by processing each
event as it arrives. Nearly everything that makes it difficult comes from having
given up the 2 comforts of the batch job, namely that all the data was present
before the work began, and that the whole job could be run again.

## The 2 times of an event

Every event has 2 times associated with it, and to confuse them is the most common
single error in the processing of streams.

The *event time* is the moment at which the thing happened: the instant at which the
visitor's finger touched the advertisement, as recorded by the visitor's device. The
*processing time* is the moment at which the event reaches the system that counts
it. The 2 differ by the time the event spent in transit, which is usually a fraction
of a second and occasionally very much more. A phone without a connection holds its
events until the connection returns. A collector that is restarted delivers a
backlog when it comes back.

The question an advertiser is asking concerns event time. "How many clicks between
10:00 and 10:01" means clicks that were made in that minute, wherever they have been
since. A system that counts by processing time answers a different question, how
many clicks happened to reach the counter in that minute, and its answers are wrong
whenever anything is delayed. Should the collectors be down for 5 minutes and then
deliver everything together, counting by processing time shows 5 minutes with no
clicks followed by 1 minute with 6 times the usual number, and an advertiser whose
campaign ended at 10:03 is charged for clicks made before the end and delivered
after it.

## Windows

A stream has no end, and a count is of a finite set. The stream is therefore divided
into *windows*, finite spans of time, and a count is produced for each. The simplest
kind, the *tumbling window*, divides time into consecutive intervals of equal length
that do not overlap: 10:00 to 10:01, 10:01 to 10:02, and so on. Each event belongs
to exactly 1 window, the one that contains its event time.

Other shapes serve other questions. A *sliding window* covers a fixed span and
advances by a smaller step, as in "the clicks of the last 5 minutes, recomputed
every minute", so that each event belongs to several windows. A *session window*
groups the events of 1 user that follow one another closely, and ends when the user
has been inactive for some time. This chapter uses tumbling windows, which are
sufficient to exhibit every difficulty.

To assign an event to its window by event time is easy: the window is determined by
the timestamp. The hard question is a different one. Since events arrive late and
out of order, the system needs to know when it has received all the events of a
window, so that it may declare the count final and publish it. At 10:01:00 by the
clock, the window from 10:00 to 10:01 is over, in the sense that no more clicks will
be made in it. But clicks that were made in it may still be on their way.

## Watermarks

There is no certain answer to that question, since an event can in principle be
delayed without limit. The system has to make a judgement, and the device by which
the judgement is expressed is the *watermark*.

A watermark is a statement by the system about its own progress through event time:
"I believe I have now received every event that happened before time T". It is an
estimate, derived from the events that have been seen. A simple and common rule
takes the largest event time observed so far and subtracts a fixed allowance for
lateness. If the newest event seen happened at 10:01:09 and the allowance is 5
seconds, the watermark stands at 10:01:04, and the system proceeds on the
assumption that nothing earlier than that is still to come.

A window is declared finished when the watermark passes its end. Until then it is
kept open, and events that belong to it are added to its count although they arrive
after the clock has moved past it.

<figure class="steps" data-prefix="figures/steps-click-watermark" data-count="6" data-version="6aec362f">
<img src="figures/steps-click-watermark-01.svg?v=6aec362f" alt="Windows, late clicks and a watermark, step 1 of 6. Clicks are counted in windows of 10 seconds, by the time at which they happened. 6 clicks of the first window have arrived. The watermark is the newest event time, 9, minus 5: the counter still expects clicks from after 4 s.">
<figcaption><b>Figure 28.1</b> Clicks arrive late, out of order and twice, and a watermark decides when each window is finished. Use Next and Back to move through the 6 steps.</figcaption>
</figure>

In these steps the windows are 10 seconds long and the allowance is 5 seconds. A
click that happened at 7 seconds and arrived at 13 is counted in the first window,
where it belongs, since the watermark had not yet passed the end of that window.
When events from 19 seconds appear, the watermark reaches 14, and the first window
is closed with a count of 7.

The simulation for this chapter runs the same stream through 2 counters. Counting by
arrival time gives 7, 5, 1 and 1 for 4 windows, which is wrong in every window, and
its first figure is right in size only by coincidence, since it includes a duplicate
and omits 2 late clicks. Counting by event time with a watermark gives 7 and 4 for
the first 2 windows, against a truth of 8 and 4.

The size of the allowance is the central parameter of the design, and it expresses a
compromise that cannot be avoided. A generous allowance waits longer, catches more
of the late events, and delays every result by as much. A small allowance publishes
promptly and misses more. Results cannot be both immediate and complete, since
completeness is only known in retrospect, and the choice of where to stand between
the 2 depends on what the counts are used for.

## Events that are later still

Whatever the allowance, some events will arrive after their window has been
declared finished. In the steps above, a click made at 2 seconds arrives a minute
late, long after the first window was closed with a count of 7. The true count for
that window was 8.

There are 3 things that can be done with such an event. It can be discarded, which
is simple and makes the published counts slightly too low for ever. It can be used
to revise the count, with the window's result published a second time as 8, which
requires everything downstream to be able to accept a correction to a figure it has
already received. Or it can be set aside in a separate stream of late events, to be
taken into account by a later and more leisurely process.

For data on which invoices are based, discarding is unacceptable, and the usual
design distinguishes 2 grades of result. The counts published within seconds are
labelled provisional. They drive the dashboards and the budgets, where promptness
matters more than the last fraction of a percent. A final count for each window is
computed later, when even very late events have had time to arrive, and it is the
final counts that are billed. The system states openly which of its figures are of
which grade, and does not present an estimate as though it were settled.

## Counting each click once

The message queue that carries the clicks delivers at least once, as chapter 11
explained, and the devices that send them retry when no acknowledgement comes. The
same click may therefore reach the counter 2 or 3 times, and a counter that counted
every delivery would overcharge the advertiser by the rate of retries.

The remedy is the one that has served throughout this book. Every click is given a
unique identifier at its origin, by the visitor's device, and the counter keeps a
record of the identifiers it has counted, declining to count any that it has seen
before. In the steps above, the second delivery of click 3 is recognised and
ignored.

The set of identifiers seen cannot be allowed to grow for ever, and here the
watermark gives a second service. An identifier needs to be remembered only for as
long as a duplicate of it could still arrive and be counted, which is as long as its
window remains open. When a window is closed, the identifiers that belong to it can
be discarded, since any later duplicate will be classed as a late event and dealt
with by that path.

## Recovering without counting twice

The processor holds state in its memory: the partial counts of the windows that are
open, the identifiers it has seen, and the position it has reached in the log of
clicks. When it fails, a replacement has to continue, and the manner in which it
continues determines whether the counts are right.

If the replacement started with empty state from the present position in the log,
the partial counts of the open windows would be lost, and those windows would be
published too low. If it started with empty state from an earlier position, it would
count again events whose windows had already been published. The difficulty is that
of chapter 11, the gap between doing work and recording that it was done, with the
addition that the work now accumulates in memory over the life of a window.

The solution is to save the state and the position together. At regular intervals
the processor writes a *checkpoint*, which consists of its entire state and the
position in the log up to which that state reflects the input. The essential
property is that the 2 are saved as a unit, so that the state corresponds exactly to
the position. On recovery, the replacement loads the latest checkpoint and resumes
reading from the recorded position. Every event before that position is reflected in
the restored state and is not read again, and every event after it is absent from
the restored state and is read. Each event affects the state exactly once.

There remains the output. Between the last checkpoint and the failure, the processor
may have published the results of some windows, and after recovery it will compute
and publish those windows again. The results must therefore be written in such a way
that writing them twice is harmless. A count is stored under a key formed from the
advertisement and the start of the window, and writing the same count under the same
key a second time merely replaces a value with an equal one. This is an idempotent
write, and it completes the chain. With a log that can be read again from any
position, a checkpoint that pairs state with position, and output that may safely be
repeated, each click contributes to the published totals exactly once, although
individual steps along the way may be performed more than once. This is the
"effectively once" of chapter 11, extended to a computation that keeps state.

## Keeping the raw events

However carefully the stream processor is built, the time will come when its results
are found to be wrong. A defect in the code will have miscounted for a week, or a
definition will change, as when clicks from automated programs, hitherto counted,
are to be excluded. The counts must then be made again, and that is possible only if
the original events still exist.

Every click is therefore retained in its raw form, in the log for some days and in
an archive in the object store of chapter 16 for much longer. The archive is the
authority, and every count is derived from it. A corrected version of the computation
can be run over the archived events to produce corrected counts, which replace the
old ones under the same keys.

This arrangement also provides the final counts mentioned earlier. A batch job run
each night over the complete events of the previous day sees every late arrival,
needs no watermark, and produces figures that are definitive. The stream gives the
prompt, provisional answer, and the batch job gives the slow, exact one. Many
systems run both for this reason, and the chief burden of doing so is that the same
logic has to be maintained in 2 places and kept in agreement. Where the stream
processor can itself reread old events from the log, the reprocessing can be done by
running the same code over the retained log from an earlier position, and the second
implementation is avoided.

## A key with too many events

For the sake of throughput, the stream is divided among several processors, each
handling the events of some of the advertisements. The division is made by hashing
the identifier of the advertisement, as chapter 11 divided messages by key, so that
all the clicks on 1 advertisement go to the same processor and can be counted
together.

Advertisements are very unequal. A single campaign shown during a major sporting
event may receive more clicks than all the others together, and every one of them is
directed to the same processor, which falls behind while its neighbours are idle.
This is the *hot key* of chapters 9 and 11 in yet another setting.

The usual remedy divides the work into 2 stages. In the first, the events of the
busy advertisement are spread across several processors, by adding a small random
number to the key, and each processor counts its share for each window. In the
second, a single processor adds the partial counts together. The second stage
receives 1 small message from each first-stage processor for each window, in place
of every event, and is easily able to keep up. Since addition gives the same result
in whatever grouping it is performed, the total is unaffected.

## Use cases

A visitor's click is recorded. An advertiser sees the counts, and is billed on the
final ones.

<figure>
<img src="figures/click-use-cases.svg?v=b8a69dfb" alt="A use case diagram of the click counter. Visitor: a click is recorded (POST /v1/clicks). Advertiser: see clicks per minute (GET /v1/ads/{id}/counts?from=&amp;to=), receive the invoice (from the final counts).">
<figcaption><b>Figure 28.2</b> The actors and what each of them does.</figcaption>
</figure>

## Functional requirements

| No. | Functional requirement |
|---|---|
| 0 | Every click on an advertisement is recorded, with the time at which it happened. |
| 1 | The number of clicks on each advertisement in each minute is available within 30 seconds of the end of that minute. |
| 2 | Clicks are counted in the minute in which they happened, whenever they arrive. |
| 3 | A click that is delivered more than once is counted once. |
| 4 | Final counts for each day are produced, which include clicks that arrived late. |
| 5 | Counts can be computed again from the recorded clicks. |

## Non-functional requirements

| No. | Property | Non-functional requirement |
|---|---|---|
| 0 | Accuracy | Final counts are exact. Provisional counts are within 1% of the final ones. |
| 1 | Freshness | Provisional counts appear within 30 seconds. |
| 2 | Durability | A click that was accepted is not lost. |
| 3 | Consistency | Eventual for provisional counts, which may be revised. Final counts do not change. |
| 4 | Scale | 1 billion clicks per day, with peaks of 100000 per second. |
| 5 | Availability | 99.9% for accepting clicks, which matters more than availability for reading counts. |

The last requirement reflects an asymmetry that is typical of systems of this kind.
A dashboard that is unavailable for a minute is an inconvenience, and its figures
are there when it returns. A click that is not accepted is lost for good, since the
visitor will not make it again. The collectors that accept clicks are therefore kept
as simple as possible, doing nothing beyond appending each click to a durable log,
so that they remain available whatever is happening to the more elaborate machinery
downstream.

## Core entities

<figure>
<img src="figures/click-entities.svg?v=ad25fbca" alt="The core entities. Click has the fields id u64, ad u64, happened time, arrived time. Window count has the fields ad u64, window start time, count u32, final yes|no. A Click carries the time it happened on the visitor&#x27;s device. A Window count is final once no more clicks are expected.">
<figcaption><b>Figure 28.3</b> The core entities and their fields.</figcaption>
</figure>

## Capacity estimate

<div class="estimate">

<img class="builder" src="art/crab-builder.svg" alt="A crab in a hard hat, in tears.">

**Arithmetic ahead.** 1 billion clicks a day of 200 bytes each are 200 GB of raw events a day, while the counts for a million advertisements are a few gigabytes.

<a class="skip" href="#high-level-design">Skip to the high-level design</a>

<details>
<summary>Show the calculation</summary>

| Quantity | Calculation | Result |
|---|---|---|
| Clicks per second, on average | 1 billion ÷ 86400 | about 11600 |
| Raw events per day | 1 billion × 200 bytes | 200 GB |
| Raw events per year, in the archive | 200 GB × 365 | 73 TB |
| Count rows per day | 1 million advertisements × 1440 minutes, of which 10% have any clicks | 144 million |
| Size of the counts per day | 144 million × 24 bytes | about 3.5 GB |
| State of the processors | identifiers of clicks in open windows: 100000 per second × 90 s × 8 bytes | about 72 MB |

</details>

</div>

## The API

A click is reported by the visitor's browser, with an identifier that the browser
generates and the time at which the click was made. An advertiser reads counts for a
range of time.

**Report a click**

```http
POST /v1/clicks HTTP/1.1
Host: clicks.example
Content-Type: application/json

{ "id": "c-7f3a91", "ad": 7, "happened": "2026-10-14T10:00:07Z" }
```

```http
HTTP/1.1 202 Accepted
```

The status is `202`, since the click has been stored and has not yet been counted.
The identifier allows a repeated report to be recognised.

**Read the counts of an advertisement**

```http
GET /v1/ads/7/counts?from=2026-10-14T10:00:00Z&to=2026-10-14T10:03:00Z HTTP/1.1
Host: clicks.example
```

```http
HTTP/1.1 200 OK
Content-Type: application/json

{
  "ad": 7,
  "window_seconds": 60,
  "counts": [
    { "start": "2026-10-14T10:00:00Z", "count": 412, "final": true },
    { "start": "2026-10-14T10:01:00Z", "count": 398, "final": false },
    { "start": "2026-10-14T10:02:00Z", "count": 87, "final": false }
  ]
}
```

Every count states whether it is final. A caller that draws a graph may use them
all, and a caller that computes an invoice uses only those marked as final.

## High-level design

<figure class="wide">
<img src="figures/click-design.svg?v=79399384" alt="Counting clicks in windows. The components are Visitors, Collectors, Click log, Stream processor, Archive, Count store. Step 1: A visitor&#x27;s browser reports a click. Step 2: The collector appends it to the log. Step 3: The processor counts clicks in windows by event time. Step 4: The log is also kept, so that counts can be made again. Step 5: Finished windows are written to the count store.">
<figcaption><b>Figure 28.4</b> The components and the path of a click. The steps are numbered.</figcaption>
</figure>

| Component | Role | State it holds | When 1 instance fails |
|---|---|---|---|
| Collector | accepts clicks and appends them to the log | none | another collector accepts |
| Click log | holds every click, in partitions by advertisement | the log, replicated, as in chapter 11 | a follower is elected |
| Stream processor | assigns clicks to windows, removes repeats, and counts | open windows, identifiers seen, and its position, saved in checkpoints | a replacement resumes from the latest checkpoint |
| Count store | holds the count for each advertisement and window | the counts, replicated | a follower is elected |
| Archive | keeps every raw click | the clicks, in an object store | as in chapter 16 |

### One click, step by step

The steps follow the arrows of figure 28.4.

1. A visitor clicks, and the browser reports the click with an identifier and the time.
2. A collector appends the click to the log, in the partition chosen by the advertisement, and answers `202`.
3. The stream processor reads the click from the log. If it has seen the identifier, it does nothing. Otherwise it adds 1 to the open window that contains the click's event time, and moves the watermark forward if the click is the newest it has seen.
4. The log is also copied to the archive, from which counts can later be made again.
5. When the watermark passes the end of a window, the processor writes that window's count to the count store, under a key formed from the advertisement and the start of the window.

## The design, deployed

<figure class="wide">
<img src="figures/click-deploy.svg?v=05190817" alt="The click counter, deployed. Browsers: Browsers (100000 clicks/s), report each click. Collection, in 3 zones: Load balancers (x 4), any collector, Collectors (x 40), append, and nothing else. The log: Click log (x 12), brokers, chapter 11, Archive (73 TB a year), every raw click. Counting: Stream processors (x 24), state in checkpoints, Nightly batch (from the archive), final counts. Serving: Count store (x 9), by ad and window, Counts API (x 8), dashboards, invoices.">
<figcaption><b>Figure 28.5</b> The click counter as it is deployed, from the collectors down to the store that serves the counts.</figcaption>
</figure>

The tiers follow the path of a click. The collectors are a large and deliberately
simple stateless tier, since their availability is what matters most. The click log
of 12 brokers is the point at which the system changes character: above it,
everything must be available at every moment, and below it, everything can be
stopped, corrected and run again from a position in the log. The 24 stream
processors hold their state in checkpoints, and the nightly batch reads the archive.
At the bottom, a small serving tier answers dashboards and the billing system from
the count store.

## How real systems do it

The vocabulary of this chapter, event time and processing time, windows, watermarks
and late data, was fixed by a paper from Google in 2015 that presents the Dataflow
model. The paper's central argument is the one made here, that a stream is
unbounded and its completeness is never known, so that a system must offer the
means to trade correctness, delay and cost against one another explicitly. It adds
a concept that this chapter touched on without naming, the *trigger*, which says
when the result of a window is to be emitted: early and provisionally, at the
watermark, and again for each late arrival. The earlier MillWheel paper describes
the system beneath, including low watermarks and the removal of duplicate records
by recording the identifiers of those processed.

Apache Flink is the open implementation in widest use, and its checkpoints are the
ones described here. They are taken without stopping the stream, by passing markers
through it that tell each operator when to record its state, a method derived from
a classical algorithm for taking a consistent snapshot of a distributed system.

The problem of this very chapter, the joining and counting of clicks for billing,
is the subject of a paper on Photon, the system that Google built for its
advertising business. Photon runs in several data centres at once, so that the loss
of 1 does not delay the counts, and it prevents a click from being processed twice
by recording the identifier of every processed click in a store that is replicated
between the data centres by Paxos. A click is thereby counted at most once at all
times and exactly once eventually, which is the guarantee sought here, obtained
across data centres.

The practice of running a stream and a batch side by side was named the lambda
architecture. The objection that the same logic then exists twice, and the proposal
to reprocess by running the stream code again over a retained log, were made in an
article by an author of Kafka. And for counting the number of distinct visitors,
which cannot be done by adding partial counts, the standard tool is a sketch that
estimates the number from a few kilobytes of state.

## Mistakes to avoid

| Mistake | What goes wrong | What to do |
|---|---|---|
| Counting by the time of arrival | Delayed clicks are counted in the wrong minute, and an outage produces an empty stretch followed by a spike. | Count by the time at which the click happened. |
| Closing a window when the clock passes its end | Every click still in transit is missed. | Close a window when the watermark passes its end. |
| Discarding late clicks silently | Billed counts are always slightly too low. | Record late clicks, and include them in the final counts. |
| Presenting provisional counts as final | A figure that has already been billed changes afterwards. | Mark every count as provisional or final. |
| Counting every delivery | Retries and redeliveries inflate the counts. | Give every click an identifier, and count each identifier once. |
| Remembering every identifier for ever | Memory grows without limit. | Forget the identifiers of a window when it closes. |
| Saving state and position separately | After a failure, clicks are counted twice or not at all. | Save them together, in a checkpoint. |
| Writing results by adding to a stored count | A result written twice after a recovery is added twice. | Write the count of a window under its own key, replacing whatever is there. |
| Keeping only the counts | A defect or a change of definition cannot be corrected. | Keep every raw click. |
| Trusting the timestamp of the visitor's device entirely | A device with a wrong clock places its clicks in the wrong day. | Record the time of arrival too, and reject event times that are impossibly far from it. |
| Sending all the clicks of a busy advertisement to 1 processor | That processor falls behind while the others are idle. | Count in 2 stages, spreading the busy key in the first. |
| Doing work in the collector | Clicks are lost when the downstream machinery is slow. | Let the collector append to the log and nothing else. |

## Failures

| Failure | What users see | How the system recovers |
|---|---|---|
| A stream processor fails | counts stop advancing for some seconds | a replacement loads the latest checkpoint and resumes from its position |
| The collectors are unreachable for a time | no new counts, then counts for the missed minutes | browsers retry, and the clicks are counted in the minutes in which they happened |
| A click arrives after its window was closed | the provisional count is slightly low | the final count includes it |
| A click is delivered twice | nothing | its identifier is recognised |
| A window's result is written twice | nothing | the second write replaces the first with the same value |
| The counts are found to be wrong | corrected figures | the computation is run again over the archive |

## Trade-offs

| Decision | What it gains | What it costs |
|---|---|---|
| Counting by event time | counts that answer the question asked | windows have to be kept open, and a watermark maintained |
| A larger allowance for lateness | more complete provisional counts | every result is published later |
| Provisional and final counts | prompt figures and exact invoices | 2 grades of result that callers must distinguish |
| Checkpoints | recovery with each click counted once | periodic pauses to save state, and reprocessing since the last checkpoint |
| Keeping raw events | counts can always be made again | 73 TB a year of storage |
| A stream and a nightly batch | speed and exactness together | the same logic in 2 places |

## The simulation

<div class="simulation">

**Simulation in the repository.** The program [`code/clicksim`](https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/distributed-systems-from-the-ground-up/code/clicksim/src/main.rs) simulates this design. To run it, clone the repository and type `cargo run --release -p clicksim` in the `code` directory.

</div>

## References

- T. Akidau and others, "The Dataflow Model: A Practical Approach to Balancing Correctness, Latency, and Cost in Massive-Scale, Unbounded, Out-of-Order Data Processing", VLDB 2015.
- T. Akidau and others, "MillWheel: Fault-Tolerant Stream Processing at Internet Scale", VLDB 2013.
- R. Ananthanarayanan and others, "Photon: Fault-tolerant and Scalable Joining of Continuous Data Streams", SIGMOD 2013.
- P. Carbone and others, "Lightweight Asynchronous Snapshots for Distributed Dataflows", 2015.
- K. Chandy and L. Lamport, "Distributed Snapshots: Determining Global States of Distributed Systems", ACM Transactions on Computer Systems, 1985.
- J. Kreps, "Questioning the Lambda Architecture", O'Reilly Radar, 2014.
- P. Flajolet and others, "HyperLogLog: the analysis of a near-optimal cardinality estimation algorithm", AofA 2007.

## Terms introduced in this chapter

| Term | Meaning |
|---|---|
| Stream processing | computing results continuously from an unending sequence of events |
| Batch processing | computing results from a complete, finite set of data |
| Event time | the time at which an event happened |
| Processing time | the time at which an event reaches the system that processes it |
| Window | a finite span of time over which events are aggregated |
| Tumbling window | 1 of a series of consecutive windows of equal length that do not overlap |
| Sliding window | a window of fixed length that advances by a smaller step |
| Session window | the events of 1 user that follow one another closely |
| Watermark | the system's estimate of the event time before which everything has arrived |
| Allowed lateness | how long the system waits for older events |
| Late event | an event that arrives after its window was declared finished |
| Provisional, final | a count that may still be revised, and one that will not |
| Checkpoint | the state of a processor saved together with its position in the input |
| Reprocessing | computing results again from the original events |

<div class="summary">

## Summary

- Counting events once a day is simple and exact, and its results come a day late.
- Every event has the time it happened and the time it arrived, and counts must go by the first.
- A stream is divided into windows, and the hard question is when a window has received all its events.
- A watermark estimates how far the system has progressed through event time, and a window is finished when the watermark passes its end.
- Events later than that are recorded and included in final counts, which are distinguished from the provisional ones published at once.
- Every click carries an identifier, and is counted once however often it is delivered.
- A checkpoint saves the processor's state together with its position in the log, and results are written under keys that make a repeated write harmless.
- The raw events are kept, so that every count can be computed again.

</div>
