// Command cgfacts measures control groups. It creates a group below the one
// it runs in, starts shell commands inside the new group, and observes the
// kernel counting their processes, refusing a fork beyond pids.max, and
// ending a process that exceeds memory.max.
//
// Run it from code/go with:
//
//	go run ./cgfacts
package main

// ANCHOR: imports
import (
	"bufio"
	"errors"
	"fmt"
	"log"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"syscall"
	"time"
)

// ANCHOR_END: imports

// ANCHOR: files
// A group is the directory of a control group under /sys/fs/cgroup.
type group string

// set writes a value to one of the group's control files.
func (g group) set(file, value string) error {
	return os.WriteFile(filepath.Join(string(g), file), []byte(value), 0)
}

// get reads one of the group's control files.
func (g group) get(file string) (string, error) {
	text, err := os.ReadFile(filepath.Join(string(g), file))

	return strings.TrimSpace(string(text)), err
}

// event returns the counter with the given key from a file of "key value"
// lines, such as pids.events and memory.events.
func (g group) event(file, key string) (string, error) {
	text, err := g.get(file)

	if err != nil {
		return "", err
	}

	for lines := bufio.NewScanner(strings.NewReader(text)); lines.Scan(); {
		if fields := strings.Fields(lines.Text()); len(fields) == 2 && fields[0] == key {
			return fields[1], nil
		}
	}

	return "", fmt.Errorf("%s: no line %q", file, key)
}

// ANCHOR_END: files

// ANCHOR: create
// create makes a new group. It goes up from the group of this process to the
// nearest group that distributes the memory and pids controllers to its
// children, and creates a directory there.
func create() (group, error) {
	line, err := os.ReadFile("/proc/self/cgroup")

	if err != nil {
		return "", err
	}

	_, path, _ := strings.Cut(strings.TrimSpace(string(line)), "::")

	for dir := filepath.Join("/sys/fs/cgroup", path); dir != "/sys/fs/cgroup"; dir = filepath.Dir(dir) {
		enabled, err := group(dir).get("cgroup.subtree_control")

		if err != nil || !strings.Contains(enabled, "memory") || !strings.Contains(enabled, "pids") {
			continue
		}

		created := filepath.Join(dir, fmt.Sprintf("cgfacts-%d", os.Getpid()))

		return group(created), os.Mkdir(created, 0o755)
	}

	return "", errors.New("no parent group delegates the memory and pids controllers")
}

// command returns a shell script that will run in the group. The shell
// first moves itself into the group by writing its own process number to
// cgroup.procs, and every process it starts afterwards is created there.
func (g group) command(script string) *exec.Cmd {
	return exec.Command("sh", "-c", `echo $$ > "$0/cgroup.procs" && `+script, string(g))
}

// remove ends every process left in the group, waits until the group is
// empty, and deletes it.
func (g group) remove() error {
	if err := g.set("cgroup.kill", "1"); err != nil {
		return err
	}

	for {
		current, err := g.get("pids.current")

		if err != nil {
			return err
		}

		if current == "0" {
			return os.Remove(string(g))
		}

		time.Sleep(time.Millisecond)
	}
}

// ANCHOR_END: create

// ANCHOR: count
// count starts a process in the group and reads the group's process count.
func count(g group) error {
	child := g.command("exec sleep 30")

	if err := child.Start(); err != nil {
		return err
	}

	current, err := g.get("pids.current")

	for err == nil && current != "1" {
		time.Sleep(time.Millisecond)
		current, err = g.get("pids.current")
	}

	child.Process.Kill()
	child.Wait()

	if err != nil {
		return err
	}

	fmt.Printf("a process moved into the new group: pids.current %s\n", current)

	return nil
}

// ANCHOR_END: count

// ANCHOR: pids
// limitPids sets pids.max to 4 and runs a shell that tries to start 6
// background commands and prints a line for each one it started.
func limitPids(g group) error {
	if err := g.set("pids.max", "4"); err != nil {
		return err
	}

	started, _ := g.command("for i in 1 2 3 4 5 6; do sleep 1 & echo started; done 2>/dev/null").Output()
	refused, err := g.event("pids.events", "max")

	if err != nil {
		return err
	}

	fmt.Printf("pids.max 4, a shell starts background commands: started %d, forks refused %s\n",
		strings.Count(string(started), "started"), refused)

	return g.set("pids.max", "max")
}

// ANCHOR_END: pids

// ANCHOR: memory
// limitMemory sets memory.max to 32 MiB with no swap and runs a command
// whose memory grows without bound.
func limitMemory(g group) error {
	if err := g.set("memory.max", "33554432"); err != nil {
		return err
	}

	if err := g.set("memory.swap.max", "0"); err != nil {
		return err
	}

	child := g.command("exec tail /dev/zero")
	child.Run()

	kills, err := g.event("memory.events", "oom_kill")

	if err != nil {
		return err
	}

	if status, ok := child.ProcessState.Sys().(syscall.WaitStatus); ok && status.Signaled() {
		fmt.Printf("memory.max 32 MiB, a command that grows without bound: killed by signal %d, oom_kill %s\n",
			status.Signal(), kills)
	}

	return nil
}

// ANCHOR_END: memory

func run() error {
	g, err := create()

	if err != nil {
		return err
	}

	for _, experiment := range []func(group) error{count, limitPids, limitMemory} {
		if err := experiment(g); err != nil {
			g.remove()

			return err
		}
	}

	return g.remove()
}

func main() {
	if err := run(); err != nil {
		log.Fatal(err)
	}
}
