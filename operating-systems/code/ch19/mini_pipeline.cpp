// ch19/mini_pipeline.cpp: what a shell does for `echo hello | tr a-z A-Z`.
#include <cstdio>
#include <sys/wait.h>
#include <unistd.h>

/// Forks a child whose stdin and stdout are replaced by the given descriptors,
/// then replaces the child with `argv[0]`. Returns the child's PID to the parent.
pid_t spawn(char* const argv[], int input_fd, int output_fd, int unused_fd) {
    pid_t pid = fork();
    if (pid != 0) {
        return pid;            // parent, or fork failed (-1)
    }

    if (input_fd != STDIN_FILENO) {
        dup2(input_fd, STDIN_FILENO);
        close(input_fd);
    }

    if (output_fd != STDOUT_FILENO) {
        dup2(output_fd, STDOUT_FILENO);
        close(output_fd);
    }

    close(unused_fd);          // the pipe end this child does not use

    execvp(argv[0], argv);
    perror("execvp");          // reached only if exec failed
    _exit(127);
}

int main() {
    int pipe_fds[2];
    if (pipe(pipe_fds) != 0) {
        perror("pipe");
        return 1;
    }

    char echo_word[] = "echo";
    char hello_word[] = "hello";
    char* const writer_argv[] = {echo_word, hello_word, nullptr};

    char tr_word[] = "tr";
    char lower_set[] = "a-z";
    char upper_set[] = "A-Z";
    char* const reader_argv[] = {tr_word, lower_set, upper_set, nullptr};

    // Nothing buffered may be copied into the children.
    fflush(stdout);

    pid_t writer = spawn(writer_argv, STDIN_FILENO, pipe_fds[1], pipe_fds[0]);
    pid_t reader = spawn(reader_argv, pipe_fds[0], STDOUT_FILENO, pipe_fds[1]);

    close(pipe_fds[0]);                  // the parent must close both ends, or `tr`
    close(pipe_fds[1]);                  // never sees end-of-file

    int writer_status = 0;
    int reader_status = 0;
    waitpid(writer, &writer_status, 0);
    waitpid(reader, &reader_status, 0);

    printf("echo exited with %d, tr exited with %d\n",
           WEXITSTATUS(writer_status), WEXITSTATUS(reader_status));
}
