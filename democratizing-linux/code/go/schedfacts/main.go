// Command schedfacts measures how the scheduler divides a CPU between busy
// processes of different nice values. It starts the processes on the same
// CPU, lets them compete, and reads the CPU time each one received.
//
// Run it from code/go with:
//
//	go run ./schedfacts
package main

// ANCHOR: imports
import (
	"fmt"
	"log"
	"os"
	"os/exec"
	"strconv"
	"strings"
	"time"
)

// ANCHOR_END: imports

// ANCHOR: spin
// spin starts a busy shell loop, restricted to CPU 0 and with
// the given nice value.
func spin(nice int) (*exec.Cmd, error) {
	child := exec.Command("taskset", "-c", "0", "nice", "-n", strconv.Itoa(nice), "sh", "-c", "while :; do :; done")

	return child, child.Start()
}

// cpuTime returns the CPU time a process has used, in clock ticks: fields 14
// and 15 of /proc/<pid>/stat, the time in user mode and in kernel mode.
func cpuTime(pid int) (int, error) {
	stat, err := os.ReadFile(fmt.Sprintf("/proc/%d/stat", pid))

	if err != nil {
		return 0, err
	}

	fields := strings.Fields(string(stat[strings.LastIndexByte(string(stat), ')')+1:]))

	if len(fields) < 13 {
		return 0, fmt.Errorf("/proc/%d/stat: too few fields", pid)
	}

	var user, kernel int

	if _, err := fmt.Sscan(fields[11], &user); err != nil {
		return 0, err
	}

	if _, err := fmt.Sscan(fields[12], &kernel); err != nil {
		return 0, err
	}

	return user + kernel, nil
}

// ANCHOR_END: spin

// ANCHOR: share
// stop ends a busy process and collects it.
func stop(child *exec.Cmd) {
	child.Process.Kill()
	child.Wait()
}

// share lets a process of nice 0 and a process of the given nice value
// compete for CPU 0 for 2 seconds and prints the share of CPU time each
// received, rounded to the nearest 5%.
func share(nice int) error {
	first, err := spin(0)

	if err != nil {
		return err
	}

	defer stop(first)

	second, err := spin(nice)

	if err != nil {
		return err
	}

	defer stop(second)

	time.Sleep(2 * time.Second)

	a, err := cpuTime(first.Process.Pid)

	if err != nil {
		return err
	}

	b, err := cpuTime(second.Process.Pid)

	if err != nil {
		return err
	}

	percent := (200*a/(a+b) + 5) / 10 * 5
	fmt.Printf("nice 0 and nice %d on 1 CPU: %d%% and %d%%\n", nice, percent, 100-percent)

	return nil
}

// ANCHOR_END: share

func main() {
	for _, nice := range []int{0, 5, 10} {
		if err := share(nice); err != nil {
			log.Fatal(err)
		}
	}
}
