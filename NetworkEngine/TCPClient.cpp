#include "TCPClient.h"
#include <cstdio>

#pragma comment(lib, "ws2_32.lib")

TCPClient::~TCPClient() {
    Disconnect();
}

bool TCPClient::Connect(const char* host, uint16_t port) {
    if (connected_) Disconnect();

    // WSAStartup should already be called by IOCPServer
    sock_ = socket(AF_INET, SOCK_STREAM, IPPROTO_TCP);
    if (sock_ == INVALID_SOCKET) {
        printf("[TCPClient] socket() failed: %d\n", WSAGetLastError());
        return false;
    }

    sockaddr_in addr = {};
    addr.sin_family = AF_INET;
    addr.sin_port = htons(port);
    inet_pton(AF_INET, host, &addr.sin_addr);

    if (connect(sock_, reinterpret_cast<sockaddr*>(&addr), sizeof(addr)) == SOCKET_ERROR) {
        closesocket(sock_);
        sock_ = INVALID_SOCKET;
        return false;
    }

    connected_ = true;
    printf("[TCPClient] Connected to %s:%d\n", host, port);
    return true;
}

bool TCPClient::Send(const char* data, int len) {
    if (!connected_ || sock_ == INVALID_SOCKET) return false;

    int sent = 0;
    while (sent < len) {
        int r = ::send(sock_, data + sent, len - sent, 0);
        if (r == SOCKET_ERROR) {
            printf("[TCPClient] send failed: %d\n", WSAGetLastError());
            connected_ = false;
            return false;
        }
        sent += r;
    }
    return true;
}

int TCPClient::RecvWithTimeout(char* buf, int max_len, int timeout_ms) {
    if (!connected_ || sock_ == INVALID_SOCKET) return -1;

    fd_set readfds;
    FD_ZERO(&readfds);
    FD_SET(sock_, &readfds);

    timeval tv;
    tv.tv_sec = timeout_ms / 1000;
    tv.tv_usec = (timeout_ms % 1000) * 1000;

    int sel = select(0, &readfds, nullptr, nullptr, &tv);
    if (sel <= 0) return 0;  // timeout or error

    int r = recv(sock_, buf, max_len, 0);
    if (r <= 0) {
        connected_ = false;
        return -1;
    }
    return r;
}

void TCPClient::Disconnect() {
    if (sock_ != INVALID_SOCKET) {
        closesocket(sock_);
        sock_ = INVALID_SOCKET;
    }
    connected_ = false;
}
