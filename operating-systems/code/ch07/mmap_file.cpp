// ch07/mmap_file.cpp: Compares counting bytes via read(2) (kernel-to-user copy)
// against reading directly through an mmap(2) virtual memory mapping.
#include <fcntl.h>
#include <sys/mman.h>
#include <sys/stat.h>
#include <unistd.h>
#include <cstdio>
#include <vector>

int main() {
    const char* file_path = "/tmp/osbook_mmap_demo.txt";
    constexpr size_t kFileBytes = 4 * 1024 * 1024;  // 4 MiB test file
    constexpr size_t kLineBytes = 64;               // 63 'a' characters + '\n'

    // Step 1: Create and populate the 4 MiB file (65,536 lines of 64 bytes).
    int file_fd = open(file_path, O_CREAT | O_RDWR | O_TRUNC, 0644);
    if (file_fd < 0) {
        perror("open");
        return 1;
    }

    std::vector<char> line_buffer(kLineBytes, 'a');
    line_buffer[kLineBytes - 1] = '\n';

    for (size_t byte_offset = 0; byte_offset < kFileBytes; byte_offset += kLineBytes) {
        write(file_fd, line_buffer.data(), kLineBytes);
    }
    fsync(file_fd);

    // Step 2: Count 'a' bytes via read(2), which copies data from the kernel page cache
    // into our user-space `read_buffer` on every system call.
    lseek(file_fd, 0, SEEK_SET);
    long count_via_read = 0;
    char read_buffer[8192];
    ssize_t bytes_read = 0;

    while ((bytes_read = read(file_fd, read_buffer, sizeof read_buffer)) > 0) {
        for (ssize_t index = 0; index < bytes_read; ++index) {
            if (read_buffer[index] == 'a') ++count_via_read;
        }
    }

    // Step 3: Map the file directly into our virtual address space via mmap(2).
    // Hardware page faults map the kernel page cache frames directly into user PTEs.
    char* mapped_file = static_cast<char*>(
        mmap(nullptr, kFileBytes, PROT_READ, MAP_PRIVATE, file_fd, 0));
    if (mapped_file == MAP_FAILED) {
        perror("mmap");
        return 1;
    }

    long count_via_mmap = 0;
    for (size_t index = 0; index < kFileBytes; ++index) {
        if (mapped_file[index] == 'a') ++count_via_mmap;
    }

    struct stat file_stat {};
    fstat(file_fd, &file_stat);
    printf("file size   : %lld bytes\n", static_cast<long long>(file_stat.st_size));
    printf("read(2)     : %ld 'a' characters\n", count_via_read);
    printf("mmap        : %ld 'a' characters\n", count_via_mmap);
    printf("match       : %s\n", count_via_read == count_via_mmap ? "yes" : "NO");

    munmap(mapped_file, kFileBytes);
    close(file_fd);
    unlink(file_path);
}
