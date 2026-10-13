<img class="plate" src="art/ch14.svg?v=f194620c" alt="Dash, a hare, stands beside a sign that reads: 1000000 becomes 4C92.">

# URL Shortener: System Design

A URL shortener accepts a long web address and returns a short one, such as
`sho.rt/4C92`, which leads to the same place. Anyone who opens the short address is
redirected to the long one. The service does 2 things only, creating a link and
following a link, and its data is a single table with 2 columns. It is nevertheless a
standard exercise in system design, and deservedly so, because within that small
compass it raises several questions that recur in much larger systems: how to generate
identifiers that are short, unique and hard to guess; how to serve a load that
consists almost entirely of reads; how to count events without slowing down the
operation being counted; and how to run a public service that people will certainly
try to misuse.

The quantities involved shape every decision. Links are created at a modest rate and
followed at a far higher one, typically a hundred times higher, and a link once
created is never changed. A system with these characteristics is designed around its
read path, which must be fast and must stay available, while the write path may be
slower and may, if necessary, be briefly unavailable without great harm. A link that
fails to open is a failure visible to everyone who was sent it, and a link that cannot
be created for a minute inconveniences 1 person.

<div class="covers">

This chapter covers

- how long a code has to be
- 3 ways of making a code: from a hash, at random, and from a counter
- writing a number in base 62, step by step
- why codes from a counter can be guessed, and how to prevent it
- the 2 kinds of redirect, and what each means for speed and for counting
- a read path built from a cache and a key-value store
- counting clicks without writing on every redirect
- custom names, expiry, and the same address submitted twice
- the misuse of a public redirect service

</div>

## How long a code must be

The code is the part of the short address that follows the domain, and its length is
the first thing to be settled, since shortness is the product.

A code is a string over some alphabet, and the number of distinct codes of a given
length is the size of the alphabet raised to that length. The customary alphabet
consists of the 10 digits, the 26 capital letters and the 26 small letters, 62
characters in all, each of which may appear in a web address without special
encoding. With 62 characters, codes of length 6 number about 57 billion and codes of
length 7 about 3.5 trillion.

The service of this chapter expects 100 million new links per month, or 6 billion in 5
years. Codes of 6 characters would suffice for that in principle, with about 10 times
as many codes as links. We choose 7, which provides nearly 600 times as many, for 2
reasons. The service should not approach exhaustion within its lifetime, since
lengthening the codes later is disruptive. And, as will appear below, a code space
that is sparsely occupied is considerably harder to explore by guessing.

Some alphabets omit characters that are easily confused in print or over the
telephone, such as the digit 0 and the capital O, or the digit 1 and the small l. This
reduces the alphabet to 58 or fewer characters and the number of codes accordingly. It
is worth doing where links are likely to be read aloud or copied by hand.

## Making a code

A code must be unique, because a code that referred to 2 addresses would send some
visitors to the wrong one. There are 3 established ways of producing codes, and they
differ in how uniqueness is obtained and in what the codes reveal.

### From a hash of the address

The first idea is to compute a hash of the long address and take its first 7
characters. The method has the attraction of needing no state at all: the code is a
function of the address, and any server can compute it.

Its defect is that 2 different addresses can produce the same 7 characters. This is
the collision that chapter 8 calculated for random identifiers, and the same
arithmetic applies: among n codes drawn from N possibilities, the expected number of
colliding pairs is about n squared divided by twice N. The simulation for this chapter
shortened 2 million addresses to 6 characters of a hash, a form that allows about 20
billion different codes, and 97 of the addresses received a code that another address
already had.

<figure>
<img src="figures/short-collide.svg?v=8bce771b" alt="2 million addresses are each given a code. With codes from a counter, no 2 addresses share a code. With codes made of 6 characters of a hash, 97 addresses share a code with another address.">
<figcaption><b>Figure 14.1</b> Codes from a counter never coincide, while codes cut from a hash coincide once there are enough of them.</figcaption>
</figure>

A collision rate of 97 in 2 million sounds small, and a service cannot send even 1
visitor in 20000 to the wrong destination. Every newly computed code must therefore be
checked against the store, and when it is found to be taken by a different address,
the service must derive another, for instance by appending a counter to the address
and hashing again. The method thus requires a read before every write and a loop for
retries, and the collisions become more frequent as the store fills.

