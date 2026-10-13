<img class="plate" src="art/ch18.svg?v=9210dffb" alt="2 pigeons stand beside a sign that lists messages 1 to 4 and the words: last received 1.">

# Chat: System Design

A chat service carries short messages between people, and its users hold it to a
standard that few other systems are asked to meet. A message is expected to appear on
the recipient's screen within a moment of being sent, as though the 2 phones were
directly connected. It is expected to arrive whether or not the recipient's phone was
reachable at the time, to arrive once, and to appear among the other messages of the
conversation in the order in which they were sent. People notice at once when any of
these expectations is disappointed, since a conversation in which replies precede
their questions, or in which a remark is repeated, or in which something said an hour
ago turns up now, is immediately felt to be broken.

The system has to meet this standard on a foundation that is distinctly unreliable. A
mobile phone loses its connection many times a day, in lifts and tunnels and when
passing from one network to another. Its operating system suspends applications that
are not on the screen. A message, or the acknowledgement of a message, may be lost at
any point, and neither party can tell which of the 2 was lost. The design of a chat
service consists largely in arranging matters so that none of this is visible: so that
every interruption is followed by an exact recovery, and no message is lost, repeated
or misplaced in consequence.

<div class="covers">

This chapter covers

- how a server can send to a phone that has not asked: 3 methods compared
- gateways, which hold the open connections, and the record of who is connected where
- numbering the messages of a conversation
- how 1 number per message deals with gaps, repetitions and disorder
- catching up after an absence, with a cursor
- sending a message twice without storing it twice
- sent, delivered and read
- groups, several devices, presence, and recipients who are offline
- what end-to-end encryption changes

</div>

## Reaching a phone that has not asked

In the ordinary use of HTTP, every exchange is begun by the client. The client sends a
request and the server replies, and a server has no means of addressing a client that
has not just asked it something. For most applications this is no restriction. For
chat it is the first obstacle, since the essential act of the service is to deliver a
message to a phone at a moment the phone could not have predicted.

There are 3 ways round the obstacle, and they are best compared by what each costs in
delay and in wasted effort.

<figure>
<img src="figures/chat-connections.svg?v=22c24da1" alt="3 time axes on which a message for a phone reaches the server at 1.3 seconds. When the phone asks every second, it receives the message at 2.0 seconds, and 3 other requests come back empty. When the phone asks and the server holds the request until there is an answer, the phone receives the message at 1.3 seconds and asks again. With 1 connection that stays open, the phone receives the message at 1.3 seconds and no requests are made.">
<figcaption><b>Figure 18.1</b> A message reaches the server at 1.3 seconds, and the phone learns of it under each of 3 methods.</figcaption>
</figure>

The first method is for the phone to ask at regular intervals whether anything has
arrived, which is called *polling*. It is trivially simple and unsatisfactory in both
respects. A message waits, on average, for half the interval before the next request
collects it, and nearly all the requests return nothing, so that a phone polling once
a second makes 86400 requests a day in order to receive perhaps 50 messages. Shortening
the interval reduces the delay and multiplies the waste, and across millions of phones
the empty requests alone amount to a formidable load.

The second method, *long polling*, removes most of both defects by a simple change on
the server. The phone sends a request as before, and the server, if it has nothing to
report, refrains from answering and holds the request open. When a message arrives,
the server answers the waiting request with it, and the phone, having received the
answer, immediately sends another request to wait on. Messages are delivered as soon
as they arrive, and no request is answered empty except when one has been held for so
long, usually about half a minute, that it is released to prevent intermediate network
equipment from concluding that the connection is dead.

The third method abandons the pattern of request and reply. The phone opens a single
connection to the server and keeps it open, and either side may send on it at any
time. The protocol that provides this over the same ports and through the same
infrastructure as HTTP is called *WebSocket*. It has the lowest delay and the least
overhead, since a message in either direction is a small frame on an existing
connection and involves no new request.

| | Polling | Long polling | Open connection |
|---|---|---|---|
| Delay before a message is received | up to 1 interval | none | none |
| Requests when nothing happens | 1 per interval | 1 per half minute or so | none, apart from a periodic sign of life |
| What the server holds for each phone | nothing | 1 waiting request | 1 connection |
| Sending from phone to server | a separate request | a separate request | on the same connection |

Chat services use the open connection, falling back on long polling in the rare
environments where a connection of the third kind cannot be established. The price is
in the third row of the table. The server must now maintain a connection for every
phone that is online, and with 50 million phones online that is 50 million connections
held open at once, most of them idle at any instant. This single fact shapes the
architecture of the service.

