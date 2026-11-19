// ch14/getaddrinfo.cpp: resolve a name and inspect what the resolver returns.
#include <arpa/inet.h>
#include <netdb.h>
#include <netinet/in.h>
#include <cstdio>

int main() {
    addrinfo hints{};
    hints.ai_family = AF_UNSPEC;
    hints.ai_socktype = SOCK_STREAM;

    addrinfo* list = nullptr;
    int rc = getaddrinfo("localhost", nullptr, &hints, &list);
    if (rc != 0) {
        printf("getaddrinfo: %s\n", gai_strerror(rc));
        return 1;
    }

    int i = 0;
    for (addrinfo* ai = list; ai != nullptr; ai = ai->ai_next, ++i) {
        char host[INET6_ADDRSTRLEN] = {};
        const void* src = nullptr;

        if (ai->ai_family == AF_INET) {
            src = &reinterpret_cast<sockaddr_in*>(ai->ai_addr)->sin_addr;
        } else if (ai->ai_family == AF_INET6) {
            src = &reinterpret_cast<sockaddr_in6*>(ai->ai_addr)->sin6_addr;
        }

        inet_ntop(ai->ai_family, src, host, sizeof host);
        printf("[%d] family=%s addr=%s socktype=%s\n", i,
               ai->ai_family == AF_INET ? "IPv4" : "IPv6", host,
               ai->ai_socktype == SOCK_STREAM ? "stream" : "other");
    }

    freeaddrinfo(list);
}
