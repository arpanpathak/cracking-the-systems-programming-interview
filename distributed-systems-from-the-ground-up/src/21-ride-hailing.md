<img class="plate" src="art/ch21.svg?v=9982c8ba" alt="A hare stands beside a sign that shows a grid of 9 squares with the middle one marked.">

# Ride Hailing: System Design

A ride hailing service brings together 2 people who are moving about a city: a rider
who wants to travel from 1 place to another, and a driver who is somewhere nearby and
free to take them. The rider opens an application, states a destination, and within a
few seconds is told that a particular car will arrive in 4 minutes. Behind that brief
exchange the service has had to determine which of the tens of thousands of drivers at
present on the road are close to this rider.

The question is unusual because it is about position, and position does not submit to
the methods on which the rest of this book has relied. A key-value store finds a
record by its exact key, and an ordered index finds the records whose keys lie in a
range. Neither is of any direct use for finding the points that lie near a given
point, since nearness involves 2 coordinates at once and no ordering of points along a
single line keeps neighbours together. The data, moreover, will not keep still. Every
driver's position changes continually and is reported every few seconds, so that the
service receives far more writes than reads, and each of those writes makes its
predecessor worthless. This chapter develops an index for moving points, and then
turns to the second problem that a ride presents, which is to give each ride to
exactly 1 driver.

<div class="covers">

This chapter covers

- why finding nearby points is unlike any lookup met so far
- dividing a map into squares, and searching a square together with its neighbours
- choosing the size of the squares, and what goes wrong at either extreme
- squares within squares, for cities whose density varies
- storing positions that are replaced every few seconds
- drivers who disappear without saying so
- offering a ride to drivers in turn, and assigning it to exactly 1
- the states of a ride, and where strong consistency is needed
- estimating a time of arrival, and dividing the world among servers

</div>

## Why nearness is hard

Suppose the service keeps the latitude and longitude of 20000 drivers and wishes to
find the 3 nearest to a rider. The plain method is to compute the distance from the
rider to each of the 20000 and to choose the 3 smallest. This is correct, and it costs
20000 calculations for a single request, a cost that grows in proportion to the
number of drivers and has to be paid again for every rider who opens the application.
At 1000 requests per second it amounts to 20 million distance calculations a second,
nearly all of them for drivers who are on the other side of the city and could have
been excluded at a glance.

The ordinary remedy for a slow search is an index, and it is instructive to see why
the ordinary index fails. An index on latitude can find, very quickly, all the drivers
within a narrow band of latitude around the rider. That band, however, extends right
round the world, and within a city it runs the full width of the city from east to
west and contains thousands of drivers, nearly all of them distant. An index on
longitude has the same defect in the other direction. A database can use the 2
together only by retrieving both bands and intersecting them, which examines far more
entries than it finally keeps. The root of the difficulty is that an index orders its
entries along 1 dimension, whereas nearness on a map is a property of 2.

What is required is some means of naming regions of the map, such that points which
are near each other usually bear the same name or closely related ones. A lookup by
name, which every store performs well, would then serve as a search by position.

## Dividing the map into squares

The simplest such scheme lays a grid of equal squares over the map. Every position
falls in exactly 1 square, and the square can be computed from the coordinates by a
division: if squares are 1 km on a side, a point 42.5 km east and 17.5 km north of the
map's origin lies in the square numbered 42 in 1 direction and 17 in the other. The
service keeps, for each square, the list of drivers currently within it, in an
ordinary table keyed by the square's number.

To find drivers near a rider, the service computes the rider's square and retrieves
the drivers listed there. Only these few need have their distances measured. The
remainder of the city is never examined.

This is very nearly sufficient, and it has 1 flaw that must be corrected.

