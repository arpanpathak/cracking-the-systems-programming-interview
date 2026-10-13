// Command vmfacts measures how the kernel fills an address space: when a
// mapped page receives physical memory, what an untouched page contains, how
// a mapping's permissions appear in /proc/self/maps, and where a write
// through a private or a shared file mapping ends up.
//
// Run it from code/go with:
//
//	go run ./vmfacts
package main

// ANCHOR: imports
import (
	"bufio"
	"encoding/binary"
	"fmt"
	"log"
	"os"
	"path/filepath"
	"reflect"
	"strings"

	"golang.org/x/sys/unix"
)

// ANCHOR_END: imports

// ANCHOR: resident
const pageSize = 4096

// address returns the virtual address of the first byte of a mapping.
func address(mapping []byte) uintptr {
	return reflect.ValueOf(mapping).Pointer()
}

// resident counts the pages of a mapping that have physical memory. The
// kernel publishes 8 bytes per virtual page in /proc/self/pagemap, and bit 63
// of an entry is set when the page is present in memory.
func resident(mapping []byte) (int, error) {
	pagemap, err := os.Open("/proc/self/pagemap")

	if err != nil {
		return 0, err
	}

	defer pagemap.Close()

	entries := make([]byte, 8*len(mapping)/pageSize)

	if _, err := pagemap.ReadAt(entries, int64(address(mapping)/pageSize*8)); err != nil {
		return 0, err
	}

	count := 0

	for i := 0; i < len(entries); i += 8 {
		if binary.LittleEndian.Uint64(entries[i:])>>63 == 1 {
			count++
		}
	}

	return count, nil
}

// ANCHOR_END: resident

// ANCHOR: demand
// demand maps 64 pages of anonymous memory, writes to 10 of them, reads 1
// more, and counts the resident pages after each step.
func demand() error {
	mapping, err := unix.Mmap(-1, 0, 64*pageSize, unix.PROT_READ|unix.PROT_WRITE, unix.MAP_PRIVATE|unix.MAP_ANONYMOUS)

	if err != nil {
		return err
	}

	defer unix.Munmap(mapping)

	before, err := resident(mapping)

	if err != nil {
		return err
	}

	for page := range 10 {
		mapping[page*pageSize] = 1
	}

	written, err := resident(mapping)

	if err != nil {
		return err
	}

	value := mapping[20*pageSize]
	read, err := resident(mapping)

	if err != nil {
		return err
	}

	fmt.Printf("64 pages mapped: %d resident\n", before)
	fmt.Printf("after writing to 10 pages: %d resident\n", written)
	fmt.Printf("after reading 1 more page: %d resident, the byte read is %d\n", read, value)

	return nil
}

// ANCHOR_END: demand

// ANCHOR: protect
// permissions returns the permission column of the line in /proc/self/maps
// that starts at the address of a mapping.
func permissions(mapping []byte) (string, error) {
	maps, err := os.Open("/proc/self/maps")

	if err != nil {
		return "", err
	}

	defer maps.Close()

	start := fmt.Sprintf("%x-", address(mapping))

	for lines := bufio.NewScanner(maps); lines.Scan(); {
		if fields := strings.Fields(lines.Text()); strings.HasPrefix(fields[0], start) {
			return fields[1], nil
		}
	}

	return "", fmt.Errorf("mapping at %s not found", start)
}

// protect reads the permissions of a mapping before and after mprotect
// removes the permission to write.
func protect() error {
	mapping, err := unix.Mmap(-1, 0, pageSize, unix.PROT_READ|unix.PROT_WRITE, unix.MAP_PRIVATE|unix.MAP_ANONYMOUS)

	if err != nil {
		return err
	}

	defer unix.Munmap(mapping)

	before, err := permissions(mapping)

	if err != nil {
		return err
	}

	if err := unix.Mprotect(mapping, unix.PROT_READ); err != nil {
		return err
	}

	after, err := permissions(mapping)

	if err != nil {
		return err
	}

	fmt.Printf("permissions of the mapping: %s, after mprotect: %s\n", before, after)

	return nil
}

// ANCHOR_END: protect

// ANCHOR: file
// throughMapping maps a file that holds "hello", writes "HELLO" through the
// mapping, unmaps it, and returns the contents of the file.
func throughMapping(path string, flags int) (string, error) {
	if err := os.WriteFile(path, []byte("hello"), 0o644); err != nil {
		return "", err
	}

	file, err := os.OpenFile(path, os.O_RDWR, 0)

	if err != nil {
		return "", err
	}

	defer file.Close()

	mapping, err := unix.Mmap(int(file.Fd()), 0, 5, unix.PROT_READ|unix.PROT_WRITE, flags)

	if err != nil {
		return "", err
	}

	copy(mapping, "HELLO")

	if err := unix.Munmap(mapping); err != nil {
		return "", err
	}

	text, err := os.ReadFile(path)

	return string(text), err
}

// files compares a private file mapping with a shared one.
func files() error {
	dir, err := os.MkdirTemp("", "vmfacts")

	if err != nil {
		return err
	}

	defer os.RemoveAll(dir)

	path := filepath.Join(dir, "file")

	for _, kind := range []struct {
		name  string
		flags int
	}{{"private", unix.MAP_PRIVATE}, {"shared", unix.MAP_SHARED}} {
		text, err := throughMapping(path, kind.flags)

		if err != nil {
			return err
		}

		fmt.Printf("HELLO written through a %s file mapping: the file holds %q\n", kind.name, text)
	}

	return nil
}

// ANCHOR_END: file

func main() {
	for _, experiment := range []func() error{demand, protect, files} {
		if err := experiment(); err != nil {
			log.Fatal(err)
		}
	}
}
