// ch15/kqueue_supervisor.cpp: process fault monitoring using kqueue on Darwin/BSD.
#include <sys/types.h>
#include <sys/event.h>
#include <sys/time.h>
#include <sys/wait.h>
#include <unistd.h>
#include <iostream>

int main() {
    int kq = kqueue();
    if (kq < 0) {
        std::cerr << "failed to create kqueue\n";
        return 1;
    }

    pid_t pid = fork();
    if (pid < 0) return 1;

    if (pid == 0) {
        // Child: simulated worker daemon that performs work and exits
        usleep(50000); // 50 ms
        _exit(0);
    }

    // Supervisor monitors the child lifecycle directly via EVFILT_PROC
    struct kevent change;
    EV_SET(&change, pid, EVFILT_PROC, EV_ADD | EV_ENABLE, NOTE_EXIT, 0, nullptr);

    if (kevent(kq, &change, 1, nullptr, 0, nullptr) < 0) {
        std::cerr << "failed to register kevent\n";
        return 1;
    }

    struct kevent event;
    int nev = kevent(kq, nullptr, 0, &event, 1, nullptr);
    if (nev > 0 && (event.fflags & NOTE_EXIT)) {
        int status = 0;
        waitpid(pid, &status, WNOHANG);
        std::cout << "supervisor detected child " << pid
                  << " termination, exit status: " << WEXITSTATUS(status) << "\n";
    }

    close(kq);
    return 0;
}