<figure>
<img src="figures/nearby-edge.svg?v=b9a929b0" alt="2 copies of a map of 4 squares with a rider near the corner of 1 square and the nearest driver just across the border in the next square. On the left only the rider&#x27;s square is searched, and the nearest driver is missed. On the right the neighbouring squares are searched as well, and the driver is found.">
<figcaption><b>Figure 21.1</b> A driver just across the border of the rider's square is missed unless the neighbouring squares are searched as well.</figcaption>
</figure>

A rider who stands close to the edge of a square may have a driver a few metres away
on the other side of the edge, in the adjoining square, and a search confined to the
rider's own square would overlook that driver and return another who is a kilometre
off. The search must accordingly include the 8 squares that surround the rider's, 9
squares in all. Any driver within the length of 1 side of the rider is then certain to
be among those examined, wherever in the square the rider happens to be.

<figure>
<img src="figures/nearby-grid.svg?v=98bca965" alt="A square map divided into 36 squares, with 60 drivers scattered over it and a rider. The square that contains the rider and the 8 squares around it are shaded. Only the drivers in those 9 squares are considered.">
<figcaption><b>Figure 21.2</b> The rider's square and its 8 neighbours contain the only drivers whose distances are measured.</figcaption>
</figure>

The simulation for this chapter places 20000 drivers at random on a map of 100 by 100
units, with squares of 1 unit, and looks for the 3 nearest to a rider by both methods.
Measuring every driver takes 20000 distance calculations. The grid takes 15, that
being the number of drivers in the rider's 9 squares, and both methods return the same
3 drivers, at distances of 0.19, 0.84 and 0.85 units. The work has been reduced by a
factor of more than 1000, and it no longer depends on the total number of drivers,
only on how many are in the vicinity.

## Choosing the size of the squares

The size of the squares is the 1 parameter of this index, and the index performs
badly when it is wrong in either direction.

If the squares are too large, each holds many drivers, and the 9 squares of a search
return hundreds or thousands of candidates whose distances must all be computed. The
index has excluded little, and in the limit of 1 square covering the whole city it
excludes nothing.

If the squares are too small, most are empty. A search of 9 tiny squares commonly
finds no driver, and the service must widen it to the next ring of 16 squares and then
to the ring beyond, issuing many lookups to collect a handful of drivers.

The suitable size is of the order of the distance over which a match is useful. If a
driver more than 2 km away is too far to be worth offering, squares of about 1 km give
a search area of 3 km by 3 km, which covers the range of interest with a single round
of lookups.

No single size, however, suits a whole city. In the centre at midday a square of 1 km
may contain 300 drivers, while on the outskirts at night an area of 25 square
kilometres may contain 2. A grid fine enough for the centre is nearly empty at the
edge, and a grid coarse enough for the edge is crowded in the centre.

## Squares within squares

The difficulty of uneven density is met by making the grid hierarchical. The whole map
is taken as 1 square and divided into 4. Each of these is divided into 4 again, and
the division is repeated to whatever depth is required, so that every square of 1
level contains exactly 4 squares of the next level down, each with half its side.

The squares of such a hierarchy can be given names with a most convenient property.
The 4 quarters of the map are named 0, 1, 2 and 3. The quarters of square 2 are named
20, 21, 22 and 23, and so on, each level adding 1 digit. The name of a square then
begins with the name of every larger square that contains it. A position can be
described by a single name of, say, 15 digits, denoting a very small square, and its
first 10 digits name the larger square containing it, and its first 6 a larger one
still.

Several consequences follow. Drivers are stored under their full, fine names in a
store that keeps its keys in order, such as the key-value store of chapter 1 with its
sorted index. All the drivers within any larger square then have names beginning with
that square's name, and since names with a common beginning are adjacent in sorted
order, they can be retrieved by a single scan of a range of keys. A search for nearby
points has thus been converted into a search by prefix, which is precisely the
operation an ordered index is built for.

The level at which to search can be chosen at the moment of searching. In a dense
district the service searches small squares, and in a sparse one it searches the
larger squares that contain them, by using a shorter prefix, with no change to
the stored data. A search may begin fine and move to a coarser level until it has
found enough candidates.

