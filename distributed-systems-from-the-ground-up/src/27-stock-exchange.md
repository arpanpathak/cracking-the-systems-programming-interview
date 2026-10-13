<img class="plate" src="art/ch27.svg?v=20c9c88c" alt="A squirrel stands beside a sign that reads: sell 1005, buy 1000, no trade yet.">

# Stock Exchange: System Design

A stock exchange is a place where people who wish to buy a share and people who
wish to sell it are brought together. Each states the price at which they are
willing to trade, and whenever a buyer's price meets a seller's, a trade is made.
The program at the centre of a modern exchange, which keeps the outstanding orders
and decides who trades with whom, is the *matching engine*.

The requirements laid on this program are unlike those of any other system in this
book, and they lead to a design that at first sight contradicts much of what the
book has recommended. An exchange must be *fair*, in a precise and legally
enforceable sense: of 2 orders at the same price, the one that arrived first must
trade first, with no exception and no ambiguity about which was first. It must be
*fast*, answering an order in well under a millisecond, since the participants are
themselves programs that compete on speed. And it must be *deterministic*, so that
its every decision can be reconstructed afterwards and shown to a regulator.

The preceding chapters have met demands for throughput by dividing work among many
machines and many threads. A matching engine does the opposite. The trading of each
share is handled by a single thread on a single machine, with all its data in
memory and no database in its path. This chapter explains why that is the right
design for this problem, and how such a system, which appears to have a single point
of failure at its heart, is nevertheless made to survive the loss of any machine.

<div class="covers">

This chapter covers

- orders, the order book, and the rule of price and time
- matching an incoming order against the book
- why fairness requires a single agreed order of events
- why the engine is 1 thread, and why that is fast
- the journal, and recovering by replaying it
- a standby that is ready to take over
- the gateway, and the checks that precede matching
- publishing prices to everybody at the same moment
- what happens after a trade

</div>

## Orders and the book

A participant expresses a wish to trade by submitting an *order*. The commonest
kind, the *limit order*, names a side, a quantity and a price: buy 100 shares at
10.05 or less, or sell 50 shares at 10.10 or more. The price is a limit beyond which
the participant will not go, and a better price is always acceptable.

An order that cannot be satisfied at once waits. The collection of waiting orders
for 1 share is its *order book*, and it has 2 halves. The buy side holds the orders
to buy, of which the most attractive to a seller is the one with the highest price.
The sell side holds the orders to sell, of which the most attractive to a buyer is
the one with the lowest. The highest price that any buyer is offering is the *best
bid*, the lowest that any seller is asking is the *best ask*, and the difference
between them is the *spread*. So long as the best bid is below the best ask, nobody
is willing to trade with anybody, and the book is at rest.

Within each half the orders are ranked by a rule called *price-time priority*. An
order at a better price ranks ahead of an order at a worse one. Among orders at the
same price, the one that arrived earlier ranks ahead. The rule rewards a participant
for offering a better price, and, at a given price, for having committed to it
sooner, and it is the definition of fairness on which the exchange rests.

Prices are held as whole numbers of the smallest unit in which the share is quoted,
for the reasons set out in chapter 19. 10.05 is the integer 1005.

## Matching

When a new order arrives, the engine compares it with the best order on the opposite
side of the book. If their prices meet, which for an incoming buy means that its
limit is at or above the best ask, a *trade* is made between them, for the smaller
of their 2 quantities. The trade takes place at the price of the order that was
waiting in the book, and this is why an incoming order may obtain a better price
than its limit. If the incoming order has quantity remaining, the engine turns to
the next best waiting order and repeats. When the prices no longer meet, or the
opposite side is exhausted, whatever remains of the incoming order is placed in the
book to wait.

<figure class="steps" data-prefix="figures/steps-match-book" data-count="4" data-version="c193a9ef">
<img src="figures/steps-match-book-01.svg?v=c193a9ef" alt="An order book, order by order, step 1 of 4. 3 orders to sell and 1 to buy are waiting. The cheapest seller asks 1005 and the buyer offers 1000, so nobody trades. Prices are in cents, and the gap between 1000 and 1005 is called the spread.">
<figcaption><b>Figure 27.1</b> 7 orders arrive at an empty book, and the book and the trades are shown after each of the last 3. Use Next and Back to move through the 4 steps.</figcaption>
</figure>

