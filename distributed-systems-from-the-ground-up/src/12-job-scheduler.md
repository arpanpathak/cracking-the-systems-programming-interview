<img class="plate" src="art/ch12.svg?v=8b2d82cb" alt="Shift, a small daemon, stands beside a sign that reads: waiting, running, done.">

# Job Scheduler: System Design

A good deal of the work that a system does is not done while anybody waits for it. A
user uploads a video and receives an immediate confirmation, while the conversion of
the video into several resolutions takes place over the following minutes. An account
is closed today, and its data is to be erased in 30 days. A report on yesterday's
sales is to be compiled every night at 2 o'clock. In each case a piece of work, which
we shall call a *job*, has to be remembered now and carried out later, by some machine
other than the one that asked for it, and it has to be carried out even if that
machine, or the one that accepted the request, fails in the meantime.

A *job scheduler* is the service that takes responsibility for such work. It accepts
jobs, stores them durably, hands them to *workers* when their time has come, and keeps
track of what became of them. The essential difficulty is that the scheduler can never
observe a job being executed. It gives a job to a worker and thereafter knows only
what the worker reports, and a worker that has stopped reporting may have crashed,
may be slow, or may have completed the job and failed only in delivering the news.
Everything in the design follows from the need to make progress in spite of this
uncertainty without either losing jobs or running them more often than can be
tolerated.

<div class="covers">

This chapter covers

- the life of a job, as a small set of states and transitions
- leases, by which a job is lent to a worker for a limited time
- why a job may run more than once, and how to make that harmless
- giving 1 job to 1 worker when many workers ask together
- retries, increasing pauses, and jobs that never succeed
- jobs that are due at a later time, and how to find them efficiently
- recurring jobs, and the hazards of firing twice or not at all
- priorities, fairness among customers, and long-running jobs

</div>

## The life of a job

Every job in the scheduler is in exactly 1 of a small number of states, and the whole
behaviour of the system can be described by the permitted movements between them.

<figure>
<img src="figures/jobs-states.svg?v=4c672151" alt="The states of a job. A waiting job becomes running when a worker takes it and receives a lease. A running job returns to waiting when it fails or its lease runs out. A running job becomes succeeded when the worker reports success before its lease runs out. A running job becomes dead when it has failed 5 times.">
<figcaption><b>Figure 12.1</b> The 4 states of a job and the transitions between them.</figcaption>
</figure>

A newly submitted job is *waiting*. When a worker takes it, the job becomes *running*,
and from that state there are 3 ways out. If the worker reports success, the job has
*succeeded* and nothing more will happen to it. If the worker reports failure, or
reports nothing before a deadline, the job returns to waiting in order to be tried
again. And if it has already been tried a fixed number of times without success, it
becomes *dead*, which means that the scheduler has given up on it and that a person
will have to look at it.

The value of describing the system in this way is that every question about its
correctness becomes a question about a transition. Jobs are not lost if every job is
always in 1 of the states and no transition discards a job. A job is not run by 2
workers at once if the transition from waiting to running can be made by 1 worker
only. The 3 sections that follow take the transitions out of the running state one by
one, beginning with the least obvious.

## Lending a job: the lease

Suppose that a worker takes a job and the scheduler marks it as running and does
nothing further. If the worker completes the job, all is well. If the worker crashes,
the job remains marked as running indefinitely, and since only waiting jobs are handed
out, it will never be given to anyone else. The job has in effect been lost, although
it is still in the store.

The scheduler therefore does not give a job to a worker outright. It lends it for a
limited period, and the loan is called a *lease*. The worker must report the result
before the lease ends. If the period passes without a report, the scheduler concludes
that the worker is not going to finish and returns the job to the waiting state, from
which another worker will take it. Chapter 10 used a lease for the same reason, to
recover a lock from a holder that has vanished.

