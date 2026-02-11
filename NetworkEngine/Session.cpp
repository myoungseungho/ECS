#include "Session.h"
#include <cstring>
#include <cstdio>

NetSession::NetSession() = default;

NetSession::~NetSession() {
    Close();
}

void NetSession::Init(SOCKET sock, uint64_t id) {
    socket_ = sock;
    id_ = id;
    connected_ = true;

    memset(&recv_ov_, 0, sizeof(recv_ov_));
    recv_ov_.io_type = IOType::RECV;

    memset(&send_ov_, 0, sizeof(send_ov_));
    send_ov_.io_type = IOType::SEND;
}

void NetSession::Close() {
    // atomic CAS로 한 번만 실행 보장 (다중 워커 스레드 안전)
    bool expected = true;
    if (!connected_.compare_exchange_strong(expected, false)) return;

    if (socket_ != INVALID_SOCKET) {
        closesocket(socket_);
        socket_ = INVALID_SOCKET;
    }
}

bool NetSession::PostRecv() {
    if (!connected_) return false;

    memset(&recv_ov_.overlapped, 0, sizeof(OVERLAPPED));
    recv_ov_.wsa_buf.buf = recv_buffer_;
    recv_ov_.wsa_buf.len = BUFFER_SIZE;

    DWORD flags = 0;
    int ret = WSARecv(socket_, &recv_ov_.wsa_buf, 1, nullptr, &flags,
                      &recv_ov_.overlapped, nullptr);

    if (ret == SOCKET_ERROR) {
        int err = WSAGetLastError();
        if (err != WSA_IO_PENDING) {
            printf("[Session %llu] WSARecv failed: %d\n", id_, err);
            return false;
        }
    }
    return true;
}

bool NetSession::PostSend(const char* data, int len) {
    if (!connected_ || len <= 0) return false;

    // 직접 송신
    OverlappedEx* ov = new OverlappedEx();
    memset(ov, 0, sizeof(OverlappedEx));
    ov->io_type = IOType::SEND;

    // 데이터 복사 (ov 뒤에 데이터를 붙여서 수명 관리)
    char* buf = new char[len];
    memcpy(buf, data, len);

    ov->wsa_buf.buf = buf;
    ov->wsa_buf.len = len;

    DWORD sent = 0;
    int ret = WSASend(socket_, &ov->wsa_buf, 1, &sent, 0,
                      &ov->overlapped, nullptr);

    if (ret == SOCKET_ERROR) {
        int err = WSAGetLastError();
        if (err != WSA_IO_PENDING) {
            printf("[Session %llu] WSASend failed: %d\n", id_, err);
            delete[] buf;
            delete ov;
            return false;
        }
    }
    return true;
}

void NetSession::QueueSendData(const char* data, int len) {
    std::lock_guard<std::mutex> lock(send_mutex_);
    send_queue_.insert(send_queue_.end(), data, data + len);
}

bool NetSession::FlushSend() {
    std::lock_guard<std::mutex> lock(send_mutex_);
    if (send_queue_.empty()) return true;

    bool ok = PostSend(send_queue_.data(), static_cast<int>(send_queue_.size()));
    send_queue_.clear();
    return ok;
}