The simulation for this chapter processes these 7 orders. The first 4 rest in the
book, since the cheapest seller asks 1005 and the only buyer offers 1000. Order 5, to
buy 50 at 1005, trades with the 2 orders waiting at that price in the order of their
arrival, taking 30 from order 2 and 20 from order 3. Order 6 takes the remainder of
order 3 and all of order 1, and its unfilled 30 shares become the best bid. Order 7,
a sale at 995 or better, trades at 1010 and at 1000, the prices of the buyers who
were waiting. 200 shares change hands, and 10 remain in the book.

Several other kinds of order are built from the same mechanism. A *market order*
names no price and trades at once with whatever is best on the other side, until it
is filled. A *cancellation* removes a waiting order from the book. An order may be
marked to trade immediately as far as it can and to cancel the rest, without ever
resting in the book. None of these changes the essential structure.

The book has to support 3 operations efficiently: finding the best price on a side,
adding an order at a price, and removing an order from anywhere within it, since
most orders on a real exchange are cancelled before they trade. A usual arrangement
keeps, for each side, a map from price to the queue of orders at that price, ordered
by price, together with an index from order identifier to the order's place in its
queue, so that a cancellation finds its target directly.

## One agreed order of events

The rule of price and time presupposes that, of any 2 orders, it is known which
arrived first. On a single machine with a single connection this is trivial. On a
real exchange, orders arrive over thousands of connections at several gateway
machines, within microseconds of one another, and the question of which was first
is by no means settled by the fact of their arrival.

The clocks of different machines cannot settle it, as chapter 8 explained at length.
2 gateways that each stamp their orders with the time will disagree by more than
the interval that separates competing orders, and whichever gateway's clock runs
slow will systematically favour its own participants.

The exchange therefore establishes the order of events by decree, at a single point.
Every order, cancellation and other input passes through a component called the
*sequencer*, which assigns to each the next number in a single sequence. That
number, and nothing else, defines the order in which events are deemed to have
occurred. An order is "first" if the sequencer numbered it first.

This is the fourth appearance in this book of the same idea. The leader of a shard
assigned sequence numbers to records in chapter 3, the message store numbered the
messages of a conversation in chapter 18, and the session server numbered the
operations on a document in chapter 26. In each case a question about order among
many parties, which could not be answered by comparing clocks, was resolved by
appointing a single party to decide.

## Why the engine is a single thread

Given a single sequence of inputs, the matching of a share is an inherently
sequential computation. Whether order 6 trades, and at what price, depends on
exactly what the book contained after order 5, which depends on order 4, and so on
to the beginning. 2 orders for the same share cannot be matched in parallel, since
the result for the second depends on the first.

One might still be tempted to use several threads, protecting the book with locks.
This would be both slower and worse. It would be slower because the work for each
order is very small, a few lookups and updates in memory, and the cost of taking
and releasing locks and of moving data between processor cores would exceed the cost
of the work itself. It would be worse because the order in which threads acquire a
lock is decided by the operating system's scheduler and varies from run to run, so
that the same inputs could produce different trades on different occasions.

The engine is therefore a single thread that takes inputs from the sequence one
after another and processes each to completion before looking at the next. It holds
the entire book in memory, waits for no disk and no network during matching, and
takes no locks, since nothing else touches its data. An engine of this kind can
process several hundred thousand orders a second on 1 core, with a response time of
a few microseconds, which is far more than a design with locks and threads achieves.
The general lesson, which applies well beyond exchanges, is that for work which is
small, sequential by nature and entirely in memory, a single thread is the fastest
arrangement, and no limitation that calls for apology. Chapter 6 reached a related
conclusion when it gave the store to a single committer thread.

Capacity beyond 1 core is obtained by partitioning. Each share has its own book, and
the books of different shares are independent of one another. Shares are divided
among engines, each engine a single thread serving some hundreds of shares, and a
share that is exceptionally busy can be given an engine to itself. This is sharding
by share, with the order book as the unit that must not be divided.