<figure class="steps" data-prefix="figures/steps-jobs-lease" data-count="6" data-version="0cec0bea">
<img src="figures/steps-jobs-lease-01.svg?v=0cec0bea" alt="A worker crashes during a job, step 1 of 6. Job 1 is waiting in the store. Each time a worker takes it, the store counts an attempt.">
<figcaption><b>Figure 12.2</b> A worker crashes while holding a job, the lease runs out, and a second worker completes the job. Use Next and Back to move through the 6 steps.</figcaption>
</figure>

The simulation for this chapter runs this scenario with 6 jobs and 3 workers, 1 of
which crashes 2 seconds into its first job. All 6 jobs are completed. The job held by
the crashed worker is recovered when its lease expires at 3 seconds and is finished by
another worker at 6, and the record shows 2 attempts for that job and 1 for each of
the others.

The length of the lease involves the compromise that chapter 10 described. If it is
short, a crashed worker's job is recovered quickly, and a worker that is merely slow
has its job taken away and given to another while it is still working. If it is long,
slow workers are safe and a crashed worker's job sits idle for a long time before
anyone notices. For jobs whose duration is predictable, the lease is set comfortably
above the usual duration. For jobs that may take minutes or hours, a fixed lease of
sufficient length would delay recovery intolerably, and the worker takes a
short lease and renews it at intervals for as long as it is making progress, as with
the renewal of a lock.

## A job may run twice

The lease brings with it a consequence that has to be faced squarely. The expiry of a
lease does not prove that the worker has stopped. The worker may be running slowly,
or may have been paused in the manner described in chapter 10, or may have finished
the job and been unable to report because of a fault in the network. In each of these
cases the scheduler gives the job to a second worker while the first is still
executing it or has already executed it, and the job is performed twice.

This is the same situation that chapter 11 called delivery at least once, and it is
unavoidable for the same reason. The scheduler must choose between reissuing a job
whose worker has fallen silent, which risks a second execution, and not reissuing it,
which risks no execution at all, and since a job that is never run is nearly always
the worse outcome, schedulers reissue. It follows that a scheduler guarantees that a
job will be run at least once, and cannot guarantee that it will be run exactly once.

The responsibility for making this harmless lies with the author of the job. A job
should be *idempotent*, which is to say that running it twice should leave the world
in the same condition as running it once. Some jobs have this property without
effort: resizing an image and storing the result under a fixed name can be repeated
indefinitely. Others must be given it. A job that charges a customer has to carry a
unique reference that the payment system uses to recognise a repeated charge, as
chapter 19 describes, and a job that sends an email should record that it has done so
and check the record before sending.

One further precaution limits the damage that a late worker can do. When a worker
reports a result, it presents the number of the lease under which it was working, and
the scheduler accepts the report only if that lease is still the current one for the
job. The slow worker of the scenario above, reporting success under lease 771 after
the job has been reissued under lease 772, is told that its lease is no longer valid
and its report is ignored. The lease number plays the part of the fencing token of
chapter 10: it cannot prevent the late worker from having done the work, and it does
prevent the late worker from overwriting the state recorded by its successor.

## Giving 1 job to 1 worker

The transition from waiting to running must be made by 1 worker only, and when many
workers ask for jobs at the same time this requires care.

The natural way of writing the operation is in 2 steps: find a job that is waiting,
then mark it as running. Between the 2 steps there is a gap, and a second worker's
request can fall into it.

<figure class="steps" data-prefix="figures/steps-jobs-claim" data-count="6" data-version="31fe08a0">
<img src="figures/steps-jobs-claim-01.svg?v=31fe08a0" alt="2 workers and 1 waiting job, step 1 of 6. 1 job is waiting, and 2 idle workers ask for work at the same moment.">
<figcaption><b>Figure 12.3</b> 2 workers ask for work together, and both receive the same job unless taking a job is a single conditional change. Use Next and Back to move through the 6 steps.</figcaption>
</figure>

