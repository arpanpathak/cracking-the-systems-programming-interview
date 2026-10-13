<img class="plate" src="art/ch22.svg?v=69a52589" alt="An owl stands beside a sign that reads: ka, then kafka, karaoke, kayak.">

# Search Autocomplete: System Design

When a person begins to type into a search box, a short list of suggestions appears
beneath it, and the list changes with every letter. Typing `ka` produces "kafka",
"karaoke near me" and "kayak", and the addition of an `f` reduces the list to "kafka"
and "kafka vs rabbitmq". The feature is called *autocomplete* or *typeahead*, and it
spares the user some typing, corrects spelling before it has gone wrong, and shows
what other people have looked for.

2 characteristics set this feature apart from the search that it accompanies. It is
invoked far more often, once for every letter typed where a search is made once, so
that a service handling 100000 searches a second may receive a million requests for
suggestions in the same second. And it must be very much faster. A page of search
results that takes half a second to appear is acceptable, whereas suggestions that
arrive half a second after a keystroke are useless, since the user has by then typed
2 further letters and the suggestions refer to text that is no longer in the box. The
practical limit is about 100 ms from the keystroke to the display, of which the
network consumes the greater part.

There is no possibility of computing anything substantial within such a limit, and
the design is governed by that fact. Whatever can be computed in advance is computed
in advance, so that answering a request amounts to a single lookup, and whatever can
be answered without reaching the service at all is answered nearer to the user. The
interest of the design lies in the question of what exactly should be prepared
beforehand, in how the prepared data is kept reasonably up to date, and in a small
number of ways in which a feature that looks harmless can cause real embarrassment.

<div class="covers">

This chapter covers

- what a suggestion is, and where the candidates come from
- finding the searches that begin with a prefix: a sorted list, and a tree of letters
- why the answers are computed before anyone asks
- how much data that requires, and how it is rebuilt
- counting what people search for
- searches that became popular within the last hour
- what the browser must do: waiting, discarding late answers, and caching
- suggestions that must not be shown
- dividing the data among servers

</div>

## What a suggestion is

A suggestion is a complete search that begins with what the user has typed so far. The
text already typed is called the *prefix*, and the suggestions are *completions* of it.

The candidates are, for the most part, searches that other people have made. A search
engine keeps a record of the searches submitted to it, and the completions of `ka` are
drawn from the searches in that record which begin with `ka`. There are generally far
more of these than can be displayed, since thousands of distinct searches begin with
any short prefix, and so they have to be ranked and only the first few shown.

The basic ranking is by frequency. A search that has been made 900 times is preferred
to one that has been made 300 times, on the reasoning that what many people have
looked for is what the next person is most likely to want. Frequency alone is a
serviceable beginning, and the later sections refine it.

The problem can therefore be stated precisely. Given a prefix, return the k most
frequent searches that begin with it, where k is a small number such as 5 and the
answer is required within a few milliseconds.

## Finding the searches that begin with a prefix

### A sorted list

The most direct structure is a list of all known searches in alphabetical order, each
accompanied by its count. In such a list, all the searches that begin with a given
prefix stand together, since alphabetical order groups words by their initial letters.
The first of them can be found by binary search, or in an ordered index of the kind
used throughout this book, and the remainder follow immediately after it.

The simulation for this chapter is built in this way, with 10 searches held in an
ordered map. For the prefix `ka` it locates the first entry not less than `ka`, reads
forward for as long as the entries begin with `ka`, which yields kafka, kafka vs
rabbitmq, karaoke near me and kayak, sorts these 4 by count, and returns the first 3.

The method is correct and, for long prefixes, perfectly adequate. Its weakness lies in
the short prefixes, which are the ones most often requested, since every search begins
with a single letter. The number of entries beginning with `k` may run to millions,
and all of them must be read and ranked in order to discover the 5 best. The cost of a
request is proportional to the number of matches, and the number of matches is
greatest for exactly those requests that are most numerous.

### A tree of letters

The traditional structure for prefixes is a tree in which each edge is labelled with a
letter and the path from the root to any node spells out a prefix. It is called a
*trie*, or a prefix tree.

