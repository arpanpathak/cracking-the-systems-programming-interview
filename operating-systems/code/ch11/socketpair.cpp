// ch11/socketpair.cpp: a socketpair: one bidirectional channel, two directions.
#include <sys/socket.h>
#include <sys/wait.h>
#include <unistd.h>
#include <cstdio>
#include <cstring>

int main() {
    int sv[2];
    if (socketpair(AF_UNIX, SOCK_STREAM, 0, sv) != 0) {
        perror("socketpair");
        return 1;
    }

    pid_t pid = fork();
    if (pid == 0) {
        close(sv[0]);

        const char* msg = "ping from child";
        write(sv[1], msg, strlen(msg));

        char buf[64] = {};
        read(sv[1], buf, sizeof buf - 1);
        printf("child  received: \"%s\"\n", buf);
        fflush(stdout);

        _exit(0);
    }

    close(sv[1]);

    char buf[64] = {};
    read(sv[0], buf, sizeof buf - 1);
    printf("parent received: \"%s\"\n", buf);

    const char* reply = "pong from parent";
    write(sv[0], reply, strlen(reply));

    waitpid(pid, nullptr, 0);
}
