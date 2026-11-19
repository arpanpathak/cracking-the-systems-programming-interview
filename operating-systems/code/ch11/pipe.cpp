// ch11/pipe.cpp: one pipe, one fork, one message from child to parent.
#include <sys/wait.h>
#include <unistd.h>
#include <cstdio>
#include <cstring>

int main() {
    int fds[2];
    if (pipe(fds) != 0) {
        perror("pipe");
        return 1;
    }

    pid_t pid = fork();
    if (pid == 0) {
        close(fds[0]);                        // child keeps the write end
        const char* msg = "hello from child";
        write(fds[1], msg, strlen(msg));
        close(fds[1]);
        _exit(0);
    }

    close(fds[1]);                            // parent keeps the read end

    char buf[64] = {};
    ssize_t n = read(fds[0], buf, sizeof buf - 1);
    waitpid(pid, nullptr, 0);

    printf("parent read %zd bytes: \"%s\"\n", n, buf);
}
