// ch09/write_buffered.cpp: many small writes, buffered and unbuffered.
#include <fcntl.h>
#include <unistd.h>
#include <chrono>
#include <cstdio>

int main() {
    constexpr int kN = 200'000;
    const char msg[] = "0123456789abcdef\n";   // 17 bytes

    int fd = open("/dev/null", O_WRONLY);
    if (fd < 0) {
        perror("open");
        return 1;
    }

    // Unbuffered: one write(2) system call per iteration.
    auto t0 = std::chrono::steady_clock::now();
    for (int i = 0; i < kN; ++i) {
        write(fd, msg, sizeof msg - 1);
    }
    auto t1 = std::chrono::steady_clock::now();

    double raw_ms = std::chrono::duration<double, std::milli>(t1 - t0).count();

    // Buffered: stdio accumulates in a 64 KiB buffer, then flushes once.
    FILE* f = fopen("/dev/null", "w");
    setvbuf(f, nullptr, _IOFBF, 64 * 1024);

    auto t2 = std::chrono::steady_clock::now();
    for (int i = 0; i < kN; ++i) {
        fwrite(msg, 1, sizeof msg - 1, f);
    }
    fflush(f);
    auto t3 = std::chrono::steady_clock::now();

    double buf_ms = std::chrono::duration<double, std::milli>(t3 - t2).count();

    printf("write(2) into /dev/null, %d x 17 bytes : %7.1f ms\n", kN, raw_ms);
    printf("fwrite buffered, %d x 17 bytes         : %7.1f ms\n", kN, buf_ms);

    close(fd);
    fclose(f);
}
