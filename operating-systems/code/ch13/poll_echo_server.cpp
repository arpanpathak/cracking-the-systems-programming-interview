// ch13/poll_echo_server.cpp: one thread, several clients, poll(2).
// Serves two clients, then exits; the harness starts it and runs two clients.
#include <arpa/inet.h>
#include <netinet/in.h>
#include <poll.h>
#include <sys/socket.h>
#include <unistd.h>
#include <cstdio>
#include <vector>

int main() {
    int ls = socket(AF_INET, SOCK_STREAM, 0);
    if (ls < 0) {
        perror("socket");
        return 1;
    }

    int one = 1;
    setsockopt(ls, SOL_SOCKET, SO_REUSEADDR, &one, sizeof one);

    sockaddr_in addr{};
    addr.sin_family = AF_INET;
    addr.sin_port = htons(45678);
    addr.sin_addr.s_addr = htonl(INADDR_LOOPBACK);

    if (bind(ls, reinterpret_cast<sockaddr*>(&addr), sizeof addr) != 0) {
        perror("bind");
        return 1;
    }

    listen(ls, 8);
    printf("listening on 127.0.0.1:45678\n");

    std::vector<pollfd> fds{{ls, POLLIN, 0}};
    int clients_served = 0;

    while (clients_served < 2) {
        int rc = poll(fds.data(), fds.size(), 1000);
        if (rc < 0) {
            perror("poll");
            return 1;
        }

        for (size_t i = 0; i < fds.size(); ++i) {
            if (!(fds[i].revents & POLLIN)) continue;

            if (fds[i].fd == ls) {
                int c = accept(ls, nullptr, nullptr);
                printf("accepted fd %d\n", c);
                fds.push_back({c, POLLIN, 0});
            } else {
                char buf[256];
                ssize_t n = read(fds[i].fd, buf, sizeof buf - 1);
                if (n <= 0) {
                    printf("client fd %d closed\n", fds[i].fd);
                    close(fds[i].fd);
                    fds.erase(fds.begin() + i);
                    --i;
                    ++clients_served;
                } else {
                    buf[n] = 0;
                    printf("echoing %zd bytes to fd %d\n", n, fds[i].fd);
                    write(fds[i].fd, buf, n);
                }
            }
        }
    }

    printf("served 2 clients, exiting\n");
    close(ls);
}