Deriving the code from the address has a further consequence that is sometimes wanted
and sometimes not. The same address always yields the same code, so that 2 people who
shorten the same address receive the same link, and neither can have statistics or an
expiry date of their own.

### At random

The second method draws 7 characters at random and checks whether the resulting code
is already in use, drawing again if it is. As with the hash, a check before each write
is unavoidable. With 6 billion links among 3.5 trillion codes, about 1 draw in 600
finds its code taken, so the retries are rare and remain rare for the life of the
service.

Random codes have an important virtue, which is that they disclose nothing. A code
says nothing about when its link was created or how many others exist, and knowing 1
valid code is of no help in finding another. The cost is the check, which on a
replicated store must be an atomic "create if absent" of the kind described in
chapter 10, since 2 servers might otherwise draw the same code at the same moment and
both find it free.

### From a counter

The third method abandons chance. Each new link is assigned the next number from a
counter, and the code is that number written in a compact notation. Since no 2 links
are given the same number, no 2 receive the same code, and uniqueness requires no
check and no retry.

The compact notation is base 62, which uses the 62 characters of the alphabet as
digits in the way that decimal notation uses 10.

<figure class="steps" data-prefix="figures/steps-short-encode" data-count="6" data-version="d0e5eca4">
<img src="figures/steps-short-encode-01.svg?v=d0e5eca4" alt="Writing a number in base 62, step 1 of 6. The link is number 1000000 from the counter. To write it as a code, we divide by 62 again and again. Each remainder is 1 digit of the code, starting from the right.">
<figcaption><b>Figure 14.2</b> The number 1000000 is written in base 62 by repeated division. Use Next and Back to move through the 6 steps.</figcaption>
</figure>

The simulation confirms the round trip for a selection of numbers: 0 is written as
`0`, 61 as `z`, 62 as `10`, a million as `4C92`, and the largest number that fits in 7
characters, 3521614606207, as `zzzzzzz`, and each code reads back as the number from
which it came. It also shortens 2 million addresses by counter and finds no collision
among them, as must be the case.

The counter itself must be shared by all the servers that create links, and chapter 8
was devoted to that problem. The method of blocks suits this service well. Each web
server obtains a block of, say, 1000 consecutive numbers from the counter and assigns
them from memory, returning for another block when the first is used up. The counter
is consulted once per 1000 links, and the numbers lost when a server restarts in the
middle of a block are of no consequence when 3.5 trillion are available.

### What a counter gives away

Codes that are consecutive numbers have a property that is unacceptable in a public
service. They can be guessed.

<figure>
<img src="figures/short-guess.svg?v=d7f03fb4" alt="4 steps. An author creates a link and receives the code 4C92, which leads to a private document. A stranger tries the neighbouring codes 4C91, 4C93 and 4C94. Each neighbour is somebody&#x27;s link, because codes come from a counter. The stranger reads documents meant for others. The cure is to scramble the number before writing it in base 62.">
<figcaption><b>Figure 14.3</b> The codes next to a known code are valid links belonging to other people.</figcaption>
</figure>

Anyone who holds 1 link can obtain others by adding or subtracting 1, and can walk
through the entire collection in order. Short links are routinely created for
addresses that carry a secret within them, such as a shared document that anyone with
the link may read or a page for resetting a password, on the assumption that the
address cannot be found by a stranger. Sequential codes destroy that assumption. They
also reveal the volume of the business, since the difference between a code created
today and one created a week ago is the number of links made in the week.

The remedy keeps the counter and conceals its order. Before the number is written in
base 62, it is passed through a fixed scrambling function that maps each number below
62 to the power 7 to a different number in the same range. Because the mapping sends
distinct inputs to distinct outputs, the codes remain unique without any check, and
because it is designed so that neighbouring inputs give unrelated outputs, consecutive
links receive codes with no visible relation to one another. Such a function is in
effect a small cipher with a secret key, and anyone without the key cannot recover the
sequence.

Even with scrambled or random codes, a stranger can still try codes blindly, and the
fraction of attempts that succeed equals the fraction of the code space in use. This
is the second reason for preferring 7 characters to 6. With 6 billion links in 57
billion codes, 1 guess in 10 would find a link. With 3.5 trillion codes, 1 guess in
600 does, and a rate limit on requests for codes that do not exist, of the kind
described in chapter 7, makes systematic exploration impractical.

