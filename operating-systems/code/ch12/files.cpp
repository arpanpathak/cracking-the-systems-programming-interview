// ch12/files.cpp: open, write, seek, read, stat: the syscall layer of a file system.
#include <fcntl.h>
#include <sys/stat.h>
#include <unistd.h>
#include <cstdio>
#include <cstring>

int main() {
    const char* path = "/tmp/osbook_files.txt";

    int fd = open(path, O_CREAT | O_RDWR | O_TRUNC, 0644);
    if (fd < 0) {
        perror("open");
        return 1;
    }

    const char* line = "operating systems\n";   // 18 bytes
    write(fd, line, strlen(line));
    write(fd, line, strlen(line));

    // The file offset is a per-open-description cursor.
    printf("offset after two writes: %lld\n",
           static_cast<long long>(lseek(fd, 0, SEEK_CUR)));

    lseek(fd, 0, SEEK_SET);
    char buf[64] = {};
    ssize_t n = read(fd, buf, sizeof buf - 1);
    printf("read back %zd bytes:\n%s", n, buf);

    struct stat st {};
    fstat(fd, &st);
    printf("inode %llu, size %lld bytes, %lld blocks\n",
           static_cast<unsigned long long>(st.st_ino),
           static_cast<long long>(st.st_size),
           static_cast<long long>(st.st_blocks));

    fsync(fd);
    close(fd);
    unlink(path);
}
