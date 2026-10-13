<img class="plate" src="art/ch20.svg?v=c8923e56" alt="A cat sits in a box numbered 12 beside a sign that reads: held for 5 minutes, then sold or free.">

# Ticket Booking: System Design

A booking system sells things of which there is a fixed and usually small supply: the
seats of a cinema for a particular showing, the rooms of a hotel for a particular
night, the places on a particular flight. Each such thing can be sold once, and the
entire purpose of the system is to see that it is not sold twice. 2 travellers who
arrive at the airport holding confirmations for seat 14C on the same flight have been
failed by the airline's booking system in the most direct way possible, and no
apology alters the fact that 1 of them will not be sitting there.

The requirement sounds elementary, and on a single machine serving 1 customer after
another it is. It becomes difficult under the conditions in which booking systems in
fact operate. Many customers act at the same time, on many servers, and 2 of them will
sooner or later choose the same seat in the same instant. A customer who has chosen a
seat needs some minutes in which to pay, and may abandon the purchase without saying
so. And demand is sometimes of a different order from supply, as when the tickets for
a concert go on sale and 2 million people arrive within a minute to compete for 50000
seats. This chapter is about keeping the 1 essential promise, that a seat belongs to
at most 1 buyer, under each of these conditions in turn.

<div class="covers">

This chapter covers

- the promise that a seat is sold at most once, and where it has to be enforced
- 2 buyers choosing the same seat at the same moment
- 3 ways of making the sale of a seat atomic
- holding a seat while its buyer pays, and what happens when the buyer does not
- a payment that arrives after its hold has run out
- booking several seats together
- a seat map that is allowed to be slightly wrong
- selling a number of places without numbered seats
- a sale for which far more buyers arrive than there are seats

</div>

## The promise

It is useful to state exactly what the system promises before considering how. The
promise is an *invariant*, a condition that must hold at every moment and that no
sequence of events may be allowed to violate: every seat of every showing is in
exactly 1 of the states free, held or sold, and when it is held or sold, it is held by
or sold to exactly 1 buyer.

Everything else in the system is permitted to be approximate. The picture of the
auditorium that a customer sees may be a few seconds out of date. The count of
remaining seats shown on the event's page may be slightly wrong. The confirmation
email may arrive a minute late. None of these does lasting harm, and each can
therefore be served from caches and queues by the methods of earlier chapters. The
state of each seat cannot be approximate, and so the design begins by identifying the
single place in which that state is kept and making sure that every change to it
passes through an operation that cannot break the invariant.

That place is the *seat store*, and it is strongly consistent in the sense of chapter
1. It is replicated by the leader and majority method of chapters 3 and 4, so that a
change to a seat is confirmed only when a majority of replicas hold it and no 2
replicas can disagree about who owns a seat.

## 2 buyers and 1 seat

The simplest implementation of a purchase reads the seat, checks that it is free, and
writes the buyer's name against it. Between the reading and the writing there is an
interval, and the entire difficulty of concurrent booking lies in that interval.

<figure class="steps" data-prefix="figures/steps-booking-race" data-count="6" data-version="5ad509b8">
<img src="figures/steps-booking-race-01.svg?v=5ad509b8" alt="2 buyers and 1 seat, step 1 of 6. Seat 12 is free. Ada and Bob both press &#x27;buy&#x27; on it within the same few milliseconds, and their requests reach 2 different servers.">
<figcaption><b>Figure 20.1</b> 2 requests read the same free seat, and both write, unless the write is made conditional on the seat still being free. Use Next and Back to move through the 6 steps.</figcaption>
</figure>

Each request, taken alone, behaved correctly. It read the seat, found it free, and
wrote. The fault lies in the combination, in which the second request's decision was
based on a reading that the first request's write had already made obsolete. This is
the same race that produced 2 leases for 1 job in chapter 12 and 2 forwarded requests
for 1 token in chapter 7, and it will arise in any design that separates a decision
from the reading on which the decision rests.

It is also far from rare. The seats in a hall are not chosen uniformly: everybody
wants the middle of the front rows, and on the first morning of a popular sale,
hundreds of buyers are looking at the same few dozen seats.

