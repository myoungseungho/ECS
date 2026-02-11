#pragma once

#include <cstdint>
#include <vector>

// SessionComponent: "이 Entity는 네트워크 연결이 있다"
// OOP: class Player : public Session (상속)
// ECS: Entity에 SessionComponent를 붙이면 "접속한 놈"
struct SessionComponent {
    uint64_t session_id = 0;   // IOCPServer의 세션 ID와 매핑
    bool connected = false;
};

// RecvBufferComponent: 아직 처리하지 않은 수신 데이터
// NetworkSystem이 여기에 적재 → MessageDispatchSystem이 여기서 꺼냄 (Session 2)
// 지금은 NetworkSystem이 직접 에코 처리
struct RecvBufferComponent {
    std::vector<char> buffer;
};