| | From a hash | At random | From a counter, scrambled |
|---|---|---|---|
| Uniqueness | by check and retry | by check and retry | by construction |
| A read before each write | yes | yes | no |
| Shared state | none | none | a counter, consulted once per block |
| The same address twice | the same code | different codes | different codes |
| Can codes be guessed | no | no | no, while the key is secret |

The design of this chapter uses a counter with blocks and a scrambling step. It avoids
the read before each write, and it never has to retry.

## Following a link

When a visitor's browser requests `sho.rt/4C92`, the service looks up the code and
replies with a *redirect*, a response that carries no page and names another
address to which the browser should go. HTTP provides 2 principal kinds, and the
choice between them is a real design decision with consequences for load and for
measurement.

A reply with status `301 Moved Permanently` tells the browser that the short address
has been replaced by the long one for good. Browsers are entitled to remember this,
and they do: the next time the same person opens the same short link, the browser goes
directly to the long address without contacting the shortener at all. A reply with
status `302 Found` states that the redirect is temporary, and the browser asks the
shortener again on each occasion.

| | `301 Moved Permanently` | `302 Found` |
|---|---|---|
| Repeat visits by the same browser | go straight to the destination | return to the shortener each time |
| Load on the shortener | lower | higher |
| Click counts | count each browser once | count every visit |
| Changing or disabling the link later | does not reach browsers that remembered it | takes effect immediately |

The last row is the one most often overlooked. A link that has been served with `301`
cannot reliably be withdrawn, because browsers that have stored the redirect will
continue to follow it. A service that must be able to disable links, which, as the
section on misuse explains, every public shortener must, should prefer `302`, or
should send `301` with a short limit on how long it may be remembered. Our design
sends `301` together with a header that limits the browser's memory of it to a day,
which removes most repeat requests while ensuring that a disabled link stops working
within 24 hours.

## The read path

Redirects outnumber creations by a hundred to 1 and must be answered in a few
milliseconds, so the read path is built for speed in layers.

The mapping from code to address is a pure lookup by key, with no queries by any
other attribute, and it is therefore kept in a key-value store of the kind built in
chapters 1 to 6, divided among shards by a hash of the code. At 6 billion links of
about 500 bytes each, the data amounts to 3 TB, which is too much for 1 machine and
entirely ordinary for a sharded store.

In front of the store stands a cache, as described in chapter 9. Traffic to short
links is extremely uneven: a link shared by a popular account may be opened a million
times in an hour, while most links are opened a few times in their whole existence. A
cache holding a small fraction of the links therefore answers the great majority of
requests. Links are also the ideal content for a cache, because a link is never
modified after creation, so that the problem of stale entries, which occupied much of
chapter 9, scarcely arises. The 1 change that can occur is the disabling of a link,
and it is handled by deleting the cache entry at that moment.

Requests for codes that do not exist deserve attention, since they are what an
exploring stranger or a mistyped address produces. As chapter 9 explained under the
name of cache penetration, such requests pass straight through an ordinary cache to
the store. The service therefore caches the fact that a code is absent, for a short
time, and limits the rate at which any 1 client may request absent codes.

The web servers themselves hold no data. Each request can be served by any of them,
and the load balancer in front distributes requests without regard to who is asking.
Servers can accordingly be added and removed freely, and the failure of 1 is of no
consequence to visitors.

## Counting clicks

Authors wish to know how often their links are followed. The obvious implementation,
incrementing a counter in the database on every redirect, would convert the read path
into a write path. Every redirect would cost a durable write, a hundred times more
writes than link creation produces, all contending on the rows of the popular links.

The redirect and the count are therefore separated. On each redirect the web server
appends a small record, consisting of the code and the time, to a message queue of the
kind described in chapter 11, and replies to the visitor without waiting for anything
further. A separate consumer reads these records and maintains the counts, typically
adding up the clicks for each link over a minute and applying the sum in a single
write. The visitor's redirect is delayed by nothing, the store receives 1 write per
link per minute in place of 1 per click, and if the counting consumer fails, redirects
continue undisturbed and the counts are brought up to date when it returns.

The price is that the counts are eventually consistent. They lag behind reality by up
to a minute, and since the queue delivers at least once, a consumer that crashes and
repeats a batch may count some clicks twice unless it records which batches it has
applied. For a statistic shown on a dashboard this is entirely acceptable. It would
not be acceptable if clicks were being billed for, in which case each click record
would need an identifier and the counting would have to be made idempotent in the
manner of chapter 11.

## Further features

