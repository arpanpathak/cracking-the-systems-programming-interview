// Command sigfacts measures signal handling from outside a process. It starts
// shell scripts that set signal dispositions, sends them signals, and reads
// their signal masks from /proc/<pid>/status.
//
// Run it from code/go with:
//
//	go run ./sigfacts
package main

// ANCHOR: imports
import (
	"bufio"
	"fmt"
	"io"
	"log"
	"os"
	"os/exec"
	"strconv"
	"strings"
	"syscall"
	"time"
)

// ANCHOR_END: imports

// ANCHOR: proc
// mask returns one of the signal masks in /proc/<pid>/status: ShdPnd
// (pending), SigBlk (blocked), SigIgn (ignored) or SigCgt (caught).
func mask(pid int, name string) (uint64, error) {
	status, err := os.Open(fmt.Sprintf("/proc/%d/status", pid))

	if err != nil {
		return 0, err
	}

	defer status.Close()

	for lines := bufio.NewScanner(status); lines.Scan(); {
		if value, ok := strings.CutPrefix(lines.Text(), name+":"); ok {
			return strconv.ParseUint(strings.TrimSpace(value), 16, 64)
		}
	}

	return 0, fmt.Errorf("%s: not in /proc/%d/status", name, pid)
}

// has reports whether a mask contains a signal. Signal n is bit n-1.
func has(mask uint64, signal syscall.Signal) bool {
	return mask&(1<<(signal-1)) != 0
}

// await polls /proc/<pid>/stat until the process has the given command name
// and state. State T is "stopped" and S is "sleeping".
func await(pid int, command string, state byte) error {
	want := fmt.Sprintf("(%s) %c", command, state)

	for {
		stat, err := os.ReadFile(fmt.Sprintf("/proc/%d/stat", pid))

		if err != nil {
			return err
		}

		if strings.Contains(string(stat), want) {
			return nil
		}

		time.Sleep(time.Millisecond)
	}
}

// ANCHOR_END: proc

// ANCHOR: pending
// pending sends SIGUSR1 3 times to a stopped process that has a handler for
// it, reads the pending mask, and counts how often the handler runs after
// the process continues.
func pending() error {
	child := exec.Command("sh", "-c", `trap 'echo caught' USR1; kill -STOP $$; echo done`)
	stdout, err := child.StdoutPipe()

	if err != nil {
		return err
	}

	if err := child.Start(); err != nil {
		return err
	}

	pid := child.Process.Pid

	if err := await(pid, "sh", 'T'); err != nil {
		return err
	}

	for range 3 {
		syscall.Kill(pid, syscall.SIGUSR1)
	}

	waiting, err := mask(pid, "ShdPnd")

	if err != nil {
		return err
	}

	syscall.Kill(pid, syscall.SIGCONT)

	text, err := io.ReadAll(stdout)

	if err != nil {
		return err
	}

	fmt.Printf("SIGUSR1 sent 3 times to a stopped process: pending mask %#x\n", waiting)
	fmt.Printf("after SIGCONT the handler ran %d time(s)\n", strings.Count(string(text), "caught"))

	return child.Wait()
}

// ANCHOR_END: pending

// ANCHOR: dispositions
// dispositions reads the ignored and caught masks of a shell that ignores
// SIGINT and handles SIGUSR1.
func dispositions() error {
	child := exec.Command("sh", "-c", `trap '' INT; trap 'echo caught' USR1; kill -STOP $$`)

	if err := child.Start(); err != nil {
		return err
	}

	defer child.Wait()
	defer child.Process.Kill()

	pid := child.Process.Pid

	if err := await(pid, "sh", 'T'); err != nil {
		return err
	}

	ignored, err := mask(pid, "SigIgn")

	if err != nil {
		return err
	}

	caught, err := mask(pid, "SigCgt")

	if err != nil {
		return err
	}

	fmt.Printf("shell with 2 traps: SIGINT ignored %v, SIGUSR1 caught %v, SIGTERM ignored %v\n",
		has(ignored, syscall.SIGINT), has(caught, syscall.SIGUSR1), has(ignored, syscall.SIGTERM))

	return nil
}

// ANCHOR_END: dispositions

// ANCHOR: exec
// acrossExec reads the masks of a process after exec, sends it a signal it
// ignores, and then SIGKILL.
func acrossExec() error {
	child := exec.Command("sh", "-c", `trap '' TERM; trap 'echo caught' USR1; exec sleep 30`)

	if err := child.Start(); err != nil {
		return err
	}

	pid := child.Process.Pid

	if err := await(pid, "sleep", 'S'); err != nil {
		return err
	}

	ignored, err := mask(pid, "SigIgn")

	if err != nil {
		return err
	}

	caught, err := mask(pid, "SigCgt")

	if err != nil {
		return err
	}

	fmt.Printf("after exec: SIGTERM ignored %v, SIGUSR1 caught %v\n",
		has(ignored, syscall.SIGTERM), has(caught, syscall.SIGUSR1))

	syscall.Kill(pid, syscall.SIGTERM)
	syscall.Kill(pid, syscall.SIGKILL)
	child.Wait()

	if status, ok := child.ProcessState.Sys().(syscall.WaitStatus); ok && status.Signaled() {
		fmt.Printf("SIGTERM, then SIGKILL: killed by signal %d\n", status.Signal())
	}

	return nil
}

// ANCHOR_END: exec

func main() {
	for _, experiment := range []func() error{pending, dispositions, acrossExec} {
		if err := experiment(); err != nil {
			log.Fatal(err)
		}
	}
}