<figure>
<img src="figures/type-trie.svg?v=f403aa27" alt="A tree of letters. From the top, branches lead to k and r. Below k are a, e and u. Below ka are f, r and y, which lead to kafka, karaoke and kayak. The path from the top through k to a is marked, and every search that begins with ka lies below it.">
<figcaption><b>Figure 22.1</b> A tree in which the path from the top to a node spells a prefix, with the path for 'ka' marked.</figcaption>
</figure>

To find the completions of `ka`, one starts at the root, follows the edge labelled `k`
and then the edge labelled `a`, and arrives at a node beneath which lie all the
searches that begin with `ka` and no others. Reaching that node takes as many steps as
the prefix has letters, 2 in this case, however many millions of searches the tree
contains.

The trie makes the node easy to find and leaves the main difficulty where it was. The
completions lie somewhere in the subtree below the node, and to determine the 5 most
frequent it is still necessary to visit the whole subtree, which for a short prefix is
a large part of the entire tree. The structure has shortened the search for the
beginning of the answer and has done nothing to shorten the collection of the answer
itself.

## Computing the answers before anyone asks

The observation that resolves the difficulty is that the question "which are the 5
most frequent searches beginning with `ka`" has the same answer whoever asks it and
whenever, until the underlying counts change. There is consequently no reason to work
it out at the time of the request. It can be worked out once, in advance, for every
prefix, and the results stored.

In terms of the trie, this means that every node carries, in addition to its children,
a short list of the best completions that lie beneath it. In terms of a plain table,
it means a row for every prefix, containing that prefix's best completions.

<figure class="steps" data-prefix="figures/steps-type-lists" data-count="5" data-version="96e5e89e">
<img src="figures/steps-type-lists-01.svg?v=96e5e89e" alt="1 lookup for each letter typed, step 1 of 5. For every prefix that occurs, the 3 most frequent searches that begin with it have been worked out in advance and stored. Answering is then a matter of looking up 1 row.">
<figcaption><b>Figure 22.2</b> Each keystroke is answered by reading the row that was prepared for the prefix. Use Next and Back to move through the 5 steps.</figcaption>
</figure>

With such a table, a request is a single lookup by key, of the kind that a key-value
store or a cache performs in well under a millisecond. Its cost does not depend on the
length of the prefix, on the number of searches that match it, or on the size of the
collection. The simulation prints the rows of this table for the prefixes of its
example: for `k`, kubernetes with 950, kafka with 900 and karaoke near me with 800;
for `ka`, kafka, karaoke near me and kayak; for `kaf`, the 2 searches about kafka; and
for `x`, nothing.

Once the answers have been computed in advance, the trie is no longer indispensable.
A flat table that maps each prefix, as a string, to its list does everything required
and can be held in any key-value store. The trie continues to be of use in building
the lists, as will be seen, and in memory it is the more compact representation, since
prefixes that share their opening letters share the corresponding nodes. As far as
serving is concerned, however, the design has reduced a search problem to a lookup
problem, and has done so by the same exchange that chapter 15 made for the news feed,
in which work was moved from the moment of reading to the moment of writing.

### What this costs

The cost is storage and the labour of construction. Every search of n letters has n
prefixes, so that a collection of 100 million distinct searches of 20 letters on
average gives rise to as many as 2 billion prefixes. In practice the number is much
smaller, since a great many searches share their prefixes and there is only 1 row for
`k`, shared by every search that begins with that letter. It can be reduced further by
2 simple rules. Prefixes beyond a certain length, 20 letters for example, are not
stored, since by that point so few searches match that they can be found directly. And
searches that have been made only a few times are excluded from the collection
altogether, which, as a later section explains, is also required for reasons that have
nothing to do with storage.

A row holds 5 completions, which can be stored as references to the searches and need
not be full copies. A few hundred million rows of some tens of bytes each come to tens
of gigabytes, an amount that can be held in the memory of a small number of machines.

### Building the lists

The lists are built from the bottom of the trie upwards. The list for a node is the
best 5 drawn from the lists of its children, together with the search that ends at the
node itself, if there is one. Since each child's list contains at most 5 entries, a
node with 26 children has to consider at most 131 candidates, and the entire trie is
processed in a single pass whose cost is proportional to the number of nodes.