The remedy, shown in the last step, is to make the transition a single conditional
operation in the job store, of the form "set this job to running, under my lease, if
it is still waiting". The store performs each such operation in its entirety before
beginning the next, so that when 2 workers attempt it on the same job, the second
finds the condition no longer true and is refused. This is the compare-and-set of
chapter 1 once more.

A conditional change is correct and, with many workers, not yet efficient. If 50 idle
workers all identify the oldest waiting job and all attempt to take it, 1 succeeds and
49 have wasted a round trip and must try again, upon which they all converge on the
next job. Databases used as job stores offer a remedy in the form of a query that
selects waiting rows while passing over any row that another transaction has locked,
so that each worker is given a different job at the first attempt. Where no such
facility exists, workers can be made to choose at random among the first few waiting
jobs, which reduces the collisions considerably.

## Retries and jobs that never succeed

A job may fail for reasons that will have passed in a moment, such as a brief network
fault or a service that was restarting, and for such failures the right response is
to try again. The scheduler counts the attempts made on each job and, after a failure,
returns the job to the queue.

It should not be returned for immediate execution. If a job has failed because some
service it depends upon is overloaded, then retrying at once adds to the overload, and
thousands of jobs doing the same can prevent the service from recovering at all. The
job is therefore made to wait before its next attempt, and to wait longer after each
successive failure: 1 second, then 2, then 4, and so on, which is called *exponential
backoff*. A random amount is added to each pause, so that jobs which failed together
do not all return together. Chapter 13 examines these pauses in detail.

Some jobs fail for reasons that will never pass. The input is malformed, or the code
has a defect that this particular input exposes, and the hundredth attempt will fail
exactly as the first did. Retrying such a job for ever would waste capacity and,
worse, would conceal the problem. The number of attempts is therefore limited, and a
job that exhausts its attempts is moved to the dead state, where it is kept with its
last error for an engineer to examine. This is the dead-letter queue of chapter 11
under another name. An alert on the number of dead jobs is among the most useful that
a scheduler can provide, since a sudden increase usually means that a defect has been
deployed.

It is helpful if workers can distinguish the 2 kinds of failure where the cause is
evident. A job that fails because its input cannot be parsed will not improve with
repetition, and a worker that reports it as permanently failed spares the system the
remaining attempts.

## Jobs that are due later

A job may be submitted with a time before which it is not to run. The scheduler must
then, at every moment, be able to find the jobs that have become due, and it must do
so without examining all the jobs that are not.

The straightforward method is to store the due time of each job and to keep the
waiting jobs in an index ordered by that time. The scheduler asks the store, every
second or so, for waiting jobs whose time is not later than the present, and since the
index is ordered, the store answers by reading from its beginning and stopping at the
first job that is not yet due. The cost is proportional to the number of jobs that are
due, however many millions are waiting for later.

2 limitations of this method should be understood. The first is precision: a job
may start up to a polling interval late, which is of no importance for a job due in 30
days and matters for one that is meant to fire at a precise second. The second is
that all scheduler nodes query the same index, which becomes a point of contention at
high rates. A common refinement divides responsibility. Jobs due in the distant future
remain in the durable store, and a scheduler node periodically loads those due within
the next minute into its own memory, where it keeps them in a structure ordered by
time and can release each at its exact moment. If that node fails, nothing is lost,
since the jobs are still in the store and another node loads them.

## Recurring jobs

A recurring job is a rule, such as "every day at 02:00", from which a new job is to be
created at each of the times the rule names. Creating those jobs is itself a piece of
work that must be done exactly once per occasion, and with several scheduler nodes
running for the sake of availability, the obvious implementation does it once per
node.

<figure>
<img src="figures/jobs-cron.svg?v=3f383fb3" alt="4 steps. A schedule says to create the job nightly report every day at 02:00. Scheduler node 1 sees that it is 02:00 and creates the job. Scheduler node 2 sees the same and creates the job as well. The report runs twice. The cure is to name each run after its time and to create it only if it is absent.">
<figcaption><b>Figure 12.4</b> 2 scheduler nodes each create the job that the schedule calls for.</figcaption>
</figure>