One caution applies to every scheme of this family. 2 points whose names share a
long prefix are certainly close together, and the converse does not hold. 2 points
that are very close may lie on either side of a boundary between 2 large squares and
have names that differ from the first digit. The neighbouring squares must therefore
still be searched, exactly as with the plain grid, and the neighbours of a square are
computed by arithmetic on its position and never by supposing that their names
resemble its own.

The squares of such schemes are in practice not always square. Some systems divide the
globe into cells bounded by lines of latitude and longitude, which are simple to
compute and become narrower towards the poles. Others cover the globe with hexagons,
which have the merit that all 6 neighbours of a cell are at the same distance from its
centre, whereas a square has 4 near neighbours and 4 that are further off at the
corners. The principle is the same in each case: to name regions so that position
becomes a key.

## Positions that are replaced every few seconds

Each driver's application reports its position every 4 seconds or so. With 500000
drivers on the road, that is 125000 updates per second, considerably more than the
rate of requests from riders, and each update supersedes the last. This pattern of
load is very different from that of the stores in earlier chapters, and it justifies a
different treatment of durability.

In chapter 2 every write was forced to disk before it was acknowledged, since an
acknowledged write that was subsequently lost would have been a broken promise. A
driver's position carries no such obligation. It will be replaced by a fresh report
within 4 seconds, and nobody will ever wish to know where a driver was 10 seconds ago
for the purpose of matching. Were the entire index of positions to be lost, it would
rebuild itself in 4 seconds as the drivers reported again. The index is therefore kept
in memory only, without any log on disk and without waiting for copies to be
confirmed, and this is what allows it to absorb 125000 writes a second on modest
hardware. To have given it the durability of chapter 2 would have multiplied its cost
many times and purchased nothing.

An update consists of 2 small steps. The driver's new position is recorded, and if the
driver has crossed into a different square, the driver is removed from the list of the
old square and added to that of the new. Most updates find the driver in the same
square as before and alter only the stored coordinates.

Positions that must be kept are a separate matter and take a separate path. The route
actually driven during a ride is needed in order to calculate the fare and to settle
any later dispute, and it is appended to a durable log, through the message queue of
chapter 11, apart from the live index.

### Drivers who disappear

A driver may cease to be available without informing the service. The phone's battery
is exhausted, the car enters a tunnel, the application is closed. If nothing were
done, the driver's last known position would remain in the index indefinitely, and
the service would go on offering rides to a car that is no longer there.

The remedy is the lease, which has now appeared in nearly every chapter. Each
position is stored with a time limit of some 15 seconds, several times the interval
between reports. Every report renews it, and a driver who stops reporting vanishes
from the index when the limit expires. Nothing has to detect the departure, since an
entry that is not renewed lapses of its own accord.

## Giving a ride to exactly 1 driver

To find nearby drivers is half of the task. The other half is to assign the ride to 1
of them, and here the considerations are of a different kind, since an error is no
longer a slightly worse match and becomes 2 cars arriving for 1 rider, or a rider left
waiting for a car that is not coming.

The nearest driver in a straight line is not necessarily the best choice. A driver 300
metres away on the far side of a river, or heading in the opposite direction along a
road with a central barrier, may need 10 minutes to arrive, while another 800 metres
off reaches the rider in 3. Having obtained a short list of candidates from the index,
the matching service therefore ranks them by estimated time of arrival along the road
network, a calculation discussed further on.

The ride is then offered to the drivers in turn.

<figure class="steps" data-prefix="figures/steps-nearby-match" data-count="6" data-version="656e8bbd">
<img src="figures/steps-nearby-match-01.svg?v=656e8bbd" alt="A ride offered to drivers in turn, step 1 of 6. A rider requests a ride. The matching service finds the nearest free drivers from the grid and ranks them by distance.">
<figcaption><b>Figure 21.3</b> A ride is offered to the nearest driver, who does not answer, and then to the next, who accepts, after which the first driver's late acceptance is refused. Use Next and Back to move through the 6 steps.</figcaption>
</figure>

