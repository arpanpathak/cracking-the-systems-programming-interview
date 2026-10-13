// Command fdfacts measures how the kernel hands out file descriptors and what
// a pair of descriptors shares: the number an open returns, the file offset, the
// status flags, and the close-on-exec flag. It ends with the redirection
// `> file 2>&1`, done once with a shared open file description and once with
// separate ones.
//
// Run it from code/go with:
//
//	go run ./fdfacts
package main

// ANCHOR: imports
import (
	"errors"
	"fmt"
	"log"
	"os"
	"os/exec"
	"path/filepath"
	"strings"

	"golang.org/x/sys/unix"
)

// ANCHOR_END: imports

// ANCHOR: numbers
// numbers closes descriptor 0, the standard input, and opens a file. The
// kernel gives an open the lowest number that is free.
func numbers(path string) error {
	if err := unix.Close(0); err != nil {
		return err
	}

	fd, err := unix.Open(path, unix.O_RDONLY, 0)

	if err != nil {
		return err
	}

	fmt.Printf("descriptor 0 closed: the next open returns %d\n", fd)

	return nil
}

// ANCHOR_END: numbers

// ANCHOR: limit
// name returns the symbolic name of a system call error, such as EMFILE.
func name(err error) string {
	var errno unix.Errno

	if errors.As(err, &errno) {
		return unix.ErrnoName(errno)
	}

	return fmt.Sprint(err)
}

// limit lowers the limit on open descriptors to 32 and opens a file until
// the kernel refuses.
func limit(path string) error {
	var saved unix.Rlimit

	if err := unix.Getrlimit(unix.RLIMIT_NOFILE, &saved); err != nil {
		return err
	}

	lowered := saved
	lowered.Cur = 32

	if err := unix.Setrlimit(unix.RLIMIT_NOFILE, &lowered); err != nil {
		return err
	}

	defer unix.Setrlimit(unix.RLIMIT_NOFILE, &saved)

	var opened []int
	highest := -1

	for {
		fd, err := unix.Open(path, unix.O_RDONLY, 0)

		if err != nil {
			fmt.Printf("limit of 32 descriptors: the highest number obtained is %d, the next open fails with %s\n",
				highest, name(err))

			break
		}

		opened, highest = append(opened, fd), max(highest, fd)
	}

	for _, fd := range opened {
		unix.Close(fd)
	}

	return nil
}

// ANCHOR_END: limit

// ANCHOR: offsets
// offset returns the file offset that a descriptor refers to.
func offset(fd int) (int64, error) {
	return unix.Seek(fd, 0, unix.SEEK_CUR)
}

// offsets writes through one descriptor and reads the offset through a
// duplicate of it and through a second open of the same file.
func offsets(path string) error {
	first, err := unix.Open(path, unix.O_WRONLY, 0)

	if err != nil {
		return err
	}

	defer unix.Close(first)

	duplicate, err := unix.Dup(first)

	if err != nil {
		return err
	}

	defer unix.Close(duplicate)

	second, err := unix.Open(path, unix.O_WRONLY, 0)

	if err != nil {
		return err
	}

	defer unix.Close(second)

	if _, err := unix.Write(first, []byte("hello")); err != nil {
		return err
	}

	shared, err := offset(duplicate)

	if err != nil {
		return err
	}

	separate, err := offset(second)

	if err != nil {
		return err
	}

	fmt.Printf("after a write of 5 bytes: offset through the duplicate %d, through a second open %d\n",
		shared, separate)

	return nil
}

// ANCHOR_END: offsets

// ANCHOR: flags
// flags sets O_APPEND and close-on-exec through a duplicate and reads both
// through the original descriptor.
func flags(path string) error {
	first, err := unix.Open(path, unix.O_WRONLY, 0)

	if err != nil {
		return err
	}

	defer unix.Close(first)

	duplicate, err := unix.Dup(first)

	if err != nil {
		return err
	}

	defer unix.Close(duplicate)

	if _, err := unix.FcntlInt(uintptr(duplicate), unix.F_SETFL, unix.O_APPEND); err != nil {
		return err
	}

	if _, err := unix.FcntlInt(uintptr(duplicate), unix.F_SETFD, unix.FD_CLOEXEC); err != nil {
		return err
	}

	status, err := unix.FcntlInt(uintptr(first), unix.F_GETFL, 0)

	if err != nil {
		return err
	}

	descriptor, err := unix.FcntlInt(uintptr(first), unix.F_GETFD, 0)

	if err != nil {
		return err
	}

	fmt.Printf("set on the duplicate, read on the original: O_APPEND %v, close-on-exec %v\n",
		status&unix.O_APPEND != 0, descriptor&unix.FD_CLOEXEC != 0)

	return nil
}