The same property makes it possible to bring the lists up to date without rebuilding
everything. When the count of a single search changes, only the lists on the path from
that search up to the root can be affected, which for a search of 20 letters is 20
nodes. In practice, most services nevertheless rebuild the whole table at intervals,
hourly or daily, from the latest counts, and replace the old table with the new one in
a single step. A complete rebuild is simpler to make correct, is done by a batch job
that places no load on the servers answering requests, and has the considerable
advantage that the previous table remains at hand and can be reinstated at once if the
new one proves to be faulty.

## Counting what people search for

The counts from which the lists are built come from the record of searches. Every
search that is actually submitted, as distinct from every prefix that is typed, is
appended to a log, by way of the message queue of chapter 11, so that the recording
adds nothing to the time taken by the search itself.

A batch job reads this log at intervals and produces, for every distinct search, the
number of times it was made within some recent period. 3 aspects of this counting
call for care.

The text of a search has to be *normalised* before it is counted, since "Kafka",
"kafka" and " kafka " are the same search to the person who typed them and would
otherwise be counted as 3 separate ones, each with a third of the proper weight.
Normalisation ordinarily converts the text to small letters, removes superfluous
spaces, and brings accented characters to a standard form. The same normalisation
must be applied to the prefix when a request for suggestions arrives, or the lookup
will fail to find a row that exists.

Not every search need be counted. At a high volume, a random sample of 1 search in 10
or 1 in 100 yields counts that are proportionally accurate for everything popular
enough to appear in a list of suggestions, at a tenth or a hundredth of the work.
Sampling loses precision only for rare searches, which are not going to be suggested
in any case.

And the counts should favour what is recent. A search that was made a million times 3
years ago and has scarcely been made since ought not to rank above one that has been
made 100000 times this week. A common method reduces older counts by a constant factor
at each period, halving the weight of every search's history each week for example, so
that popularity has to be sustained in order to be retained. This is the decay that
chapter 9 applied to the counts of the least frequently used rule, and it is applied
here for the same reason.

## What became popular within the hour

A table rebuilt once a day cannot know of anything that happened today. When news
breaks and a million people begin to search for a name that nobody had searched for
the day before, suggestions built from yesterday's counts will not include it, and the
feature appears conspicuously out of touch at exactly the moment when attention is
greatest.

The usual remedy is to maintain a second, much smaller collection alongside the main
table. A stream processor reads the log of searches as they arrive and keeps counts
over a short sliding window, the last hour for instance, using the windowed counting
of chapter 7. Searches whose recent rate far exceeds their historical rate are
recognised as *trending* and placed in a small table of their own, which is brought up
to date every minute or so. When a request arrives, the service consults both the main
table and the small one and merges the 2 lists.

The division gives each part the method that suits it. The great mass of suggestions
changes slowly and is rebuilt at leisure, in bulk, with every opportunity for
checking. The few that change quickly are handled by a mechanism that is fast because
it is small.

## What the browser must do

Much of the performance of autocomplete depends on the behaviour of the client, and a
well-constructed service can be made to seem slow and erratic by a carelessly written
one.

A user who types quickly produces a keystroke every 100 ms or less. A request sent on
every keystroke is mostly wasted, since its answer will be out of date before it has
arrived. The client therefore waits for a brief pause in the typing, of perhaps 50 to
100 ms, before sending a request, a technique known as *debouncing*. A user who types
5 letters in rapid succession and then stops causes 1 request where there would have been 5. Requests are
likewise withheld until at least 1 or 2 letters have been typed, according to the
language, since the suggestions for a single letter are seldom of any use and such
prefixes account for a large share of the load.

A second matter concerns the order in which answers arrive, and it is the source of a
defect that is frequently seen.

<figure>
<img src="figures/type-stale.svg?v=7c128e1b" alt="5 steps. The searcher types ka, and request 1 is sent and is slow. The searcher types kaf, and request 2 is sent and is fast. The answer to request 2 arrives and is shown. The answer to request 1 arrives late and replaces it. The suggestions no longer match the text in the box. The cure is to show an answer only if it is for the text now in the box.">
<figcaption><b>Figure 22.3</b> The answer to an earlier request arrives after the answer to a later one and replaces it.</figcaption>
</figure>

