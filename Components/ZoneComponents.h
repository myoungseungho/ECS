#pragma once

// ━━━ Zone (Map) System (Session 6) ━━━
//
// 맵(존)이 다르면 완전히 격리된다.
// 채널/AOI 필터보다 상위 필터.
//
// 가시성 계층:
//   Zone (같은 맵?) → Channel (같은 채널?) → Grid (근처 셀?)
//   세 단계 모두 통과해야 서로 보인다.
//
// 예:
//   A(맵1, 채널1, 셀0,0) ↔ B(맵1, 채널1, 셀0,1) → 보임 ✓
//   A(맵1, 채널1, 셀0,0) ↔ C(맵2, 채널1, 셀0,0) → 안 보임 ✗
//
// 실제 게임에서 맵(존)의 역할:
//   - 공간 격리: 마을, 사냥터, 던전을 독립 공간으로 분리
//   - 스폰 포인트: 맵 진입 시 지정된 위치에 등장
//   - 콘텐츠 단위: 맵마다 다른 몬스터, 이벤트, 규칙 적용 가능
//
// 맵 전환 흐름:
//   1. 기존 맵 이웃에게 DISAPPEAR (핸들러에서 즉시)
//   2. ZoneComponent 갱신
//   3. 스폰 포인트로 위치 이동 + dirty + GridCell 제거
//   4. 다음 틱에서 InterestSystem이 새 맵 이웃에게 APPEAR

struct ZoneComponent {
    int zone_id = 0;  // 0 = 미배정
};

// 맵별 스폰 포인트
struct SpawnPoint {
    float x, y, z;
};

// 맵 ID → 스폰 포인트 반환
// (하드코딩. 실제 게임에서는 CSV/DB에서 로드)
inline SpawnPoint GetSpawnPoint(int zone_id) {
    switch (zone_id) {
        case 1:  return { 100.0f,  100.0f, 0.0f};  // 맵 1: 마을
        case 2:  return { 500.0f,  500.0f, 0.0f};  // 맵 2: 사냥터
        case 3:  return {1000.0f, 1000.0f, 0.0f};  // 맵 3: 던전 입구
        default: return {   0.0f,    0.0f, 0.0f};  // 미정의 맵
    }
}