## Making the sale atomic

The reading and the writing must be joined into a single step that the store carries
out in its entirety before attending to anything else. There are 3 established ways
of doing so.

The first is a *lock taken in advance*. The transaction that handles a purchase asks
the database to lock the row of the seat before reading it. A second transaction that
wants the same row has to wait until the first has finished, by which time the seat
is taken, and the second, reading it now, finds it so. This approach, in which a lock
is taken on the assumption that a conflict is likely, is called *pessimistic*. It is
straightforward and correct, and its cost is that buyers queue behind one another for
popular seats, each holding a database connection while it waits. If the holder of a
lock is slow, everyone behind it is slow as well.

The second is a *conditional write*. The request does not lock anything. It issues a
single statement of the form "set this seat to held by Ada, provided that it is
currently free", and the store reports whether the condition was met. Of 2
simultaneous statements for the same seat, the store executes one first, which
succeeds, and then the other, whose condition is now false and which therefore changes
nothing. This is the compare-and-set of chapter 1, and it is called *optimistic*,
since it proceeds on the assumption that conflicts are unusual and merely detects them
when they occur. Nobody waits. A buyer who loses the race is told immediately and
chooses again.

The third relies on a *uniqueness constraint*. Bookings are kept in a table of their
own, and the database is instructed that no 2 rows of that table may have the same
showing and seat. A purchase is then an attempt to insert a row, and of 2
simultaneous attempts for the same seat the database accepts 1 and rejects the other
as a violation of the constraint. The invariant is thereby enforced by the database
itself, independently of the application's logic, and it continues to hold even if
some future code path forgets to check.

| | Lock in advance | Conditional write | Uniqueness constraint |
|---|---|---|---|
| What a losing buyer experiences | waits, then is refused | is refused at once | is refused at once |
| Database connections held while waiting | yes | no | no |
| Behaviour when many want 1 seat | a queue forms | 1 wins, the rest retry elsewhere | 1 wins, the rest retry elsewhere |
| Protection if application code is wrong | none | none | the database still refuses |

Our design uses the conditional write for changes of a seat's state and, in addition,
a uniqueness constraint on confirmed bookings, as a second line of defence that does
not depend on every part of the application being correct.

## Holding a seat while the buyer pays

A purchase is not instantaneous. The buyer selects a seat, then enters the details of
a card, and the payment itself takes some seconds to be authorised, as chapter 19
described. During this time the seat must not be sold to anyone else, since it would
be intolerable to take a buyer's payment and then report that the seat has gone. Yet
the seat cannot be marked as sold either, since the buyer may never complete the
payment.

The seat is therefore given an intermediate state, *held*. A *hold* reserves the seat
for 1 buyer for a limited period, commonly between 5 and 15 minutes. If the buyer
pays within that period, the seat becomes sold. If not, the hold lapses and the seat
is available again. A hold is a lease in the sense of chapter 10, granted on a seat.

<figure class="steps" data-prefix="figures/steps-booking-hold" data-count="6" data-version="09c68547">
<img src="figures/steps-booking-hold-01.svg?v=09c68547" alt="A hold that runs out, step 1 of 6. Ada chooses seat 1. The seat is not sold to her yet. It is held in her name for 5 minutes, which gives her time to pay and keeps everyone else away from it meanwhile.">
<figcaption><b>Figure 20.2</b> Ada holds a seat and does not pay, the hold runs out, Bob takes the seat, and Ada's late payment is refused. Use Next and Back to move through the 6 steps.</figcaption>
</figure>

The simulation for this chapter plays out these events on a hall of 3 seats and ends
with seat 1 sold to Bob, Ada's late attempt to pay having been refused.

The time limit is what prevents a seat from being lost to sale. Without it, every
buyer who closed the browser in the middle of a purchase would leave a seat
permanently reserved, and within a few hours of a busy sale the hall would appear
full while a large part of it had been paid for by nobody. The hold must carry its
expiry time within itself, as a field of the seat's record, so that its validity can
be judged by anyone who reads the record, at any time, by a comparison with the
clock.

