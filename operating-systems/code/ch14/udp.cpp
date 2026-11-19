// ch14/udp.cpp: a datagram sent to the loopback address and read back.
#include <arpa/inet.h>
#include <netinet/in.h>
#include <sys/socket.h>
#include <unistd.h>
#include <cstdio>
#include <cstring>

int main() {
    int fd = socket(AF_INET, SOCK_DGRAM, 0);
    if (fd < 0) {
        perror("socket");
        return 1;
    }

    sockaddr_in addr{};
    addr.sin_family = AF_INET;
    addr.sin_port = htons(45680);
    addr.sin_addr.s_addr = htonl(INADDR_LOOPBACK);

    if (bind(fd, reinterpret_cast<sockaddr*>(&addr), sizeof addr) != 0) {
        perror("bind");
        return 1;
    }

    const char* msg = "datagram";
    socklen_t len = sizeof addr;
    sendto(fd, msg, strlen(msg), 0, reinterpret_cast<sockaddr*>(&addr), len);

    char buf[64] = {};
    ssize_t n = recvfrom(fd, buf, sizeof buf - 1, 0, nullptr, nullptr);
    printf("sent %zu bytes, received %zd bytes: \"%s\"\n", strlen(msg), n, buf);

    close(fd);
}
