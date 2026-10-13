// Command sigmodel models the signal state the kernel keeps for a process: a
// pending mask, a blocked mask, and an action for each signal. It separates
// sending a signal from delivering it, and shows what a delivered signal
// does to a process that is blocked in a system call.
//
// Run it from code/go with:
//
//	go run ./sigmodel
package main

// ANCHOR: imports
import (
	"errors"
	"fmt"
	"log"
)

// ANCHOR_END: imports

// ANCHOR: state
const (
	sigKill = 9
	sigUsr1 = 10
	sigTerm = 15
	sigChld = 17
	sigLast = 64
)

type action int

const (
	byDefault action = iota
	ignore
	handle
)

var errInvalid = errors.New("EINVAL")

// A process holds the signal state of one process. Signal n is bit n-1 of
// the masks.
type process struct {
	pending  uint64
	blocked  uint64
	actions  [sigLast + 1]action
	restart  [sigLast + 1]bool
	handled  int
	killedBy int

	// call is the system call the process is blocked in, or "" when it is
	// running. outcome records what a signal did to that call.
	call    string
	outcome string
}

func bit(signal int) uint64 {
	return 1 << (signal - 1)
}

// ANCHOR_END: state

// ANCHOR: control
// setAction installs an action for a signal. restart is the SA_RESTART flag
// of a handler. The action of SIGKILL cannot be changed.
func (p *process) setAction(signal int, a action, restart bool) error {
	if signal == sigKill {
		return errInvalid
	}

	p.actions[signal], p.restart[signal] = a, restart

	return nil
}

// block adds signals to the blocked mask. SIGKILL is removed from the
// request without an error, as the kernel does.
func (p *process) block(mask uint64) {
	p.blocked |= mask &^ bit(sigKill)
}

// unblock removes signals from the blocked mask and delivers what was
// waiting for it.
func (p *process) unblock(mask uint64) {
	p.blocked &^= mask
	p.deliver()
}

// ANCHOR_END: control

// ANCHOR: send
// ignored reports whether a signal would be discarded on delivery: its
// action is ignore, or its action is the default and the default is to
// ignore, which is the case for SIGCHLD.
func (p *process) ignored(signal int) bool {
	return p.actions[signal] == ignore || p.actions[signal] == byDefault && signal == sigChld
}

// send is the sender's half. It discards a signal that the target ignores
// and does not block. Otherwise it sets the pending bit, which is already
// set when the same signal is waiting.
func (p *process) send(signal int) {
	if p.ignored(signal) && p.blocked&bit(signal) == 0 {
		return
	}

	p.pending |= bit(signal)
}

// ANCHOR_END: send

// ANCHOR: deliver
// deliver is the target's half. The kernel runs it when the process is about
// to return to user mode. It takes each pending signal that is not blocked,
// lowest number first, and performs its action.
func (p *process) deliver() {
	for signal := 1; signal <= sigLast && p.killedBy == 0; signal++ {
		if p.pending&^p.blocked&bit(signal) == 0 {
			continue
		}

		p.pending &^= bit(signal)

		switch {
		case p.actions[signal] == handle:
			p.handled++
			p.interrupt(signal)

		case !p.ignored(signal):
			p.killedBy = signal
		}
	}
}

// interrupt decides what happens to a blocking system call when a handler
// has run: the call is restarted, or it fails with EINTR.
func (p *process) interrupt(signal int) {
	if p.call == "" {
		return
	}

	if p.restart[signal] {
		p.outcome = "the " + p.call + " is restarted"

		return
	}

	p.outcome = "the " + p.call + " fails with EINTR"
	p.call = ""
}

// ANCHOR_END: deliver

// ANCHOR: trace
func coalescing() error {
	p := &process{}

	if err := p.setAction(sigUsr1, handle, false); err != nil {
		return err
	}

	p.block(bit(sigUsr1))

	for range 3 {
		p.send(sigUsr1)
		p.deliver()
	}

	fmt.Printf("SIGUSR1 blocked and sent 3 times: pending mask %#x\n", p.pending)

	p.unblock(bit(sigUsr1))
	fmt.Printf("after unblocking the handler ran %d time(s)\n", p.handled)

	return nil
}

func ignoring() error {
	p := &process{}

	if err := p.setAction(sigTerm, ignore, false); err != nil {
		return err
	}

	p.send(sigTerm)
	fmt.Printf("SIGTERM ignored and sent: pending mask %#x\n", p.pending)

	fmt.Printf("installing a handler for SIGKILL: %v\n", p.setAction(sigKill, handle, false))

	p.block(^uint64(0))
	p.send(sigKill)
	p.deliver()
	fmt.Printf("every signal blocked, SIGKILL sent: killed by signal %d\n", p.killedBy)

	return nil
}

func interrupting(restart bool) error {
	p := &process{call: "read"}

	if err := p.setAction(sigUsr1, handle, restart); err != nil {
		return err
	}

	p.send(sigUsr1)
	p.deliver()
	fmt.Printf("handler runs during a blocking read, SA_RESTART %v: %s\n", restart, p.outcome)

	return nil
}

func main() {
	steps := []func() error{
		coalescing,
		ignoring,
		func() error { return interrupting(false) },
		func() error { return interrupting(true) },
	}

	for _, step := range steps {
		if err := step(); err != nil {
			log.Fatal(err)
		}
	}
}

// ANCHOR_END: trace
