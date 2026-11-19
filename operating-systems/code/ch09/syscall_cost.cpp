// ch09/syscall_cost.cpp: compare a system call with a plain function call.
#include <unistd.h>
#include <chrono>
#include <cstdint>
#include <cstdio>

__attribute__((noinline)) int plain_fn(int x) { return x + 1; }

int main() {
    constexpr uint64_t kN = 5'000'000;

    // Plain function calls: nothing leaves user mode.
    uint64_t acc = 0;
    auto t0 = std::chrono::steady_clock::now();
    for (uint64_t i = 0; i < kN; ++i) {
        acc += static_cast<uint64_t>(plain_fn(static_cast<int>(acc & 0xff)));
    }
    auto t1 = std::chrono::steady_clock::now();

    double fn_ns =
        std::chrono::duration<double, std::nano>(t1 - t0).count() / kN;

    // System calls: each one traps into the kernel and back. We use getppid(),
    // not getpid(): on macOS libc caches getpid() after the first call, so a
    // getpid() loop would measure a library lookup, not a trap.
    pid_t pid = 0;
    auto t2 = std::chrono::steady_clock::now();
    for (uint64_t i = 0; i < kN; ++i) {
        pid = getppid();
    }
    auto t3 = std::chrono::steady_clock::now();

    double sys_ns =
        std::chrono::duration<double, std::nano>(t3 - t2).count() / kN;

    printf("plain function call  : %7.1f ns\n", fn_ns);
    printf("getppid() system call: %7.1f ns\n", sys_ns);
    printf("ratio                : %7.1fx\n", sys_ns / fn_ns);
    printf("(parent pid %d, checksum %llu)\n", pid,
           static_cast<unsigned long long>(acc));
}
