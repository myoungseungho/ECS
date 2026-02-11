#pragma once

#include <winsock2.h>
#include <ws2tcpip.h>

#include "Session.h"
#include <cstdint>
#include <unordered_map>
#include <memory>
#include <vector>
#include <thread>
#include <mutex>
#include <functional>
#include <atomic>

// IOCP 이벤트 (워커 스레드 → 메인 스레드로 전달)
struct IOCPEvent {
    enum class Type { CONNECTED, DISCONNECTED, DATA_RECEIVED };

    Type type;
    uint64_t session_id;
    std::vector<char> data;  // DATA_RECEIVED일 때만 사용
};

// IOCP 기반 네트워크 서버 (ECS 바깥)
// NetworkSystem이 이 서버의 이벤트를 폴링해서 ECS 세계로 가져감
class IOCPServer {
public:
    IOCPServer();
    ~IOCPServer();

    // 서버 시작 (포트, 워커 스레드 수)
    bool Start(uint16_t port, int worker_count = 2);
    void Stop();

    // 메인 스레드에서 호출: 이벤트 꺼내기
    // NetworkSystem이 매 틱마다 이걸 호출
    std::vector<IOCPEvent> PollEvents();

    // 세션에 데이터 전송
    bool SendTo(uint64_t session_id, const char* data, int len);

    // 세션 끊기
    void Disconnect(uint64_t session_id);

    bool IsRunning() const { return running_.load(); }

private:
    void AcceptThread();
    void WorkerThread();

    void OnAccept(SOCKET client_sock);
    void OnRecv(NetSession* session, int bytes_transferred);
    void OnSend(OverlappedEx* ov);
    void OnDisconnect(NetSession* session);

    void PushEvent(IOCPEvent event);

    HANDLE iocp_ = nullptr;
    SOCKET listen_socket_ = INVALID_SOCKET;
    std::atomic<bool> running_{false};

    // 세션 관리
    std::mutex session_mutex_;
    std::unordered_map<uint64_t, std::unique_ptr<NetSession>> sessions_;
    uint64_t next_session_id_ = 1;

    // 이벤트 큐 (워커 → 메인)
    std::mutex event_mutex_;
    std::vector<IOCPEvent> event_queue_;

    // 스레드
    std::thread accept_thread_;
    std::vector<std::thread> worker_threads_;
};
