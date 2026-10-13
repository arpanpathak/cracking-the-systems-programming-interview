<img class="plate" src="art/ch24.svg?v=c4ca9b72" alt="An owl stands beside a sign that reads: 40, plus 2, minus 3, plus 1.">

# Metrics and Monitoring: System Design

Every system in this book has been described as doing what its design says. A real
system has also to be watched, since machines fail, software is released with
defects, and traffic arrives in patterns that nobody foresaw. The people responsible
need to know, at every moment, how many requests the system is receiving, how many
of them are failing, how long they take, and how close each machine is to the limits
of its memory and its disks. They need to see these quantities change over hours and
weeks, and they need to be woken at night when one of them goes wrong. The system
that provides for this is a *monitoring system*, and the numbers it collects are
called *metrics*.

A monitoring system has a peculiar workload. It receives an enormous number of very
small writes, since every service on every machine reports dozens of numbers every
few seconds, and those writes never stop. Its data is of a single shape, a number
with a time attached, which permits a degree of compression that no general database
approaches. Almost nobody reads the data, and yet when it is read, during an
incident, the answer is wanted immediately and may span months. And the system has a
responsibility of an unusual kind. It is the means by which every other failure is
detected, and it must therefore go on working when the things around it do not.

<div class="covers">

This chapter covers

- what a metric is, and the 3 kinds in common use
- time series, and why their number is the quantity to watch
- whether services send their measurements or are asked for them
- storing a number every few seconds for a year in 2 bytes a point
- reducing old data to 1 point a minute, and what that loses
- why an average of response times misleads, and what to keep in its place
- alerts that wake somebody for the right reasons
- keeping the monitoring system alive when everything else is failing

</div>

## What a metric is

A metric is a number, measured repeatedly, that describes some aspect of a running
system. 3 kinds account for nearly all of them, and they behave differently enough
that it matters which is which.

A *counter* is a number that only ever increases: the requests served since the
process started, or the bytes sent. Its value at a single moment is of no interest.
What is wanted is its rate of change, obtained by subtracting 2 readings and dividing
by the time between them. Counters have the great merit that nothing is lost between
readings. If a reading is missed, the next one still includes everything that
happened in the interval.

A *gauge* is a number that rises and falls: the memory in use, the length of a queue,
the temperature of a processor. Here the value at a moment is the thing of interest,
and whatever it did between 2 readings is unknown. A queue that filled and emptied
within 5 seconds leaves no trace in a gauge read every 10.

A *histogram* records the distribution of a quantity that takes a different value on
every occasion, above all the time taken to answer a request. Its treatment needs a
section of its own, since the natural way of summarising such a quantity, by its
average, turns out to be nearly useless.

## Time series

A measurement is identified by the name of the metric and by a set of *labels*,
which are pairs of a key and a value saying what the measurement refers to. The
requests served by the payments service on machine 14 with status 500 might be
recorded as the metric `requests_total` with the labels `service=payments`,
`machine=14` and `status=500`. The sequence of values recorded for 1 metric with 1
particular set of label values is a *time series*.

Labels are what make metrics useful, since they allow the same measurement to be
added up or separated out along any dimension: all requests to payments, all
requests with status 500, all requests on machine 14. They are also the principal
hazard in the operation of a monitoring system, for a reason that follows from simple
multiplication.

Every distinct combination of label values is a separate series, to be stored and
indexed separately. A metric with the labels service, machine and status, in a
system with 20 services, 100 machines and 5 statuses in use, has up to 10000 series,
which is entirely manageable. Suppose now that a well-meaning engineer adds a label
for the identifier of the user, so as to see which users experience errors. With a
million users, the 1 metric has up to 10 billion series. The number of series that a
metric gives rise to is called its *cardinality*, and a single label whose values are
unbounded, such as a user identifier, a request identifier or the full text of an
address, is enough to exhaust the memory of the system within hours.

The rule that follows is that labels must take a small and bounded number of values.
A question about an individual user or request is a legitimate one, and it belongs
to a different kind of system: to *logs*, which record individual events, or to
*traces*, which follow a single request through the services it touches. Metrics
answer questions about aggregates, and pay for their cheapness by being unable to
answer any other kind.

## Sending or being asked

Measurements have to travel from the services to the monitoring system, and there
are 2 ways of arranging it.