Authors sometimes wish to choose the code themselves, as in `sho.rt/spring-sale`. A
*custom name* is stored in the same table as a generated code and must be reserved
with an atomic "create if absent", since 2 authors may ask for the same name at the
same moment. Custom names and generated codes have to be kept from colliding, which is
most arranged by making them differ in form: generated codes are exactly 7
characters, and custom names are required to be longer or to contain a hyphen.

A link may be given an *expiry*, after which it ceases to work. The expiry time is
stored with the link, and the web server compares it with the clock on each redirect,
so that an expired link is refused from the correct moment even though its row has not
yet been removed. A periodic job deletes expired rows later, at leisure. Codes of
expired links should not be given to new links, since old messages and documents
containing the code would then lead to an unrelated destination.

When the same long address is submitted twice, the service may return the existing
link or create a new one. Returning the existing link saves storage and requires an
additional index from addresses to codes, and it means that the 2 submitters share 1
link, with shared statistics. Most services create a new link each time, on the
grounds that links belong to their authors and that storage is the cheaper resource.

## Misuse

A service that will redirect anyone to anywhere is useful to people with bad
intentions, and a design that ignores this will not survive contact with the public.

The principal abuse is concealment. A short link hides its destination, and so it is
used to disguise addresses that the recipient would not knowingly open: pages that
imitate a bank's login form, or downloads of harmful software. Mail filters and
messaging services respond by treating all links of a shortener that carries much of
this as suspect, at which point the legitimate links of the service stop working in
practice. A public shortener therefore checks each submitted address against lists of
known harmful sites when the link is created, checks again periodically, since a
destination may turn harmful after the link was made, and provides a means of
reporting links. A link found to be harmful is disabled, and this is the reason the
service must retain the ability to disable a link promptly, which the earlier
discussion of `301` and `302` turned upon.

Creation must be rate limited, per account and per network address, to prevent a
single party from generating links by the million. And the service must refuse to
shorten its own short links, since chains of redirects are used to defeat the checks
just described and a link that redirects to itself would loop.

## Use cases

Authors create links and read their statistics. Visitors follow links, in far greater
numbers.

<figure>
<img src="figures/shortener-use-cases.svg?v=d0ea3d7d" alt="A use case diagram of the URL shortener. Author: shorten a URL (POST /v1/links), read the click count (GET /v1/links/{code}). Visitor: open a short link (GET /{code}, then 301).">
<figcaption><b>Figure 14.4</b> The actors and what each of them does.</figcaption>
</figure>

## Functional requirements

| No. | Functional requirement |
|---|---|
| 0 | An author can create a short link for a URL and receives a code of 7 characters. |
| 1 | Opening a short link redirects the visitor to the URL. |
| 2 | A code, once given out, always leads to the same URL. |
| 3 | An author can read how often a link was opened. |

## Non-functional requirements

| No. | Property | Non-functional requirement |
|---|---|---|
| 0 | Availability | 99.99% for redirects. A link that does not open is the worst failure. |
| 1 | Latency | A redirect takes under 10 ms. |
| 2 | Consistency | Strong for creating a link: each code belongs to exactly 1 URL. Eventual for click counts. |
| 3 | Scale | 100 million new links per month, and 100 redirects for every new link. |

The mapping from a code to its address must be strongly consistent in 1 specific
respect: once a link has been created and its code returned to the author, every
subsequent lookup must find it, since the author will share the code immediately. The
key-value store provides this by confirming a write only when a majority holds it.
Click counts, by contrast, are eventually consistent by design, as the section on
counting explained.

## Core entities

<figure>
<img src="figures/shortener-entities.svg?v=8a5ba436" alt="The core entities. Link has the fields code 7 characters, url string, owner string, created time. Click has the fields code 7 characters, at time. A Link is written once and read many times. Clicks are counted apart from links, so that reading a link stays cheap.">
<figcaption><b>Figure 14.5</b> The core entities and their fields.</figcaption>
</figure>

## Capacity estimate

<div class="estimate">

<img class="builder" src="art/crab-builder.svg" alt="A crab in a hard hat, in tears.">

**Arithmetic ahead.** 5 years of links are 6 billion codes and 3 TB, and redirects average 3900 per second.

<a class="skip" href="#high-level-design">Skip to the high-level design</a>

<details>
<summary>Show the calculation</summary>