This last point determines how expiry is implemented. One possibility is a background
process, sometimes called a reaper, that periodically searches for holds whose time
has passed and sets those seats back to free. The simpler and more dependable method
requires no such process for correctness. A held seat whose expiry time has passed is
treated as free by every operation that examines it, so that the conditional write
for a new hold reads "set this seat to held by Bob, provided that it is free or that
its hold has run out". The seat becomes available at the exact moment of expiry
without anything having to happen at that moment. A background process may still tidy
the records, and nothing depends on its punctuality.

The length of the hold is a compromise between 2 kinds of loss. A long hold gives
buyers ample time and keeps abandoned seats out of circulation for longer, which in a
sale that will sell out matters a great deal. A short hold returns seats quickly and
causes more buyers to lose their seat while they are still typing. Systems commonly
display the remaining time to the buyer, which both informs and hurries.

A further abuse must be anticipated. Someone who wishes to disrupt a sale, or to
reserve seats for resale, can request holds on a great many seats with no intention
of paying, and so remove them from sale for the duration of each hold. Holds are
therefore limited in number for each account and each session, and repeated
abandonment by the same party is noticed and restricted.

## Payment and the hold

The hold and the payment are separate operations in separate systems, and the
interval between them contains a case that has to be decided in advance.

Suppose a buyer submits payment 10 seconds before the hold is due to expire, and the
authorisation takes 15 seconds. When the payment system reports success, the hold has
lapsed, and the seat may already have been taken by somebody else. The booking system
now holds a successful payment for a seat it can no longer deliver.

2 measures deal with this, and a careful system uses both. When the buyer submits
payment, the hold is first extended by an amount comfortably longer than a payment
can take, in a conditional write that succeeds only if the hold is still valid and
still belongs to this buyer. If the extension fails, the buyer is told that the seat
is gone and no payment is attempted. And when the payment succeeds, the conversion of
the hold into a sale is itself conditional on the seat's still being held by this
buyer. In the rare case that this last write fails nonetheless, the system refunds
the payment at once, by the procedure of chapter 19, and informs the buyer. The
invariant is never sacrificed to complete a payment: it is always the money that is
returned and never the seat that is double-sold.

The whole exchange must also be idempotent, for the reasons given at length in
chapter 19. The request that confirms a booking carries a key, and a repetition of it,
after a lost reply, returns the original booking and neither charges again nor fails
for want of a hold that the first attempt already consumed.

## Several seats together

A family books 4 seats and wishes to have all 4 or none. A booking that secured 2 of
them and then failed on the third would leave the family with 2 seats it does not
want and 2 other buyers refused for no purpose.

The seats of a single showing normally reside in the same shard of the seat store,
and the 4 conditional writes can then be made within 1 transaction, which succeeds
only if every one of them does. Where a database with locks is used, a hazard arises
that is worth describing because it recurs wherever several locks are taken. If 1
request locks seat 5 and then asks for seat 6, while another locks seat 6 and then
asks for seat 5, each waits for the other indefinitely. This is a *deadlock*, and the
customary prevention is for every request to take its locks in the same fixed order,
by seat number for example, so that no such cycle can form.

## The seat map

Before choosing, a buyer looks at a picture of the hall showing which seats are free.
This picture is requested far more often than seats are bought, since every buyer
looks, most look several times, and many look without buying.

To assemble the picture from the seat store on every request would place the heaviest
load on the 1 component that must remain fast and correct for the sake of the sales
themselves. The seat map is therefore served from a cache, of the kind described in
chapter 9, which is refreshed every second or 2 or updated by messages announcing each
change of a seat's state.

The map is consequently eventually consistent. A buyer may be shown a seat as free
that was taken half a second earlier. This is entirely acceptable, and the reason
should be clearly understood, since it illustrates a principle of wide application.
The map is advisory. It influences which seat a buyer attempts to take, and it decides
nothing. The decision is made by the conditional write to the seat store, which is
always correct, and a buyer who acts on stale information is refused and shown a
fresh map. An approximate display backed by an exact transaction is a combination
that appears throughout well-designed systems. It would be a serious error to reverse
the roles, allowing a sale to proceed because a cached map showed the seat as free.

