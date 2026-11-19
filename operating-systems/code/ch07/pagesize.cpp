// ch07/pagesize.cpp: page size, page alignment, and a guard page that faults.
#include <sys/mman.h>
#include <unistd.h>
#include <csignal>
#include <csetjmp>
#include <cstdio>

static sigjmp_buf g_env;
static volatile void* g_fault_addr = nullptr;

static void on_segv(int, siginfo_t* si, void*) {
    g_fault_addr = si->si_addr;   // address the CPU tried to touch
    siglongjmp(g_env, 1);
}

int main() {
    long ps = sysconf(_SC_PAGESIZE);
    printf("page size: %ld bytes\n", ps);

    // Three anonymous pages, mapped readable and writable.
    char* region = static_cast<char*>(
        mmap(nullptr, 3 * ps, PROT_READ | PROT_WRITE, MAP_PRIVATE | MAP_ANON, -1, 0));
    if (region == MAP_FAILED) {
        perror("mmap");
        return 1;
    }

    printf("region:    %p (page-aligned by construction)\n", static_cast<void*>(region));

    region[0] = 'a';
    region[ps] = 'b';
    region[2 * ps] = 'c';

    // Turn the middle page into a guard page: any access faults.
    if (mprotect(region + ps, ps, PROT_NONE) != 0) {
        perror("mprotect");
        return 1;
    }

    struct sigaction sa {};
    sa.sa_sigaction = on_segv;
    sa.sa_flags = SA_SIGINFO;
    sigemptyset(&sa.sa_mask);

    // macOS reports protection violations as SIGBUS; Linux reports SIGSEGV.
    sigaction(SIGSEGV, &sa, nullptr);
    sigaction(SIGBUS, &sa, nullptr);

    if (sigsetjmp(g_env, 1) == 0) {
        region[ps] = 'x';          // faults: page has PROT_NONE
        printf("write succeeded (unexpected)\n");
    } else {
        printf("fault on write to %p\n", g_fault_addr);
        printf("fault address is the guard page: %s\n",
               g_fault_addr == static_cast<void*>(region + ps) ? "yes" : "no");
    }

    // The neighbors are untouched by the fault.
    printf("neighbors still readable: %c %c\n", region[0], region[2 * ps]);

    munmap(region, 3 * ps);
}