2 decisions embodied in these steps merit comment.

The ride is offered to 1 driver and, only if that driver declines or fails to answer
in time, to the next. The alternative, to offer it to several at once and take the
first acceptance, would assign rides sooner and would leave every driver but 1 having
responded to an offer that was then withdrawn, which drivers reasonably resent. An
offer has a time limit and is in effect a lease on the ride, so that a driver who does
not respond cannot hold it up for more than a few seconds.

The assignment itself is a conditional write to a strongly consistent store, of the
form "set the driver of this ride to 7056, provided that it has no driver". This is
the operation that guarantees a ride at most 1 driver. In the last step, a late
acceptance from the first driver arrives after the second has been assigned, and the
identical conditional write, finding the ride already assigned, is refused. The same
operation marks the driver as busy, so that a driver cannot be assigned to 2 rides.
It will be recognised as the conditional write that sold a seat to 1 buyer in chapter
20 and gave a job to 1 worker in chapter 12.

In a busy area, to match each ride at the instant it is requested does not give the
best result overall. If 2 riders make requests within a second of each other and 2
drivers are nearby, giving the first rider the nearest driver may leave the second
rider with a long wait, where the other pairing would have served both tolerably.
Services therefore sometimes collect the requests of a small area for a second or 2
and assign the whole batch together, so as to minimise the total waiting time of all
the riders concerned.

## The states of a ride

A ride, like the payment of chapter 19 and the job of chapter 12, is an object that
passes through a series of states: requested, offered, accepted, driver arriving, in
progress, completed, and paid, with cancellation possible from several of them. Each
transition is caused by an event from the rider's application, the driver's
application, or the service itself, and each is recorded durably.

This record requires the strong consistency that the index of positions was able to
do without. Money depends on it, since the fare is calculated from the recorded
beginning and end of the ride, and both parties must be shown the same state, since a
rider who is shown "driver arriving" while the driver is shown "cancelled" has been
badly served. The ride store is accordingly a replicated database of the kind
described in chapters 3 and 4, in which each transition is a conditional write that
verifies the current state before altering it, so that a ride cannot, for example, be
both cancelled and started.

The design thus contains 2 stores at opposite ends of the range of consistency, each
suited to what it holds.

| | Index of positions | Ride store |
|---|---|---|
| Contents | where each driver is at present | the state and history of every ride |
| Writes | 125000 per second, each superseding the last | a few per ride |
| Durability | none: in memory, and rebuilt in 4 seconds | full: stored on a majority |
| Consistency | eventual, and stale by up to 4 seconds | strong |
| If it is lost | matching pauses for a few seconds | not permitted |

Once a ride has been accepted, the rider wishes to watch the car approach on a map.
The driver's position must then be conveyed to 1 particular rider every few seconds,
which is the delivery problem of chapter 18. The rider's application holds a
connection open, and the service forwards on it the positions of the assigned driver.

## Estimating the time of arrival

The figure that riders care most about is the number of minutes until the car
arrives, and the distance in a straight line is a poor guide to it. The estimate
requires a model of the road network, represented as a graph in which the junctions
are nodes and the stretches of road between them are edges, each edge carrying the
time presently needed to drive along it. The estimated time of arrival is the length
of the shortest path through this graph from the driver to the rider.

To compute shortest paths on the road graph of an entire country for every candidate
driver of every request would be far too slow by the textbook method, which examines a
large part of the graph for each query. Practical systems carry out a great deal of
the work beforehand. They identify in advance the major roads that long journeys
almost always use and compute the times between the points where such roads meet, so
that a query has only to find its way from each end to the nearest major road and
then consult a table. The travel times on the edges are revised continually from the
movements of the very drivers that the service is tracking, which makes the stream of
position reports serve a second purpose as a measurement of traffic.

