# 4. Filesystems, Overlayfs, and I/O {#filesystems-and-io}

Every container image is a stack of read-only layers with one writable layer
on top, and the filesystem that makes that stack behave like a single
directory tree is overlayfs. Understanding it, and the VFS objects underneath
it, answers two questions that come up constantly on a real cluster: why the
first write to a large file inside a container is slow, and why two processes
can hold what looks like the same file open at different positions.

## VFS and core objects

The Linux VFS abstracts filesystem implementations behind four objects. A
`super_block` represents a mounted filesystem. An `inode` holds a file's
metadata: owner, mode, size, block pointers. A `dentry` is a directory entry
mapping a name to an inode, heavily cached by the VFS. A `file` is an open
file description with its own offset, flags, and operation methods.

These objects nest. A `super_block` owns a set of `inode`s. An `inode` has no
name of its own. A `dentry` is what gives an inode a name inside a directory.
A `file` is a per-open-descriptor view with its own offset. That structure
explains three things that otherwise look like trivia: two processes can hold
the same file open at different offsets, because that is two `file` objects
referencing one `inode`; renaming a file does not change the inode it refers
to, only the `dentry` moved; and a hard link is a second `dentry` pointing at
an existing `inode`, so a hard link cannot cross filesystems, since a `dentry`
on one filesystem cannot name an `inode` that belongs to another.

At the syscall boundary this becomes an error convention: failure is `-1`
with `errno` set, and `errno` is thread-local, so it stays safe to use from a
threaded program.

```c
/* errno.c: the syscall boundary reports failure with -1 plus errno. */
#include <errno.h>
#include <fcntl.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>

static void try_open(const char *path)
{
    char buf[64];
    ssize_t n;
    int fd = open(path, O_RDONLY);

    if (fd < 0) {
        printf("open(\"%s\") = -1 errno=%d (%s)\n", path, errno, strerror(errno));
        return;
    }
    printf("open(\"%s\") = %d\n", path, fd);

    n = read(fd, buf, sizeof buf - 1);      /* may return fewer bytes than asked */
    if (n > 0) {
        buf[n] = '\0';
        if (buf[n - 1] == '\n')
            buf[n - 1] = '\0';
        printf("  read() returned %zd byte(s): \"%s\"\n", n, buf);
    }
    close(fd);
}

int main(void)
{
    try_open("/definitely/not/here");
    try_open("/etc/hostname");
    try_open("/etc/shadow");                /* exists, but not readable by this uid */
    return 0;
}
```

```text
$ gcc -O2 -o errno errno.c && ./errno
open("/definitely/not/here") = -1 errno=2 (No such file or directory)
open("/etc/hostname") = 3
  read() returned 8 byte(s): "yahboom"
open("/etc/shadow") = -1 errno=13 (Permission denied)
```

Three distinct failures appear in those four lines. `ENOENT` (2) and `EACCES`
(13) are different conditions a caller must be able to distinguish, which is
the reason `errno` exists instead of a single "it failed" return. The
descriptor is 3 rather than 1 because 0, 1, and 2 are already stdin, stdout,
and stderr: the descriptor table is a small integer namespace per process, and
exhausting it is a failure mode, `EMFILE`, seen in servers. And `read`
returned 8 bytes; a syscall is permitted to return fewer bytes than requested
at any time, so a correct reader loops. Treating a short read as an error, or
as end of file, is one of the most common bugs in systems code.

## Filesystems relevant to Kubernetes

ext4 and xfs are the standard local disk filesystems. tmpfs is RAM-backed,
used for `emptyDir` volumes with `medium: Memory` and for `/dev/shm`.
Overlayfs combines lower, read-only image layers with an upper writable
layer, and is what containerd and Docker use for image rootfs. FUSE backs
user-space filesystems used by some CSI drivers and tools such as gcsfuse.
Network filesystems cover NFS and cloud CSI volumes such as EBS, EFS, and PVC
backends generally.

Overlayfs's defining behavior is copy-up: when a container modifies a file
that exists in a lower image layer, the kernel copies that file to the upper
layer before performing the write. Deleting a file that exists in a lower
layer creates a whiteout entry in the upper layer rather than removing
anything from the lower one. This is why the first write to a large file that
lives in a lower layer is expensive inside a container: the whole file has to
be copied up before a single byte changes.

## Mount propagation

Mounts propagate between mount namespaces according to one of four modes:
`shared`, `slave`, `private`, and `unbindable`. Kubernetes relies on this for
`hostPath` volumes and for the container runtime to inject devices and
libraries. `mount --make-rshared /` is common on nodes so that mounts created
inside containers stay visible where the host needs to see them.
Misconfigured propagation shows up as "device or resource busy" errors or as
mounts that silently do not appear where expected.

```bash
mount | grep -E 'overlay|nvidia|/var/lib/kubelet'
cat /proc/self/mountinfo
findmnt -R /var/lib/kubelet | head -50
```

## The I/O stack and pressure

The I/O path runs process syscall, VFS, filesystem, block layer, device
driver. The page cache absorbs reads and writes; dirty pages are written back
later by per-device writeback threads. `iostat -x 1` reports `%util`, await,
and service time; `pidstat -d 1` reports per-process I/O; `iotop` shows
per-process I/O in real time; and `/proc/pressure/io`,
`/proc/pressure/memory`, and `/proc/pressure/cpu` expose Pressure Stall
Information, which is a more actionable signal of contention than raw
utilization percentages, and is covered further in Chapter 6.

## References

- Kerrisk, *The Linux Programming Interface*, the chapters on files and file
  I/O.
- The kernel documentation for overlayfs, under
  `Documentation/filesystems/overlayfs.rst`.
- The `proc(5)` man page, for `/proc/<pid>/mountinfo` and pressure stall
  information.
