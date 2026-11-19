# Chapter 10: Asynchronous Notifications and Signal Semantics

A signal serves as the primary mechanism for asynchronous notification within a process, acting as the process-level analogue to a hardware interrupt. A signal is an event-driven notification—triggered by hardware faults, terminal events, or inter-process communication—that compels the kernel to interrupt the current execution stream to execute a designated handler.

## 10.1 The Signal Lifecycle: Generation, Pending, and Delivery

The lifecycle of a signal is characterized by three distinct phases: generation, pendency, and delivery. A signal is **generated** when a specific event occurs. Upon generation, the kernel updates the process's **pending set**, a bitmask where each bit represents a specific signal number. It is crucial to note that the pending set is non-accumulative; if multiple instances of the same signal are generated before a single delivery, the pending set merely records that at least one such signal is outstanding, and the handler will execute only once.

**Delivery** occurs at the next transition from kernel mode to user mode. Before proceeding, the kernel consults the process's **signal mask**—a bitmask of signals currently marked as blocked. If a signal is masked, it remains in the pending set until the mask is updated. For unmasked signals, the kernel executes the specified **disposition**, which may be the default action (e.g., termination) or a user-defined **signal handler**.

## 10.2 Constraints on Asynchronous Execution

Because a signal handler is invoked at an indeterminate point within the program's execution—potentially between any two machine instructions—it introduces severe constraints on what the handler may safely perform. The interrupted code may be in the midst of modifying a critical data structure or may hold a mutex that the handler itself requires. To prevent deadlocks and data corruption, signal handlers must be restricted to a subset of functions known as **async-signal-safe** operations. These typically include atomic stores to `sig_atomic_t` variables or writes to a pipe, but explicitly exclude complex functions like `malloc`, `printf`, or any routine involving synchronization primitives.

A common and robust design pattern is to have the handler perform only the minimal necessary work—such as setting an atomic flag—and then returning, allowing the main execution loop to process the event in a synchronous, controlled context.

## 10.3 Process Lifecycle Synchronization: `SIGCHLD` and Reaping

The `SIGCHLD` signal provides a mechanism for parent processes to asynchronously manage the lifecycle of their children. When a child process terminates or changes state, the kernel generates a `SIGCHLD` to notify the parent. This enables the parent to perform "reaping"—collecting the child's exit status via `waitpid`—without necessitating a blocking wait that would impede the parent's other responsibilities.

To avoid the loss of information due to the non-accumulative nature of the pending set, a `SIGCHLD` handler must invoke `waitpid` within a loop, utilizing the `WNOHANG` option to non-blockingly reap all currently exited children. Furthermore, the use of the `SA_RESTART` flag during handler installation is often necessary to ensure that system calls interrupted by the signal are automatically resumed by the kernel, thereby preventing spurious errors like `EINTR` from propagating through the application.