One remedy is to elect 1 scheduler node as the only one that evaluates schedules,
using the lock service of chapter 10. This works, and it inherits the weakness of
every lock, namely that for a short time during a change of leader there may be 2
nodes that each believe themselves elected. The more dependable remedy does not rely
on there being a single creator. Each run of a recurring job is given a name
constructed from the rule and the scheduled time, and the job is created only if no
job of that name exists. Any number of nodes may then attempt the creation, and the
store admits the first and rejects the rest. The creation has been made idempotent,
which, as so often in this book, is more reliable than trying to ensure that it is
attempted only once.

The opposite hazard is the run that is missed. If every scheduler node is down from
01:55 to 02:10, the question arises of what should happen at 02:10 to the run that
was due at 02:00. There is no universally right answer. A nightly report should
probably be run late, since a late report is better than none. A job that sends a
"good morning" notification should probably be skipped if it is already afternoon. And
a job due every minute that has missed 3 hours should certainly not be run 180 times
in succession. The policy for missed runs, whether to run once on recovery, to run
every missed occasion, or to skip, has to be stated for each recurring job, and a
scheduler that leaves it unstated has made the choice on its users' behalf.

Schedules expressed in local time have a further peculiarity that causes a failure
once or twice a year. On the night when clocks are set forward, the time 02:30 does
not occur, and a job scheduled for it is either skipped or run at an unexpected hour.
On the night when clocks are set back, 02:30 occurs twice, and the job may run twice.
Schedules are best expressed in coordinated universal time, which has no such
discontinuities, and converted for display only.

## Priorities and fairness

When more jobs are waiting than the workers can take, the order in which jobs are
handed out becomes a matter of policy. The simplest policy is first come, first
served, and 2 situations call for something more.

Some jobs are more urgent than others. An email carrying a password reset should not
wait behind 100000 jobs that regenerate thumbnails. Jobs are accordingly given a
*priority*, and the scheduler hands out the highest priority first. Strict priority
has a well-known defect, which is that a continuous supply of high-priority jobs
prevents low-priority jobs from ever running, a condition called *starvation*. It is
countered by letting the effective priority of a job rise with the time it has
waited, or by reserving a share of the workers for each level.

Fairness among customers presents a similar problem. If 1 customer submits a million
jobs and they are served in order of arrival, every other customer's jobs wait behind
all of them. The remedy is to keep a separate queue for each customer and to take from
the queues in rotation, so that a customer who submits a great deal delays chiefly its
own jobs. A limit on the number of jobs of 1 customer that may be running at once
serves the same end.

## Use cases

Developers submit jobs and ask about their state. Workers take jobs and report
results.

<figure>
<img src="figures/jobs-use-cases.svg?v=901b0dc0" alt="A use case diagram of the job scheduler. Developer: submit a job (POST /v1/jobs), read a job&#x27;s state (GET /v1/jobs/{id}). Worker: take a job (POST /v1/leases), report the result (PUT /v1/jobs/{id}/results/{lease}).">
<figcaption><b>Figure 12.5</b> The actors and what each of them does.</figcaption>
</figure>

## Functional requirements

| No. | Functional requirement |
|---|---|
| 0 | A developer can submit a job, to run now or at a later time. |
| 1 | A worker can take a waiting job. A job is given to 1 worker at a time. |
| 2 | A worker reports success or failure. A failed job is tried again, up to 5 times. |
| 3 | A job whose worker stops responding is given to another worker. |
| 4 | A developer can read the state and the number of attempts of a job. |

## Non-functional requirements

| No. | Property | Non-functional requirement |
|---|---|---|
| 0 | Durability | A submitted job is not lost when a scheduler node fails. |
| 1 | Consistency | Strong for job state: 2 workers are not given the same job at the same time. |
| 2 | Delivery | At least once. A job can be started a second time. |
| 3 | Scale | 10 million jobs per day. |