## Dividing the world

Rides are local. A rider in 1 city is never matched with a driver in another, and
this affords a natural way of dividing the system among machines, by geography. The
map is partitioned into regions, each consisting of a set of the squares described
earlier, and each region's index of positions and matching are served by their own
group of servers.

Partitioning by position has the same hazard as partitioning by any other key, namely
that the load is unevenly distributed. The centre of a great city on a Friday evening
has many times the activity of a rural region, so that regions are made small where
the density is high and large where it is low, which the hierarchical naming of
squares makes straightforward. Riders and drivers close to the boundary between 2
regions need the search to extend across it, which is once again the matter of
neighbouring squares, between servers this time.

Demand also moves in ways that can to some degree be foreseen. When a concert ends or
rain begins, requests in a district may increase fivefold within minutes, more
quickly than drivers are able to get there. The service has accordingly to guard its
own components against such surges, using the rate limiting of chapter 7, and many
services raise the price in the affected district for the time being, so as to attract
drivers to it and to moderate the demand.

## Use cases

A rider requests a ride and watches the car approach. A driver reports a position
every few seconds and accepts rides.

<figure>
<img src="figures/nearby-use-cases.svg?v=3f254e0c" alt="A use case diagram of the ride service. Rider: request a ride (POST /v1/rides), watch the driver approach (GET /v1/rides/{id}). Driver: report a position (POST /v1/drivers/{id}/positions), accept a ride (PUT /v1/rides/{id}/assignments/{driver}).">
<figcaption><b>Figure 21.4</b> The actors and what each of them does.</figcaption>
</figure>

## Functional requirements

| No. | Functional requirement |
|---|---|
| 0 | A driver's application reports the driver's position every 4 seconds. |
| 1 | A rider can request a ride from a position to a destination. |
| 2 | The service finds free drivers near the rider and offers the ride to them in turn. |
| 3 | A ride is assigned to at most 1 driver, and a driver to at most 1 ride. |
| 4 | The rider can follow the position of the assigned driver. |
| 5 | Every change in the state of a ride is recorded. |

## Non-functional requirements

| No. | Property | Non-functional requirement |
|---|---|---|
| 0 | Latency | Nearby drivers are found within 100 ms. |
| 1 | Consistency | Strong for rides and their assignment. Eventual for positions, which may be 4 seconds old. |
| 2 | Availability | 99.95% for requesting a ride. |
| 3 | Durability | The record of a ride is not lost. A driver's current position need not survive a failure. |
| 4 | Scale | 500000 drivers on the road, 125000 position reports per second, and 1000 ride requests per second. |

Non-functional requirements 1 and 3 state the division that runs through this whole
design. To hold positions to the standard appropriate to rides would make the index
many times more expensive and no more useful, and to hold rides to the standard
appropriate to positions would lose customers' money. The skill lies in recognising
which of the system's data is of which kind.

## Core entities

<figure>
<img src="figures/nearby-entities.svg?v=1327cb82" alt="The core entities. Driver has the fields id string, position x, y, square column, row, state free|busy. Ride has the fields id u64, rider string, driver string, state requested|.... A driver&#x27;s square is computed from the position. The service keeps, for every square, the list of drivers inside it.">
<figcaption><b>Figure 21.5</b> The core entities and their fields.</figcaption>
</figure>

## Capacity estimate

<div class="estimate">

<img class="builder" src="art/crab-builder.svg" alt="A crab in a hard hat, in tears.">

**Arithmetic ahead.** The positions of 500000 drivers occupy about 50 MB of memory. The quantity that matters is the rate of updates, 125000 per second.

<a class="skip" href="#high-level-design">Skip to the high-level design</a>

<details>
<summary>Show the calculation</summary>

