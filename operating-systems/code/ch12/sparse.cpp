// ch12/sparse.cpp: a sparse file: two small islands, a hole between them.
#include <fcntl.h>
#include <sys/stat.h>
#include <unistd.h>
#include <cstdio>
#include <cstring>

int main() {
    const char* path = "/tmp/osbook_sparse.txt";
    constexpr off_t kEnd = 8 * 1024 * 1024;   // logical size: 8 MiB

    int fd = open(path, O_CREAT | O_RDWR | O_TRUNC, 0644);
    if (fd < 0) {
        perror("open");
        return 1;
    }

    char island[4096];
    memset(island, 'a', sizeof island);

    write(fd, island, sizeof island);             // bytes 0..4096
    lseek(fd, 4 * 1024 * 1024, SEEK_SET);         // jump to 4 MiB
    write(fd, island, sizeof island);             // bytes 4M..4M+4096
    ftruncate(fd, kEnd);                          // extend to 8 MiB

    struct stat st {};
    fstat(fd, &st);
    printf("logical size : %lld bytes\n", static_cast<long long>(st.st_size));
    printf("blocks used  : %lld x 512 bytes = %lld bytes\n",
           static_cast<long long>(st.st_blocks),
           static_cast<long long>(st.st_blocks) * 512);

    // Read the hole: the file system supplies zeros.
    lseek(fd, 2 * 1024 * 1024, SEEK_SET);
    char probe[16];
    ssize_t n = read(fd, probe, sizeof probe);

    bool all_zero = true;
    for (ssize_t i = 0; i < n; ++i) {
        if (probe[i] != 0) all_zero = false;
    }

    printf("hole at 2 MiB reads back %zd bytes, all zero: %s\n", n,
           all_zero ? "yes" : "no");

    close(fd);
    unlink(path);
}