## Gateways and sessions

An open connection is a resource of an unusual kind. It consumes little processing
and a modest amount of memory, and it is tied irrevocably to the particular machine on
which it terminates: a message for a given phone can be written to its connection only
by the 1 process that holds that connection. The service therefore sets aside a class
of servers, called *gateways*, whose sole function is to hold connections. A gateway
accepts connections from phones, authenticates them, relays what arrives on them to
the rest of the service, and writes to them whatever the rest of the service asks it
to deliver. It contains as little other logic as possible, so that the software which
changes often, concerning messages and conversations, can be deployed without
disturbing the millions of connections.

A properly configured machine can hold some hundreds of thousands of idle connections,
and at 100000 each, 50 million phones require 500 gateways. A message addressed to a
member must be handed to the particular gateway on which that member's phone is
connected, and so the service needs to know, for every member who is online, which
gateway that is. This knowledge is kept in a *session store*, an in-memory store
mapping each connected device to its gateway. A gateway writes an entry when a phone
connects and removes it when the phone disconnects.

The session store can be wrong, and the design has to allow for it. A gateway that
crashes has no opportunity to remove its entries, which continue to assert that
100000 phones are connected to a machine that no longer exists. Every entry is
therefore given a time limit and must be renewed periodically by the gateway that owns
it, so that the entries of a dead gateway lapse of their own accord, which is the
lease of chapter 10 in another setting. More fundamentally, the session store is
treated as a hint and nothing more. If the service forwards a message to a gateway and
the phone proves not to be there, nothing has been lost, since the message is safely
stored and the phone will collect it when it reconnects, by the mechanism described
below. The correctness of delivery does not depend on the session store's being
accurate, only its speed.

When a gateway does fail, its 100000 phones all detect the loss within a few seconds
and all attempt to reconnect. If they did so immediately, the surviving gateways
would receive 100000 connection attempts in the same instant, each requiring a
cryptographic handshake, and might themselves be overwhelmed, causing further
disconnections and further attempts. Phones therefore wait for a random interval
before reconnecting and lengthen the interval after each failure, which is the backoff
with jitter of chapter 13 applied by the client.

## Numbering the messages of a conversation

We come now to the central problem, which is to ensure that every member of a
conversation sees the same messages in the same order, without omission or
repetition, in spite of everything that can happen to connections.

It is necessary first to say what "the order" is, since the obvious definition does
not survive examination. One might order messages by the time at which they were sent,
as recorded by the sender's phone. But the clocks of phones differ by seconds or
minutes, and a phone whose clock is slow would have its messages placed before
messages to which they are replies. Nor can the times at which messages arrive at the
various recipients be used, since these differ from one recipient to another, and the
members would see different orders.

The order is therefore defined by decree, at a single place. All messages of a
conversation pass through 1 point in the service, which assigns to each the next
number in a sequence belonging to that conversation: 1, 2, 3 and so on. The order of
the conversation is the order of these numbers, for every member and on every device.
A number of this kind is a *sequence number*, and the reader will recognise it as the
sequence number that the leader of a shard assigned to each record in chapter 3. The
message store that assigns it is, in fact, a replicated log for each conversation, and
the requirement that 2 messages never receive the same number is met in the same way,
by having a single leader accept all appends to a given conversation.

The effect of this decision is to reduce the whole problem of reliable, ordered
delivery to a matter of arithmetic on the recipient's device. Each device remembers 1
number for each conversation, the number of the last message it has displayed, and
compares the number of every incoming message with it.

<figure class="steps" data-prefix="figures/steps-chat-catchup" data-count="7" data-version="d7621933">
<img src="figures/steps-chat-catchup-01.svg?v=d7621933" alt="A phone catches up after a gap, step 1 of 7. The server gives every message of a conversation the next number. The phone is online and shows message 1. It remembers that 1 is the last number it has shown.">
<figcaption><b>Figure 18.2</b> A phone loses its connection while 3 messages are sent, receives 1 of them out of order, catches up, and ignores a repeated message. Use Next and Back to move through the 7 steps.</figcaption>
</figure>

3 distinct faults occur in the course of these steps, and the same comparison
disposes of each. A message whose number is exactly 1 greater than the last displayed
is the next message, and is shown. A message whose number is greater than that has
arrived ahead of others that are missing, and the device does not show it, since to do
so would present the conversation out of order. It asks the server for everything
after the last number it has. A message whose number is equal to or less than the last
displayed has been seen before, and is discarded. The simulation for this chapter runs
exactly this scenario, and ends with 4 messages on the server and the same 4, in the
same order and each once, on the phone.