The state of a job has to be strongly consistent. Were 2 scheduler nodes to hold
different views of whether a job is waiting or running, each could hand it to a
worker, and the lease, on which all recovery depends, would mean nothing. The job
store is therefore replicated in the manner of chapters 3 and 4, and a transition is
acknowledged only when a majority has recorded it. What remains eventual is the
relationship between the store and the world: a job recorded as running may in fact
have finished a moment ago, and the design accepts this by allowing a job to run more
than once.

## Core entities

<figure>
<img src="figures/jobs-entities.svg?v=7598339a" alt="The core entities. Job has the fields id u64, payload bytes, state waiting|..., attempts u32, run_at time. Lease has the fields job u64, worker string, deadline time. A Lease lends a job to a worker until a deadline. A job whose lease runs out goes back to the queue.">
<figcaption><b>Figure 12.6</b> The core entities and their fields.</figcaption>
</figure>

## Capacity estimate

<div class="estimate">

<img class="builder" src="art/crab-builder.svg" alt="A crab in a hard hat, in tears.">

**Arithmetic ahead.** 10 million jobs per day are 116 per second on average, which 1 replicated job store handles.

<a class="skip" href="#high-level-design">Skip to the high-level design</a>

<details>
<summary>Show the calculation</summary>

| Quantity | Calculation | Result |
|---|---|---|
| Jobs per second, average | 10000000 ÷ 86400 | 116 |
| Jobs per second, at a peak of 10 times the average | 116 × 10 | 1160 |
| Storage for 30 days | 10000000 × 30 × 1 KB | 300 GB |

</details>

</div>

## The API

A worker takes a job by creating a lease, which is why the request is a `POST` to the
collection of leases, and it reports by writing the result that belongs to its lease,
which is a `PUT` to an address that names the job and the lease.

**Submit a job**

```http
POST /v1/jobs HTTP/1.1
Host: jobs.example
Content-Type: application/json

{ "kind": "resize-image", "payload": { "image": "cat.jpg" }, "run_at": "2026-10-14T09:00:00Z" }
```

```http
HTTP/1.1 201 Created
Location: /v1/jobs/8231
Content-Type: application/json

{ "id": 8231, "state": "waiting", "attempts": 0 }
```

`Location` gives the URL of the new job, as HTTP expects after a `201`.

**Take a job: create a lease**

```http
POST /v1/leases HTTP/1.1
Host: jobs.example
Content-Type: application/json

{ "worker": "worker-2", "seconds": 30 }
```

```http
HTTP/1.1 201 Created
Location: /v1/leases/771
Content-Type: application/json

{ "lease": 771, "job": { "id": 8231, "kind": "resize-image", "payload": { "image": "cat.jpg" } }, "expires_in": 30 }
```

A worker takes a job by creating a lease, so the path names a thing and the method says what happens to it. The scheduler picks the job. When no job is waiting, the answer is `204 No Content`.

**Report the result**

```http
PUT /v1/jobs/8231/results/771 HTTP/1.1
Host: jobs.example
Content-Type: application/json

{ "outcome": "succeeded" }
```

```http
HTTP/1.1 204 No Content
```

The lease number proves that this worker still holds the job. A report with an expired lease is answered `409 Conflict`.

Workers ask the scheduler for jobs, and the scheduler does not push jobs to workers.
A worker that asks is by that fact ready to work, and one that is overloaded or
shutting down merely stops asking, so that no separate mechanism is needed for the
scheduler to learn the capacity of each worker.

## High-level design

<figure class="wide">
<img src="figures/jobs-design.svg?v=5b301a8d" alt="A job scheduler. The components are Developers, Scheduler, Job store, Workers, Reclaimer. Step 1: A developer submits a job. Step 2: The scheduler stores it, in the state waiting. Step 3: A worker takes a job and receives a lease. Step 4: A job whose lease has run out is queued again.">
<figcaption><b>Figure 12.7</b> The components and the path of a request. The steps are numbered.</figcaption>
</figure>

