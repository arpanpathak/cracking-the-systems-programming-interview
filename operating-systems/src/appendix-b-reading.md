# Appendix B. Further Reading

The following books treat the topics of this book in greater depth. For
each one, we note which chapters it extends.

**Remzi H. Arpaci-Dusseau and Andrea C. Arpaci-Dusseau.**
*Operating Systems: Three Easy Pieces.*
An introduction to operating systems in three parts: virtualization,
concurrency, and persistence. Its chapters on scheduling and on locks
cover the material of our Chapters 5 and 6 in more detail, and its
chapters on paging and file systems continue from our Chapters 7 and 12.
The book is available free of charge at ostep.org.

**Randal E. Bryant and David R. O'Hallaron.**
*Computer Systems: A Programmer's Perspective.*
A description of a computer from the point of view of a programmer. It
covers data representation, machine code, the memory hierarchy, linking,
and exceptional control flow. Its chapters on the memory hierarchy and on
concurrent programming complement our Chapters 2, 4, and 18.

**Abraham Silberschatz, Peter B. Galvin, and Greg Gagne.**
*Operating System Concepts.*
A comprehensive textbook. For each topic of this book, it presents many
alternatives, for example further scheduling policies, page replacement
algorithms, and file system structures.

**Michael Kerrisk.**
*The Linux Programming Interface.*
A complete reference for the system calls of Linux. Our Chapters 9 to 15
cover the calls that are common to Unix systems. Kerrisk describes every
flag and every error of each call, along with the features that only Linux
offers.

**W. Richard Stevens and Stephen A. Rago.**
*Advanced Programming in the UNIX Environment.*
A reference for the same interface across Unix systems, including macOS.
Its chapters on processes, signals, and daemons treat the subjects of our
Chapters 3, 10, and 15 thoroughly.

**Marshall Kirk McKusick, Keith Bostic, Michael J. Karels, and John
S. Quarterman.**
*The Design and Implementation of the 4.4BSD Operating System.*
A description of a complete kernel. This book ends at the system call
interface, and McKusick and his coauthors continue from there into the
scheduler, the virtual memory system, and the file system.

**Robert Love.**
*Linux Kernel Development.*
An introduction to the data structures of the Linux kernel, such as the
process descriptor, the run queue, the page cache, and the virtual file
system. It is shorter than the 4.4BSD book and describes Linux.

**David B. Kirk, Wen-mei W. Hwu, and Izzat El Hajj.**
*Programming Massively Parallel Processors: A Hands-on Approach.*
A textbook on programming GPUs. It covers the execution model and the
memory model of an accelerator, which we only outline in Section 17.3,
and it develops each technique from a small example into a complete
program.

**Apple Inc.**
*Apple Platform Security.*
A description of the security architecture of macOS, iOS, and Apple
silicon, including the boot process, code signing, and sandboxing. It
shows how one production system applies the privilege levels and the
isolation of our Chapters 2 and 16.

In addition to these books, two primary sources are useful. The POSIX
standard defines the interface that our listings use. The manual pages of
a system, such as `man 2 fork`, `man 2 mmap`, and `man 7 signal`, describe
each call as that system implements it. We recommend reading the manual
page of each call when it first appears in a chapter.
