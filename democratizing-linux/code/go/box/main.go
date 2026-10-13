// Command box runs a shell script in a container built by hand: new user,
// mount, UTS, PID, IPC and network namespaces, a root file system of its own, and a
// control group with a limit on the number of processes.
//
// Run it from code/go with:
//
//	go run ./box
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

	"golang.org/x/sys/unix"
)

// ANCHOR_END: imports

// ANCHOR: group
// createGroup makes a control group for the container below the nearest
// group that passes the pids controller to its children, and sets pids.max.
func createGroup(pidsMax int) (string, error) {
	line, err := os.ReadFile("/proc/self/cgroup")

	if err != nil {
		return "", err
	}

	_, path, _ := strings.Cut(strings.TrimSpace(string(line)), "::")

	for dir := filepath.Join("/sys/fs/cgroup", path); dir != "/sys/fs/cgroup"; dir = filepath.Dir(dir) {
		enabled, err := os.ReadFile(filepath.Join(dir, "cgroup.subtree_control"))

		if err != nil || !strings.Contains(string(enabled), "pids") {
			continue
		}

		group := filepath.Join(dir, fmt.Sprintf("box-%d", os.Getpid()))

		if err := os.Mkdir(group, 0o755); err != nil {
			return "", err
		}

		return group, os.WriteFile(filepath.Join(group, "pids.max"), fmt.Append(nil, pidsMax), 0)
	}

	return "", errors.New("no parent group passes on the pids controller")
}

// refused returns the number of forks the group has refused.
func refused(group string) (string, error) {
	events, err := os.Open(filepath.Join(group, "pids.events"))

	if err != nil {
		return "", err
	}

	defer events.Close()

	for lines := bufio.NewScanner(events); lines.Scan(); {
		if count, ok := strings.CutPrefix(lines.Text(), "max "); ok {
			return count, nil
		}
	}

	return "", errors.New("pids.events has no line max")
}

// removeGroup waits until the group is empty and deletes it.
func removeGroup(group string) error {
	for {
		current, err := os.ReadFile(filepath.Join(group, "pids.current"))

		if err != nil {
			return err
		}

		if strings.TrimSpace(string(current)) == "0" {
			return os.Remove(group)
		}

		time.Sleep(time.Millisecond)
	}
}

// ANCHOR_END: group

// ANCHOR: launch
// launch starts this program again as the first process of a container. The
// clone flags create the namespaces, the mappings make the current user
// user 0 inside, and CgroupFD makes the kernel create the child inside the
// control group.
func launch(group, root, script string) (*exec.Cmd, error) {
	directory, err := os.Open(group)

	if err != nil {
		return nil, err
	}

	defer directory.Close()

	child := exec.Command("/proc/self/exe", "init", root, script)
	child.Stdout, child.Stderr = os.Stdout, os.Stderr

	child.SysProcAttr = &syscall.SysProcAttr{
		Cloneflags: syscall.CLONE_NEWUSER | syscall.CLONE_NEWNS | syscall.CLONE_NEWUTS |
			syscall.CLONE_NEWPID | syscall.CLONE_NEWIPC | syscall.CLONE_NEWNET,
		UidMappings: []syscall.SysProcIDMap{{ContainerID: 0, HostID: os.Getuid(), Size: 1}},
		GidMappings: []syscall.SysProcIDMap{{ContainerID: 0, HostID: os.Getgid(), Size: 1}},
		UseCgroupFD: true,
		CgroupFD:    int(directory.Fd()),
	}

	return child, child.Start()
}

// ANCHOR_END: launch

// ANCHOR: root
// shared are the directories of the host that the container can see.
var shared = []string{"bin", "sbin", "lib", "usr"}

