// Command cachefacts measures the page cache for one file: how many of the
// file's pages are held in memory after a write, after the cache is told to
// drop them, and after reads of different kinds.
//
// Run it from code/go with:
//
//	go run ./cachefacts
package main

// ANCHOR: imports
import (
	"fmt"
	"io"
	"log"
	"os"
	"os/exec"
	"path/filepath"
	"strconv"
	"strings"

	"golang.org/x/sys/unix"
)

// ANCHOR_END: imports

// ANCHOR: cached
const pageSize = 4096

// cached returns the number of pages of a file that are in the page cache,
// as reported by the fincore utility.
func cached(path string) (int, error) {
	text, err := exec.Command("fincore", "--noheadings", "--output", "PAGES", path).Output()

	if err != nil {
		return 0, err
	}

	return strconv.Atoi(strings.TrimSpace(string(text)))
}

// report prints a step and the number of cached pages after it.
func report(step, path string) error {
	pages, err := cached(path)

	if err != nil {
		return err
	}

	fmt.Printf("%-38s cached pages: %d\n", step+":", pages)

	return nil
}

// drop writes the file's dirty pages to disk and asks the kernel to remove
// the file's pages from the cache.
func drop(file *os.File) error {
	if err := file.Sync(); err != nil {
		return err
	}

	return unix.Fadvise(int(file.Fd()), 0, 0, unix.FADV_DONTNEED)
}

// ANCHOR_END: cached

// ANCHOR: steps
// run writes a file of 64 pages and reads it in 3 ways, dropping the cached
// pages between the steps.
func run(path string) error {
	file, err := os.OpenFile(path, os.O_RDWR|os.O_CREATE, 0o644)

	if err != nil {
		return err
	}

	defer file.Close()

	if _, err := file.Write(make([]byte, 64*pageSize)); err != nil {
		return err
	}

	if err := report("write of 64 pages", path); err != nil {
		return err
	}

	if err := drop(file); err != nil {
		return err
	}

	if err := report("fsync, then FADV_DONTNEED", path); err != nil {
		return err
	}

	one := make([]byte, 1)

	if _, err := file.ReadAt(one, 0); err != nil {
		return err
	}

	if err := report("read of 1 byte at offset 0", path); err != nil {
		return err
	}

	if _, err := io.Copy(io.Discard, io.NewSectionReader(file, 0, 64*pageSize)); err != nil {
		return err
	}

	if err := report("read of the whole file", path); err != nil {
		return err
	}

	if err := drop(file); err != nil {
		return err
	}

	if err := unix.Fadvise(int(file.Fd()), 0, 0, unix.FADV_RANDOM); err != nil {
		return err
	}

	if _, err := file.ReadAt(one, 0); err != nil {
		return err
	}

	return report("dropped, FADV_RANDOM, read of 1 byte", path)
}

// ANCHOR_END: steps

func main() {
	dir, err := os.MkdirTemp("", "cachefacts")

	if err != nil {
		log.Fatal(err)
	}

	err = run(filepath.Join(dir, "file"))
	os.RemoveAll(dir)

	if err != nil {
		log.Fatal(err)
	}
}
