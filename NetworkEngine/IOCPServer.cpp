#include "IOCPServer.h"
#include <cstdio>

#pragma comment(lib, "ws2_32.lib")

IOCPServer::IOCPServer() = default;

IOCPServer::~IOCPServer() {
    Stop();
}

bool IOCPServer::Start(uint16_t port, int worker_count) {
    // Winsock 초기화
    WSADATA wsa;
    if (WSAStartup(MAKEWORD(2, 2), &wsa) != 0) {
        printf("[IOCP] WSAStartup failed\n");
        return false;
    }

    // IOCP 생성
    iocp_ = CreateIoCompletionPort(INVALID_HANDLE_VALUE, nullptr, 0, 0);
    if (!iocp_) {
        printf("[IOCP] CreateIoCompletionPort failed\n");
        return false;
    }

    // 리슨 소켓
    listen_socket_ = WSASocketW(AF_INET, SOCK_STREAM, IPPROTO_TCP,
                                nullptr, 0, WSA_FLAG_OVERLAPPED);
    if (listen_socket_ == INVALID_SOCKET) {
        printf("[IOCP] WSASocket failed\n");
        return false;
    }

    // SO_REUSEADDR
    int opt = 1;
    setsockopt(listen_socket_, SOL_SOCKET, SO_REUSEADDR,
               reinterpret_cast<const char*>(&opt), sizeof(opt));

    // 바인드 + 리슨
    sockaddr_in addr = {};
    addr.sin_family = AF_INET;
    addr.sin_port = htons(port);
    addr.sin_addr.s_addr = INADDR_ANY;

    if (bind(listen_socket_, reinterpret_cast<sockaddr*>(&addr), sizeof(addr)) == SOCKET_ERROR) {
        printf("[IOCP] bind failed: %d\n", WSAGetLastError());
        return false;
    }

    if (listen(listen_socket_, SOMAXCONN) == SOCKET_ERROR) {
        printf("[IOCP] listen failed: %d\n", WSAGetLastError());
        return false;
    }

    running_ = true;

    // Accept 스레드
    accept_thread_ = std::thread(&IOCPServer::AcceptThread, this);

    // Worker 스레드
    for (int i = 0; i < worker_count; ++i) {
        worker_threads_.emplace_back(&IOCPServer::WorkerThread, this);
    }

    printf("[IOCP] Server started on port %d (workers: %d)\n", port, worker_count);
    return true;
}

void IOCPServer::Stop() {
    if (!running_.exchange(false)) return;

    // 리슨 소켓 닫기 → Accept 스레드 종료
    if (listen_socket_ != INVALID_SOCKET) {
        closesocket(listen_socket_);
        listen_socket_ = INVALID_SOCKET;
    }

    // 워커 스레드 종료 신호 (더미 Completion)
    for (size_t i = 0; i < worker_threads_.size(); ++i) {
        PostQueuedCompletionStatus(iocp_, 0, 0, nullptr);
    }

    if (accept_thread_.joinable()) accept_thread_.join();
    for (auto& t : worker_threads_) {
        if (t.joinable()) t.join();
    }

    // 세션 정리
    {
        std::lock_guard<std::mutex> lock(session_mutex_);
        sessions_.clear();
    }

    if (iocp_) {
        CloseHandle(iocp_);
        iocp_ = nullptr;
    }

    WSACleanup();
    printf("[IOCP] Server stopped\n");
}

void IOCPServer::AcceptThread() {
    printf("[IOCP] Accept thread started\n");
    while (running_) {
        sockaddr_in client_addr = {};
        int addr_len = sizeof(client_addr);
        SOCKET client = accept(listen_socket_,
                               reinterpret_cast<sockaddr*>(&client_addr),
                               &addr_len);

        if (client == INVALID_SOCKET) {
            if (running_) {
                printf("[IOCP] accept failed: %d\n", WSAGetLastError());
            }
            break;
        }

        OnAccept(client);
    }
    printf("[IOCP] Accept thread ended\n");
}

