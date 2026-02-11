#pragma once

#include <winsock2.h>
#include <ws2tcpip.h>

#include <cstdint>
#include <vector>
#include <mutex>
#include <atomic>

// IOCP 오퍼레이션 타입
enum class IOType : uint8_t {
    ACCEPT,
    RECV,
    SEND,
};

// Overlapped 확장 구조체 (IOCP가 완료 시 돌려주는 컨텍스트)
struct OverlappedEx {
    OVERLAPPED overlapped = {};
    IOType io_type = IOType::RECV;
    WSABUF wsa_buf = {};
};

// 네트워크 세션 (ECS 바깥, OS 수준)
// ECS의 SessionComponent가 이 세션의 ID를 참조한다.
class NetSession {
public:
    static constexpr int BUFFER_SIZE = 4096;

    NetSession();
    ~NetSession();

    void Init(SOCKET sock, uint64_t id);
    void Close();

    // 수신 시작 (IOCP에 등록)
    bool PostRecv();
    // 송신
    bool PostSend(const char* data, int len);

    SOCKET GetSocket() const { return socket_; }
    uint64_t GetId() const { return id_; }
    bool IsConnected() const { return connected_.load(); }

    // 수신 완료 시 데이터를 여기서 꺼냄
    char* GetRecvBuffer() { return recv_buffer_; }
    OverlappedEx& GetRecvOverlapped() { return recv_ov_; }

    // 송신용 버퍼 (간단 구현: 뮤텍스로 보호)
    void QueueSendData(const char* data, int len);
    bool FlushSend();

private:
    SOCKET socket_ = INVALID_SOCKET;
    uint64_t id_ = 0;
    std::atomic<bool> connected_{false};

    // 수신
    char recv_buffer_[BUFFER_SIZE] = {};
    OverlappedEx recv_ov_;

    // 송신
    std::mutex send_mutex_;
    std::vector<char> send_queue_;
    OverlappedEx send_ov_;
    bool sending_ = false;
};
