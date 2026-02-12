// ━━━ InventoryManager.cs ━━━
// 인벤토리 관리 — 아이템 목록, 사용, 장착/해제
// NetworkManager 이벤트 구독 → UI에 인벤토리 이벤트 발행

using System;
using System.Collections.Generic;
using UnityEngine;
using Network;

public class InventoryManager : MonoBehaviour
{
    // ━━━ 인벤토리 데이터 ━━━
    private readonly Dictionary<byte, InventoryItemInfo> _items = new Dictionary<byte, InventoryItemInfo>();

    public IReadOnlyDictionary<byte, InventoryItemInfo> Items => _items;

    // ━━━ 이벤트 ━━━
    public event Action OnInventoryChanged;
    public event Action<ItemAddResultData> OnItemAdded;
    public event Action<ItemUseResultData> OnItemUsed;
    public event Action<ItemEquipResultData> OnItemEquipped;

    // ━━━ 싱글톤 (Scene-bound) ━━━
    public static InventoryManager Instance { get; private set; }

    private void Awake()
    {
        if (Instance != null && Instance != this)
        {
            Destroy(gameObject);
            return;
        }
        Instance = this;
    }

    private void Start()
    {
        var net = NetworkManager.Instance;
        net.OnInventoryResp += HandleInventoryResp;
        net.OnItemAddResult += HandleItemAddResult;
        net.OnItemUseResult += HandleItemUseResult;
        net.OnItemEquipResult += HandleItemEquipResult;
        net.OnEnterGame += HandleEnterGame;
    }

    private void OnDestroy()
    {
        var net = NetworkManager.Instance;
        if (net == null) return;

        net.OnInventoryResp -= HandleInventoryResp;
        net.OnItemAddResult -= HandleItemAddResult;
        net.OnItemUseResult -= HandleItemUseResult;
        net.OnItemEquipResult -= HandleItemEquipResult;
        net.OnEnterGame -= HandleEnterGame;

        if (Instance == this) Instance = null;
    }

    // ━━━ 공개 API ━━━

    public void UseItem(byte slot)
    {
        NetworkManager.Instance.UseItem(slot);
    }

    public void EquipItem(byte slot)
    {
        NetworkManager.Instance.EquipItem(slot);
    }

    public void UnequipItem(byte slot)
    {
        NetworkManager.Instance.UnequipItem(slot);
    }

    public InventoryItemInfo GetItem(byte slot)
    {
        _items.TryGetValue(slot, out var item);
        return item;
    }

    public int ItemCount => _items.Count;

    // ━━━ 핸들러 ━━━

    private void HandleInventoryResp(InventoryItemInfo[] items)
    {
        _items.Clear();
        foreach (var item in items)
            _items[item.Slot] = item;

        Debug.Log($"[InventoryManager] Loaded {items.Length} items");
        OnInventoryChanged?.Invoke();
    }

    private void HandleItemAddResult(ItemAddResultData data)
    {
        if (data.Result == ItemResult.SUCCESS)
        {
            _items[data.Slot] = new InventoryItemInfo
            {
                Slot = data.Slot,
                ItemId = data.ItemId,
                Count = data.Count,
                Equipped = 0
            };
        }

        OnItemAdded?.Invoke(data);
        OnInventoryChanged?.Invoke();
    }

    private void HandleItemUseResult(ItemUseResultData data)
    {
        if (data.Result == 0 && _items.ContainsKey(data.Slot))
        {
            var item = _items[data.Slot];
            if (item.Count <= 1)
                _items.Remove(data.Slot);
            else
                item.Count--;
        }

        OnItemUsed?.Invoke(data);
        OnInventoryChanged?.Invoke();
    }

    private void HandleItemEquipResult(ItemEquipResultData data)
    {
        if (data.Result == 0 && _items.TryGetValue(data.Slot, out var item))
        {
            item.Equipped = data.Equipped;
        }

        OnItemEquipped?.Invoke(data);
        OnInventoryChanged?.Invoke();
    }

    private void HandleEnterGame(EnterGameResult result)
    {
        if (result.ResultCode != 0) return;
        NetworkManager.Instance.RequestInventory();
    }
}
