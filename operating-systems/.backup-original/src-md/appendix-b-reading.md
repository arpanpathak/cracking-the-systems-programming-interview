# Appendix B. Further Reading

The books below are the ones this text stands on. Each entry names
what the book is for; the list is ordered by how directly it extends
a chapter of this one.

**Remzi H. Arpaci-Dusseau and Andrea C. Arpaci-Dusseau.**
*Operating Systems: Three Easy Pieces.*
The modern introduction to operating systems, organized as
virtualization, concurrency, and persistence. The scheduling and
synchronization chapters of this book follow its policy-first
approach; its chapters on paging and file systems are the natural
next depth after Chapters 7 and 12.

**Randal E. Bryant and David R. O'Hallaron.**
*Computer Systems: A Programmer's Perspective.*
The machine from the programmer's side: data representation, machine
code, the memory hierarchy, linking, exceptional control flow. Its
treatment of the memory hierarchy and of concurrent programming is
the closest companion to Chapters 2, 4, and 18.

**Abraham Silberschatz, Peter B. Galvin, and Greg Gagne.**
*Operating System Concepts.*
The comprehensive reference. Where this book develops one mechanism
to working depth, *Operating System Concepts* catalogs the
alternatives — every scheduling policy, every page replacement
algorithm, every file system structure — with the same first
principles but broader coverage.

**Michael Kerrisk.**
*The Linux Programming Interface.*
The definitive account of the Linux system call interface. Chapters 9
through 15 of this book cover the portable core; Kerrisk covers every
flag, every error, and every portability trap, with Linux specifics
that this book only notes.

**W. Richard Stevens and Stephen A. Rago.**
*Advanced Programming in the UNIX Environment.*
The companion volume for the same interface on the UNIX family,
including macOS. Its process, signal, and daemon chapters are the
canonical treatment of the patterns in Chapters 10 and 15.

**Marshall Kirk McKusick, Keith Bostic, Michael J. Karels, and John
S. Quarterman.**
*The Design and Implementation of the 4.4BSD Operating System.*
A complete kernel, read from the inside. Where this book stops at the
system call boundary, McKusick continues into the scheduler, the
virtual memory system, and the file system the calls invoke.

**Robert Love.**
*Linux Kernel Development.*
The Linux kernel's data structures at working depth: the process
descriptor, the runqueue, the page cache, the VFS. A shorter, more
current inside view than McKusick for the kernel this book's Linux
notes refer to.

**David B. Kirk, Wen-mei W. Hwu, and Izzat El Hajj.**
*Programming Massively Parallel Processors: A Hands-on Approach.*
The complete development of Chapter 17's third section: the
accelerator's execution model, memory model, and the patterns that
use it. The book's method — a concrete computation, then a program,
built step by step — is the method this book's code sections follow.

**Apple Inc.**
*Apple Platform Security.*
The security architecture of macOS, iOS, and Apple silicon: boot
chains, code signing, sandboxing, and the hardware roots of trust.
Its treatment of privilege and isolation extends Chapters 2 and 16
with the details of one production system.

For primary material, the POSIX standard defines the interface this
book programs against, and the manual pages — `man 2 fork`, `man 2
mmap`, `man 7 signal`, and their siblings — are the ground truth for
every call in the listings. Read the manual page for each call as you
meet it; the habit pays more than any single book.
