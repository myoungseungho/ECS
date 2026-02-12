#pragma once

#include <cstdint>
#include <cstring>

// ━━━ Session 32: NPC Shop System Components ━━━
//
// NPC 상점: 아이템 구매/판매
// - 골드(재화)로 거래
// - NPC별 판매 품목 다름
// - 판매 가격 = 구매 가격의 40%

// 통화 컴포넌트: "이 Entity는 골드를 갖고 있다"
struct CurrencyComponent {
    int32_t gold = 1000;  // 초기 골드 (테스트용)

    bool CanAfford(int32_t cost) const { return gold >= cost; }
    void Spend(int32_t amount) { gold -= amount; }
    void Earn(int32_t amount) { gold += amount; }
};

// 상점 아이템 엔트리
struct ShopItemEntry {
    int32_t item_id;
    int32_t buy_price;    // 구매 가격 (플레이어→NPC)
    int16_t stock;        // -1 = 무한
};

// NPC 상점 템플릿
struct ShopTemplate {
    int32_t npc_id;
    char name[32];
    int entry_count;
    ShopItemEntry items[10];  // 최대 10개
};

// 상점 거래 결과
enum class ShopResult : uint8_t {
    SUCCESS        = 0,
    SHOP_NOT_FOUND = 1,
    ITEM_NOT_FOUND = 2,
    NOT_ENOUGH_GOLD = 3,
    INVENTORY_FULL = 4,
    OUT_OF_STOCK   = 5,
    EMPTY_SLOT     = 6,
    INVALID_COUNT  = 7,
};

// 거래 방향
enum class ShopAction : uint8_t {
    BUY  = 0,
    SELL = 1,
};

// 판매 가격 비율 (구매 가격의 40%)
constexpr float SELL_PRICE_RATIO = 0.4f;

// ━━━ NPC 상점 데이터 ━━━
constexpr int SHOP_COUNT = 3;
inline const ShopTemplate SHOP_TEMPLATES[SHOP_COUNT] = {
    // 잡화 상인 (NPC 1)
    {1, "General Store", 4, {
        {1,  50,  -1},   // HP Potion: 50 골드, 무한
        {2,  40,  -1},   // MP Potion: 40 골드, 무한
        {3,  200, -1},   // HP Potion L: 200 골드, 무한
        {4,  150, -1},   // MP Potion L: 150 골드, 무한
    }},
    // 무기 상인 (NPC 2)
    {2, "Weapon Shop", 2, {
        {10, 500,  5},   // Iron Sword: 500 골드, 5개 한정
        {11, 1500, 2},   // Steel Sword: 1500 골드, 2개 한정
    }},
    // 방어구 상인 (NPC 3)
    {3, "Armor Shop", 2, {
        {20, 400,  5},   // Leather Armor: 400 골드, 5개 한정
        {21, 1200, 2},   // Iron Armor: 1200 골드, 2개 한정
    }},
};

inline const ShopTemplate* FindShopTemplate(int32_t npc_id) {
    for (int i = 0; i < SHOP_COUNT; i++) {
        if (SHOP_TEMPLATES[i].npc_id == npc_id) return &SHOP_TEMPLATES[i];
    }
    return nullptr;
}
