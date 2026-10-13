// Command nsfacts measures namespaces. It compares the namespaces of a
// process with those of an ordinary child, and then starts a child in new
// user, UTS and PID namespaces and reports what that child sees.
//
// Run it from code/go with:
//
//	go run ./nsfacts
package main

// ANCHOR: imports
import (
	"bufio"
	"errors"
	"fmt"
	"log"
	"os"
	"os/exec"
	"strings"
	"syscall"

	"golang.org/x/sys/unix"
)

// ANCHOR_END: imports

// ANCHOR: identity
// kinds are the namespace types of Linux 5.15, as named under /proc/<pid>/ns.
var kinds = []string{"cgroup", "ipc", "mnt", "net", "pid", "time", "user", "uts"}

// namespaces returns the identity of each namespace of a process. The kernel
// shows it as the target of a symbolic link, such as "uts:[4026531838]".
// Processes are in the same namespace when the targets are equal.
func namespaces(pid string) (map[string]string, error) {
	ids := map[string]string{}

	for _, kind := range kinds {
		id, err := os.Readlink("/proc/" + pid + "/ns/" + kind)

		if err != nil {
			return nil, err
		}

		ids[kind] = id
	}

	return ids, nil
}

// ANCHOR_END: identity

// ANCHOR: inside
// name returns the symbolic name of a system call error, such as EPERM.
func name(err error) string {
	var errno unix.Errno

	if errors.As(err, &errno) {
		return unix.ErrnoName(errno)
	}

	return fmt.Sprint(err)
}

// inside runs in the child. It tries to change the host name, and prints
// what it sees as key=value lines for the parent to read.
func inside() error {
	outcome := "succeeds"

	if err := unix.Sethostname([]byte("box")); err != nil {
		outcome = "fails with " + name(err)
	}

	host, err := os.Hostname()

	if err != nil {
		return err
	}

	ids, err := namespaces("self")

	if err != nil {
		return err
	}

	uidMap, err := os.ReadFile("/proc/self/uid_map")

	if err != nil {
		return err
	}

	fmt.Printf("sethostname=%s\nhostname=%s\npid=%d\nuid=%d\n", outcome, host, os.Getpid(), os.Getuid())
	fmt.Printf("map=%s\nuts=%s\npidns=%s\n", strings.Join(strings.Fields(string(uidMap)), " "), ids["uts"], ids["pid"])

	return nil
}

// ANCHOR_END: inside

// ANCHOR: start
// report runs this program again as a child and returns the lines the child
// prints, as a map. With isolate set, the child is created in new user, UTS
// and PID namespaces, and user 0 inside is mapped to the current user.
func report(isolate bool) (map[string]string, error) {
	child := exec.Command("/proc/self/exe", "inside")
	child.Stderr = os.Stderr

	if isolate {
		child.SysProcAttr = &syscall.SysProcAttr{
			Cloneflags:  syscall.CLONE_NEWUSER | syscall.CLONE_NEWUTS | syscall.CLONE_NEWPID,
			UidMappings: []syscall.SysProcIDMap{{ContainerID: 0, HostID: os.Getuid(), Size: 1}},
			GidMappings: []syscall.SysProcIDMap{{ContainerID: 0, HostID: os.Getgid(), Size: 1}},
		}
	}

	output, err := child.Output()

	if err != nil {
		return nil, err
	}

	seen := map[string]string{}

	for lines := bufio.NewScanner(strings.NewReader(string(output))); lines.Scan(); {
		if key, value, ok := strings.Cut(lines.Text(), "="); ok {
			seen[key] = value
		}
	}

	return seen, nil
}

// ANCHOR_END: start

// ANCHOR: compare
func run() error {
	mine, err := namespaces("self")

	if err != nil {
		return err
	}

	name, err := os.Hostname()

	if err != nil {
		return err
	}

	for _, isolate := range []bool{false, true} {
		seen, err := report(isolate)

		if err != nil {
			return err
		}

		after, err := os.Hostname()

		if err != nil {
			return err
		}

		fmt.Printf("child in new user, UTS and PID namespaces: %v\n", isolate)
		fmt.Printf("  same UTS namespace as the parent %v, same PID namespace %v\n",
			seen["uts"] == mine["uts"], seen["pidns"] == mine["pid"])
		fmt.Printf("  sethostname %s; host name inside is \"box\" %v, outside unchanged %v\n",
			seen["sethostname"], seen["hostname"] == "box", after == name)
		fmt.Printf("  pid inside is 1 %v; uid inside is 0 %v\n", seen["pid"] == "1", seen["uid"] == "0")

		if fields := strings.Fields(seen["map"]); isolate && len(fields) == 3 {
			fmt.Printf("  uid map: user 0 inside is user %s outside\n", fields[1])
		}
	}

	return nil
}

// ANCHOR_END: compare

func main() {
	if len(os.Args) > 1 && os.Args[1] == "inside" {
		if err := inside(); err != nil {
			log.Fatal(err)
		}

		return
	}

	if err := run(); err != nil {
		log.Fatal(err)
	}
}