The number that a device remembers is called its *cursor*, and it is what makes
recovery from an absence exact. A device that has been offline does not ask the server
what it has missed, a question the server could answer only by keeping track of what
each device has received. The device states its position, "I have everything up to
number 1 in this conversation", and the server replies with everything after that
position. The server keeps no record of deliveries and has no need to know why the
device was away or for how long. A phone that was switched off for a week recovers by
the same request as a phone that passed through a tunnel.

## Sending without duplicating

The preceding section dealt with messages travelling to a device. A similar hazard
attends messages travelling from it. A phone sends a message and waits for the
server's confirmation. If none arrives, the phone cannot distinguish between a message
that never reached the server and a message that was stored and whose confirmation
was lost, and since an unsent message is the worse outcome, it must send again. In the
second case the server now receives the same message twice, and a server that stored
whatever it received would give the 2 copies 2 successive numbers, to be displayed
twice on every member's screen.

<figure class="steps" data-prefix="figures/steps-chat-send" data-count="5" data-version="a60bd9ad">
<img src="figures/steps-chat-send-01.svg?v=a60bd9ad" alt="Sent twice, stored once, step 1 of 5. Before sending, the phone gives the message an identifier of its own, chosen at random: a7f3. The identifier travels with the message.">
<figcaption><b>Figure 18.3</b> The confirmation of a message is lost, the phone sends the message again, and the server recognises it. Use Next and Back to move through the 5 steps.</figcaption>
</figure>

The remedy is the idempotency key that chapters 11 and 13 used for the same purpose.
The phone generates a random identifier for each message before the first attempt and
includes it in every attempt. The server records the identifier with the stored
message, and on receiving an identifier it has already recorded for that conversation,
stores nothing and returns the number it assigned originally. A message may then be
sent any number of times and will be stored once.

The same identifier serves the phone in another way. A message that has been typed
and sent should appear in the sender's own view of the conversation at once, before
the server has confirmed it, since any perceptible delay makes the application feel
sluggish. The phone therefore displays the message immediately, marked as pending,
and when the confirmation arrives with the server's number, it uses the identifier to
find the pending message and move it to its proper place in the sequence.

## Sent, delivered and read

Chat applications commonly show the sender how far a message has progressed, and the
3 customary indications correspond to 3 different events in the system. A message is
*sent* when the server has stored it and assigned its number, at which point it is
safe and will not be lost. It is *delivered* when a device of the recipient has
received it, which the device reports by informing the server of its new cursor. It is
*read* when the recipient has opened the conversation, which the device reports
similarly, as the number of the last message actually displayed on screen.

It will be seen that delivery and reading are both conveyed by a single number for
each device, with no separate acknowledgement for every message. A cursor of 40
acknowledges messages 1 to 40 together. This economy matters in large and busy
conversations, and it has the further merit of being idempotent, since reporting the
same cursor twice has no additional effect.

These reports are themselves events that must be conveyed to the sender's devices,
and they pass through the same machinery as messages. They are, however, of less
consequence. A message that is lost is a serious failure, whereas a read indication
that arrives late or is occasionally lost is a blemish, and services accordingly
transmit such indications with less ceremony, without storing each durably.

## Recipients who are offline

When a message is stored and the recipient has no device connected, the service has
done all that it can do directly. The message waits in the store, and will be
delivered by the catching-up procedure when a device next connects.

To the recipient, however, a message that waits until the application is next opened
has not really arrived. The service therefore asks the notification service of chapter
13 to send a push notification through the provider that serves the phone's operating
system, which is able to wake the device and display an alert even when the
application is not running. The notification is merely a signal. It may be delayed or
dropped by the provider, as chapter 13 explained, and it need not carry the message
itself. When the user responds to it, the application opens its connection, reports
its cursor, and obtains the messages in the ordinary way. Reliability thus continues
to rest on the store and the cursor, and the notification serves only to bring the
user back sooner.

Mobile operating systems reinforce this division. They suspend applications that are
in the background and close their connections in order to save power, so that a phone
is, from the service's point of view, offline for most of the day although it is
switched on and in its owner's pocket. The combination of a push notification to
attract attention and a cursor to recover the state is the pattern to which every
mobile messaging application conforms.

## Groups and several devices