## Places without numbers

Many events sell admission without assigning seats: 5000 places on the floor of a
concert hall, any of which is as good as any other. The inventory is then a count,
with no distinct seats, and the invariant becomes that the number sold shall
never exceed the capacity.

The same reasoning applies in a simpler form. To read the count, check that it is
below the capacity, and write it back increased by 1 is the race already described,
and would oversell. The sale must be a conditional update, "increase the number sold
by 2, provided that the result does not exceed 5000", which the store applies
atomically.

A single counter for a popular event is, however, a single row that every purchase
must modify, and under very heavy demand it becomes a point of contention, the hot key
of earlier chapters. A common remedy divides the inventory in advance into several
portions, 50 portions of 100 places for example, each a separate counter, and directs
each buyer to a portion chosen at random. Purchases then contend only within a
portion. The portions empty at different rates, so that a buyer may occasionally be
refused by an exhausted portion while places remain in others and must be redirected,
and this complication is the price of removing the bottleneck.

It should be mentioned that some businesses sell more places than they possess, by
policy. Airlines know from experience that a certain proportion of passengers do not
appear, and sell a correspondingly greater number of tickets than there are seats.
The invariant has not failed in such a case. It is a different invariant, with a capacity
set above the physical number, and the system enforces the limit it is given exactly
as before.

## A sale with far more buyers than seats

When the tickets for a greatly anticipated event are released, the load on the system
bears no relation to anything it experiences at other times. 2 million people may
arrive in the first minute for 50000 seats. Of all those requests, at most 50000 can
end in a sale, and the remaining 1950000 are certain to be disappointed. The task of
the system is to conduct the 50000 sales correctly and to disappoint the others
cheaply, without the weight of the crowd bringing down the machinery on which the
sales depend.

No amount of capacity in the booking system itself is a satisfactory answer, since
the seat store's rate of work is limited by the need for strong consistency, and
provisioning for a peak that lasts for minutes and occurs a few times a year is
wasteful. The crowd is therefore kept away from the booking system altogether.

<figure>
<img src="figures/booking-room.svg?v=6affd940" alt="5 steps. 2 million people arrive at 10:00 for 50000 seats. Each is given a place in a waiting room. 5000 at once are admitted to the seat map. As buyers finish, more are admitted in the order of their places. When the seats are gone, the rest are told, without having reached the booking system.">
<figcaption><b>Figure 20.3</b> Arrivals are placed in a waiting room and admitted to the booking system at the rate it can serve.</figcaption>
</figure>

A *waiting room* is a very simple service placed in front of the sale. Each person
who arrives is assigned a position in a queue and shown a page that reports the
position and refreshes occasionally. Serving this page requires almost no work and
can be done from the edge servers of chapter 17. People are admitted from the queue to
the booking system proper at a controlled rate, matched to what that system can serve
comfortably, and each person admitted receives a signed token, valid for a limited
time, without which the booking system accepts no request. The token is what makes the
arrangement enforceable, since a person cannot skip the queue by addressing the
booking system directly.

The effect is to convert a peak that the booking system could not survive into a
steady load that it handles with ease, the excess being absorbed by a component
designed for nothing else. It is the load levelling that chapter 11 attributed to
queues, applied to people. It also restores a measure of fairness, since admission
follows the order of the queue, where it would otherwise fall to whoever's request
happened to get through an overloaded server.

Whether the order of the queue should be the order of arrival is itself a question of
policy. When a sale opens at a known moment, the people who arrive in the first second
are separated by network delays and nothing else, and strict order of arrival rewards
those with the fastest connections and, above all, automated programs. Many systems
therefore gather everyone who arrives before the opening into a pool and assign their
positions at random when the sale begins.