Under the *push* model, each service sends its measurements to the monitoring system
at regular intervals. Under the *pull* model, each service exposes its current values
at an address of its own, and the monitoring system visits every service at regular
intervals to collect them.

| | Push | Pull |
|---|---|---|
| Who must know whom | every service knows the address of the monitoring system | the monitoring system knows the address of every service |
| A service that has died | stops sending, which looks the same as having nothing to report | fails to answer, which is itself a clear signal |
| A service that lives for seconds | can report before it exits | may be gone before it is visited |
| Who controls the load | the services, all at once | the monitoring system, at its own pace |
| Services behind a firewall | can send outwards | cannot be reached |

The second row is the strongest argument for pulling. When the monitoring system
does the asking, the absence of an answer is information, and the health of every
service is checked as a by-product of collecting its numbers. The third row is the
strongest argument for pushing, since a batch job that runs for 5 seconds cannot
wait to be visited. Many installations use both, pulling from long-lived services
and accepting pushes from short-lived ones. The design of this chapter pulls, with
collectors that visit each service every 10 seconds.

## Storing a number every 10 seconds

The store receives points, each consisting of a time and a value, and must keep them
for months. Stored plainly, as 2 numbers of 8 bytes, a point occupies 16 bytes. A
million series sampled every 10 seconds produce 8.6 billion points a day, or 138 GB,
and a year of that is 50 TB.

Time series have 2 properties that allow far better. The points of a series arrive
in order of time and are never modified afterwards, so that the store only ever
appends. And successive points resemble one another closely: the times are evenly
spaced, and the values change little from one reading to the next. A number that is
close to its predecessor can be stored as the difference between them, and a small
difference needs few bits.

<figure class="steps" data-prefix="figures/steps-metrics-delta" data-count="5" data-version="e332f4cb">
<img src="figures/steps-metrics-delta-01.svg?v=e332f4cb" alt="Storing changes in place of numbers, step 1 of 5. 4 measurements, 1 second apart. Each time is a number of 10 digits and needs 8 bytes when stored as it is.">
<figcaption><b>Figure 24.1</b> The times and the values of a series, stored as changes from the point before. Use Next and Back to move through the 5 steps.</figcaption>
</figure>

For the times, the differences are themselves nearly constant, the interval of
collection, so that storing the difference between successive differences yields 0
almost every time. For the values, the difference from the previous value is small
whenever the quantity being measured is steady, which most are for most of the time.

The simulation for this chapter stores an hour of a response time measured every
second, 3600 points. Stored plainly they occupy 57600 bytes. Stored as changes, with
small numbers written in fewer bytes, they occupy 7223, which is 2 bytes for each
point and an eighth of the plain size. Production systems encode at the level of
individual bits and exploit the structure of floating-point numbers, and commonly
reach between 1 and 2 bytes a point. The 50 TB a year computed above becomes about 5.

Compression of this kind has a consequence for the layout of the store. A point
encoded as a difference can be decoded only by starting from the beginning of its
run and working forwards. Points are therefore grouped into *blocks*, each covering
a fixed span of time for 1 series, 2 hours for example, and each block is encoded
and decoded as a unit. The block being written is held in memory, where it can be
appended to, and is protected by a write-ahead log of the kind described in chapter
2, and when its span is over it is compressed and written to disk, never to be
modified again. Reading a range of time means locating the blocks that cover it,
which is quick because blocks are indexed by series and by time.

## Keeping less of the past

Even well compressed, points every 10 seconds for a year are more than most
questions about the past require. A graph of the last year, drawn on a screen 2000
pixels wide, can show at most 2000 values, and to compute them from 3 million points
for each series would be slow and pointless.

Older data is therefore reduced in resolution, a process called *downsampling* or
*rollup*. A background job reads the raw points of each series and writes 1 point
for every minute, and later 1 for every hour. Recent data is retained at full
resolution for some days, the 1-minute data for some months, and the hourly data for
years. A query chooses the resolution suited to the range it covers.

What is written for each minute has to be chosen with care, since a single number
cannot represent 6 or 60 readings without losing something, and what is lost depends
on the number chosen.

<figure>
<img src="figures/metrics-rollup.svg?v=052523c7" alt="2 bars for a minute that contains 57 seconds at 40 ms and 3 seconds at 900 ms. Kept as its average, the minute is 83 ms. Kept as its largest value, the minute is 900 ms.">
<figcaption><b>Figure 24.2</b> A minute containing a spike of 3 seconds, kept as its average and as its largest value.</figcaption>
</figure>

