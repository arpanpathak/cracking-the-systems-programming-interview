# About this book

In this book, we will learn how Linux works and dive deep into the kernel's machinery
with hands-on examples, both in Rust and Go. We will first build intuition by reasoning
and quickly prototype the data structures behind each kernel mechanism. Then we will run
the same experiments against the real kernel and compare the results.

Linux runs most of the world's servers and phones, and the machines that train and serve
AI models. Containers, Kubernetes, and cloud platforms are all built on a small set of
kernel mechanisms: pipes, processes, file descriptors, signals, virtual memory,
namespaces, and control groups. When we understand these mechanisms, we can reason about
what a container is, why a service stalls, and where a machine's memory has gone.

The kernel is tens of millions of lines of C, and knowing all of it can look like a pipe
dream. The ideas inside it are much smaller than the code. A pipe is a ring of pages
indexed by a pair of counters. A container is a process with a restricted view of the system. Each
of these is small enough for us to build ourselves, so we will build them one at a time,
starting with the pipe.

The examples run on any Linux machine. The output shown in this book was recorded on a
Jetson Orin NX, an arm64 machine running Linux 5.15.