## The journal and the replay

An engine that keeps everything in memory loses everything when its machine fails,
and an exchange cannot lose its order book. The apparent conflict is resolved by a
property that the design has been careful to preserve.

The engine is *deterministic*. Its output depends on its sequence of inputs and on
nothing else. It consults no clock, generates no random numbers, and is not
affected by the timing of threads, there being only 1. From this it follows that the
state of the engine can always be recomputed by starting from an empty book and
applying the same inputs again in the same order.

It is therefore sufficient to make the inputs durable. The sequencer writes every
input to a *journal* on disk, in sequence, before the engine processes it. This is
the write-ahead log of chapter 2, and it is kept on several machines by the
replication of chapter 3, so that it survives the loss of any 1 of them.

<figure>
<img src="figures/match-replay.svg?v=bdb9b4c4" alt="4 steps. Every event is written to the journal first. The engine applies events in that order, and the same input always gives the same book. The machine fails, and the book in its memory is gone. A standby replays the journal and arrives at exactly the same book.">
<figcaption><b>Figure 27.2</b> The engine's state is lost with its machine and recomputed from the journal.</figcaption>
</figure>

If the engine's machine fails, a replacement reads the journal from the beginning
and arrives at exactly the book that the failed engine held, having made exactly the
same trades. The state was never the thing that needed protecting. The inputs were,
and the state follows from them.

To replay a whole day's journal would take too long to be acceptable, and in
practice a *standby* engine runs continuously on another machine, reading the same
journal and applying the same inputs a moment behind the primary. It holds an
identical book at all times and suppresses its outputs. When the primary fails, the
standby is promoted and begins to publish, and the changeover takes milliseconds.
Since the 2 engines processed the same inputs deterministically, there is no
question of their disagreeing about the state of the book.

The same property serves purposes other than recovery. A regulator who asks why a
particular order did not trade can be answered by replaying the journal to that
moment and examining the book. A new version of the engine can be tested by feeding
it yesterday's journal and comparing its trades with those that were actually made.
And a defect that occurred in production can be reproduced exactly, as often as
required, on a developer's machine.

Determinism has to be defended deliberately, since it is easily lost. An engine that
reads the time from the system clock in order to stamp a trade has made its output
depend on something outside the journal, and its replay will produce different
stamps. The time must therefore itself be an input, assigned by the sequencer and
recorded in the journal. Iterating over a hash table whose order varies between
runs, or performing arithmetic in floating point that differs between processors,
would break determinism in the same way.

## The gateway

Participants do not communicate with the engine directly. They connect to
*gateways*, which authenticate them, check the syntax of what they send, and apply
the checks that have to be made before an order is allowed to reach the book.

The most important of these are the checks of risk. A participant must have the
funds to pay for what they buy and the shares to deliver what they sell, and must be
within the limits their broker has set. An order of obviously mistaken size or
price, such as a sale at a hundredth of the current price, is rejected, since such
errors have on more than one occasion caused very large losses within seconds. And
each participant is limited in the rate at which they may send orders, by the rate
limiter of chapter 7.

It matters where these checks are made. They are performed before the sequencer, so
that an order which fails them never enters the journal and never affects the book.
Checks that depend on the state of the book itself, on the other hand, must be made
by the engine, after sequencing, since only there is the state well defined.

Since the gateways lie before the sequencer, there is a subtle demand of fairness on
them as well. If 1 gateway were consistently faster than another, the participants
connected to it would have their orders sequenced earlier. Exchanges go to
considerable lengths to equalise the path from every participant to the sequencer,
to the extent of giving all participants network cables of the same length.

## Publishing prices

Every change to the book is of interest to all participants: each trade, and each
change in the best bid and ask. The engine publishes a stream of these events, the
*market data*, and participants decide what to do next on the basis of it.

The demand of fairness applies here with particular force. A participant who learned
of a trade a millisecond before the others could act on it first, to their profit
and at the others' expense. Market data is therefore published to all participants
simultaneously, by a mechanism designed to deliver the same message to every
recipient at as nearly the same instant as can be arranged.