In the simulation, 1 minute contains 57 seconds in which the response time is about
40 ms and 3 seconds in which it is 900. Kept as its average, that minute is recorded
as 83 ms, which suggests a slight slowness and conceals entirely that for 3 seconds
the service was nearly unusable. Kept as its largest value, the minute is recorded
as 900 ms, which preserves the incident and says nothing of how brief it was.
Neither is wrong, and neither is sufficient. A rollup therefore stores several
numbers for each interval, usually the smallest value, the largest, the sum and the
count, from which the average can be derived and the extremes are not lost.

## Why an average of response times misleads

The same example exposes a wider difficulty. The time taken to answer a request is
the most important single measure of a service, and its average is a poor
description of it.

Response times are not distributed symmetrically about a typical value. Most
requests are fast, and a small proportion are very much slower, because they met a
busy disk, an expired cache entry or a retry. The average is pulled upwards a little
by these slow requests and describes neither group. A service whose requests take 40
ms in 99 cases and 2 seconds in the hundredth has an average of 60 ms, which looks
entirely healthy, while 1 user in every 100 waits 2 seconds, and a user who loads a
page that issues 50 requests has a chance of 2 in 5 of encountering at least 1 of
them.

The quantity that describes experience is the *percentile*, introduced in chapter 1.
The 99th percentile, written p99, is the time within which 99% of requests complete,
and it states directly how bad the experience is for the least fortunate 1 in 100.

Percentiles have an awkward property that averages lack, and it shapes how response
times must be collected. They cannot be combined. The average of 2 machines can be
computed from the average and the count of each. The p99 of 2 machines cannot be
computed from the p99 of each: if one machine has a p99 of 50 ms and the other of 2
seconds, the combined p99 may be almost anything between, depending on how the
requests were divided. A service that computes its own percentiles and reports them
has produced numbers that can never be aggregated across machines or across time.

The histogram solves this. A service does not report a percentile. It counts its
requests in *buckets* by duration, so many under 10 ms, so many under 50 ms, so many
under 250 ms and so on, and reports the counts. Counts can be added, across machines
and across intervals, and a percentile is estimated from the combined counts at the
moment of the query. The estimate is only as fine as the buckets, so the boundaries
of the buckets have to be chosen around the durations that matter, but it can be
computed for any grouping of machines over any period, which no percentile computed
in advance allows.

## Alerts

A monitoring system that is only looked at when something is already known to be
wrong has done half its work. The other half is to notice the trouble first, by
means of *alerts*. An alert is a rule consisting of a query and a condition, which
the system evaluates at regular intervals, notifying somebody when the condition
holds.

Rules are easy to write and hard to write well, and the commonest failing of
monitoring in practice is too many alerts. An engineer who is woken 3 times a night
by alerts that required no action soon ceases to respond with any urgency, and the
alert that matters is then lost among the rest. A few principles keep alerts worth
answering.

An alert should concern what users experience. What machines are doing is a different matter.
"The proportion of failed requests has exceeded 1%" is a statement about harm.
"Processor usage is at 90%" is a statement about a machine, which may be working
exactly as intended. Alerts on causes multiply endlessly, since there are countless
possible causes, while the symptoms that matter are few.

A condition should have to hold for some time before the alert fires. A single
reading above a threshold is very often a momentary disturbance, and a rule that
requires the condition to persist for 5 minutes ignores the noise at the price of 5
minutes' delay.

Every alert should demand an action. If the proper response to an alert is to
observe it and go back to sleep, it belongs on a dashboard, and nobody should be
notified of it.

And related alerts should be grouped. When a database fails, 50 services that depend
on it fail too, and 50 alerts arriving together tell the engineer less than 1 that
names the database. The notification itself is delivered by the notification service
of chapter 13, with escalation to a second person if the first does not acknowledge
it.

One further case deserves mention because it is so often overlooked. A rule that
tests whether a value is too high does not fire when there is no value at all. If a
service stops reporting altogether, its error rate is not high, it is absent, and a
naively written alert remains silent during the worst failure of all. Every
important series therefore needs a second rule that fires when data has ceased to
arrive.

## Watching the watcher

