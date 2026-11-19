# Chapter 3: Process Abstraction and Lifecycle

A program is a static sequence of instructions; it becomes a process only when the operating system instantiates it into an active execution environment. A process is defined by its execution state, its resource ownership, and its isolated address space.

## 3.1 The Process Control Block and Address Space Topology

To manage multiple concurrent executions, the kernel maintains a Process Control Block (PCB) for every active process. The PCB serves as the primary vehicle for context switching, storing the process's unique identifier (PID), its lineage, its current execution state (running, ready, or blocked), and the precise architectural state—including registers and the program counter—required to resume execution. Beyond execution state, the PCB tracks the process's environmental resources, including its page tables for memory isolation, its file descriptor table, and its signal configuration.

The process's memory is organized into a structured address space, which provides a consistent view of memory regardless of the underlying physical allocation. This topology typically includes:
- **Text Segment:** The read-only machine code of the program, which can be shared across multiple processes to conserve physical memory.
- **Data and BSS Segments:** Regions for initialized and uninitialized global variables, respectively.
- **Heap:** A dynamically expanding region for runtime memory allocation, growing toward higher addresses.
- **Stack:** A region that manages function activation records, growing toward lower addresses.
- **Kernel Space:** A protected region at the apex of the address space, mapped into every process but inaccessible in user mode, facilitating efficient system calls.

## 3.2 Process Creation and the Mechanics of `fork`

On Unix-like systems, process creation is facilitated through the `fork` system call, which implements a "copy-on-write" (COW) paradigm. Rather than performing an immediate, computationally expensive duplication of the parent's entire address space, the kernel initially permits the parent and child to share the same physical pages, marking them as read-only. A private copy is only instantiated when one of the processes attempts a write operation. This mechanism ensures that `fork` remains highly efficient, particularly when the child intends to immediately replace its image using `execve`.

A critical nuance of `fork` involves the inheritance of process state, specifically the buffers within standard I/O libraries. Because `fork` duplicates the process's memory, including any unwritten data in user-mode buffers, a child process may inadvertently re-output data that was buffered by the parent prior to the fork. This necessitates explicit synchronization, such as calling `fflush` before a `fork` operation, to maintain output integrity.

## 3.3 Lifecycle Management and Termination

The lifecycle of a process is governed by a sequence of fundamental transitions: `fork` for creation, `execve` for program replacement, `exit` for termination, and `waitpid` for status collection. `execve` is particularly vital as it allows a process to discard its current address space and load a new program image while retaining its existing process identity (PID) and inherited file descriptors.

Proper lifecycle management is required to prevent the accumulation of "zombie" processes. When a process terminates via `exit`, the kernel preserves its PCB and exit status until the parent process acknowledges the termination through a `waitpid` call. If a parent fails to reap its children, these defunct processes remain in the system as zombies, consuming entries in the process table and potentially exhausting system resources.

The operational state of a process is categorized into three primary modes: **Running** (actively executing on a core), **Ready** (eligible for execution but awaiting a CPU), and **Blocked** (waiting for an external event or resource). The scheduler's role is to manage transitions between these states, ensuring efficient CPU utilization and responsiveness.