| Quantity | Calculation | Result |
|---|---|---|
| Position reports | 500000 drivers ÷ 4 seconds | 125000 per second |
| Memory per driver | id, position, square, state, expiry | about 100 bytes |
| Memory for all drivers | 500000 × 100 bytes | 50 MB |
| Drivers in a search | 9 squares × about 20 drivers | about 180 |
| Rides per day | 1000 per second at the peak, a third of that on average | about 30 million |

</details>

</div>

## The API

Every report of a position creates a new position in the collection of that driver's
positions, with `POST`. A ride is created with `POST` as well. A driver accepts by
writing the assignment of that driver to the ride, with `PUT`, so that repeating the
request has no further effect.

**A driver reports a position**

```http
POST /v1/drivers/7056/positions HTTP/1.1
Host: rides.example
Content-Type: application/json

{ "latitude": 38.7223, "longitude": -9.1393, "heading": 270 }
```

```http
HTTP/1.1 201 Created
```

Reports are sent so frequently that many services convey them over an open connection
in a compact binary form, without a separate HTTP request for each. The meaning is unchanged.

**A rider requests a ride**

```http
POST /v1/rides HTTP/1.1
Host: rides.example
Idempotency-Key: 3f7a-ride-1
Content-Type: application/json

{
  "from": { "latitude": 38.7169, "longitude": -9.1399 },
  "to": { "latitude": 38.7742, "longitude": -9.1342 }
}
```

```http
HTTP/1.1 201 Created
Location: /v1/rides/501
Content-Type: application/json

{ "id": 501, "state": "requested" }
```

The key ensures that a rider whose application retries after a lost reply does not
summon 2 cars.

**A driver accepts**

```http
PUT /v1/rides/501/assignments/7056 HTTP/1.1
Host: rides.example
```

```http
HTTP/1.1 200 OK
Content-Type: application/json

{ "id": 501, "state": "accepted", "driver": 7056 }
```

A driver whose offer has ended, or who accepts after another driver has been assigned,
receives `409 Conflict`.

## High-level design

<figure class="wide">
<img src="figures/nearby-design.svg?v=94deaf32" alt="Finding a driver for a rider. The components are Drivers, Location service, Grid index, Rider, Matching service, Ride store. Step 1: Every driver reports its position. Step 2: The location service files it under a grid square. Step 3: A rider requests a ride from a position. Step 4: The matcher reads 9 squares and records the ride.">
<figcaption><b>Figure 21.6</b> The components and the path of a request. The steps are numbered.</figcaption>
</figure>

| Component | Role | State it holds | When 1 instance fails |
|---|---|---|---|
| Location service | receives position reports and files each driver under a square | none | another instance receives the reports |
| Grid index | holds the drivers of each square | positions, in memory, with a lease | it is rebuilt from reports within 4 seconds |
| Matching service | finds candidates, ranks them, and offers the ride in turn | none | another instance continues from the ride's recorded state |
| Ride store | holds every ride and its state | rides, replicated | a follower is elected, as in chapter 4 |

### One request, step by step

The steps follow the arrows of figure 21.6.

1. Every driver's application reports its position every 4 seconds.
2. The location service computes the square of the position and updates the grid index, moving the driver from 1 square's list to another's when a border has been crossed and renewing the driver's lease.
3. A rider requests a ride. The matching service computes the rider's square, reads the drivers of that square and its 8 neighbours from the grid index, and ranks the free ones by estimated time of arrival.
4. The matching service offers the ride to the first of them. When a driver accepts, it writes the assignment to the ride store as a conditional write, which succeeds for 1 driver only.

## The design, deployed