The monitoring system is relied upon precisely when other things are failing, and
its design has to take account of that.

It must not share the fate of what it monitors. If it runs on the same machines, the
same network and the same storage as the services it watches, a single failure may
remove both, and the engineers are left without information exactly when they need
it most. It is therefore given infrastructure of its own, and kept as simple and as
free of dependencies as its function allows. A monitoring system that needs the
message queue, the coordinator and the object store all to be healthy before it can
display a graph will be unavailable in most serious incidents.

It must also withstand the load that incidents themselves produce. When something
breaks, many engineers open many dashboards together, each issuing dozens of
queries over long ranges, at the very moment when the stream of incoming
measurements may also be surging. The paths for writing and for querying are
separated, so that a flood of queries cannot delay the storing of new points, and
queries are bounded in the time and memory they may consume.

Finally, something has to watch the monitoring system itself. The usual arrangement
is a second, minimal instance that checks nothing except whether the first is alive
and evaluating its rules, and that raises its own alert through an independent
channel when it is not.

## Use cases

Services report measurements. Engineers look at graphs, define alerts and are
notified.

<figure>
<img src="figures/metrics-use-cases.svg?v=0a09f42d" alt="A use case diagram of the monitoring system. Service: send measurements (POST /v1/points). Engineer: draw a graph (GET /v1/series?name=&amp;from=&amp;to=), define an alert (PUT /v1/alerts/{name}), be paged when it fires (a notification, chapter 13).">
<figcaption><b>Figure 24.3</b> The actors and what each of them does.</figcaption>
</figure>

## Functional requirements

| No. | Functional requirement |
|---|---|
| 0 | The system collects measurements from every service at a fixed interval. |
| 1 | An engineer can query any series, or a combination of series selected by labels, over any range of time. |
| 2 | Percentiles of durations can be computed across any group of machines. |
| 3 | An engineer can define alerts, each a query, a condition and a duration. |
| 4 | When an alert fires, the people responsible are notified. |
| 5 | Data is kept at full resolution for 15 days and at lower resolution for 2 years. |

## Non-functional requirements

| No. | Property | Non-functional requirement |
|---|---|---|
| 0 | Scale | 10 million series, sampled every 10 seconds: 1 million points per second. |
| 1 | Latency of queries | A dashboard covering the last 6 hours loads within 1 second. |
| 2 | Freshness | A point is visible in queries within 30 seconds of being measured. |
| 3 | Availability | 99.9%, and independent of the systems that are monitored. |
| 4 | Durability | The loss of a few seconds of points in a failure is acceptable. The loss of history is not. |
| 5 | Consistency | Eventual. 2 queries moments apart may differ in the most recent points. |

Non-functional requirement 4 distinguishes 2 things that are often run together. A
single point of a metric is nearly worthless: if 10 seconds of 1 series are lost, a
graph shows a small gap and no decision is affected. The accumulated history is
valuable, since it is what allows this week to be compared with the same week of
last year. The design accordingly accepts weak durability for incoming points, which
keeps the write path cheap, and stores completed blocks with the full protection of
the object store of chapter 16.

## Core entities

<figure>
<img src="figures/metrics-entities.svg?v=b132dd3f" alt="The core entities. Series has the fields name string, labels key=value, .... Point has the fields series u64, time seconds, value f64. Alert has the fields query string, threshold f64, for duration. A Series is 1 name with 1 set of label values. Every different combination of label values is a separate series.">
<figcaption><b>Figure 24.4</b> The core entities and their fields.</figcaption>
</figure>

## Capacity estimate

<div class="estimate">

<img class="builder" src="art/crab-builder.svg" alt="A crab in a hard hat, in tears.">

**Arithmetic ahead.** 10 million series at 1 point every 10 seconds, compressed to 2 bytes a point, need about 170 GB a day at full resolution.

<a class="skip" href="#high-level-design">Skip to the high-level design</a>

<details>
<summary>Show the calculation</summary>

| Quantity | Calculation | Result |
|---|---|---|
| Points per second | 10 million series ÷ 10 s | 1 million |
| Points per day | 1 million × 86400 | 86.4 billion |
| Bytes per day, plain | 86.4 billion × 16 bytes | 1.4 TB |
| Bytes per day, compressed | 86.4 billion × 2 bytes | 173 GB |
| 15 days at full resolution | 173 GB × 15 | 2.6 TB |
| 2 years at 1 point per hour, 4 numbers each | 10 million × 17520 × 4 × 2 bytes | 1.4 TB |
| Memory for the current blocks | 10 million series × 720 points × 2 bytes | 14 GB |