| Quantity | Calculation | Result |
|---|---|---|
| Links in 5 years | 100000000 × 12 × 5 | 6 billion |
| Codes of 7 characters | 62 to the power 7 | 3.5 trillion |
| Storage for links | 6 billion × 500 bytes | 3 TB |
| New links per second | 100000000 ÷ (30 × 86400) | 39 |
| Redirects per second | 39 × 100 | 3900 |

</details>

</div>

## The API

Creating a link is an ordinary `POST` to the collection of links. Following one is a
`GET` on the shortest path the service can offer, the code itself.

**Create a link**

```http
POST /v1/links HTTP/1.1
Host: sho.rt
Content-Type: application/json

{ "url": "https://example.com/a/very/long/address?with=parameters" }
```

```http
HTTP/1.1 201 Created
Location: /v1/links/4C92
Content-Type: application/json

{ "code": "4C92", "short_url": "https://sho.rt/4C92" }
```

Its code is the base 62 form of the link's id.

**Open a link**

```http
GET /4C92 HTTP/1.1
Host: sho.rt
```

```http
HTTP/1.1 301 Moved Permanently
Location: https://example.com/a/very/long/address?with=parameters
Cache-Control: max-age=86400
```

Browsers follow `Location` by themselves.

## High-level design

<figure class="wide">
<img src="figures/shortener-design.svg?v=2c037aed" alt="A URL shortener. The components are Visitors, Load balancer, Web servers, Cache, Key-value store, Id generator. Step 1: A visitor opens a short link. Step 2: The load balancer picks a web server. Step 3: The server looks for the code in the cache. Step 4: On a miss it reads the store and fills the cache. Step 5: For a new link, it takes the next id and encodes it. Step 6: The visitor is redirected with status 301.">
<figcaption><b>Figure 14.6</b> The components and the path of a request. The steps are numbered.</figcaption>
</figure>

| Component | Role | State it holds | When 1 instance fails |
|---|---|---|---|
| Web server | creates links and answers redirects | none | the load balancer uses the others |
| Cache | holds the most opened links | copies, in memory | its links are read from the store once more |
| Key-value store | maps a code to its URL | every link, replicated | a follower takes over, as in chapter 4 |
| Id generator | gives each new link a number | see chapter 8 | another id node is asked |

### One request, step by step

The steps follow the arrows of figure 14.6.

1. A visitor's browser sends `GET /4C92`.
2. The load balancer passes the request to a web server.
3. The web server asks the cache for `4C92`. Popular links are found here.
4. On a miss, it reads `4C92` from the key-value store and puts the answer in the cache.
5. When an author creates a link, the web server takes the next number from the id generator and writes it in base 62.
6. The visitor receives `301` with the long address in `Location`, and the browser goes there.

## The design, deployed

<figure class="wide">
<img src="figures/shortener-deploy.svg?v=be160444" alt="The URL shortener, deployed. Visitors: Visitors (3900 redirects/s), open short links. Edge, in 3 zones: Load balancers (x 2), any web server, Web servers (x 12), hold no data. Data, in 3 zones: Cache nodes (x 6), popular links, Key-value store (x 24), 8 shards x 3 replicas, Id counter (x 3), blocks of numbers. Counting: Click queue (x 3), see chapter 11, Click counters (x 4), sum each minute.">
<figcaption><b>Figure 14.7</b> The URL shortener as it is deployed, with the tier that counts clicks kept off the path of a redirect.</figcaption>
</figure>

Visitors reach a pair of load balancers in front of 12 web servers in 3 zones, any
of which can answer any request. A redirect reads the cache and, on a miss, 1 of the
8 shards of the key-value store, each of which has a replica in every zone. The
counter that supplies numbers for new links is consulted once for each block of 1000
and stands to 1 side. Below the line, the click queue and its counters form a
separate tier, which a redirect writes to and never waits for. In front of all this,
a service of this kind normally places the edge servers of a content delivery
network, which can answer a popular redirect without reaching the origin at all.

## How real systems do it

The published material on URL shorteners is thinner than on most systems in this
book, since their operators have written little about them, and this section is
accordingly short and confined to what can be supported.

The semantics of the redirects are fixed by the HTTP standard, which also defines 2
further status codes, `307` and `308`. These are the temporary and permanent
redirects that additionally require the browser to repeat the request with the same
method, where `301` and `302` allow a `POST` to be turned into a `GET`. For a link
that is only ever followed with `GET`, the difference does not arise.

