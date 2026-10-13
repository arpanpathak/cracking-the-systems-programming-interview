// Command procfacts measures the life cycle of a process: who its parent is,
// how its termination is reported, what exec keeps, what remains of a child
// that has exited and has not been waited for, and who becomes the parent of
// an orphan.
//
// Run it from code/go with:
//
//	go run ./procfacts
package main

// ANCHOR: imports
import (
	"errors"
	"fmt"
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
// field returns one field of /proc/<pid>/stat, counted from 1. The second
// field, the command name, is in parentheses and may contain spaces, so the
// fields after it are counted from the closing parenthesis.
func field(pid, n int) (string, error) {
	stat, err := os.ReadFile(fmt.Sprintf("/proc/%d/stat", pid))

	if err != nil {
		return "", err
	}

	end := strings.LastIndexByte(string(stat), ')')
	rest := strings.Fields(string(stat[end+1:]))

	return rest[n-3], nil
}

// output runs a shell command and returns what it printed, without the final
// newline.
func output(script string) (string, error) {
	text, err := exec.Command("sh", "-c", script).Output()

	return strings.TrimSpace(string(text)), err
}

// ANCHOR_END: proc

// ANCHOR: parent
// parent asks a child for the number of its parent process.
func parent() error {
	text, err := output("echo $PPID")

	if err != nil {
		return err
	}

	fmt.Printf("the child's parent is this process: %v\n", text == strconv.Itoa(os.Getpid()))

	return nil
}

// ANCHOR_END: parent

// ANCHOR: status
// status runs a script and reports how it terminated.
func status(script string) error {
	err := exec.Command("sh", "-c", script).Run()

	var exit *exec.ExitError

	if !errors.As(err, &exit) {
		return fmt.Errorf("%s: %v", script, err)
	}

	wait, ok := exit.Sys().(syscall.WaitStatus)

	switch {
	case ok && wait.Signaled():
		fmt.Printf("%s: killed by signal %d\n", script, wait.Signal())
	default:
		fmt.Printf("%s: exited with status %d\n", script, exit.ExitCode())
	}

	return nil
}

// ANCHOR_END: status

// ANCHOR: exec
// execKeepsPid prints the process number of a shell before and after the
// shell replaces its program with exec.
func execKeepsPid() error {
	text, err := output(`echo $$; exec sh -c 'echo $$'`)

	if err != nil {
		return err
	}

	pids := strings.Fields(text)

	fmt.Printf("pid before and after exec: equal %v\n", len(pids) == 2 && pids[0] == pids[1])

	return nil
}

// ANCHOR_END: exec

// ANCHOR: zombie
// zombie starts a child that exits at once, and reads its state before and
// after waiting for it.
func zombie() error {
	child := exec.Command("true")

	if err := child.Start(); err != nil {
		return err
	}

	pid := child.Process.Pid
	state, err := field(pid, 3)

	for err == nil && state != "Z" {
		time.Sleep(time.Millisecond)
		state, err = field(pid, 3)
	}

	if err != nil {
		return err
	}

	if err := child.Wait(); err != nil {
		return err
	}

	_, err = os.Stat(fmt.Sprintf("/proc/%d", pid))

	fmt.Printf("exited child: state %s before wait, /proc entry present after wait: %v\n", state, err == nil)

	return nil
}

// ANCHOR_END: zombie

// ANCHOR: orphan
// orphan starts a shell that starts a background sleep and exits. The sleep
// outlives its parent, and the kernel gives it a new one.
func orphan() error {
	text, err := output("sleep 30 >/dev/null 2>&1 & echo $!")

	if err != nil {
		return err
	}

	pid, err := strconv.Atoi(text)

	if err != nil {
		return err
	}

	defer syscall.Kill(pid, syscall.SIGKILL)

	adopter, err := field(pid, 4)

	if err != nil {
		return err
	}

	name, err := os.ReadFile("/proc/" + adopter + "/comm")

	if err != nil {
		return err
	}

	fmt.Printf("orphan adopted by: %s\n", strings.TrimSpace(string(name)))

	return nil
}

// ANCHOR_END: orphan

func main() {
	experiments := []func() error{
		parent,
		func() error { return status("exit 7") },
		func() error { return status("exit 300") },
		func() error { return status("kill -TERM $$") },
		execKeepsPid,
		zombie,
		orphan,
	}

	for _, experiment := range experiments {
		if err := experiment(); err != nil {
			log.Fatal(err)
		}
	}
}