Requests travel independently over the network and may be answered in an order
different from that in which they were sent. If the client displays every answer as it
arrives, a slow answer for `ka` can overwrite the correct answer for `kaf`, and the
user is shown suggestions that do not correspond to the text in the box. The client
must therefore remember which prefix each request was for, and display an answer only
if that prefix is still the text in the box. Requests that have been overtaken should
also be cancelled, which saves the work of answering them.

The third matter is caching, for which autocomplete is exceptionally well suited. The
answer for a given prefix is the same for every user, in the absence of
personalisation, and remains valid for minutes or hours. It can therefore be cached at
every level, with the methods of chapter 9. The browser keeps the answers it has
already received, so that a user who deletes a letter sees the previous suggestions
again instantly, with no request. The edge servers of a content delivery network, as
described in chapter 17, keep the answers for common prefixes close to users, and
since requests are heavily concentrated on a small number of short prefixes, a large
proportion of them never reach the service. For this to work, a request for
suggestions must be an ordinary `GET` with the prefix in its address, and the reply
must state for how long it may be reused.

## Suggestions that must not be shown

Autocomplete presents text that the service did not write, taken from what other
people have typed, directly beneath the service's own name. It has in consequence 2
ways of causing harm that are not apparent from the engineering alone.

The first concerns offensive or damaging suggestions. If a sufficient number of people
search for a person's name together with an accusation, the plain frequency ranking
will propose that accusation to everybody who starts to type the name, and so lends
the authority of the service to a rumour. Suggestions may equally promote abuse,
dangerous activity or unlawful content, for no better reason than that many people
have searched for it. The service therefore passes candidates through a filter before
they enter the table, composed of lists of terms and categories that are never to be
suggested, and provides a means by which any particular suggestion can be removed
promptly once it has been reported. Because the table is built in advance, the filter
is applied during the build and costs nothing when requests are answered, and an
urgent removal is effected by a small list of exclusions that is checked as answers
are served.

The second concerns privacy. A search may contain a person's name, an address, a
telephone number or a medical question. If a search that only 1 person ever made were
to be offered as a suggestion, that person's private search would be shown to
strangers who chanced to type the same opening letters. A search is therefore admitted
as a candidate only when it has been made by a sufficient number of different people,
some hundreds for example, so that no suggestion can be traced to an individual. This
threshold, which was mentioned earlier as a means of saving storage, is in fact
required on grounds of privacy, and the number to be counted is that of distinct
people, whatever the number of searches, since 1 person may make the same search a great many
times.

## Dividing the data among servers

The table of prefixes is too large for 1 machine in a big service and has to be
divided. The natural key for the division is the prefix itself.

It is tempting to assign prefixes to servers by their first letter, and this
distributes the load poorly. Far more searches begin with `s` than with `x`, so that
some servers would be overloaded and others nearly idle. The division is better based
on measured load: the ranges of prefixes are chosen so that each receives roughly the
same number of requests, with the consequence that a common letter is spread over
several servers by its second letter and several rare letters share 1 server. As an
alternative, prefixes may be distributed by a hash, with the consistent hashing of
chapter 1, which balances the load without any measurement and gives up the property
that neighbouring prefixes reside on the same server.

Since the table is read-only between rebuilds, replicating it is uncomplicated. Every
replica of a shard holds an identical copy of the same immutable file, and any of them
may answer any request. There is no leader and no question of consistency among the
replicas, apart from the short interval during which a new table is being distributed
and some replicas have it while others still serve the old one. A user may notice a
small change in the suggestions if 2 successive requests fall on either side of that
interval, and this is harmless.

## Use cases

A person types into a search box, and the service proposes completions.

<figure>
<img src="figures/typeahead-use-cases.svg?v=7d81dcdf" alt="A use case diagram of the suggestion service. Searcher: get suggestions (GET /v1/suggestions?q=ka), run the search (GET /v1/search?q=kafka).">
<figcaption><b>Figure 22.4</b> The actor and what it does.</figcaption>
</figure>

## Functional requirements

| No. | Functional requirement |
|---|---|
| 0 | For the text typed so far, the service returns up to 5 searches that begin with it. |
| 1 | Suggestions are ordered by how often they have recently been searched for. |
| 2 | Searches that have become popular within the last hour appear among the suggestions. |
| 3 | A suggestion that has been reported can be removed within minutes. |
| 4 | No suggestion is shown that fewer than a set number of different people have searched for. |