// ANCHOR_END: flags

// ANCHOR: names
// inode returns the inode number and the link count of a file.
func inode(path string) (number uint64, links uint64, err error) {
	var status unix.Stat_t

	err = unix.Stat(path, &status)

	return status.Ino, uint64(status.Nlink), err
}

// names gives a file a second name and compares the inodes behind the names.
func names(path string) error {
	first, second := path+".first", path+".second"

	if err := os.WriteFile(first, []byte("hello"), 0o644); err != nil {
		return err
	}

	defer os.Remove(first)
	defer os.Remove(second)

	if err := unix.Link(first, second); err != nil {
		return err
	}

	a, _, err := inode(first)

	if err != nil {
		return err
	}

	b, links, err := inode(second)

	if err != nil {
		return err
	}

	fmt.Printf("a second name for the file: same inode %v, link count %d\n", a == b, links)

	return nil
}

// ANCHOR_END: names

// ANCHOR: unlinked
// unlinked opens a file, removes its only name, and reads through the
// descriptor.
func unlinked(path string) error {
	file := path + ".unlinked"

	if err := os.WriteFile(file, []byte("hello"), 0o644); err != nil {
		return err
	}

	fd, err := unix.Open(file, unix.O_RDONLY, 0)

	if err != nil {
		return err
	}

	defer unix.Close(fd)

	if err := unix.Unlink(file); err != nil {
		return err
	}

	var status unix.Stat_t

	if err := unix.Fstat(fd, &status); err != nil {
		return err
	}

	buf := make([]byte, 16)
	n, err := unix.Read(fd, buf)

	if err != nil {
		return err
	}

	fmt.Printf("the name removed, the file still open: link count %d, read through the descriptor returns %q\n",
		status.Nlink, buf[:n])

	return nil
}

// ANCHOR_END: unlinked

// ANCHOR: redirect
// redirect runs a command that writes "out" to descriptor 1 and then "err" to
// descriptor 2, with both descriptors on the same file, and returns the
// file's contents.
func redirect(path string, stdout, stderr *os.File) (string, error) {
	command := exec.Command("sh", "-c", "echo out; echo err >&2")
	command.Stdout, command.Stderr = stdout, stderr

	if err := command.Run(); err != nil {
		return "", err
	}

	text, err := os.ReadFile(path)

	return strings.Join(strings.Fields(string(text)), " "), err
}

// redirections compares `> file 2>&1`, where descriptor 2 is a duplicate of
// descriptor 1, with `> file 2> file`, where the file is opened once for each.
func redirections(path string) error {
	stdout, err := os.Create(path)

	if err != nil {
		return err
	}

	defer stdout.Close()

	text, err := redirect(path, stdout, stdout)

	if err != nil {
		return err
	}

	fmt.Printf("> file 2>&1: the file holds %q\n", text)

	first, err := os.Create(path)

	if err != nil {
		return err
	}

	defer first.Close()

	second, err := os.OpenFile(path, os.O_WRONLY, 0)

	if err != nil {
		return err
	}

	defer second.Close()

	text, err = redirect(path, first, second)

	if err != nil {
		return err
	}

	fmt.Printf("> file 2> file: the file holds %q\n", text)

	return nil
}

// ANCHOR_END: redirect

func run() error {
	dir, err := os.MkdirTemp("", "fdfacts")

	if err != nil {
		return err
	}

	defer os.RemoveAll(dir)

	path := filepath.Join(dir, "file")

	if err := os.WriteFile(path, nil, 0o644); err != nil {
		return err
	}

	for _, experiment := range []func(string) error{numbers, limit, offsets, flags, names, unlinked, redirections} {
		if err := experiment(path); err != nil {
			return err
		}
	}

	return nil
}

func main() {
	if err := run(); err != nil {
		log.Fatal(err)
	}
}
