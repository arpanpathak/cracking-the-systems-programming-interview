// ch10/signals.cpp: block a signal, watch it stay pending, then deliver it.
#include <csignal>
#include <unistd.h>
#include <cstdio>

static volatile sig_atomic_t g_got_usr1 = 0;
static volatile sig_atomic_t g_got_int = 0;

static void on_usr1(int) { g_got_usr1 = 1; }
static void on_int(int) { g_got_int = 1; }

int main() {
    struct sigaction sa {};
    sa.sa_handler = on_usr1;
    sigemptyset(&sa.sa_mask);
    sigaction(SIGUSR1, &sa, nullptr);

    sa.sa_handler = on_int;
    sigaction(SIGINT, &sa, nullptr);

    // Block SIGUSR1, send it to ourselves, and observe that it stays pending.
    sigset_t set, oldset;
    sigemptyset(&set);
    sigaddset(&set, SIGUSR1);
    sigprocmask(SIG_BLOCK, &set, &oldset);

    raise(SIGUSR1);   // queued, not delivered
    printf("after raise while blocked: handled=%d\n", static_cast<int>(g_got_usr1));

    sigprocmask(SIG_UNBLOCK, &set, nullptr);   // delivery happens here
    printf("after unblock: handled=%d\n", static_cast<int>(g_got_usr1));

    raise(SIGINT);    // delivered immediately
    printf("after SIGINT: handled=%d\n", static_cast<int>(g_got_int));

    sigprocmask(SIG_SETMASK, &oldset, nullptr);
}
