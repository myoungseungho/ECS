#pragma once

#include <cstdint>
#include <cstring>
#include <vector>

// ━━━ 패킷 프로토콜 정의 (Session 2) ━━━
//
// 모든 패킷 구조:
//   [4바이트: 전체 길이(헤더 포함)] [2바이트: 메시지 타입] [N바이트: 페이로드]
//
// 예: "hello"를 ECHO(타입 1)로 보내는 경우
//   길이 = 4(len) + 2(type) + 5(hello) = 11
//   [0B 00 00 00] [01 00] [h e l l o]
//   ^^^^^^^^^^^   ^^^^^^  ^^^^^^^^^^^
//   little-endian  type    payload
//
// OOP였다면: class Packet { int length; short type; byte[] data; }
// ECS에서는: PacketHeader는 순수 데이터 구조, System이 조립/분해

// 패킷 헤더 크기
constexpr int PACKET_HEADER_SIZE = 6;  // 4(length) + 2(type)

// 최대 패킷 크기 (DoS 방지)
constexpr int MAX_PACKET_SIZE = 8192;

// 메시지 타입 정의
enum class MsgType : uint16_t {
    ECHO            = 1,   // 에코: 페이로드 그대로 돌려줌
    PING            = 2,   // 핑: PONG 응답

    // Session 3: 이동 + 브로드캐스트
    MOVE            = 10,  // 클라이언트→서버: 이동 요청 [x(4) y(4) z(4)]
    MOVE_BROADCAST  = 11,  // 서버→클라이언트: 타인 이동 알림 [entity(8) x(4) y(4) z(4)]
    POS_QUERY       = 12,  // 내 위치 조회 (테스트용)

    // Session 4: AOI (관심 영역)
    APPEAR          = 13,  // 서버→클라이언트: Entity가 시야에 들어옴 [entity(8) x(4) y(4) z(4)]
    DISAPPEAR       = 14,  // 서버→클라이언트: Entity가 시야에서 사라짐 [entity(8)]

    // Session 5: 채널 시스템
    CHANNEL_JOIN    = 20,  // 클라이언트→서버: 채널 입장/변경 [channel_id(4 int)]
    CHANNEL_INFO    = 22,  // 서버→클라이언트: 채널 배정 확인 [channel_id(4 int)]

    // Session 6: 존(맵) 시스템
    ZONE_ENTER      = 30,  // 클라이언트→서버: 맵 진입/이동 [zone_id(4 int)]
    ZONE_INFO       = 31,  // 서버→클라이언트: 맵 배정 확인 [zone_id(4 int)]

    // Session 7: 핸드오프 (서버 간 이동)
    HANDOFF_REQUEST = 40,  // 클라이언트→서버: 핸드오프 요청 (빈 페이로드)
    HANDOFF_DATA    = 41,  // 서버→클라이언트: 직렬화된 Entity 데이터 [serialized bytes]
    HANDOFF_RESTORE = 42,  // 클라이언트→서버: 직렬화 데이터로 Entity 복원 [serialized bytes]
    HANDOFF_RESULT  = 43,  // 서버→클라이언트: 복원 결과 [zone(4) ch(4) x(4) y(4) z(4)]

    // Session 8: Ghost Entity (크로스서버 동기화)
    GHOST_QUERY     = 50,  // 클라이언트→서버: Ghost 수 조회 (빈 페이로드)
    GHOST_INFO      = 51,  // 서버→클라이언트: Ghost 정보 [ghost_count(4 int)]

    // Session 9: Login + Character Select
    LOGIN           = 60,  // 클라이언트→서버: 로그인 [username_len(1) username(N) pw_len(1) pw(N)]
    LOGIN_RESULT    = 61,  // 서버→클라이언트: 로그인 결과 [result(1) account_id(4)]
    CHAR_LIST_REQ   = 62,  // 클라이언트→서버: 캐릭터 목록 요청 (빈 페이로드)
    CHAR_LIST_RESP  = 63,  // 서버→클라이언트: 캐릭터 목록 [count(1) {id(4) name(32) level(4) job(4)}...]
    CHAR_SELECT     = 64,  // 클라이언트→서버: 캐릭터 선택 [char_id(4)]
    ENTER_GAME      = 65,  // 서버→클라이언트: 게임 진입 결과 [result(1) entity(8) zone(4) x(4) y(4) z(4)]

    // Session 10: Gate Server (로드밸런싱)
    GATE_ROUTE_REQ  = 70,  // 클라이언트→게이트: 게임서버 배정 요청 (빈 페이로드)
    GATE_ROUTE_RESP = 71,  // 게이트→클라이언트: 서버 배정 [result(1) port(2) ip_len(1) ip(N)]

    STATS       = 99,  // 내부 진단
};

// 패킷 헤더 (네트워크 바이트 → 구조체로 파싱)
#pragma pack(push, 1)
struct PacketHeader {
    uint32_t length;    // 전체 패킷 크기 (헤더 포함)
    uint16_t msg_type;  // MsgType
};
#pragma pack(pop)

// ━━━ 패킷 빌드 유틸리티 ━━━

// 헤더 + 페이로드를 하나의 버퍼로 조립
inline std::vector<char> BuildPacket(MsgType type, const char* payload, int payload_len) {
    uint32_t total_len = PACKET_HEADER_SIZE + payload_len;
    std::vector<char> buf(total_len);

    // 헤더 쓰기 (little-endian)
    std::memcpy(buf.data(), &total_len, 4);
    uint16_t t = static_cast<uint16_t>(type);
    std::memcpy(buf.data() + 4, &t, 2);

    // 페이로드 쓰기
    if (payload_len > 0) {
        std::memcpy(buf.data() + PACKET_HEADER_SIZE, payload, payload_len);
    }

    return buf;
}

// 오버로드: string 버전
inline std::vector<char> BuildPacket(MsgType type, const std::vector<char>& payload) {
    return BuildPacket(type, payload.data(), static_cast<int>(payload.size()));
}

// 빈 페이로드 패킷
inline std::vector<char> BuildPacket(MsgType type) {
    return BuildPacket(type, nullptr, 0);
}
