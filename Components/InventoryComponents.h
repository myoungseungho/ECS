#pragma once

#include <cstdint>
#include <cstring>

// ━━━ Session 23: Inventory/Item System Components ━━━

constexpr int MAX_INVENTORY_SLOTS = 20;

// 아이템 타입
enum class ItemType : uint8_t {
    NONE        = 0,
    CONSUMABLE  = 1,  // 소모품 (포션 등)
    WEAPON      = 2,  // 무기
    ARMOR       = 3,  // 방어구
};

// 아이템 정의 테이블
struct ItemTemplate {
    int32_t item_id;
    char name[24];
    ItemType type;
    int32_t param1;   // 소모품: 회복량 / 장비: 공격력 보너스
    int32_t param2;   // 소모품: 0=HP,1=MP / 장비: 방어력 보너스
    int32_t max_stack;
};

constexpr int ITEM_TEMPLATE_COUNT = 8;
inline const ItemTemplate ITEM_TEMPLATES[ITEM_TEMPLATE_COUNT] = {
    {1,  "HP Potion",    ItemType::CONSUMABLE, 50,  0, 99},
    {2,  "MP Potion",    ItemType::CONSUMABLE, 30,  1, 99},
    {3,  "HP Potion L",  ItemType::CONSUMABLE, 200, 0, 99},
    {4,  "MP Potion L",  ItemType::CONSUMABLE, 100, 1, 99},
    {10, "Iron Sword",   ItemType::WEAPON,     15,  0, 1},
    {11, "Steel Sword",  ItemType::WEAPON,     30,  0, 1},
    {20, "Leather Armor", ItemType::ARMOR,     0,  10, 1},
    {21, "Iron Armor",   ItemType::ARMOR,      0,  25, 1},
};

inline const ItemTemplate* FindItemTemplate(int32_t id) {
    for (int i = 0; i < ITEM_TEMPLATE_COUNT; i++) {
        if (ITEM_TEMPLATES[i].item_id == id) return &ITEM_TEMPLATES[i];
    }
    return nullptr;
}

// 인벤토리 슬롯
struct InventorySlot {
    int32_t item_id = 0;     // 0 = 빈 슬롯
    int16_t count = 0;
    bool equipped = false;
};

// 인벤토리 컴포넌트
struct InventoryComponent {
    InventorySlot slots[MAX_INVENTORY_SLOTS];

    // 빈 슬롯 찾기
    int FindEmptySlot() const {
        for (int i = 0; i < MAX_INVENTORY_SLOTS; i++) {
            if (slots[i].item_id == 0) return i;
        }
        return -1;
    }

    // 아이템 추가 (스택 가능하면 스택)
    int AddItem(int32_t item_id, int16_t count) {
        auto* tmpl = FindItemTemplate(item_id);
        if (!tmpl) return -1;

        // 기존 스택에 추가 시도
        if (tmpl->max_stack > 1) {
            for (int i = 0; i < MAX_INVENTORY_SLOTS; i++) {
                if (slots[i].item_id == item_id && slots[i].count < tmpl->max_stack) {
                    int16_t space = static_cast<int16_t>(tmpl->max_stack - slots[i].count);
                    int16_t add = (count < space) ? count : space;
                    slots[i].count += add;
                    return i;
                }
            }
        }

        // 빈 슬롯에 추가
        int slot = FindEmptySlot();
        if (slot < 0) return -1;  // 인벤토리 가득 참
        slots[slot].item_id = item_id;
        slots[slot].count = count;
        slots[slot].equipped = false;
        return slot;
    }

    // 아이템 제거
    bool RemoveItem(int slot, int16_t count) {
        if (slot < 0 || slot >= MAX_INVENTORY_SLOTS) return false;
        if (slots[slot].item_id == 0) return false;
        slots[slot].count -= count;
        if (slots[slot].count <= 0) {
            slots[slot] = {};
        }
        return true;
    }
};

enum class ItemResult : uint8_t {
    SUCCESS         = 0,
    INVALID_SLOT    = 1,
    EMPTY_SLOT      = 2,
    NOT_CONSUMABLE  = 3,
    NOT_EQUIPMENT   = 4,
    INVENTORY_FULL  = 5,
    ALREADY_EQUIPPED = 6,
    NOT_EQUIPPED    = 7,
};