Automated purchasing is the abiding adversary of such sales. Programs operated by
resellers can submit requests faster than any person and from thousands of addresses.
The defences are layered and none is complete: rate limits for each account and each
address, as in chapter 7; a limit on the number of tickets for each buyer; challenges
that are easy for people and costly for programs; and the requirement of an account
with some history. The waiting room is where most of these checks are applied, before
a request has cost the booking system anything.

## Use cases

A buyer looks at the seats of a showing, holds one, and pays for it.

<figure>
<img src="figures/booking-use-cases.svg?v=1e8300a2" alt="A use case diagram of the booking system. Buyer: see which seats are free (GET /v1/shows/{id}/seats), hold a seat (POST /v1/shows/{id}/holds), pay for a held seat (POST /v1/bookings).">
<figcaption><b>Figure 20.4</b> The actor and what it does.</figcaption>
</figure>

## Functional requirements

| No. | Functional requirement |
|---|---|
| 0 | A buyer can see which seats of a showing are free. |
| 1 | A buyer can hold a free seat for 5 minutes. |
| 2 | A buyer can pay for a seat that they hold, upon which the seat is sold to them. |
| 3 | A hold that is not paid for within its time ends, and the seat is free again. |
| 4 | A seat is held by, or sold to, at most 1 buyer at any moment. |
| 5 | A buyer can book several seats together, receiving all of them or none. |

## Non-functional requirements

| No. | Property | Non-functional requirement |
|---|---|---|
| 0 | Consistency | Strong for the state of every seat. Eventual for the seat map. |
| 1 | Availability | 99.95% for booking. When the seat store cannot reach a majority, sales stop. |
| 2 | Latency | A hold is granted or refused within 200 ms. |
| 3 | Scale | 100000 showings on sale, and a peak of 2 million arrivals in a minute for a single showing. |

Non-functional requirements 0 and 1 belong together. The state of a seat is the 1
thing in this system that may never be wrong, and the design accordingly accepts that
when the seat store has lost its majority, no seats can be sold until it is restored.
An hour without sales is a loss of revenue. A hall with 2 buyers for 1 seat is a loss
of the customers' trust, and cannot be repaired by restarting anything.

## Core entities

<figure>
<img src="figures/booking-entities.svg?v=ed1f3bfb" alt="The core entities. Seat has the fields show u64, label string, state free|held|sold. Hold has the fields seat string, buyer string, expires time. Booking has the fields id u64, seat string, buyer string, payment u64. A Hold reserves a seat for a few minutes. A Booking is made from a hold that is still valid when the payment succeeds.">
<figcaption><b>Figure 20.5</b> The core entities and their fields.</figcaption>
</figure>

## Capacity estimate

<div class="estimate">

<img class="builder" src="art/crab-builder.svg" alt="A crab in a hard hat, in tears.">

**Arithmetic ahead.** The seats of 100000 showings fit in a few gigabytes. The difficulty of this system lies in the peak of arrivals. The volume of data is small.

<a class="skip" href="#high-level-design">Skip to the high-level design</a>

<details>
<summary>Show the calculation</summary>

| Quantity | Calculation | Result |
|---|---|---|
| Seats on sale | 100000 showings × 300 seats | 30 million |
| Storage for seats | 30 million × 100 bytes | 3 GB |
| Arrivals at the peak | 2000000 ÷ 60 seconds | 33000 per second |
| Admitted to booking | chosen to suit the seat store | 500 per second |
| Time to sell 50000 seats | 50000 ÷ 500 per second | 100 seconds |

</details>

</div>

## The API

A hold is a resource created within a showing, and a booking is a resource created
from a hold. Both are created with `POST`, and both carry an idempotency key.

**See which seats are free**

```http
GET /v1/shows/881/seats HTTP/1.1
Host: tickets.example
```

```http
HTTP/1.1 200 OK
Content-Type: application/json
Cache-Control: max-age=2

{
  "seats": [
    { "label": "A1", "state": "free" },
    { "label": "A2", "state": "held" },
    { "label": "A3", "state": "sold" }
  ]
}
```

The header `Cache-Control` permits this answer to be reused for 2 seconds, which
states openly that the map may be that much out of date.

**Hold a seat**

