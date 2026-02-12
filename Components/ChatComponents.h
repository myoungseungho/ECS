#pragma once

#include <cstdint>
#include <cstring>

// ━━━ Session 30: Chat System Components ━━━
//
// 채팅 채널:
//   GENERAL (0) - 존(맵) 전체 채팅 (같은 존에 있는 모든 플레이어)
//   PARTY   (1) - 파티 채팅 (파티원만)
//   WHISPER (2) - 귓속말 (1:1)
//   SYSTEM  (3) - 시스템 메시지 (서버→전체)

// 채팅 채널 타입
enum class ChatChannel : uint8_t {
    GENERAL = 0,   // 존 채팅
    PARTY   = 1,   // 파티 채팅
    WHISPER = 2,   // 귓속말
    SYSTEM  = 3,   // 시스템 메시지
};

// 귓속말 결과
enum class WhisperResult : uint8_t {
    SUCCESS         = 0,
    TARGET_NOT_FOUND = 1,  // 해당 이름의 캐릭터 없음
    TARGET_OFFLINE   = 2,  // 접속 중이 아님
};

// 귓속말 방향 (WHISPER_RESULT 패킷에서 사용)
enum class WhisperDirection : uint8_t {
    RECEIVED = 0,  // 수신한 귓속말
    SENT     = 1,  // 보낸 귓속말 에코 (본인 확인용)
};

// NameComponent: "이 Entity에는 표시 이름이 있다"
// 캐릭터 선택(CHAR_SELECT) 시 부착됨
struct NameComponent {
    char name[32] = {};

    void SetName(const char* n) {
        std::memset(name, 0, 32);
        std::strncpy(name, n, 31);
    }
};

// 채팅 메시지 최대 길이
constexpr int MAX_CHAT_MESSAGE_LEN = 200;