The scrambling of a counter described above is an instance of *format-preserving
encryption*, a cipher whose output lies in the same range as its input. The
construction generally used for small ranges is a Feistel network of a few rounds,
and it should be distinguished from libraries that merely obfuscate numbers by a
fixed shuffle of the alphabet, which resist casual inspection and do not resist
analysis.

The alphabet of 58 characters that omits the easily confused ones is known as
Base58, and Flickr has described using it for its short addresses. The checking of
submitted addresses against lists of harmful sites is offered as a public service by
the makers of the major browsers.

## Mistakes to avoid

| Mistake | What goes wrong | What to do |
|---|---|---|
| Codes cut from a hash, without a check | 2 addresses receive the same code, and some visitors reach the wrong page. | Check every code against the store, or use a counter. |
| Checking for a free code and then writing it | 2 servers find the same code free and both take it. | Use an atomic create-if-absent. |
| Codes that are consecutive numbers | Anyone can walk through all links by counting. | Scramble the number before encoding it, or use random codes. |
| Codes only just long enough | Blind guesses find real links often, and the codes run out. | Choose a length that leaves the code space sparsely used. |
| `301` with unlimited caching | A link that has been disabled keeps working in browsers that remembered it. | Use `302`, or limit how long `301` may be remembered. |
| Incrementing a counter on every redirect | Every read becomes a write, and popular links contend. | Record clicks in a queue and count them in batches. |
| Not caching absent codes | Requests for nonexistent codes all reach the store. | Cache absence briefly, and rate limit such requests. |
| Giving the code of an expired link to a new link | Old references lead to an unrelated destination. | Do not reuse codes. |
| Accepting any address | The service carries links to harmful pages and is blocked by mail filters. | Check addresses against lists of harmful sites, and be able to disable a link. |
| Shortening the service's own links | Redirects chain or loop. | Refuse addresses on the service's own domain. |

## Failures

| Failure | What users see | How the system recovers |
|---|---|---|
| The cache is lost | redirects are slower for a few minutes | links are read from the store and cached again |
| The id generator is unreachable | new links cannot be created; redirects work | another id node is used |
| A store leader fails | about 1 second without new links for its shard | a follower is elected |

## Trade-offs

| Decision | What it gains | What it costs |
|---|---|---|
| Codes from a counter | no collisions and no retry | codes can be guessed in order |
| Cache in front of the store | most redirects avoid the store | more memory |
| `301` with a time limit | fewer requests reach us | click counts are approximate |

## The simulation

<div class="simulation">

**Simulation in the repository.** The program [`code/shortener`](https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/distributed-systems-from-the-ground-up/code/shortener/src/main.rs) simulates this design. To run it, clone the repository and type `cargo run --release -p shortener` in the `code` directory.

</div>

## References

- RFC 9110, *HTTP Semantics*, 2022, sections on status codes 301, 302, 307 and 308.
- M. Bellare and others, "Format-Preserving Encryption", Selected Areas in Cryptography, 2009.
- J. Black and P. Rogaway, "Ciphers with Arbitrary Finite Domains", CT-RSA 2002.
- Flickr API documentation, "URLs", on short addresses in base 58.

## Terms introduced in this chapter

| Term | Meaning |
|---|---|
| Short link | a short address that redirects to a longer one |
| Code | the part of a short link that identifies it |
| Base 62 | a way of writing numbers with 62 digits: 0 to 9, A to Z and a to z |
| Collision | 2 addresses receiving the same code |
| Redirect | a response that tells the browser to go to another address |
| `301 Moved Permanently` | a redirect that the browser may remember |
| `302 Found` | a redirect that the browser asks for again each time |
| Custom name | a code chosen by the author |
| Expiry | the time after which a link no longer works |
| Enumeration | finding valid codes by trying them in order |

<div class="summary">

## Summary

- Codes of 7 characters over 62 symbols give 3.5 trillion possibilities, far more than the links expected, which keeps guessing unrewarding.
- Codes cut from a hash or drawn at random must be checked against the store before use, while codes from a counter are unique by construction.
- A counter's numbers are written in base 62 after a scrambling step, since consecutive codes could be guessed.
- `301` lets browsers skip the shortener on repeat visits, and `302` keeps every visit visible and every link revocable.
- Redirects are served from a cache in front of a sharded key-value store, by web servers that hold no data.
- Clicks are written to a queue and counted in batches, so that a redirect never waits for a write.
- A public shortener checks destinations, limits creation, and can disable a link quickly.

</div>