The engine does not wait for the market data to be delivered, or even to be sent.
It hands each event to a separate publishing component and proceeds to the next
input. Every event carries its sequence number, and a participant who notices a gap
in the numbers requests the missing events again, which is the recovery by sequence
number that chapter 18 used for messages.

## After the trade

A trade made by the engine is an agreement, and the exchange of shares for money
that it calls for happens later. The record of each trade passes to a *clearing*
system, which works out what each participant owes and is owed, and thence to
*settlement*, in which shares and money actually change hands, typically 1 or 2 days
afterwards.

These later stages have requirements of the kind that chapter 19 described. They
must be exact, every movement must be recorded twice in a ledger, and nothing may be
lost, while speed is of little account. They are built on ordinary strongly
consistent databases, and they receive the trades from the engine through a durable
queue, so that the engine is never made to wait for them. The architecture of an
exchange is thus divided at the trade: before it, a path built for speed and
determinism, in memory and on a single thread, and after it, a path built for
exactness and durability, with databases and reconciliation.

## Use cases

A trader places orders, cancels them, and watches the prices.

<figure>
<img src="figures/match-use-cases.svg?v=58f9224f" alt="A use case diagram of the exchange. Trader: place an order (POST /v1/orders), cancel an order (DELETE /v1/orders/{id}), watch the prices (a stream of market data).">
<figcaption><b>Figure 27.3</b> The actor and what it does.</figcaption>
</figure>

## Functional requirements

| No. | Functional requirement |
|---|---|
| 0 | A participant can place an order to buy or sell a quantity of a share at a limit price. |
| 1 | A participant can cancel an order that has not been completely filled. |
| 2 | An incoming order trades with waiting orders on the other side whose prices meet its own, best price first, and earliest first at each price. |
| 3 | A trade is made at the price of the order that was waiting. |
| 4 | What remains of an order waits in the book. |
| 5 | Every trade and every change in the best prices is published to all participants. |

## Non-functional requirements

| No. | Property | Non-functional requirement |
|---|---|---|
| 0 | Fairness | Events are processed in the order of a single sequence, which is the same for every participant. |
| 1 | Determinism | The same sequence of inputs always produces the same trades. |
| 2 | Latency | An order is answered within 1 ms, 99% of the time. |
| 3 | Durability | No input that was sequenced is lost. |
| 4 | Availability | 99.99% during trading hours, with a changeover of under 1 second when a machine fails. |
| 5 | Consistency | Strong. There is exactly 1 order book for each share. |

The system is strongly consistent in the most literal sense available. For each
share there is 1 sequence of events and 1 book, and no participant can ever be shown
a state that another participant's view contradicts. Where earlier chapters accepted
eventual consistency in order to gain availability or speed, an exchange cannot,
since 2 books that disagreed about who had bought what would be a failure of the
exchange's entire purpose. It obtains its speed by other means, namely by keeping
the consistent part small enough to be executed by a single thread.

## Core entities

<figure>
<img src="figures/match-entities.svg?v=0993d9dc" alt="The core entities. Order has the fields id u64, side buy|sell, price cents, quantity shares. Trade has the fields buy order id, sell order id, price cents, quantity shares. Book has the fields buys price -&gt; queue, sells price -&gt; queue. The Book holds the orders that are waiting. A Trade is made when a new order meets a waiting order at an agreed price.">
<figcaption><b>Figure 27.4</b> The core entities and their fields.</figcaption>
</figure>

## Capacity estimate

<div class="estimate">

<img class="builder" src="art/crab-builder.svg" alt="A crab in a hard hat, in tears.">

**Arithmetic ahead.** A busy share receives a few thousand orders per second at its peak, which a single thread handles with a great deal to spare, and a day's journal for the whole exchange is some tens of gigabytes.

<a class="skip" href="#high-level-design">Skip to the high-level design</a>

<details>
<summary>Show the calculation</summary>

| Quantity | Calculation | Result |
|---|---|---|
| Orders and cancellations per day | given | 500 million |
| Average per second, in a trading day of 6.5 hours | 500 million ÷ 23400 s | about 21000 |
| Peak per second | 10 times the average | about 210000 |
| Capacity of 1 engine thread | measured, in memory, without locks | several hundred thousand per second |
| Size of a journal entry | sequence, time, participant, share, side, price, quantity | about 64 bytes |
| Journal per day | 500 million × 64 bytes | 32 GB |
| Orders resting in the books | 5000 shares × 10000 orders | 50 million, about 3 GB in memory |

