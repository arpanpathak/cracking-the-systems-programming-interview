// Command cfs models the Completely Fair Scheduler: every runnable task has a
// virtual runtime, the scheduler always runs the task with the smallest one,
// and a task's virtual runtime advances more slowly the larger its weight.
//
// Run it from code/go with:
//
//	go run ./cfs
package main

// ANCHOR: imports
import (
	"container/heap"
	"fmt"
	"strings"
)

// ANCHOR_END: imports

// ANCHOR: weights
// weights is the kernel's table sched_prio_to_weight: the weight of each nice
// value from -20 to 19. Each step of nice changes the weight by about 25%.
var weights = [40]int64{
	88761, 71755, 56483, 46273, 36291, 29154, 23254, 18705, 14949, 11916,
	9548, 7620, 6100, 4904, 3906, 3121, 2501, 1991, 1586, 1277,
	1024, 820, 655, 526, 423, 335, 272, 215, 172, 137,
	110, 87, 70, 56, 45, 36, 29, 23, 18, 15,
}

// slice is the time a task runs before the scheduler chooses again, in
// nanoseconds.
const slice = 1_000_000

// A task is one schedulable entity. vruntime is its virtual runtime in
// nanoseconds, and slices counts how often it has run.
type task struct {
	name     string
	weight   int64
	vruntime int64
	slices   int
}

func newTask(name string, nice int) *task {
	return &task{name: name, weight: weights[nice+20]}
}

// ANCHOR_END: weights

// ANCHOR: queue
// A queue holds the runnable tasks ordered by virtual runtime, with the name
// as a tie-break. It implements heap.Interface. The kernel keeps the same
// order in a red-black tree and takes the leftmost node.
type queue []*task

func (q queue) Len() int      { return len(q) }
func (q queue) Swap(i, j int) { q[i], q[j] = q[j], q[i] }
func (q *queue) Push(t any)   { *q = append(*q, t.(*task)) }

func (q queue) Less(i, j int) bool {
	if q[i].vruntime != q[j].vruntime {
		return q[i].vruntime < q[j].vruntime
	}

	return q[i].name < q[j].name
}

func (q *queue) Pop() any {
	old := *q
	last := old[len(old)-1]
	*q = old[:len(old)-1]

	return last
}

// ANCHOR_END: queue

// ANCHOR: tick
// A scheduler is a run queue and the smallest virtual runtime it has seen,
// which only increases.
type scheduler struct {
	runnable    queue
	minVruntime int64
}

// tick runs the task with the smallest virtual runtime for one slice and
// returns it. The task is charged slice * 1024 / weight, so a task of weight
// 1024 is charged real time and a heavier task is charged less.
func (s *scheduler) tick() *task {
	t := heap.Pop(&s.runnable).(*task)

	t.vruntime += slice * 1024 / t.weight
	t.slices++

	heap.Push(&s.runnable, t)
	s.minVruntime = max(s.minVruntime, s.runnable[0].vruntime)

	return t
}

// wake makes a task runnable. With place set, a task that slept is moved
// forward to the queue's minimum, so that it cannot claim the time it did
// not use while it slept.
func (s *scheduler) wake(t *task, place bool) {
	if place {
		t.vruntime = max(t.vruntime, s.minVruntime)
	}

	heap.Push(&s.runnable, t)
}

// ANCHOR_END: tick

// ANCHOR: share
// share runs a task of nice 0 against a task of the given nice value for
// 2000 slices and prints each task's share, rounded to the nearest 5%.
func share(nice int) {
	s := &scheduler{}
	first, second := newTask("A", 0), newTask("B", nice)

	s.wake(first, true)
	s.wake(second, true)

	for range 2000 {
		s.tick()
	}

	percent := (200*first.slices/(first.slices+second.slices) + 5) / 10 * 5
	fmt.Printf("nice 0 and nice %d on 1 CPU: %d%% and %d%%\n", nice, percent, 100-percent)
}

// ANCHOR_END: share

// ANCHOR: order
// order prints which task runs in each of the first 12 slices.
func order() {
	s := &scheduler{}

	for _, t := range []*task{newTask("A", 0), newTask("B", 0), newTask("C", 5)} {
		s.wake(t, true)
	}

	var names []string

	for range 12 {
		names = append(names, s.tick().name)
	}

	fmt.Printf("A and B at nice 0, C at nice 5: %s\n", strings.Join(names, " "))
}

// ANCHOR_END: order

// ANCHOR: sleeper
// sleeper lets A and B run for 200 slices, wakes C with a virtual runtime of
// 0, and counts how many of the next 30 slices C receives.
func sleeper(place bool) int {
	s := &scheduler{}

	s.wake(newTask("A", 0), true)
	s.wake(newTask("B", 0), true)

	for range 200 {
		s.tick()
	}

	c := newTask("C", 0)
	s.wake(c, place)

	for range 30 {
		s.tick()
	}

	return c.slices
}

// ANCHOR_END: sleeper

func main() {
	for _, nice := range []int{0, 5, 10} {
		share(nice)
	}

	order()

	fmt.Printf("C wakes with its old virtual runtime: it receives %d of the next 30 slices\n", sleeper(false))
	fmt.Printf("C wakes and is placed at the minimum: it receives %d of the next 30 slices\n", sleeper(true))
}