</details>

</div>

## The API

Under the pull model, a service takes no action to report. It answers a request from
a collector with its current values. The API of the monitoring system itself is used
by dashboards and by the people who define alerts.

**What a collector receives from a service**

```http
GET /metrics HTTP/1.1
Host: payments-14.internal
```

```http
HTTP/1.1 200 OK
Content-Type: text/plain

requests_total{service="payments",status="200"} 918234
requests_total{service="payments",status="500"} 417
queue_length{service="payments"} 12
request_duration_bucket{service="payments",le="0.05"} 880112
request_duration_bucket{service="payments",le="0.25"} 915540
request_duration_bucket{service="payments",le="+Inf"} 918651
```

Each line is the present value of 1 series. The lines of `request_duration_bucket`
are a histogram: `le` is the upper bound of a bucket in seconds, and each count
includes every request that took no longer than that.

**Query a series over a range**

```http
GET /v1/series?query=rate(requests_total{service="payments",status="500"})&from=2026-10-14T08:00:00Z&to=2026-10-14T09:00:00Z&step=60 HTTP/1.1
Host: metrics.internal
```

```http
HTTP/1.1 200 OK
Content-Type: application/json

{
  "step": 60,
  "points": [
    { "time": "2026-10-14T08:00:00Z", "value": 0.02 },
    { "time": "2026-10-14T08:01:00Z", "value": 0.03 }
  ]
}
```

**Define an alert**

```http
PUT /v1/alerts/payments-errors HTTP/1.1
Host: metrics.internal
Content-Type: application/json

{
  "query": "rate(requests_total{service=\"payments\",status=\"500\"}) / rate(requests_total{service=\"payments\"})",
  "condition": "> 0.01",
  "for_seconds": 300,
  "notify": "payments-on-call"
}
```

```http
HTTP/1.1 204 No Content
```

The rule fires when more than 1% of the requests to payments have failed
continuously for 5 minutes.

## High-level design

<figure class="wide">
<img src="figures/metrics-design.svg?v=80a8b262" alt="A monitoring system. The components are Services, Collectors, Series store, Query service, Rollup job, Alert evaluator. Step 1: Every service sends its measurements every 10 seconds. Step 2: A collector appends each point to its series. Step 3: A graph is a query over a range of time. Step 4: Older points are reduced to 1 per minute. Step 5: Every rule is evaluated once a minute.">
<figcaption><b>Figure 24.5</b> The components and the path of a measurement. The steps are numbered.</figcaption>
</figure>

| Component | Role | State it holds | When 1 instance fails |
|---|---|---|---|
| Collector | visits each service and reads its values | the list of services | its services are visited by another collector |
| Series store | appends points, and compresses finished blocks | current blocks in memory, with a log, and finished blocks on disk | a replica that received the same points answers |
| Rollup job | reduces old points to 1 per minute and 1 per hour | none | it is run again |
| Query service | reads blocks and computes what a graph or a rule asks for | a cache of recent results | another instance answers |
| Alert evaluator | evaluates every rule once a minute | which alerts are firing | a second evaluator runs the same rules |

### One measurement, step by step

The steps follow the arrows of figure 24.5.

1. Every 10 seconds, a collector asks each of its services for its current values.
2. The collector attaches the time to each value and sends the points to the series store, which appends each to the current block of its series.
3. A dashboard sends a query. The query service finds the blocks that cover the range, decodes them, and computes the result.
4. In the background, the rollup job reads blocks that are some hours old and writes 1 point for each minute.
5. Once a minute, the alert evaluator runs the query of every rule, and notifies the people named when a condition has held for long enough.

So that the loss of 1 machine of the series store leaves no gap, every point is sent
to 2 machines, each of which builds its own blocks independently. The 2 copies are
not kept identical by any protocol, and may differ by a point here and there. For
this data that is acceptable, and the query service merges whatever it receives.

## Mistakes to avoid