</details>

</div>

## The API

Participants on a real exchange use compact binary protocols over persistent
connections, since every microsecond counts. The operations themselves are few, and
are shown here in the form of HTTP for clarity.

**Place an order**

```http
POST /v1/orders HTTP/1.1
Host: exchange.example
Idempotency-Key: firm-22-000481
Content-Type: application/json

{ "share": "ACME", "side": "buy", "price": 1005, "quantity": 50 }
```

```http
HTTP/1.1 201 Created
Location: /v1/orders/5
Content-Type: application/json

{
  "id": 5,
  "sequence": 88213,
  "state": "filled",
  "trades": [
    { "price": 1005, "quantity": 30, "with": 2 },
    { "price": 1005, "quantity": 20, "with": 3 }
  ]
}
```

The `sequence` is the number that the sequencer assigned, which fixes the position
of this order relative to every other event. The key guards against an order's being
placed twice when a reply is lost, a mistake that in this setting costs money at
once.

**Cancel an order**

```http
DELETE /v1/orders/4 HTTP/1.1
Host: exchange.example
```

```http
HTTP/1.1 200 OK
Content-Type: application/json

{ "id": 4, "state": "cancelled", "remaining": 10 }
```

A cancellation is an input like any other. It is sequenced, and it takes effect at
its place in the sequence. If the order traded in full before the cancellation was
sequenced, the answer is `409 Conflict`, since there is nothing left to cancel.

**An event of the market data stream**

```json
{ "sequence": 88213, "share": "ACME", "trade": { "price": 1005, "quantity": 30 }, "best_bid": 1000, "best_ask": 1005 }
```

## High-level design

<figure class="wide">
<img src="figures/match-design.svg?v=34afba22" alt="An exchange for 1 share. The components are Traders, Gateway, Sequencer, Matching engine, Journal, Market data. Step 1: A trader sends an order. Step 2: The gateway checks it and passes it on. Step 3: The sequencer numbers it and writes it to the journal. Step 4: The engine matches orders in the order of their numbers. Step 5: Every trade is published.">
<figcaption><b>Figure 27.5</b> The components and the path of an order. The steps are numbered.</figcaption>
</figure>

| Component | Role | State it holds | When 1 instance fails |
|---|---|---|---|
| Gateway | authenticates participants, and applies checks of syntax, risk and rate | connections, and limits | participants reconnect to another gateway |
| Sequencer | gives every input the next number, and writes it to the journal | the sequence number | a standby continues from the journal |
| Journal | holds every input, in order | the journal, replicated on several machines | a follower is elected |
| Matching engine | applies inputs in order to the books it serves | the order books, in memory | the standby, which has applied the same inputs, takes over |
| Market data | publishes trades and best prices to all participants | recent events, for requests to resend | a second publisher sends the same stream |

### One order, step by step

The steps follow the arrows of figure 27.5.

1. A trader sends an order to a gateway over a connection that is already open.
2. The gateway checks the order: that it is well formed, that the trader is within their limits, and that its price is not absurd. It then passes the order to the sequencer.
3. The sequencer assigns the next sequence number and a time, and appends the order to the journal, which is confirmed when a majority of its replicas hold it.
4. The engine takes the order from the sequence, matches it against the book, and updates the book. The standby engine does the same, a moment later.
5. The engine emits the trades and the new best prices, which are published to every participant and passed on for clearing.

## Mistakes to avoid

