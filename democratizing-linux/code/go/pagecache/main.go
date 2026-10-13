// Command pagecache models the kernel's page cache for one file: pages read
// from a disk are kept in memory, sequential reads fetch pages ahead of the
// reader, writes change only the cached page until a sync, and the page used
// least recently is evicted when the cache is full.
//
// Run it from code/go with:
//
//	go run ./pagecache
package main

// ANCHOR: imports
import (
	"fmt"
	"slices"
)

// ANCHOR_END: imports

// ANCHOR: types
// maxWindow is the largest number of pages one disk request reads ahead.
const maxWindow = 8

// A disk holds the pages of a file and counts the requests made to it. The
// contents of a page are reduced to one byte.
type disk struct {
	pages    []byte
	requests int
	written  int
}

// A page is a cached copy of a disk page. dirty is set when the copy has
// been written and the disk has not. used is the time of the last access.
type page struct {
	value byte
	dirty bool
	used  int
}

// A cache maps page numbers to cached pages. next is the page that a
// sequential reader would ask for next, and window is the current number of
// pages to read ahead.
type cache struct {
	disk     *disk
	pages    map[int]*page
	capacity int
	clock    int
	next     int
	window   int
}

func newCache(d *disk, capacity int) *cache {
	return &cache{disk: d, pages: map[int]*page{}, capacity: capacity}
}

// ANCHOR_END: types

// ANCHOR: read
// read returns the contents of a page. A page that is cached costs no disk
// request. For a page that is missing, read makes one request for a window
// of pages. The window doubles while the reads are sequential and returns
// to 1 page when they are not.
func (c *cache) read(index int) byte {
	if _, hit := c.pages[index]; !hit {
		if index == c.next {
			c.window = min(2*max(c.window, 1), maxWindow)
		} else {
			c.window = 1
		}

		c.load(index, c.window)
	}

	c.next = index + 1

	return c.touch(index).value
}

// load reads count pages starting at index from the disk in one request.
func (c *cache) load(index, count int) {
	c.disk.requests++

	for i := index; i < min(index+count, len(c.disk.pages)); i++ {
		if _, hit := c.pages[i]; !hit {
			c.insert(i, &page{value: c.disk.pages[i]})
		}
	}
}

// touch records an access to a cached page and returns the page.
func (c *cache) touch(index int) *page {
	c.clock++
	c.pages[index].used = c.clock

	return c.pages[index]
}

// ANCHOR_END: read

// ANCHOR: write
// write changes a page in the cache and marks it dirty. It makes no disk
// request.
func (c *cache) write(index int, value byte) {
	if _, hit := c.pages[index]; !hit {
		c.insert(index, &page{})
	}

	p := c.touch(index)
	p.value, p.dirty = value, true
}

// sync writes every dirty page to the disk and returns the number written.
func (c *cache) sync() int {
	before := c.disk.written

	for index, p := range c.pages {
		c.clean(index, p)
	}

	return c.disk.written - before
}

// clean writes one page to the disk if it is dirty.
func (c *cache) clean(index int, p *page) {
	if p.dirty {
		c.disk.pages[index] = p.value
		c.disk.written++
		p.dirty = false
	}
}

// ANCHOR_END: write

// ANCHOR: evict
// insert adds a page to the cache. When the cache is full it first evicts
// the page whose last access is the oldest. A dirty page is written to the
// disk before it is removed.
func (c *cache) insert(index int, p *page) {
	if len(c.pages) == c.capacity {
		oldest := -1

		for i, candidate := range c.pages {
			if oldest == -1 || candidate.used < c.pages[oldest].used {
				oldest = i
			}
		}

		c.clean(oldest, c.pages[oldest])
		delete(c.pages, oldest)
	}

	c.clock++
	p.used = c.clock
	c.pages[index] = p
}

// held returns the numbers of the cached pages in increasing order.
func (c *cache) held() []int {
	held := make([]int, 0, len(c.pages))

	for index := range c.pages {
		held = append(held, index)
	}

	slices.Sort(held)

	return held
}

// ANCHOR_END: evict

// ANCHOR: trace
// requests reads the given pages through a new cache and returns the number
// of disk requests.
func requests(order []int) int {
	d := &disk{pages: make([]byte, 16)}
	c := newCache(d, 32)

	for _, index := range order {
		c.read(index)
	}

	return d.requests
}

func main() {
	forward := make([]int, 16)

	for i := range forward {
		forward[i] = i
	}

	backward := slices.Clone(forward)
	slices.Reverse(backward)

	fmt.Printf("16 pages read in order: %d disk requests\n", requests(forward))
	fmt.Printf("16 pages read in reverse order: %d disk requests\n", requests(backward))
	fmt.Printf("16 pages read in order, 2 times: %d disk requests\n", requests(append(forward, forward...)))

	d := &disk{pages: []byte("----------------")}
	c := newCache(d, 4)

	c.write(3, 'x')
	fmt.Printf("write of x to page 3: %d pages written, the disk holds %c\n", d.written, d.pages[3])
	fmt.Printf("sync: %d page written, the disk holds %c\n", c.sync(), d.pages[3])

	for _, index := range []int{2, 1, 0, 3} {
		c.read(index)
	}

	c.read(8)
	fmt.Printf("capacity 4, pages 3 2 1 0 3 used, then page 8: cache holds %v\n", c.held())

	c.write(1, 'y')

	for _, index := range []int{0, 3, 8, 12} {
		c.read(index)
	}

	fmt.Printf("write of y to page 1, then pages 0 3 8 12 used: cache holds %v, the disk holds %c\n", c.held(), d.pages[1])
}

// ANCHOR_END: trace
