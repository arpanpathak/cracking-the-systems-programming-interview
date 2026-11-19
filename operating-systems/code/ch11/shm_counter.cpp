// ch11/shm_counter.cpp: a counter in shared memory, guarded by a
// process-shared mutex. Parent and child each add half a million.
#include <sys/mman.h>
#include <sys/wait.h>
#include <unistd.h>
#include <pthread.h>
#include <cstdint>
#include <cstdio>

struct Shared {
    pthread_mutex_t mu;
    uint64_t counter;
};

int main() {
    constexpr uint64_t kIters = 500'000;

    Shared* s = static_cast<Shared*>(mmap(nullptr, sizeof(Shared),
                                          PROT_READ | PROT_WRITE,
                                          MAP_SHARED | MAP_ANON, -1, 0));
    if (s == MAP_FAILED) {
        perror("mmap");
        return 1;
    }

    pthread_mutexattr_t attr;
    pthread_mutexattr_init(&attr);
    pthread_mutexattr_setpshared(&attr, PTHREAD_PROCESS_SHARED);
    pthread_mutex_init(&s->mu, &attr);
    s->counter = 0;

    pid_t pid = fork();
    if (pid == 0) {
        for (uint64_t i = 0; i < kIters; ++i) {
            pthread_mutex_lock(&s->mu);
            ++s->counter;
            pthread_mutex_unlock(&s->mu);
        }
        _exit(0);
    }

    for (uint64_t i = 0; i < kIters; ++i) {
        pthread_mutex_lock(&s->mu);
        ++s->counter;
        pthread_mutex_unlock(&s->mu);
    }

    waitpid(pid, nullptr, 0);

    printf("expected %llu, observed %llu\n",
           static_cast<unsigned long long>(2 * kIters),
           static_cast<unsigned long long>(s->counter));

    pthread_mutex_destroy(&s->mu);
    munmap(s, sizeof(Shared));
}