| Component | Role | State it holds | When 1 instance fails |
|---|---|---|---|
| Scheduler | accepts jobs and hands out leases | none of its own | another scheduler node serves the API |
| Job store | holds every job and its state | the jobs, replicated | a follower takes over, as in chapter 4 |
| Worker | takes a job, runs it, reports | none that must survive | its jobs return to the queue when their leases end |
| Reclaimer | returns jobs with expired leases to the queue | none | leases are reclaimed late, by the next reclaimer run |

### One request, step by step

The steps follow the arrows of figure 12.7.

1. A developer sends `POST /v1/jobs`. The scheduler checks the request and gives the job an id.
2. The scheduler writes the job to the job store in the state *waiting*. The store keeps it on a majority of its nodes, as in chapter 3.
3. A worker sends `POST /v1/leases`. The scheduler picks a waiting job, marks it *running* with this worker and a deadline, and returns it.
4. Every few seconds the reclaimer looks for running jobs whose deadline has passed and sets them back to *waiting*.

## The design, deployed

<figure class="wide">
<img src="figures/jobs-deploy.svg?v=f1df67a5" alt="The job scheduler, deployed. Submitters: Services (116 jobs/s), submit jobs. Scheduler, in 3 zones: Load balancers (x 2), any scheduler node, Scheduler nodes (x 6), stateless, Reclaimer (x 2), 1 of 2 is active. Job store, in 3 zones: Job store (x 3), 1 leader, 2 followers. Workers: Workers (x 200), ask, run, report.">
<figcaption><b>Figure 12.8</b> The job scheduler as it is deployed: stateless scheduler nodes, a replicated job store, and 200 workers.</figcaption>
</figure>

The scheduler nodes hold no state and stand behind a pair of load balancers, through
which both submitters and workers reach them. All state is in the job store, a
leader with 2 followers in 3 zones. The reclaimer, which returns jobs with expired
leases to the queue, runs as 2 instances of which 1 is active, chosen through the
lock service of chapter 10, and since reclaiming is itself a conditional write, a
moment in which both believe themselves active does no harm. The 200 workers are the
only tier whose size follows the amount of work, and it can be changed freely.

## How real systems do it

Google has published an account of its distributed cron service that agrees with
this chapter on the essentials and is frank about the same limits. The service keeps
its state in a store replicated by Paxos, and only the leader launches jobs. The
authors state that the system cannot guarantee that a job is launched exactly once,
since the leader may fail between launching and recording the launch, and that the
owners of each job must therefore decide whether it is worse for the job to be
skipped or to run twice. They recommend making launches idempotent, and naming each
launch after its scheduled time so that a repeat can be recognised, as this chapter
does.

The remedy for many workers competing for the same waiting job, a query that passes
over rows locked by other transactions, is the clause `SKIP LOCKED`, which
PostgreSQL has offered since version 9.5 and which is the basis of several job
queues built on that database. For keeping very large numbers of timers in memory,
the classical structure is the timing wheel, in which timers are placed in slots by
their expiry time and a pointer advances 1 slot at each tick, so that starting and
stopping a timer take constant time.

A more recent development goes beyond anything in this chapter. Systems such as
Temporal, which descends from Uber's Cadence, record every step of a long-running
piece of work in a durable history, and recover a failed worker by replaying that
history to the point it had reached. A job in such a system is a program that
appears to run for days without interruption, and the leases, retries and
idempotency of this chapter are handled beneath it. The underlying guarantee is
unchanged: each step runs at least once, and the steps must tolerate repetition.

## Mistakes to avoid

