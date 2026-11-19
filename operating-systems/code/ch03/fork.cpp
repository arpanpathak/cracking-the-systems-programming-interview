// ch03/fork.cpp: one program, two processes.
#include <sys/wait.h>
#include <unistd.h>
#include <cstdio>

int main() {
    printf("before fork: pid=%d\n", getpid());

    pid_t pid = fork();
    if (pid < 0) {
        perror("fork");
        return 1;
    }

    if (pid == 0) {
        // Child: fork() returned 0 here.
        printf("child : pid=%d parent=%d\n", getpid(), getppid());
        fflush(stdout);           // _exit() skips stdio flushing
        _exit(7);
    }

    // Parent: fork() returned the child's pid here.
    int status = 0;
    waitpid(pid, &status, 0);
    if (WIFEXITED(status)) {
        printf("parent: child %d exited with status %d\n", pid, WEXITSTATUS(status));
    }

    return 0;
}