<figure class="wide">
<img src="figures/nearby-deploy.svg?v=4c9cf5e5" alt="The ride service, deployed. Phones: Drivers (500000), report every 4 s, Riders (1000 req/s), request rides. Edge, in each region: Load balancers (x 8), by connection, Gateways (x 40), open connections, Location service (x 20), position to square. Matching, in each region: Grid index (x 30), in memory, by region, Matching service (x 20), rank and offer. Durable state: Ride store (x 9), shards x 3 replicas, Position log (x 6), routes, for fares.">
<figcaption><b>Figure 21.7</b> The ride service as it is deployed, with the grid index in memory and the ride store replicated.</figcaption>
</figure>

The system is deployed separately in each region of the world, since no ride crosses
between them, and the figure shows 1 region. Drivers and riders hold connections to
gateways, as the phones of chapter 18 do. The location service is stateless and
turns each of the 125000 reports per second into an update of the grid index, which
is divided among 30 machines by area and kept in memory only. The matching service
reads the index and writes assignments to the ride store, which is the 1 component
here with replicas in 3 zones and durable storage. The picture makes visible the
division that the chapter insisted upon, between data that is rebuilt in seconds and
data that must not be lost.

## How real systems do it

The grid of this chapter corresponds to 3 schemes that are in wide use, and they
differ in the shape of the cell and in how the cells are named.

The *geohash* divides the world by latitude and longitude, halving alternately in
each direction, and writes the result as a short string in which every further
character selects a smaller cell within the last. It is the hierarchy of names with
shared prefixes described above, and several in-memory stores offer queries by
radius that are built on it. Its cells are rectangles whose width varies with
latitude.

Google's S2 library projects the sphere onto the faces of a cube and numbers the
cells along a space-filling curve, so that a cell is a 64-bit integer and cells that
are close on the curve are close on the ground. A region is covered by a small set
of cells of mixed sizes, and a search becomes a few scans of ranges of integers.

Uber developed H3, which it published in 2018, and which uses hexagons. The stated
reason is the one given above: the centres of all 6 neighbours of a hexagon are at
the same distance, which makes it natural to reason about rings of cells around a
point and about movement between adjacent cells, where a square has neighbours at 2
different distances. H3 has 16 levels of resolution, each cell containing 7 of the
next, and since hexagons do not divide exactly into smaller hexagons, a child cell
is only approximately contained in its parent. The surface of a sphere cannot be
covered by hexagons alone, and every level contains exactly 12 pentagons, placed
where they are least likely to matter.

For the estimate of arrival time, the technique of computing in advance along the
important roads is known as contraction hierarchies, and it answers a query on the
road network of a continent in about a millisecond. And Uber has described assigning
the work for each area to particular servers with a ring of consistent hashing whose
membership spreads by gossip, which is the alternative to a coordinator that chapter
1 described.

## Mistakes to avoid

| Mistake | What goes wrong | What to do |
|---|---|---|
| Measuring the distance to every driver | The cost of each request grows with the size of the whole fleet. | Index drivers by the square they are in. |
| Searching only the rider's square | A driver just across the border is missed. | Search the 8 neighbouring squares as well. |
| A single size of square for everything | The centre is crowded, and the outskirts are empty. | Use a hierarchy of squares, and choose the level when searching. |
| Supposing that neighbouring squares have similar names | 2 nearby points on either side of a major boundary are treated as distant. | Compute the neighbours of a square, and search them. |
| Storing live positions durably | Every 1 of 125000 writes a second waits for a disk, to no purpose. | Keep positions in memory, where they rebuild themselves. |
| Positions without a time limit | Drivers who have gone offline are still offered rides. | Store each position with a lease that its reports renew. |
| Ranking by distance in a straight line | The nearest driver is across a river and 10 minutes away. | Rank by estimated time along the roads. |
| Offering a ride to many drivers at once | All but 1 respond to an offer that is then withdrawn. | Offer to 1 driver, and move to the next after a time limit. |
| Assigning a ride by reading and then writing | 2 drivers are assigned to 1 ride. | Assign with a conditional write that requires the ride to have no driver. |
| Keeping rides in the store used for positions | The record of a ride is lost in a restart. | Keep rides in a durable, strongly consistent store. |
| Requesting a ride without an idempotency key | A retry summons a second car. | Require a key on the request. |