A conversation with many members requires no new mechanism. The message is stored
once, in the conversation's sequence, and each member's devices keep their own
cursors. What differs is the work of delivery: the chat service must look up the
sessions of every member and forward the message to the gateway of each one who is
online, which is the fan-out of chapter 15.

For groups of ordinary size, a few dozen or a few hundred members, this is done
directly. For very large groups, of tens of thousands, direct fan-out for every
message becomes as expensive as it was for the accounts with millions of followers in
chapter 15, and the same remedy applies. Devices are told only that the conversation
has new messages, or discover it when the conversation is opened, and then fetch from
their cursors.

A member who uses a phone, a tablet and a computer has 3 devices, each of which may
be online or offline independently, and each must show the complete conversation. This
too is already provided for, since every device has a cursor of its own and catches up
separately. A message sent from the phone reaches the member's own computer in the
same way that it reaches the other members, by being stored in the sequence and
delivered to every device that has not yet reached that number. The 1 thing that is
shared among a member's devices is the position up to which the member has read, so
that a conversation read on the phone is not shown as unread on the computer.

## Presence

Many applications show whether a contact is at present online, which is called
*presence*. It appears a small feature and is, relative to its importance, among the
most expensive.

The difficulty is one of fan-out. Whenever a member comes online or goes offline,
every contact who might be displaying that member's status must be informed, and with
phones connecting and disconnecting continually, a member with 500 contacts produces
500 notifications at each change of state. Across all members, the traffic in presence
updates can exceed the traffic in messages.

Services contain this in several ways. Presence is declared to be eventually
consistent, and a status that is some seconds out of date is accepted. Updates are
sent only to contacts who are themselves online and have the member in view, a device
subscribing to the presence of the contacts it is currently displaying and to no
others. And a brief disconnection is not announced at all: the service waits some
seconds before declaring a member offline, so that a phone which drops its connection
and restores it at once does not cause its owner to flicker in a thousand contact
lists.

The indication that someone is typing is handled in the same spirit. It is forwarded
to the other participants who are online and is stored nowhere, since if it is lost
nothing of value is lost with it.

## Storing messages

At 20 billion messages a day, the message store receives some 230000 writes a second
and grows by terabytes daily. Its pattern of access is, fortunately, very regular.
Messages are always appended to the end of a conversation and almost always read as a
range from the end of a conversation, the most recent 50, or everything after a
cursor.

The store is accordingly keyed by conversation and, within a conversation, by sequence
number, so that the messages of a conversation lie together in order and a request for
a range reads 1 contiguous run. It is divided among shards by a hash of the
conversation identifier, in the manner of chapter 1, so that each conversation resides
entirely on 1 shard and has 1 leader assigning its numbers. A very active conversation
becomes a hot key in the sense of chapter 9, and the shards must be small enough that
1 busy group cannot overwhelm its neighbours.

Recent messages are requested constantly and old ones hardly ever, since people
seldom scroll back more than a few days. The store can therefore keep recent messages
on fast storage and move older ones to cheaper media, as the object store of chapter
16 does with cold data.

## End-to-end encryption

In the design described, the service can read every message, since messages reach it
in a form it is able to store, index and search. Many chat services now offer
*end-to-end encryption*, in which a message is encrypted on the sender's device with
keys known only to the participants' devices and is decrypted only on the recipients'
devices. The service transports and stores ciphertext that it has no means of reading.

Nothing in the architecture of this chapter is thereby altered. The service still
numbers, stores, forwards and replays messages, which are now opaque to it. What
changes is everything that depended on the server's knowledge of the contents. The
server can no longer search messages, so search must be performed on each device over
its own copy. It cannot compose the text of a push notification, so the notification
carries ciphertext or a bare signal, and the device decrypts or fetches. A newly added
device cannot be given the history by the server in readable form, and must obtain the
means of reading it from another of the member's devices. The exchange and
verification of keys, which is the difficult part of such a scheme, is a subject for a
book on cryptography.

## Use cases

A member sends messages, receives them, and returns after absences of every length.

<figure>
<img src="figures/chat-use-cases.svg?v=53ad15c1" alt="A use case diagram of the chat service. Member: send a message (POST /v1/conversations/{id}/messages), catch up after being offline (GET ...?after=17), see who is online (GET /v1/members/{id}/presence).">
<figcaption><b>Figure 18.4</b> The actors and what each of them does.</figcaption>
</figure>

## Functional requirements

