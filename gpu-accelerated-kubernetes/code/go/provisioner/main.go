// Command provisioner models a controller that asks a provider for machines
// until a pool has the size its owner asked for.
//
// The provider's create call can fail in an awkward way: the machine is
// created and the reply is lost. The program runs the same controller twice.
// The first run retries a lost reply with a plain create call. The second
// sends a client token with every call, so a retry returns the machine that
// the first attempt created.
//
// Run it from code/go with:
//
//	go run ./provisioner
package main

import (
	"errors"
	"fmt"
)

// ANCHOR: provider
// Machine is one machine the provider has created.
type Machine struct {
	// ID is the provider's identifier for the machine.
	ID string
	// Model is the kind of machine.
	Model string
	// Token is the client token of the call that created it, or "".
	Token string
}

// Errors a create call can return.
var (
	// ErrTimeout means no reply arrived. The machine may or may not exist.
	ErrTimeout = errors.New("timed out")
	// ErrQuota means the account already holds as many machines of this model
	// as it is allowed.
	ErrQuota = errors.New("quota exceeded")
)

// Provider is the account that machines are created in.
type Provider struct {
	// quota is the number of machines of each model the account may hold.
	quota map[string]int
	// machines lists every machine that exists, in creation order.
	machines []Machine
	// calls counts create calls, so the run can lose the reply to one of them.
	calls int
	// loseReply is the number of the call whose reply is lost.
	loseReply int
}

// count returns how many machines of a model exist.
func (p *Provider) count(model string) int {
	n := 0
	for _, m := range p.machines {
		if m.Model == model {
			n++
		}
	}
	return n
}

// Create makes one machine. A call that carries a token already used by an
// existing machine returns that machine and creates nothing.
func (p *Provider) Create(model, token string) (Machine, error) {
	p.calls++
	if token != "" {
		for _, m := range p.machines {
			if m.Token == token {
				return m, nil
			}
		}
	}
	if p.count(model) >= p.quota[model] {
		return Machine{}, ErrQuota
	}
	m := Machine{ID: fmt.Sprintf("m-%02d", len(p.machines)+1), Model: model, Token: token}
	p.machines = append(p.machines, m)
	if p.calls == p.loseReply {
		return Machine{}, ErrTimeout
	}
	return m, nil
}

// ANCHOR_END: provider

// ANCHOR: controller
// Pool is a group of identical machines and the size its owner wants.
type Pool struct {
	// Name prefixes the name of each slot: thor-1, thor-2, and so on.
	Name string
	// Model is the kind of machine in the pool.
	Model string
	// Want is the number of machines the pool should have.
	Want int
}

// Controller brings each pool to its wanted size.
type Controller struct {
	provider *Provider
	// tokens says whether create calls carry a client token.
	tokens bool
	// owned maps a pool's name to the machines the controller knows it has.
	owned map[string][]Machine
}

// Reconcile fills the empty slots of one pool, in order, and stops at the
// first call that fails. It returns true when the pool is full.
func (c *Controller) Reconcile(pool Pool) bool {
	for len(c.owned[pool.Name]) < pool.Want {
		slot := fmt.Sprintf("%s-%d", pool.Name, len(c.owned[pool.Name])+1)
		token := ""
		if c.tokens {
			token = slot
		}
		m, err := c.provider.Create(pool.Model, token)
		if err != nil {
			fmt.Printf("    %-8s create failed: %v\n", slot, err)
			return false
		}
		fmt.Printf("    %-8s is machine %s\n", slot, m.ID)
		c.owned[pool.Name] = append(c.owned[pool.Name], m)
	}
	return true
}

// ANCHOR_END: controller

// ANCHOR: run
// pools is the fleet we ask for: the Thors on the shelf and the two Sparks.
var pools = []Pool{
	{"thor", "Jetson AGX Thor", 5},
	{"spark", "DGX Spark", 2},
}

// run reconciles every pool for three passes and then compares what the
// controller owns with what the provider holds.
func run(tokens bool) {
	provider := &Provider{quota: map[string]int{"Jetson AGX Thor": 5, "DGX Spark": 2}, loseReply: 3}
	c := &Controller{provider: provider, tokens: tokens, owned: map[string][]Machine{}}
	for pass := 1; pass <= 3; pass++ {
		fmt.Printf("  pass %d\n", pass)
		full := true
		for _, pool := range pools {
			full = c.Reconcile(pool) && full
		}
		if full {
			fmt.Println("    every pool is full")
			break
		}
	}
	known := map[string]bool{}
	for _, pool := range pools {
		for _, m := range c.owned[pool.Name] {
			known[m.ID] = true
		}
		fmt.Printf("  %-5s wanted %d, controller owns %d, provider holds %d\n",
			pool.Name, pool.Want, len(c.owned[pool.Name]), provider.count(pool.Model))
	}
	for _, m := range provider.machines {
		if !known[m.ID] {
			fmt.Printf("  machine %s (%s) is running and belongs to no pool\n", m.ID, m.Model)
		}
	}
}

func main() {
	fmt.Println("create calls without a client token:")
	run(false)
	fmt.Println("create calls with the slot name as the client token:")
	run(true)
}

// ANCHOR_END: run
