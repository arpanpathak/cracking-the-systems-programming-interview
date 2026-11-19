// ch07/mmap_file.cpp: read a file with read(2), then map it and read it again.
#include <fcntl.h>
#include <sys/mman.h>
#include <sys/stat.h>
#include <unistd.h>
#include <cstdio>
#include <vector>

int main() {
    const char* path = "/tmp/osbook_mmap_demo.txt";
    constexpr size_t kSize = 4 * 1024 * 1024;   // 4 MiB
    constexpr size_t kLine = 64;                // 63 'a' + newline

    // 1. Create the file: 65,536 identical lines.
    int fd = open(path, O_CREAT | O_RDWR | O_TRUNC, 0644);
    if (fd < 0) {
        perror("open");
        return 1;
    }

    std::vector<char> line(kLine, 'a');
    line[kLine - 1] = '\n';

    for (size_t off = 0; off < kSize; off += kLine) {
        write(fd, line.data(), kLine);
    }

    fsync(fd);

    // 2. Count characters with read(2): the file is copied into a buffer first.
    lseek(fd, 0, SEEK_SET);
    long via_read = 0;
    char buf[8192];
    ssize_t n;

    while ((n = read(fd, buf, sizeof buf)) > 0) {
        for (ssize_t i = 0; i < n; ++i) {
            if (buf[i] == 'a') ++via_read;
        }
    }

    // 3. Map the file and count again: no explicit copies in the loop.
    char* map = static_cast<char*>(mmap(nullptr, kSize, PROT_READ, MAP_PRIVATE, fd, 0));
    if (map == MAP_FAILED) {
        perror("mmap");
        return 1;
    }

    long via_mmap = 0;
    for (size_t i = 0; i < kSize; ++i) {
        if (map[i] == 'a') ++via_mmap;
    }

    struct stat st {};
    fstat(fd, &st);
    printf("file size   : %lld bytes\n", static_cast<long long>(st.st_size));
    printf("read(2)     : %ld 'a' characters\n", via_read);
    printf("mmap        : %ld 'a' characters\n", via_mmap);
    printf("match       : %s\n", via_read == via_mmap ? "yes" : "NO");

    munmap(map, kSize);
    close(fd);
    unlink(path);
}
