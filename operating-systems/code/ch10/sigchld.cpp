// ch10/sigchld.cpp: reaping by hand versus reaping by a SIGCHLD handler.
#include <sys/wait.h>
#include <unistd.h>
#include <csignal>
#include <cstdio>

static void on_sigchld(int) {
    int status;
    while (waitpid(-1, &status, WNOHANG) > 0) {
        // reap one exited child per iteration
    }
}

int main() {
    // Child 1: the parent reaps it by hand.
    pid_t c1 = fork();
    if (c1 == 0) {
        printf("child %d: exiting\n", getpid());
        fflush(stdout);
        _exit(0);
    }

    sleep(1);   // c1 sits unreaped (a zombie) during this second
    int status = 0;
    pid_t r = waitpid(c1, &status, 0);

    printf("parent reaped child %d by hand, status %d\n", r, WEXITSTATUS(status));
    fflush(stdout);   // flush before the next fork: the child inherits the buffer

    // Child 2: a SIGCHLD handler reaps it.
    struct sigaction sa {};
    sa.sa_handler = on_sigchld;
    sigemptyset(&sa.sa_mask);
    sa.sa_flags = SA_RESTART;
    sigaction(SIGCHLD, &sa, nullptr);

    pid_t c2 = fork();
    if (c2 == 0) {
        printf("child %d: exiting\n", getpid());
        fflush(stdout);
        _exit(0);
    }

    sleep(1);   // the pending SIGCHLD is delivered; the handler reaps c2
    r = waitpid(c2, &status, WNOHANG);
    printf("after handler: waitpid(WNOHANG) -> %d (-1 = already reaped)\n", r);
}