## Non-functional requirements

| No. | Property | Non-functional requirement |
|---|---|---|
| 0 | Latency | Suggestions are displayed within 100 ms of a keystroke, and the service itself answers within 10 ms. |
| 1 | Availability | 99.9%. If suggestions are unavailable, searching still works. |
| 2 | Consistency | Eventual. Suggestions reflect counts that are up to a day old, or up to a minute old for trending searches. |
| 3 | Scale | 1 million requests per second, and 100 million distinct searches. |

Autocomplete is an aid, and nothing else depends on it, which is
reflected in non-functional requirements 1 and 2. A search box with no suggestions is
merely a search box, and suggestions computed from yesterday's counts are nearly as
good as suggestions computed from this minute's. Both facts are used to the full. The
table is built offline and is allowed to be stale, and the client is written so that a
slow or failed request for suggestions leaves the user free to type and to search
without hindrance.

## Core entities

<figure>
<img src="figures/typeahead-entities.svg?v=0037c210" alt="The core entities. Search count has the fields text string, count u32, per week. Suggestion list has the fields prefix string, top 5 searches. Counts are collected from the searches people run. Lists are computed from the counts ahead of time, 1 for each prefix.">
<figcaption><b>Figure 22.5</b> The core entities and their fields.</figcaption>
</figure>

## Capacity estimate

<div class="estimate">

<img class="builder" src="art/crab-builder.svg" alt="A crab in a hard hat, in tears.">

**Arithmetic ahead.** The table of prefixes occupies about 25 GB, which is held in memory on a few machines, and most requests are answered by caches before they reach those machines.

<a class="skip" href="#high-level-design">Skip to the high-level design</a>

<details>
<summary>Show the calculation</summary>

| Quantity | Calculation | Result |
|---|---|---|
| Requests per second | 100000 searches × about 10 letters typed | 1 million |
| Requests that reach the service | 1 million × 20% not answered by caches | 200000 per second |
| Rows in the table | distinct prefixes, after the rules on length and popularity | about 500 million |
| Size of a row | prefix 12 bytes + 5 references of 8 bytes | about 50 bytes |
| Size of the table | 500 million × 50 bytes | 25 GB |

</details>

</div>

## The API

Suggestions are a resource addressed by the prefix, which is passed as a parameter of
the query. The request is a plain `GET`, so that every cache between the user and the
service is able to store the answer.

**Suggestions for a prefix**

```http
GET /v1/suggestions?q=ka HTTP/1.1
Host: search.example
```

```http
HTTP/1.1 200 OK
Content-Type: application/json
Cache-Control: public, max-age=300

{
  "prefix": "ka",
  "suggestions": ["kafka", "karaoke near me", "kayak"]
}
```

The reply repeats the prefix so that the client can verify that the answer belongs to
the text now in the box. `Cache-Control` permits browsers and edge servers to reuse
the answer for 5 minutes.

**A prefix with no completions**

```http
GET /v1/suggestions?q=kafx HTTP/1.1
Host: search.example
```

```http
HTTP/1.1 200 OK
Content-Type: application/json
Cache-Control: public, max-age=300

{ "prefix": "kafx", "suggestions": [] }
```

An empty list is a successful answer and is returned with `200`. It is cached like any
other, which protects the service against repeated requests for prefixes that lead
nowhere.

## High-level design

<figure class="wide">
<img src="figures/typeahead-design.svg?v=7cca881d" alt="Suggestions while typing. The components are Searcher, Suggestion API, Prefix lists, Search log, Counting job, Search counts. Step 1: After each letter, the browser asks for suggestions. Step 2: The API returns the stored list for that prefix. Step 3: Every search that is run is written to a log. Step 4: A job counts the searches of the last week. Step 5: New lists are built from the counts.">
<figcaption><b>Figure 22.6</b> The components and the path of a request. The steps are numbered.</figcaption>
</figure>