| Mistake | What goes wrong | What to do |
|---|---|---|
| Marking a job as running with no deadline | A worker that crashes keeps the job for ever. | Lend the job under a lease, and requeue it when the lease runs out. |
| Assuming a job runs exactly once | A slow or disconnected worker and its replacement both run it. | Write jobs to be idempotent. |
| Finding a waiting job and marking it in 2 steps | 2 workers take the same job. | Make the change conditional on the job still being waiting. |
| Accepting a result from any worker | A late worker overwrites the state set by its successor. | Accept a result only under the current lease. |
| Retrying at once | Jobs that failed because a service is overloaded keep it overloaded. | Wait longer after each failure, with a random addition. |
| Retrying without limit | A job that can never succeed occupies workers and hides a defect. | Move it to the dead state after a fixed number of attempts, and raise an alert. |
| A fixed lease shorter than the job | The job is reissued while it is still running, every time. | Renew the lease while the job makes progress. |
| Each scheduler node creating recurring jobs | Every run is created once per node. | Name each run after its scheduled time and create it only if absent. |
| No stated policy for missed runs | After an outage, runs are silently skipped or all fire together. | Decide for each recurring job whether to run once, run all, or skip. |
| Schedules in local time | A run is skipped or doubled when the clocks change. | Use coordinated universal time. |
| Strict priorities | Low-priority jobs never run. | Let waiting raise a job's priority, or reserve workers for each level. |
| 1 queue for all customers | A large customer delays everyone. | Keep a queue per customer and serve them in rotation. |

## Failures

| Failure | What users see | How the system recovers |
|---|---|---|
| A worker crashes during a job | the job finishes later | its lease ends and another worker takes the job |
| A worker stalls and finishes late | nothing, if the job is safe to repeat | its late report is refused |
| A job fails every time | the job stops after 5 attempts | it is marked failed for a person to inspect |

## Trade-offs

| Decision | What it gains | What it costs |
|---|---|---|
| Leases with deadlines | no job is stuck with a dead worker | a slow worker can cause a second run |
| Workers pull jobs | a worker takes work only when it has room | a job waits until some worker asks |
| At-least-once execution | no job is lost | jobs must be safe to repeat |

## The simulation

<div class="simulation">

**Simulation in the repository.** The program [`code/jobsim`](https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/distributed-systems-from-the-ground-up/code/jobsim/src/main.rs) simulates this design. To run it, clone the repository and type `cargo run --release -p jobsim` in the `code` directory.

</div>

## References

- S. Davidovic and K. Guliani, "Reliable Cron across the Planet", ACM Queue, 2015.
- PostgreSQL documentation, "SELECT", on `FOR UPDATE SKIP LOCKED`.
- G. Varghese and A. Lauck, "Hashed and Hierarchical Timing Wheels", SOSP 1987.
- Temporal documentation, "Workflow execution" and "Event history".

## Terms introduced in this chapter

| Term | Meaning |
|---|---|
| Job | a piece of work that is recorded now and carried out later |
| Worker | a process that takes jobs and runs them |
| Lease | the loan of a job to a worker until a deadline |
| Attempt | 1 run of a job by a worker |
| Idempotent | having the same effect whether performed once or several times |
| Exponential backoff | waiting longer after each successive failure |
| Dead job | a job that has used up its attempts and is kept for inspection |
| Delayed job | a job that is not to run before a given time |
| Recurring job | a rule from which a job is created at each scheduled time |
| Priority | a rank that decides which waiting job is handed out first |
| Starvation | low-priority jobs never running because higher ones keep arriving |

<div class="summary">

## Summary

- A job is always in 1 of 4 states, and the design consists in making each transition between them safe.
- A job is lent to a worker under a lease, so that the job of a crashed worker returns to the queue.
- A lease can run out while its worker is still running the job, so a job may be executed more than once and has to be idempotent.
- A job is taken with a single conditional change, and a result is accepted only under the current lease.
- Failed jobs are retried after increasing pauses, and jobs that keep failing are set aside as dead.
- Due jobs are found through an index on their time, and recurring jobs are created under a name that makes a second creation fail.
- Priorities need protection against starvation, and customers need separate queues to be treated fairly.

</div>