| Mistake | What goes wrong | What to do |
|---|---|---|
| Ordering events by the clocks of the gateways | Clocks differ by more than the gap between competing orders, and priority is decided by clock error. | Number every input in a single sequencer. |
| Matching with several threads and locks | Slower than 1 thread, and no longer the same from run to run. | Use 1 thread for each book, and partition by share. |
| A database in the path of matching | Every order waits for a disk and a network. | Keep the book in memory, and make the inputs durable in a journal. |
| Protecting the state and not the inputs | Recovery needs a consistent copy of a book that changes thousands of times a second. | Journal the inputs, and recompute the state. |
| Reading the clock inside the engine | A replay gives different results from the original run. | Make the time an input, assigned by the sequencer. |
| Processing an input before it is in the journal | A crash loses an order that has already traded. | Journal first, then process. |
| Prices in floating-point numbers | Prices that ought to be equal compare as different. | Use whole numbers of the smallest unit. |
| Waiting for market data to be delivered | A slow recipient delays the engine for everybody. | Hand events to a publisher, and let recipients recover gaps by sequence number. |
| Publishing to some participants before others | Those who see a trade first profit at the others' expense. | Publish to all at the same moment. |
| No checks before the book | A mistaken order moves the price in milliseconds. | Check size, price and limits at the gateway. |
| Orders without an idempotency key | A retry after a lost reply places the order twice. | Require a key for every order. |

## Failures

| Failure | What participants see | How the system recovers |
|---|---|---|
| The engine's machine fails | a pause of under a second | the standby, which holds the same book, begins to publish |
| The sequencer fails | a pause of under a second | a standby sequencer continues from the last number in the journal |
| A gateway fails | its participants are disconnected | they reconnect elsewhere, and their waiting orders are untouched in the book |
| The reply to an order is lost | the participant does not know whether the order was placed | the retry carries the same key and returns the original result |
| A participant misses market data | a gap in the sequence numbers | the missing events are requested again |
| A defect is found in the engine | a wrong trade, or a halt in trading | the journal is replayed against a corrected engine to establish what should have happened |

## Trade-offs

| Decision | What it gains | What it costs |
|---|---|---|
| A single sequencer | an unambiguous order, and hence fairness | every input passes through 1 point |
| A single thread for each book | speed and determinism together | the capacity of a book is limited to 1 core |
| State in memory, inputs in a journal | no database in the path, and exact recovery | recovery requires replay, hence a standby |
| A standby that applies the same inputs | changeover in milliseconds | a second machine doing the same work |
| Strict determinism | replay, audit and exact reproduction of defects | no clocks, no randomness, and great care with every change |

## The simulation

<div class="simulation">

**Simulation in the repository.** The program [`code/matchsim`](https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/distributed-systems-from-the-ground-up/code/matchsim/src/main.rs) simulates this design. To run it, clone the repository and type `cargo run --release -p matchsim` in the `code` directory.

</div>

## Terms introduced in this chapter

| Term | Meaning |
|---|---|
| Order | a statement of willingness to buy or sell a quantity at a price |
| Limit order | an order with a price beyond which it will not trade |
| Market order | an order that trades at once at the best price available |
| Order book | the waiting orders for 1 share, on the buy side and the sell side |
| Best bid, best ask | the highest price offered by a buyer, and the lowest asked by a seller |
| Spread | the difference between the best ask and the best bid |
| Price-time priority | ranking orders by price, and by time of arrival at the same price |
| Matching engine | the program that matches incoming orders against the book |
| Trade | an exchange agreed between a buy order and a sell order |
| Sequencer | the component that gives every input its place in a single sequence |
| Journal | the durable record of every input, in sequence |
| Deterministic | producing the same output whenever it is given the same input |
| Replay | recomputing state by applying the journal again |
| Market data | the published stream of trades and best prices |
| Clearing, settlement | working out what is owed after trades, and the actual exchange of shares and money |

<div class="summary">

## Summary

- An order book ranks waiting orders by price and, at the same price, by time of arrival, and an incoming order trades with the best of them at their prices.
- Which order was first cannot be decided by clocks, and is decided by a sequencer that numbers every input.
- Matching is sequential by nature, and a single thread with the book in memory is both the fastest and the only repeatable way of doing it.
- Capacity is added by giving different shares to different engines, and never by dividing 1 book.
- The engine is deterministic, so its state can be recomputed from a journal of its inputs, which is what is made durable.
- A standby applies the same inputs and holds the same book, and takes over within milliseconds.
- Checks are made at the gateway before sequencing, and prices are published to all participants at once.
- After the trade, clearing and settlement proceed on ordinary strongly consistent databases, without delaying the engine.

</div>
