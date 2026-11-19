// ch07/pagesize.cpp: Queries hardware page size, maps three contiguous virtual pages,
// and converts the middle page into an inaccessible guard page via mprotect(PROT_NONE).
#include <sys/mman.h>
#include <unistd.h>
#include <csignal>
#include <csetjmp>
#include <cstdio>

static sigjmp_buf g_recovery_env;
static volatile void* g_fault_address = nullptr;

// Signal handler invoked by the kernel when the MMU raises a page protection fault.
static void on_protection_fault(int, siginfo_t* sig_info, void*) {
    g_fault_address = sig_info->si_addr;  // Exact virtual address that triggered the fault
    siglongjmp(g_recovery_env, 1);        // Resume execution cleanly in main()
}

int main() {
    // Query the hardware virtual-memory page granularity (4,096 B on x86-64; 16,384 B on Apple Silicon).
    long page_size = sysconf(_SC_PAGESIZE);
    printf("page size: %ld bytes\n", page_size);

    // Map three contiguous anonymous virtual pages with read/write permissions.
    // The kernel guarantees the returned base address is aligned to `page_size`.
    char* mapped_region = static_cast<char*>(
        mmap(nullptr, 3 * page_size, PROT_READ | PROT_WRITE, MAP_PRIVATE | MAP_ANON, -1, 0));
    if (mapped_region == MAP_FAILED) {
        perror("mmap");
        return 1;
    }

    printf("region:    %p (page-aligned by construction)\n", static_cast<void*>(mapped_region));

    // Write one byte into Page 0, Page 1, and Page 2 (triggering demand-zero physical frame allocation).
    mapped_region[0] = 'a';
    mapped_region[page_size] = 'b';
    mapped_region[2 * page_size] = 'c';

    // Convert Page 1 (the middle page) into a guard page by stripping all PTE permissions (PROT_NONE).
    if (mprotect(mapped_region + page_size, page_size, PROT_NONE) != 0) {
        perror("mprotect");
        return 1;
    }

    struct sigaction signal_action {};
    signal_action.sa_sigaction = on_protection_fault;
    signal_action.sa_flags = SA_SIGINFO;  // Deliver siginfo_t containing the faulting virtual address
    sigemptyset(&signal_action.sa_mask);

    // Linux delivers SIGSEGV for PTE permission faults; macOS/Darwin delivers SIGBUS.
    sigaction(SIGSEGV, &signal_action, nullptr);
    sigaction(SIGBUS, &signal_action, nullptr);

    if (sigsetjmp(g_recovery_env, 1) == 0) {
        mapped_region[page_size] = 'x';   // Triggers hardware page protection fault on Page 1
        printf("write succeeded (unexpected)\n");
    } else {
        printf("fault on write to %p\n", g_fault_address);
        printf("fault address is the guard page: %s\n",
               g_fault_address == static_cast<void*>(mapped_region + page_size) ? "yes" : "no");
    }

    // Neighboring Page 0 and Page 2 retain their permissions and data intact.
    printf("neighbors still readable: %c %c\n", mapped_region[0], mapped_region[2 * page_size]);

    munmap(mapped_region, 3 * page_size);
}