```http
POST /v1/shows/881/holds HTTP/1.1
Host: tickets.example
Idempotency-Key: 5d1c-hold-1
Content-Type: application/json

{ "seats": ["A1"] }
```

```http
HTTP/1.1 201 Created
Location: /v1/shows/881/holds/7730
Content-Type: application/json

{ "id": 7730, "seats": ["A1"], "expires": "2026-10-14T10:05:00Z" }
```

**Hold a seat that somebody else has taken**

```http
POST /v1/shows/881/holds HTTP/1.1
Host: tickets.example
Idempotency-Key: 9a2e-hold-1
Content-Type: application/json

{ "seats": ["A1"] }
```

```http
HTTP/1.1 409 Conflict
Content-Type: application/problem+json

{
  "type": "/problems/seat-taken",
  "title": "The seat is no longer available",
  "status": 409,
  "seats": ["A1"]
}
```

`409 Conflict` is the status for a request that is valid in itself and cannot be
carried out because of the present state of the resource.

**Pay for a held seat**

```http
POST /v1/bookings HTTP/1.1
Host: tickets.example
Idempotency-Key: 5d1c-book-1
Content-Type: application/json

{ "hold": 7730, "payment_token": "tok_83hf" }
```

```http
HTTP/1.1 201 Created
Location: /v1/bookings/55102
Content-Type: application/json

{ "id": 55102, "show": 881, "seats": ["A1"], "state": "confirmed" }
```

The payment token stands for the buyer's card, as chapter 19 explained, so that the
booking system never handles a card number.

## High-level design

<figure class="wide">
<img src="figures/booking-design.svg?v=7a047cb0" alt="Booking a seat. The components are Buyer, Booking API, Seat store, Payment system, Hold reaper. Step 1: A buyer asks to hold seat 12. Step 2: The API writes the hold only if the seat is free. Step 3: The buyer pays, and the hold becomes a booking. Step 4: Holds that are not paid in time are released.">
<figcaption><b>Figure 20.6</b> The components and the path of a request. The steps are numbered.</figcaption>
</figure>

| Component | Role | State it holds | When 1 instance fails |
|---|---|---|---|
| Waiting room | admits buyers at a rate the booking system can serve | queue positions, in memory | positions are assigned again, and those already admitted keep their tokens |
| Booking API | turns requests into conditional writes | none | another instance serves the request |
| Seat store | holds the state of every seat | seats, holds and bookings, replicated | a follower is elected, and sales pause for about a second |
| Seat map cache | serves the picture of the hall | a copy, up to 2 seconds old | the map is rebuilt from the seat store |
| Payment system | charges the buyer | see chapter 19 | holds are extended, and bookings wait |

### One request, step by step

The steps follow the arrows of figure 20.6.

1. A buyer asks to hold seat A1 of showing 881.
2. The booking API sends the seat store 1 conditional write: set A1 to held by this buyer until 10:05, provided that A1 is free or its hold has run out. The store answers that the write was applied, and the API returns the hold. Had the condition been false, the API would have answered `409`.
3. The buyer submits payment. The API first extends the hold, conditionally, and then asks the payment system to charge the buyer. When the charge succeeds, the API sends a second conditional write: set A1 to sold to this buyer, provided that it is still held by them.
4. Independently of any request, holds whose time has passed are cleared from the records. No sale depends on this, since an expired hold is already treated as free.

## Mistakes to avoid