| Component | Role | State it holds | When 1 instance fails |
|---|---|---|---|
| Suggestion API | looks up the list for a prefix and applies the list of exclusions | a copy of the table, in memory | another replica answers |
| Prefix lists | the table of the best completions for every prefix | an immutable file, replaced at each rebuild | every replica holds the same file |
| Search log | records every search that is submitted | the log, in a message queue | as in chapter 11 |
| Counting job | counts searches, with decay, at intervals | none between runs | the job is run again |
| Search counts | the count of every distinct search | counts, in a store | the previous counts are still available |

### One request, step by step

The steps follow the arrows of figure 22.6.

1. After a pause in the typing, the browser asks for suggestions for the text in the box, unless it already holds the answer.
2. The suggestion API, if no cache has answered first, normalises the prefix, reads the row for it from the table in its memory, removes any excluded entries, and returns the list.
3. Independently of this, every search that a user submits is appended to the search log.
4. At intervals, the counting job reads the log and brings the count of every search up to date, reducing older counts.
5. A new table of prefix lists is built from the counts, checked, and distributed to the replicas, which begin serving it in place of the old one.

## The design, deployed

<figure class="wide">
<img src="figures/typeahead-deploy.svg?v=0a7a695f" alt="The suggestion service, deployed. Browsers: Browsers (1 million req/s), keep answers they had. Near the users: Edge servers (x 100s), cache by prefix, 5 min. Serving, in 3 zones: Load balancers (x 4), by range of prefixes, Suggestion API (x 24), whole table in memory. Building, offline: Search log (x 6), every search made, Counting job (batch), normalise, count, decay, Trending processor (x 4), the last hour.">
<figcaption><b>Figure 22.7</b> The suggestion service as it is deployed: caches in front, a serving tier that only reads, and an offline build behind.</figcaption>
</figure>

Most of the million requests per second are answered before they reach this
system, by the browser's own memory of earlier answers and by edge servers that
cache each prefix for 5 minutes. The serving tier receives about a fifth of them. It
consists of 24 machines, each holding a part of the table in memory, behind load
balancers that route by the range of the prefix. Nothing in the serving tier ever
writes. The table is produced by the build tier below, from the log of searches, and
handed upwards once an hour as a finished file, so that a fault in the building can
at worst leave the serving tier with an old table.

## How real systems do it

Facebook published an early and clear account of a typeahead in 2010, for the search
box that suggests people and pages. Its design starts in the browser, which is
loaded with the user's own friends and pages before a letter is typed and answers
from that list first, and which caches every reply so that deleting a letter costs
nothing. Only then is the service asked, and the service is a set of indexes, 1 for
each kind of result, queried in parallel and merged by an aggregator. The emphasis
on the client is the same as in this chapter, and the personal first stage is a
form of the personalisation that this chapter mentions only in passing.

The data structure for the general problem, the most frequent completions of a
prefix, has been studied as *top-k completion*. A paper from Microsoft compares
several structures and shows that a trie which stores at each node the best score
beneath it can find the best completions without visiting the whole subtree, in
space close to that of the compressed strings. This is a middle way between the 2
extremes of this chapter, the trie that must be searched and the table that stores
every answer, and it is what a system uses when the table would be too large. Search
libraries commonly implement completion with a compact automaton that shares both
the prefixes and the suffixes of the stored strings.

On what must not be shown, the operators of the large search engines publish
policies stating which kinds of prediction they remove, covering violence, sexually
explicit and hateful predictions and those that make damaging statements about
named people, together with a means of reporting. The existence of these policies
is the practical evidence for the section on suggestions that must not be shown.
The threshold of distinct users is an application of the idea of k-anonymity, that
no released item should be traceable to fewer than k people.

## Mistakes to avoid

| Mistake | What goes wrong | What to do |
|---|---|---|
| Ranking the matches while the user waits | Short prefixes match millions of searches and cannot be ranked in time. | Compute the best completions for every prefix in advance. |
| Updating the table on every search | The serving path carries a constant load of writes. | Rebuild in batches, and keep a small separate table for what is trending. |
| A request on every keystroke | Most answers are out of date on arrival. | Wait for a brief pause in the typing before asking. |
| Displaying every answer as it arrives | A slow answer for an earlier prefix overwrites the right one. | Display an answer only if it is for the text now in the box. |
| Requests that caches cannot store | Every keystroke of every user reaches the service. | Use `GET` with the prefix in the address, and state how long the answer may be reused. |
| Counting searches without normalising | The same search is divided among several spellings. | Normalise the text before counting and before looking up. |
| Counts that never decay | Searches that were popular years ago keep their places. | Reduce older counts at each period. |
| Suggesting anything that is frequent | Offensive or defamatory suggestions appear under the service's name. | Filter candidates during the build, and allow prompt removal. |
| Suggesting rare searches | 1 person's private search is shown to strangers. | Admit a search only when enough different people have made it. |
| Dividing by first letter | Servers for common letters are overloaded. | Divide by measured load, or by a hash. |
| Making search depend on suggestions | A failure of suggestions blocks the search box. | Let the user type and search whether or not suggestions arrive. |