| No. | Functional requirement |
|---|---|
| 0 | A member can send a message to a conversation of 2 or more members. |
| 1 | A member who is online receives a message within 500 ms. |
| 2 | A member who was offline receives every missed message after reconnecting. |
| 3 | Messages in a conversation are shown in the same order to every member. |
| 4 | A message is shown once, even when it is delivered more than once. |

## Non-functional requirements

| No. | Property | Non-functional requirement |
|---|---|---|
| 0 | Durability | A message that the sender saw as sent is not lost. |
| 1 | Consistency | Strong within a conversation: 1 order of messages. Presence is eventual. |
| 2 | Availability | 99.95% for sending and receiving. |
| 3 | Scale | 50 million members online, and 20 billion messages per day. |

Order is the property that members perceive most directly, and so the sequence of
each conversation is strongly consistent. A message is confirmed to its sender only
when a majority of the replicas of the conversation's log has stored it under its
number, and no 2 replicas ever disagree about which message bears a given number.
Everything of secondary importance, presence, typing indications and read positions,
is eventually consistent, on the principle that it is better for these to be briefly
wrong than for the sending of messages to wait upon them.

## Core entities

<figure>
<img src="figures/chat-entities.svg?v=74a35f50" alt="The core entities. Message has the fields conversation u64, number u64, sender string, text string. Conversation has the fields id u64, members string[], last u64. Cursor has the fields member string, conversation u64, received u64. Every message has a number within its conversation. A Cursor records the last number a member&#x27;s device has received.">
<figcaption><b>Figure 18.5</b> The core entities and their fields.</figcaption>
</figure>

## Capacity estimate

<div class="estimate">

<img class="builder" src="art/crab-builder.svg" alt="A crab in a hard hat, in tears.">

**Arithmetic ahead.** 50 million open connections need about 500 gateway servers, and 20 billion messages per day are 230000 per second.

<a class="skip" href="#high-level-design">Skip to the high-level design</a>

<details>
<summary>Show the calculation</summary>

| Quantity | Calculation | Result |
|---|---|---|
| Connections per gateway | given | 100000 |
| Gateways | 50000000 ÷ 100000 | 500 |
| Messages per second | 20000000000 ÷ 86400 | 231000 |
| Storage per day | 20 billion × 200 bytes | 4 TB |

</details>

</div>

## The API

Sending a message and catching up are ordinary HTTP requests, shown below. Live
delivery takes place on the open connection, on which the server pushes each new
message as a small frame carrying the conversation, the number and the content.

**Send a message**

```http
POST /v1/conversations/301/messages HTTP/1.1
Host: chat.example
Idempotency-Key: phone-a-000512
Content-Type: application/json

{ "text": "are you coming?" }
```

```http
HTTP/1.1 201 Created
Content-Type: application/json

{ "number": 1, "time": "2026-10-14T09:00:00Z" }
```

The server chooses the number. The key lets the phone send again after a lost answer without creating a second message.

**Catch up after being offline**

```http
GET /v1/conversations/301/messages?after=1 HTTP/1.1
Host: chat.example
```

```http
HTTP/1.1 200 OK
Content-Type: application/json

{
  "messages": [
    { "number": 2, "sender": "bob", "text": "hello?" },
    { "number": 3, "sender": "bob", "text": "we are starting" },
    { "number": 4, "sender": "bob", "text": "table 4" }
  ]
}
```

`after=1` is the phone's cursor: the last number it has shown.

## High-level design

<figure class="wide">
<img src="figures/chat-design.svg?v=12795254" alt="Delivering a chat message. The components are Sender&#x27;s phone, Gateway A, Chat service, Message store, Gateway B, Receiver&#x27;s phone, Session store. Step 1: The sender&#x27;s phone sends the message over its connection. Step 2: The gateway passes it to the chat service. Step 3: The service gives it the next number and stores it. Step 4: It finds the receiver&#x27;s gateway and forwards the message. Step 5: The gateway pushes it to the receiver&#x27;s phone.">
<figcaption><b>Figure 18.6</b> The components and the path of a request. The steps are numbered.</figcaption>
</figure>

| Component | Role | State it holds | When 1 instance fails |
|---|---|---|---|
| Gateway | holds the open connections of many phones | connections, in memory | its phones reconnect to another gateway and catch up |
| Chat service | numbers and stores messages, and forwards them | none | another instance takes the requests |
| Message store | keeps every conversation's messages in order | messages, replicated | a follower takes over, as in chapter 4 |
| Session store | remembers which gateway each online member is connected to | sessions, in memory | phones re-register when they reconnect |

### One request, step by step

The steps follow the arrows of figure 18.6.

