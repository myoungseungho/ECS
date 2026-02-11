#pragma once

#include <cstdint>
#include <cstring>
#include <vector>
#include <string>
#include <unordered_map>

// ━━━ Session 9: Login + Character Select Components ━━━

// 로그인 상태
enum class LoginState : uint8_t {
    CONNECTED = 0,        // 접속만 함 (아직 로그인 안 함)
    AUTHENTICATED = 1,    // 로그인 성공 (캐릭터 선택 가능)
    IN_GAME = 2,          // 캐릭터 선택 후 게임 진입
};

// LoginComponent: "이 Entity는 로그인 상태가 있다"
struct LoginComponent {
    LoginState state = LoginState::CONNECTED;
    uint32_t account_id = 0;
    char username[32] = {};
};

// 캐릭터 정보 (DB 대신 메모리에 저장)
struct CharacterInfo {
    uint32_t char_id = 0;
    char name[32] = {};
    int32_t level = 1;
    int32_t job_class = 0;    // 0=전사, 1=궁수, 2=마법사
    int32_t zone_id = 1;      // 마지막 위치
    float x = 100.0f;
    float y = 100.0f;
    float z = 0.0f;
};

// ━━━ 인메모리 계정/캐릭터 데이터베이스 ━━━
// 교육용: 실제 DB 대신 하드코딩된 테스트 데이터

struct AccountData {
    uint32_t account_id;
    std::string username;
    std::string password;
    std::vector<CharacterInfo> characters;
};

// 전역 계정 DB (싱글턴 대신 단순 전역)
inline std::unordered_map<std::string, AccountData>& GetAccountDB() {
    static std::unordered_map<std::string, AccountData> db;
    static bool initialized = false;

    if (!initialized) {
        initialized = true;

        // 테스트 계정 1: hero (캐릭터 2개)
        AccountData acc1;
        acc1.account_id = 1001;
        acc1.username = "hero";
        acc1.password = "pass123";

        CharacterInfo c1;
        c1.char_id = 1;
        std::strncpy(c1.name, "Warrior_Kim", 31);
        c1.level = 50;
        c1.job_class = 0;
        c1.zone_id = 1;
        c1.x = 100.0f; c1.y = 100.0f; c1.z = 0.0f;
        acc1.characters.push_back(c1);

        CharacterInfo c2;
        c2.char_id = 2;
        std::strncpy(c2.name, "Mage_Lee", 31);
        c2.level = 35;
        c2.job_class = 2;
        c2.zone_id = 2;
        c2.x = 500.0f; c2.y = 500.0f; c2.z = 0.0f;
        acc1.characters.push_back(c2);

        db["hero"] = acc1;

        // 테스트 계정 2: guest (캐릭터 1개)
        AccountData acc2;
        acc2.account_id = 1002;
        acc2.username = "guest";
        acc2.password = "guest";

        CharacterInfo c3;
        c3.char_id = 3;
        std::strncpy(c3.name, "Archer_Park", 31);
        c3.level = 20;
        c3.job_class = 1;
        c3.zone_id = 1;
        c3.x = 200.0f; c3.y = 200.0f; c3.z = 0.0f;
        acc2.characters.push_back(c3);

        db["guest"] = acc2;

        // 테스트 계정 3: empty (캐릭터 0개)
        AccountData acc3;
        acc3.account_id = 1003;
        acc3.username = "empty";
        acc3.password = "empty";
        db["empty"] = acc3;
    }

    return db;
}
