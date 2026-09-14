# 5. Networking: Sockets to the Wire {#networking-sockets-to-wire}

A Kubernetes Service is a set of iptables or eBPF rules sitting on top of the
same socket and netfilter machinery every Linux network program already uses.
Nothing about "cluster networking" is a separate stack; it is sockets,
netfilter, and network namespaces, composed by controllers that write rules on
a node's behalf. This chapter goes from a single socket up to the Pod network
namespace those controllers manage.

## Sockets and TCP

A socket is an endpoint identified by an IP address and port. `socket()`
creates it, `bind()` assigns an address, `listen()` marks it passive,
`accept()` returns a newly connected socket, and `connect()` initiates an
outbound connection. `ss` is the modern way to inspect sockets:

```bash
ss -tulpn
ss -tan state established
ss -tnp | grep :443
```

The TCP state machine for a server-side connection runs
`LISTEN → SYN_RECV → ESTABLISHED → FIN_WAIT/CLOSE_WAIT → ...`. Two states are
worth knowing on sight. `CLOSE_WAIT` means the remote side closed the
connection but the local application has not yet closed its socket; a large
count usually means the application forgot to close something. `TIME_WAIT` is
normal after an active close, and exists so delayed packets can expire; a
large `TIME_WAIT` count is not automatically a problem unless ephemeral ports
or socket descriptors are actually being exhausted. `somaxconn`, the backlog,
limits how many pending connections the kernel will queue before `accept()`
catches up.

## The packet path through a Linux host

Outbound, a packet moves from the application through the socket buffer, the
TCP/IP stack, routing, netfilter (`iptables`/`nftables`), the neighbor/ARP
layer, the NIC driver, and onto the wire. Inbound, the NIC DMAs packets into
ring buffers and raises an interrupt, or the kernel polls via NAPI; the kernel
then parses headers, runs netfilter's prerouting hooks, and either forwards
the packet or delivers it to a socket.

## Netfilter, conntrack, iptables, and nftables

Netfilter hooks are the kernel's interception points for packet filtering and
NAT. `iptables` manages tables, `filter`, `nat`, `mangle`, `raw`, and chains
within them. `conntrack` tracks connection state, which is what makes a rule
like `-m conntrack --ctstate ESTABLISHED,RELATED` possible.

In a Kubernetes cluster, a Service running kube-proxy in iptables mode
performs DNAT to a selected Pod IP; `ClusterIP` traffic is NATed on the way in
and un-NATed on the way back out through conntrack. NetworkPolicy is often
implemented by the CNI plugin, Calico or Cilium, using iptables or eBPF, and
Cilium in particular can bypass iptables entirely and use eBPF for both
service load balancing and policy enforcement.

```bash
iptables -L -n -v
iptables -t nat -L -n -v
conntrack -L | head
nft list ruleset | head
```

## Network namespaces, veth pairs, bridges, and CNI

Each Kubernetes Pod usually gets its own network namespace. The CNI plugin
sets it up: it creates a veth pair, puts one end inside the Pod's network
namespace, attaches the other end to a bridge, an Open vSwitch instance, or a
routing/encapsulation device on the host, assigns an IP address, usually from
the node's Pod CIDR, adds routes and any policy, and reports the interface and
IP configuration back to the kubelet.

```text
Pod netns                    Host netns
┌─────────────┐ veth         ┌─────────────────────────┐
│ eth0        ├─────────────►│ vethXXX ──► cni0/bridge │
│ 10.244.1.5  │              │           │             │
└─────────────┘              │         eth0            │
                             └─────────────────────────┘
```

`localhost` inside a Pod resolves only within that Pod's network namespace,
not the node's, which is why containers in the same Pod can reach each other
over `localhost` while containers in different Pods cannot.

## DNS

Pods use CoreDNS, or another cluster DNS service. Resolution inside a Pod
first consults `/etc/resolv.conf`, which points at the cluster DNS endpoint,
and search domains let short service names resolve without a fully qualified
name. Two problems recur: host-networked Pods that bypass the cluster DNS
configuration entirely, and `ndots:5`, which causes a name with fewer than
five dots to be tried against every search domain before the literal name is
tried, generating extra queries for every external lookup.

## References

- Stevens, Fenner & Rudoff, *Unix Network Programming*, Volume 1, for the
  socket API.
- The `iptables(8)`, `nft(8)`, and `conntrack(8)` man pages.
- The Kubernetes documentation on cluster networking and the CNI
  specification, for the veth/bridge sequence this chapter follows.