| Mistake | What goes wrong | What to do |
|---|---|---|
| Reading a seat and then writing it | 2 buyers both find it free and both are sold it. | Make the write conditional on the seat's state. |
| Trusting the seat map to decide a sale | A stale map sells a seat that is already taken. | Let the map advise, and the conditional write decide. |
| Selling a seat as soon as it is chosen | Buyers who never pay keep seats for ever. | Hold the seat for a limited time, and sell it on payment. |
| Holds without an expiry time in the record | Expiry depends on a background process being punctual. | Store the expiry time, and treat an expired hold as free. |
| Taking payment without checking the hold | A buyer pays for a seat that has since gone to someone else. | Extend the hold conditionally before charging. |
| Keeping the money when the final write fails | The buyer has paid and has no seat. | Refund at once, and never double-sell to save a payment. |
| A booking request without an idempotency key | A retry charges twice, or fails because the hold is already used. | Require a key, and return the first result for a repeat. |
| Booking several seats in separate steps | A buyer is left with some of the seats they wanted. | Write all of them in 1 transaction. |
| Locking seats in whatever order they were requested | 2 requests wait for each other indefinitely. | Take locks in a fixed order. |
| 1 counter for a very popular event | Every purchase contends on the same row. | Divide the places into portions with separate counters. |
| Letting the whole crowd reach the booking system | The seat store is overwhelmed, and the sales themselves fail. | Admit buyers from a waiting room at a controlled rate. |
| Unlimited holds for each account | 1 party removes many seats from sale without paying. | Limit the holds of each account and session. |

## Failures

| Failure | What users see | How the system recovers |
|---|---|---|
| A buyer abandons a purchase | the seat appears as held for up to 5 minutes | the hold runs out, and the seat is free |
| The payment is slow | the buyer waits | the hold was extended before charging, so the seat is kept |
| The payment succeeds and the seat is gone | the buyer is told, and refunded | the refund is issued automatically |
| The reply to a booking is lost | the buyer's app tries again | the key returns the booking already made |
| The seat store's leader fails | holds and bookings fail for about 1 second | a follower is elected, as in chapter 4 |
| The seat map cache is lost | the map loads more slowly for a moment | it is rebuilt from the seat store |
| A sale opens to an enormous crowd | most people wait in the queue | the waiting room admits them at the rate the system can serve |

## Trade-offs

| Decision | What it gains | What it costs |
|---|---|---|
| Strong consistency for seats | a seat is never sold twice | no sales while the seat store lacks a majority |
| Conditional writes | no buyer waits behind another | a buyer who loses a race has to choose again |
| Holds with a time limit | abandoned seats return to sale | a slow buyer can lose a seat |
| A cached seat map | the seat store is spared most of the reads | the map can show a seat that has just been taken |
| A waiting room | the booking system works at a steady load | buyers wait, and may wait for nothing |

## The simulation

<div class="simulation">

**Simulation in the repository.** The program [`code/bookingsim`](https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/distributed-systems-from-the-ground-up/code/bookingsim/src/main.rs) simulates this design. To run it, clone the repository and type `cargo run --release -p bookingsim` in the `code` directory.

</div>

## Terms introduced in this chapter

| Term | Meaning |
|---|---|
| Invariant | a condition that must hold at every moment |
| Seat store | the strongly consistent store of the state of every seat |
| Pessimistic locking | locking a record before reading it, on the assumption that a conflict is likely |
| Optimistic concurrency | writing on condition that the record is unchanged, and retrying when it is not |
| Uniqueness constraint | a rule, enforced by the database, that no 2 rows may share certain values |
| Hold | the reservation of a seat for 1 buyer for a limited time |
| Deadlock | 2 requests each waiting for a lock that the other holds |
| Seat map | the picture of which seats are free, held and sold |
| Overbooking | deliberately selling more places than physically exist |
| Waiting room | a queue in front of a sale, from which buyers are admitted at a controlled rate |
| `409 Conflict` | the HTTP status for a request that the present state of the resource does not allow |

<div class="summary">

## Summary

- The 1 promise of a booking system is that a seat is held by or sold to at most 1 buyer, and everything else may be approximate.
- Reading a seat and then writing it lets 2 buyers take the same seat, so the write is made conditional on the seat's state.
- A seat is held for a limited time while its buyer pays, and an expired hold is treated as free without anything having to act.
- Before charging, the hold is extended, and if the seat is lost in spite of that, the payment is refunded.
- The seat map is served from a cache and may be stale, because it advises and the conditional write decides.
- Places without numbers are sold by a conditional update of a count, divided into portions when demand is extreme.
- When far more buyers arrive than there are seats, a waiting room admits them at the rate the system can serve.

</div>