void IOCPServer::WorkerThread() {
    while (running_) {
        DWORD bytes = 0;
        ULONG_PTR key = 0;
        OVERLAPPED* ov = nullptr;

        BOOL ok = GetQueuedCompletionStatus(iocp_, &bytes, &key, &ov, INFINITE);

        // 종료 신호 (key=0, ov=nullptr)
        if (!ok && ov == nullptr) break;
        if (key == 0 && ov == nullptr) break;

        NetSession* session = reinterpret_cast<NetSession*>(key);
        OverlappedEx* ov_ex = reinterpret_cast<OverlappedEx*>(ov);

        if (!ok || bytes == 0) {
            // 연결 종료
            if (ov_ex && ov_ex->io_type == IOType::SEND) {
                // 송신 완료 + 정리
                delete[] ov_ex->wsa_buf.buf;
                delete ov_ex;
            }
            if (session) {
                OnDisconnect(session);
            }
            continue;
        }

        switch (ov_ex->io_type) {
        case IOType::RECV:
            OnRecv(session, bytes);
            break;
        case IOType::SEND:
            OnSend(ov_ex);
            break;
        default:
            break;
        }
    }
}

void IOCPServer::OnAccept(SOCKET client_sock) {
    std::lock_guard<std::mutex> lock(session_mutex_);

    uint64_t sid = next_session_id_++;
    auto session = std::make_unique<NetSession>();
    session->Init(client_sock, sid);

    // IOCP에 소켓 등록
    HANDLE h = CreateIoCompletionPort(
        reinterpret_cast<HANDLE>(client_sock),
        iocp_,
        reinterpret_cast<ULONG_PTR>(session.get()),
        0);

    if (!h) {
        printf("[IOCP] Failed to associate socket with IOCP: %d\n", GetLastError());
        session->Close();
        return;
    }

    // 수신 시작
    if (!session->PostRecv()) {
        session->Close();
        return;
    }

    printf("[IOCP] Client connected: session %llu\n", sid);

    // 이벤트 발행
    PushEvent({IOCPEvent::Type::CONNECTED, sid, {}});

    sessions_[sid] = std::move(session);
}

void IOCPServer::OnRecv(NetSession* session, int bytes_transferred) {
    if (!session || !session->IsConnected()) return;

    // 수신 데이터를 이벤트로 변환
    std::vector<char> data(session->GetRecvBuffer(),
                           session->GetRecvBuffer() + bytes_transferred);

    PushEvent({IOCPEvent::Type::DATA_RECEIVED, session->GetId(), std::move(data)});

    // 다음 수신 대기
    if (!session->PostRecv()) {
        OnDisconnect(session);
    }
}

void IOCPServer::OnSend(OverlappedEx* ov) {
    // 송신 완료 → 버퍼 정리
    if (ov) {
        delete[] ov->wsa_buf.buf;
        delete ov;
    }
}

void IOCPServer::OnDisconnect(NetSession* session) {
    if (!session) return;
    uint64_t sid = session->GetId();

    printf("[IOCP] Client disconnected: session %llu\n", sid);

    PushEvent({IOCPEvent::Type::DISCONNECTED, sid, {}});

    std::lock_guard<std::mutex> lock(session_mutex_);
    sessions_.erase(sid);
}

void IOCPServer::PushEvent(IOCPEvent event) {
    std::lock_guard<std::mutex> lock(event_mutex_);
    event_queue_.push_back(std::move(event));
}

std::vector<IOCPEvent> IOCPServer::PollEvents() {
    std::lock_guard<std::mutex> lock(event_mutex_);
    std::vector<IOCPEvent> events;
    events.swap(event_queue_);
    return events;
}

bool IOCPServer::SendTo(uint64_t session_id, const char* data, int len) {
    std::lock_guard<std::mutex> lock(session_mutex_);
    auto it = sessions_.find(session_id);
    if (it == sessions_.end()) return false;
    return it->second->PostSend(data, len);
}

void IOCPServer::Disconnect(uint64_t session_id) {
    std::lock_guard<std::mutex> lock(session_mutex_);
    auto it = sessions_.find(session_id);
    if (it != sessions_.end()) {
        it->second->Close();
        sessions_.erase(it);
    }
}