// buildRoot assembles the root file system of the container in an empty
// directory: a tmpfs, the host's program directories, the null device, and
// a new /proc.
func buildRoot(root string) error {
	// Mount changes made from here on stay in this mount namespace.
	if err := unix.Mount("", "/", "", unix.MS_REC|unix.MS_PRIVATE, ""); err != nil {
		return fmt.Errorf("make mounts private: %w", err)
	}

	if err := unix.Mount("tmpfs", root, "tmpfs", 0, ""); err != nil {
		return fmt.Errorf("mount tmpfs: %w", err)
	}

	for _, name := range shared {
		source, target := "/"+name, filepath.Join(root, name)

		// On this system /bin, /sbin and /lib are symbolic links into /usr.
		if link, err := os.Readlink(source); err == nil {
			if err := os.Symlink(link, target); err != nil {
				return err
			}

			continue
		}

		if err := os.Mkdir(target, 0o755); err != nil {
			return err
		}

		if err := unix.Mount(source, target, "", unix.MS_BIND|unix.MS_REC, ""); err != nil {
			return fmt.Errorf("bind %s: %w", source, err)
		}
	}

	// The container gets a /dev with the null device and nothing else.
	null := filepath.Join(root, "dev", "null")

	if err := os.Mkdir(filepath.Dir(null), 0o755); err != nil {
		return err
	}

	if err := os.WriteFile(null, nil, 0o666); err != nil {
		return err
	}

	if err := unix.Mount("/dev/null", null, "", unix.MS_BIND, ""); err != nil {
		return fmt.Errorf("bind /dev/null: %w", err)
	}

	proc := filepath.Join(root, "proc")

	if err := os.Mkdir(proc, 0o555); err != nil {
		return err
	}

	if err := unix.Mount("proc", proc, "proc", 0, ""); err != nil {
		return fmt.Errorf("mount proc: %w", err)
	}

	return nil
}

// enterRoot makes root the root directory of the mount namespace and
// detaches the host's file system from it.
func enterRoot(root string) error {
	old := filepath.Join(root, "old")

	if err := os.Mkdir(old, 0o700); err != nil {
		return err
	}

	if err := unix.PivotRoot(root, old); err != nil {
		return fmt.Errorf("pivot_root: %w", err)
	}

	if err := os.Chdir("/"); err != nil {
		return err
	}

	if err := unix.Unmount("/old", unix.MNT_DETACH); err != nil {
		return fmt.Errorf("unmount the old root: %w", err)
	}

	return os.Remove("/old")
}

// ANCHOR_END: root

// ANCHOR: init
// initialize runs as process 1 of the container. It builds and enters the
// root file system, sets the host name, and replaces itself with a shell
// that runs the script.
func initialize(root, script string) error {
	if err := buildRoot(root); err != nil {
		return err
	}

	if err := enterRoot(root); err != nil {
		return err
	}

	if err := unix.Sethostname([]byte("box")); err != nil {
		return err
	}

	environment := []string{"PATH=/usr/sbin:/usr/bin:/sbin:/bin"}

	return unix.Exec("/bin/sh", []string{"sh", "-c", script}, environment)
}

// ANCHOR_END: init

// ANCHOR: run
// script is what the container runs.
const script = `echo "host name: $(hostname)"
echo "process number of the shell: $$"
echo "user number: $(id -u)"
echo "processes under /proc:" /proc/[0-9]*
echo "root directory:" /*
while read device directory type rest; do echo "mounted: $directory ($type)"; done < /proc/mounts
echo "network interfaces:" $(tail -n +3 /proc/net/dev | cut -d: -f1)
echo "effective capabilities:" $(grep CapEff /proc/self/status | cut -f2)
for i in 1 2 3 4 5 6; do sleep 1 & echo "started a background command"; done 2>/dev/null`

func run() error {
	group, err := createGroup(5)

	if err != nil {
		return err
	}

	defer removeGroup(group)

	root, err := os.MkdirTemp("", "box-root")

	if err != nil {
		return err
	}

	defer os.Remove(root)

	before, err := os.Hostname()

	if err != nil {
		return err
	}

	child, err := launch(group, root, script)

	if err != nil {
		return err
	}

	child.Wait()

	count, err := refused(group)

	if err != nil {
		return err
	}

	after, err := os.Hostname()

	if err != nil {
		return err
	}

	fmt.Printf("the container ended with status %d; forks refused by its group: %s\n", child.ProcessState.ExitCode(), count)
	fmt.Printf("host name outside unchanged: %v\n", before == after)

	return nil
}

func main() {
	var err error

	if len(os.Args) == 4 && os.Args[1] == "init" {
		err = initialize(os.Args[2], os.Args[3])
	} else {
		err = run()
	}

	if err != nil {
		log.Fatal(err)
	}
}

// ANCHOR_END: run