## Failures

| Failure | What users see | How the system recovers |
|---|---|---|
| A driver's phone loses its connection | that driver receives no offers | the lease on the position runs out, and the driver leaves the index |
| The grid index is lost | matching pauses for a few seconds | drivers' next reports rebuild it |
| A driver does not answer an offer | the rider waits 15 seconds longer | the offer ends, and the next driver is asked |
| 2 drivers accept the same ride | the later driver is told that the ride is taken | the conditional write accepts only the first |
| The reply to a ride request is lost | the rider's application tries again | the key returns the ride already created |
| The ride store's leader fails | requests fail for about 1 second | a follower is elected |
| No driver is nearby | the rider is told so, or the search is widened | the search moves to a coarser level of squares |

## Trade-offs

| Decision | What it gains | What it costs |
|---|---|---|
| Positions in memory only | 125000 updates per second on modest hardware | a failure empties the index for a few seconds |
| A grid in place of exact search | the work depends only on the drivers nearby | borders must be handled by searching neighbours |
| Offers in turn | no driver has an accepted offer withdrawn | assignment is slower when drivers do not answer |
| Strong consistency for rides | a ride has 1 driver and 1 state | a brief pause in new rides when a leader fails |
| Regions by geography | each city is served independently | busy districts need smaller regions |

## The simulation

<div class="simulation">

**Simulation in the repository.** The program [`code/nearbysim`](https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/distributed-systems-from-the-ground-up/code/nearbysim/src/main.rs) simulates this design. To run it, clone the repository and type `cargo run --release -p nearbysim` in the `code` directory.

</div>

## References

- I. Brodsky, "H3: Uber's Hexagonal Hierarchical Spatial Index", Uber engineering blog, 2018.
- Google, S2 Geometry Library documentation, "S2 Cells".
- G. Niemeyer, "geohash.org", 2008.
- R. Geisberger and others, "Contraction Hierarchies: Faster and Simpler Hierarchical Routing in Road Networks", WEA 2008.
- A. Guttman, "R-Trees: A Dynamic Index Structure for Spatial Searching", SIGMOD 1984.
- Uber engineering blog, "How Ringpop from Uber Engineering Helps Distribute Your Application", 2016.

## Terms introduced in this chapter

| Term | Meaning |
|---|---|
| Spatial index | a structure that finds the points near a given point without examining them all |
| Grid | a division of the map into equal squares |
| Square, cell | 1 region of such a division, which serves as a key |
| Neighbouring squares | the 8 squares that touch a given square |
| Hierarchical grid | squares divided into 4 smaller squares, repeatedly |
| Prefix | the first digits of a square's name, which name a larger square that contains it |
| Position report | a message from a driver's application that gives the driver's position |
| Matching | choosing a driver for a ride |
| Offer | a proposal of a ride to 1 driver, valid for a limited time |
| Estimated time of arrival | the predicted time until the driver reaches the rider, along the roads |
| Road graph | the road network as junctions joined by stretches of road, each with a travel time |

<div class="summary">

## Summary

- Finding nearby points is hard for ordinary indexes, which order their entries along 1 dimension.
- A grid names each region of the map, so that a lookup by square replaces a comparison with every driver.
- A search covers the rider's square and its 8 neighbours, since the nearest driver may be just across a border.
- A hierarchy of squares whose names share prefixes allows the size to be chosen for each search and turns nearness into a scan of a range of keys.
- Positions are replaced every few seconds and are kept in memory with a lease, since losing them costs 4 seconds.
- A ride is offered to drivers in turn and assigned by a conditional write, so that it has at most 1 driver.
- Rides are kept in a durable, strongly consistent store, at the opposite extreme from the index of positions.

</div>