## Failures

| Failure | What users see | How the system recovers |
|---|---|---|
| The suggestion service is unreachable | no suggestions, and search works as usual | caches continue to answer common prefixes, and the service returns |
| A newly built table is faulty | strange or missing suggestions | the previous table is reinstated in 1 step |
| The counting job fails | suggestions grow slowly out of date | the job is run again, and the previous table serves meanwhile |
| An offensive suggestion is reported | it disappears within minutes | it is added to the exclusions, and the filter is corrected for the next build |
| An answer is lost or late | the list fails to update for 1 keystroke | the next keystroke sends a new request |

## Trade-offs

| Decision | What it gains | What it costs |
|---|---|---|
| Answers computed in advance | 1 lookup per request, whatever the prefix | storage for every prefix, and staleness between rebuilds |
| Rebuilding in batches | simple, verifiable, and easy to reverse | new searches appear late, without the trending table |
| A separate trending table | fresh suggestions within a minute | a second mechanism to operate |
| Caching at the edge and in the browser | most requests never reach the service | a removed suggestion lingers until the caches expire |
| A threshold of distinct people | privacy, and a smaller table | rare searches that would be legitimate are never suggested |

The fourth row conceals a tension that deserves to be noticed. The longer the answers
may be cached, the lighter the load, and the longer a suggestion that has been removed
continues to be shown from caches that the service cannot reach. The period for which
answers are cached is therefore chosen with removals in mind, and it is the reason why
5 minutes is a more usual figure than 5 hours.

## The simulation

<div class="simulation">

**Simulation in the repository.** The program [`code/typeahead`](https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/distributed-systems-from-the-ground-up/code/typeahead/src/main.rs) simulates this design. To run it, clone the repository and type `cargo run --release -p typeahead` in the `code` directory.

</div>

## References

- Facebook engineering blog, "The Life of a Typeahead Query", 2010.
- B. Hsu and G. Ottaviano, "Space-Efficient Data Structures for Top-k Completion", WWW 2013.
- Google Search Help, "How Google autocomplete predictions work".
- L. Sweeney, "k-Anonymity: A Model for Protecting Privacy", International Journal of Uncertainty, Fuzziness and Knowledge-Based Systems, 2002.

## Terms introduced in this chapter

| Term | Meaning |
|---|---|
| Autocomplete, typeahead | proposing complete searches for the text typed so far |
| Prefix | the text that has been typed so far |
| Completion | a search that begins with the prefix |
| Trie, prefix tree | a tree in which the path to each node spells a prefix |
| Top k | the k best items by some measure, here the k most frequent |
| Normalisation | bringing text to a standard form before comparing or counting it |
| Decay | reducing the weight of older counts |
| Trending | recently far more frequent than in the past |
| Debouncing | waiting for a pause in the typing before sending a request |
| Sampling | counting a random fraction of events in place of all of them |

<div class="summary">

## Summary

- Autocomplete is requested for every keystroke and must answer within about 100 ms, which leaves no time to compute anything.
- A sorted list or a trie finds the searches that begin with a prefix quickly, and ranking them still costs in proportion to their number.
- The best completions of every prefix are therefore computed in advance, so that a request is a single lookup.
- The table is rebuilt in batches from counts of submitted searches, normalised, sampled and weighted towards the recent.
- A small table of trending searches, brought up to date every minute, supplies what the daily rebuild cannot.
- The client waits for a pause before asking, discards answers that arrive late, and reuses answers it already has.
- Candidates are filtered for offensive content, and a search is suggested only if enough different people have made it.

</div>
