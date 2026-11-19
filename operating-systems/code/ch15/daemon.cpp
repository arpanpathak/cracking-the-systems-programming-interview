// ch15/daemon.cpp: a complete daemon lifecycle in C++.
// double fork, setsid, redirected stdio, pidfile, signal-driven shutdown.
#include <fcntl.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <unistd.h>
#include <csignal>
#include <cstdio>

static volatile sig_atomic_t g_reload = 0;
static volatile sig_atomic_t g_stop = 0;

static void on_hup(int) { g_reload = 1; }
static void on_term(int) { g_stop = 1; }

int main() {
    const char* pidfile = "/tmp/osbook_daemon.pid";
    const char* logfile = "/tmp/osbook_daemon.log";

    pid_t pid = fork();
    if (pid < 0) return 1;
    if (pid > 0) _exit(0);          // first parent exits

    setsid();                       // new session: no controlling terminal

    pid = fork();
    if (pid > 0) _exit(0);          // session leader exits; terminal cannot return

    umask(0027);
    chdir("/");

    // stdout/stderr to the log, stdin from /dev/null.
    int fd = open(logfile, O_CREAT | O_WRONLY | O_APPEND, 0644);
    if (fd < 0) return 1;
    dup2(fd, STDOUT_FILENO);
    dup2(fd, STDERR_FILENO);
    close(fd);

    int devnull = open("/dev/null", O_RDONLY);
    dup2(devnull, STDIN_FILENO);
    close(devnull);

    FILE* pf = fopen(pidfile, "w");
    if (pf == nullptr) return 1;
    fprintf(pf, "%d\n", getpid());
    fclose(pf);

    struct sigaction sa {};
    sa.sa_handler = on_hup;
    sigemptyset(&sa.sa_mask);
    sigaction(SIGHUP, &sa, nullptr);

    sa.sa_handler = on_term;
    sigaction(SIGTERM, &sa, nullptr);

    printf("daemon %d started\n", getpid());
    fflush(stdout);

    int ticks = 0;
    while (!g_stop) {
        sleep(1);
        ++ticks;

        printf("tick %d\n", ticks);
        fflush(stdout);

        if (g_reload) {
            g_reload = 0;
            printf("reload requested\n");
            fflush(stdout);
        }
    }

    printf("stopping after %d ticks\n", ticks);
    unlink(pidfile);
    return 0;
}