1. The sender's phone sends the message over the connection it keeps open to gateway A.
2. Gateway A passes the message to the chat service.
3. The chat service asks the message store to append it. The store gives it the next number of the conversation, and the sender is told that the message is sent.
4. The chat service looks up the receiver in the session store, finds gateway B, and forwards the message there. A receiver who is offline is skipped: the message waits in the store.
5. Gateway B pushes the message down the receiver's open connection.

## Mistakes to avoid

| Mistake | What goes wrong | What to do |
|---|---|---|
| Ordering messages by the sender's clock | Phones' clocks differ, and replies appear before the messages they answer. | Let the server number the messages of each conversation. |
| Displaying whatever arrives | A message that overtakes others appears out of order, and a repeat appears twice. | Display a message only if its number follows the last one shown. |
| Sending only new messages after a reconnection | Whatever was sent during the absence is never delivered. | Have the device report its cursor, and send everything after it. |
| Tracking on the server what each device has received | The server holds a great deal of state and still cannot know what was lost in transit. | Let each device keep its cursor and report it. |
| Storing every message the server receives | A retry after a lost confirmation is stored as a second message. | Have the phone attach an identifier, and store each identifier once. |
| Trusting the session store | A message is sent to a gateway where the phone no longer is, and is considered delivered. | Treat sessions as a hint, and rely on the stored sequence and the cursor. |
| Session entries without a time limit | A crashed gateway's phones appear connected indefinitely. | Give entries a lease that the gateway renews. |
| Reconnecting immediately after a gateway fails | Its phones overwhelm the remaining gateways. | Reconnect after a random, lengthening delay. |
| Relying on a push notification to deliver the message | Notifications are delayed and dropped, and messages with them. | Use the notification as a signal, and fetch from the cursor. |
| Announcing every change of presence to every contact | Presence traffic exceeds message traffic. | Inform only contacts who are watching, and wait before declaring someone offline. |
| Putting message logic in the gateways | Every deployment drops millions of connections. | Keep gateways minimal and deploy the logic separately. |

## Failures

| Failure | What users see | How the system recovers |
|---|---|---|
| The receiver is offline | the message arrives later | it waits in the message store until the phone reports its cursor |
| A gateway crashes | its phones show 'connecting' for a moment | they reconnect elsewhere and catch up from their cursors |
| The answer to a send is lost | the sender's phone sends again | the idempotency key returns the same message number |

## Trade-offs

| Decision | What it gains | What it costs |
|---|---|---|
| Open connections | messages arrive at once | servers hold 1 connection per online phone |
| Numbers per conversation | order, gaps and repeats are handled by 1 mechanism | every message goes through the store that assigns numbers |
| Storing every message | offline members catch up | storage grows with every message |

## The simulation

<div class="simulation">

**Simulation in the repository.** The program [`code/chatsim`](https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/distributed-systems-from-the-ground-up/code/chatsim/src/main.rs) simulates this design. To run it, clone the repository and type `cargo run --release -p chatsim` in the `code` directory.

</div>

## Terms introduced in this chapter

| Term | Meaning |
|---|---|
| Polling | asking at regular intervals whether anything has arrived |
| Long polling | asking, and having the server hold the request until it has an answer |
| WebSocket | a protocol for a connection that stays open, on which either side may send |
| Gateway | a server whose function is to hold many open connections |
| Session | the record that a device is connected to a particular gateway |
| Conversation | a set of members and the ordered messages exchanged among them |
| Sequence number | the position of a message in its conversation, assigned by the server |
| Cursor | the number of the last message a device has received or displayed |
| Catching up | fetching every message after a device's cursor |
| Sent, delivered, read | stored by the server, received by a device, and displayed to the recipient |
| Presence | whether a member is currently online |
| End-to-end encryption | encryption between the participants' devices, which the service cannot undo |

<div class="summary">

## Summary

- A phone keeps 1 connection open, so that the server can deliver a message the moment it arrives.
- Gateways hold the connections, and a session store records which gateway each device is on, as a hint that may be wrong.
- The server assigns every message the next number of its conversation, and that numbering is the order for everyone.
- A device displays a message only if its number follows the last one displayed, which handles gaps, disorder and repetition alike.
- After any absence, a device reports its cursor and receives everything after it, and the server keeps no record of deliveries.
- A message carries an identifier chosen by the sending phone, so that a retry is stored once.
- Push notifications call the user back, and the stored sequence and the cursor do the delivering.
- The sequence is strongly consistent, and presence and read positions are eventually consistent.

</div>