| Mistake | What goes wrong | What to do |
|---|---|---|
| A label with unbounded values | The number of series multiplies until memory is exhausted. | Keep labels to small, fixed sets of values, and put identifiers in logs. |
| Reporting gauges for things that are counted | Whatever happened between 2 readings is lost. | Report counters, and compute rates when querying. |
| Storing points plainly | Storage is 8 times what it need be. | Encode each point as its change from the one before. |
| Rolling up to the average alone | Short spikes vanish from the history. | Keep the smallest value, the largest, the sum and the count. |
| Watching the average response time | A slow hundredth of requests is invisible. | Watch percentiles. |
| Computing percentiles in each service | They cannot be combined across machines. | Report histograms, and compute percentiles when querying. |
| Alerts on causes | Engineers are woken by things that harm nobody. | Alert on what users experience. |
| Alerts that fire on 1 reading | Momentary noise pages people. | Require the condition to hold for some minutes. |
| No alert for missing data | A service that stops reporting raises no alarm. | Add a rule that fires when a series stops arriving. |
| Monitoring on the monitored infrastructure | A single failure removes both the system and the view of it. | Give monitoring its own machines, network path and storage. |
| Queries without limits | 1 dashboard over a year exhausts the query service during an incident. | Bound the time and memory of every query, and use rollups for long ranges. |

## Failures

| Failure | What is observed | How the system recovers |
|---|---|---|
| A service stops answering the collector | its series end | the rule for missing data fires |
| A collector fails | its services are not visited | another collector takes over its list |
| A machine of the series store fails | no gap, since each point went to 2 machines | a replacement builds its blocks from then on, and older blocks are in the object store |
| The store restarts | up to a few seconds of points may be missing | the current blocks are rebuilt from the log |
| A flood of queries | dashboards load slowly | queries are limited, and writes are unaffected |
| The alert evaluator fails | no alerts fire | a second evaluator runs, and an independent check watches both |

## Trade-offs

| Decision | What it gains | What it costs |
|---|---|---|
| Pulling measurements | a silent service is noticed, and the collectors set the pace | short-lived jobs need a separate way in |
| Bounded labels | a predictable number of series | no questions about individual users or requests |
| Compression by differences | about 2 bytes a point | a block must be decoded from its start |
| Rollups | fast queries over long ranges, and far less storage | the detail of the past is gone |
| 2 independent copies without agreement | a simple and cheap write path | the copies may differ by a few points |
| Histograms | percentiles over any group and period | accuracy limited by the buckets chosen |

## The simulation

<div class="simulation">

**Simulation in the repository.** The program [`code/metricsim`](https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/distributed-systems-from-the-ground-up/code/metricsim/src/main.rs) simulates this design. To run it, clone the repository and type `cargo run --release -p metricsim` in the `code` directory.

</div>

## Terms introduced in this chapter

| Term | Meaning |
|---|---|
| Metric | a number, measured repeatedly, that describes a running system |
| Counter | a metric that only increases, of which the rate is what matters |
| Gauge | a metric that rises and falls, of which the present value is what matters |
| Histogram | counts of events in buckets by size, from which percentiles are estimated |
| Label | a key and a value that say what a measurement refers to |
| Time series | the values of 1 metric with 1 set of label values, in order of time |
| Cardinality | the number of series that a metric gives rise to |
| Push, pull | services sending their measurements, and the monitoring system asking for them |
| Block | the points of 1 series for a fixed span of time, compressed together |
| Downsampling, rollup | reducing old data to fewer points |
| Percentile | the value below which a given percentage of measurements fall |
| Alert | a query and a condition that, when it holds, causes somebody to be notified |
| Logs, traces | records of individual events, and of the path of a single request |

<div class="summary">

## Summary

- Metrics are numbers measured repeatedly, of 3 kinds: counters, gauges and histograms.
- Every combination of label values is a separate series, and a label with unbounded values will exhaust the system.
- Pulling lets the monitoring system notice a service that has fallen silent, and pushing suits jobs that live for seconds.
- Points arrive in order and resemble their predecessors, so that storing each as its change from the one before takes about 2 bytes.
- Old data is reduced to 1 point for each minute or hour, keeping the smallest value, the largest, the sum and the count.
- An average of response times hides the slow requests that users notice, and percentiles must be computed from histograms because they cannot be combined.
- An alert should concern what users experience, hold for some time before firing, demand an action, and have a companion that fires when data stops.
- The monitoring system runs on infrastructure of its own, and is itself watched by something independent.

</div>
