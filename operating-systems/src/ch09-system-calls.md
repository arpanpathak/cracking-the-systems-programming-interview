# 9. The Kernel Boundary and the Cost of System Calls

The system call represents the formal interface between user-mode application logic and the privileged operations of the operating system. It serves as the single, controlled gateway through which a process may request services, such as file I/O, process management, or network communication, that require hardware access or kernel-level authority.

## 9.1 The Mechanics of the System Call Interface

A system call is initiated via a specialized "trap" instruction executed by a user-mode library stub. This stub populates specific registers with a system call identifier and any necessary arguments before triggering the hardware transition. The CPU responds by saving the current architectural state (registers and program counter), elevating the privilege level to kernel mode, and jumping to a pre-registered entry point within the kernel.

The kernel identifies the requested service by indexing into a system call table using the provided identifier. Once the appropriate handler is located and executed, the kernel restores the process's registers and returns control to user mode. A critical security invariant of this boundary is that the kernel must treat all incoming arguments, including call numbers, pointers, and buffer lengths, as untrusted. Rigorous validation of these parameters is mandatory to prevent a malicious or faulty process from using an unverified pointer to bypass isolation and compromise kernel memory.

<figure>
<img src="figures/ch09_trap.svg" alt="Six numbered steps of a system call from user mode to the kernel and back"/>
</figure>

## 9.2 Performance Implications and Optimization via Buffering

The transition between user and kernel modes is not a zero-cost abstraction. The overhead of saving and restoring the architectural state, combined with the hardware requirements of privilege elevation and the subsequent impact on instruction and data caches, renders a system call significantly more expensive than a standard function call. On modern systems, this latency is typically two orders of magnitude greater than a typical function call.

To mitigate this performance penalty, software frequently employs **buffering** strategies. Rather than issuing a system call for every discrete unit of data, the application accumulates small writes in a user-mode buffer. Once the buffer reaches a specific threshold, a single, large-scale system call is issued to transfer the accumulated data to the kernel. This reduces the total number of mode transitions required for a given workload.

However, buffering introduces a trade-off between performance and durability. Data residing in a user-mode buffer is volatile; if the application crashes before the buffer is flushed, that data is lost, as the kernel remains unaware of its existence. Furthermore, mixing buffered and unbuffered I/O on the same file descriptor can lead to non-deterministic output ordering if the buffers are not explicitly synchronized. Effective system design requires a careful balance between minimizing system call frequency and ensuring data integrity through appropriate flushing and synchronization primitives.

**Listing 9-1. A system call compared with a function call (C++20).**

```cpp
{{#include ../code/ch09/syscall_cost.cpp}}
```

**Output 9-1. One run on the verification machine.**

```text
{{#include ../code/out/ch09_syscall_cost.out}}
```

**Listing 9-2. The same comparison in Rust.**

```rust
{{#include ../code/ch09/syscall_cost.rs}}
```

**Output 9-2.**

```text
{{#include ../code/out/ch09_syscall_cost_rs.out}}
```

<figure>
<img src="figures/ch09_buffering.svg" alt="Unbuffered writes cross into the kernel per call; a 64 KiB user buffer crosses only when full"/>
</figure>

**Listing 9-3. 200,000 small writes, unbuffered and buffered (C++20).**

```cpp
{{#include ../code/ch09/write_buffered.cpp}}
```

**Output 9-3.**

```text
{{#include ../code/out/ch09_write_buffered.out}}
```

**Listing 9-4. The same comparison in Rust, with write(2) and BufWriter.**

```rust
{{#include ../code/ch09/write_buffered.rs}}
```

**Output 9-4.**

```text
{{#include ../code/out/ch09_write_buffered_rs.out}}
```
