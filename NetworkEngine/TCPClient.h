#pragma once

#include <winsock2.h>
#include <ws2tcpip.h>
#include <cstdint>

// Session 17: Simple blocking TCP client for server-to-server communication
// Field -> Gate connection uses this (not IOCP - just a plain socket)
class TCPClient {
public:
    TCPClient() = default;
    ~TCPClient();

    // Blocking connect
    bool Connect(const char* host, uint16_t port);

    // Blocking send (fine for small heartbeat packets)
    bool Send(const char* data, int len);

    // Recv with timeout (select + recv)
    // Returns: >0 bytes received, 0 = timeout, -1 = error/disconnected
    int RecvWithTimeout(char* buf, int max_len, int timeout_ms);

    void Disconnect();
    bool IsConnected() const { return connected_; }

private:
    SOCKET sock_ = INVALID_SOCKET;
    bool connected_ = false;
};
