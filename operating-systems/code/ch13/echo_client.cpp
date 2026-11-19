// ch13/echo_client.cpp: connect, send three messages, verify the echoes.
#include <arpa/inet.h>
#include <netinet/in.h>
#include <sys/socket.h>
#include <unistd.h>
#include <cstdio>
#include <cstring>

int main() {
    int fd = socket(AF_INET, SOCK_STREAM, 0);
    if (fd < 0) {
        perror("socket");
        return 1;
    }

    sockaddr_in addr{};
    addr.sin_family = AF_INET;
    addr.sin_port = htons(45678);
    addr.sin_addr.s_addr = htonl(INADDR_LOOPBACK);

    if (connect(fd, reinterpret_cast<sockaddr*>(&addr), sizeof addr) != 0) {
        perror("connect");
        return 1;
    }

    const char* msgs[] = {"one", "two", "three"};
    for (const char* m : msgs) {
        write(fd, m, strlen(m));
        char buf[64] = {};
        read(fd, buf, sizeof buf - 1);
        printf("sent \"%s\", got \"%s\" (%s)\n", m, buf,
               strcmp(m, buf) == 0 ? "ok" : "MISMATCH");
    }

    close(fd);
}
