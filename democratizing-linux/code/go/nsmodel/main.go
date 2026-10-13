// Command nsmodel models 2 kinds of namespace. A PID namespace gives its
// processes their own process numbers, and every process also has a number
// in each enclosing namespace. A UTS namespace holds a host name.
//
// Run it from code/go with:
//
//	go run ./nsmodel
package main

// ANCHOR: imports
import "fmt"

// ANCHOR_END: imports

// ANCHOR: types
// A pidNamespace hands out process numbers. level is its depth below the
// root namespace, which has level 0.
type pidNamespace struct {
	parent *pidNamespace
	level  int
	last   int
}

// allocate returns the next unused number of the namespace.
func (ns *pidNamespace) allocate() int {
	ns.last++

	return ns.last
}

// A utsNamespace holds the host name that its processes see.
type utsNamespace struct {
	hostname string
}

// A process belongs to one namespace of each kind. numbers holds its process
// number in every PID namespace from the root, at index 0, down to its own.
type process struct {
	pid     *pidNamespace
	uts     *utsNamespace
	numbers []int
}

// ANCHOR_END: types

// ANCHOR: fork
// fork creates a child. By default the child is in its parent's namespaces.
// With newPID it is the first process of a new PID namespace below the
// parent's. With newUTS it gets a copy of the parent's UTS namespace.
func fork(parent *process, newPID, newUTS bool) *process {
	child := &process{pid: parent.pid, uts: parent.uts}

	if newPID {
		child.pid = &pidNamespace{parent: parent.pid, level: parent.pid.level + 1}
	}

	if newUTS {
		child.uts = &utsNamespace{hostname: parent.uts.hostname}
	}

	child.numbers = make([]int, child.pid.level+1)

	for ns := child.pid; ns != nil; ns = ns.parent {
		child.numbers[ns.level] = ns.allocate()
	}

	return child
}

// ANCHOR_END: fork

// ANCHOR: visible
// numberIn returns the number by which a process is known in a namespace. A
// process is visible in its own PID namespace and in every namespace that
// encloses it, and in no other.
func (p *process) numberIn(ns *pidNamespace) (int, bool) {
	own := p.pid

	for own != nil && own.level > ns.level {
		own = own.parent
	}

	if own != ns {
		return 0, false
	}

	return p.numbers[ns.level], true
}

// seen describes a process as a namespace sees it.
func seen(p *process, ns *pidNamespace) string {
	if number, ok := p.numberIn(ns); ok {
		return fmt.Sprintf("pid %d", number)
	}

	return "not visible"
}

// ANCHOR_END: visible

// ANCHOR: trace
func main() {
	root := &pidNamespace{}
	host := &utsNamespace{hostname: "host"}

	first := &process{pid: root, uts: host, numbers: []int{root.allocate()}}
	shell := fork(first, false, false)
	a := fork(shell, true, true)
	child := fork(a, false, false)
	b := fork(shell, true, true)
	nested := fork(child, true, false)

	rows := []struct {
		name string
		p    *process
	}{{"first process", first}, {"shell", shell}, {"first process of A", a}, {"its child", child},
		{"first process of B", b}, {"nested below A", nested}}

	for _, row := range rows {
		fmt.Printf("%-20s numbers from the root namespace down: %v\n", row.name, row.p.numbers)
	}

	fmt.Printf("the first process of B, seen from the root namespace: %s\n", seen(b, root))
	fmt.Printf("the first process of B, seen from A: %s\n", seen(b, a.pid))
	fmt.Printf("the shell, seen from A: %s\n", seen(shell, a.pid))
	fmt.Printf("the nested process, seen from A: %s\n", seen(nested, a.pid))

	a.uts.hostname = "box"
	fmt.Printf("host name set to \"box\" in A: A sees %q, its child %q, B %q, the shell %q\n",
		a.uts.hostname, child.uts.hostname, b.uts.hostname, shell.uts.hostname)
}

// ANCHOR_END: trace
