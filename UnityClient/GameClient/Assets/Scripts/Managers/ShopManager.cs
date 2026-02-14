// ━━━ ShopManager.cs ━━━
// NPC 상점 시스템 관리 — 상점 열기/구매/판매, 골드 관리
// NetworkManager 이벤트 구독 → ShopUI에 이벤트 발행

using System;
using UnityEngine;
using Network;

public class ShopManager : MonoBehaviour
{
    // ━━━ 상태 ━━━
    public bool IsShopOpen { get; private set; }
    public uint CurrentNpcId { get; private set; }
    public ShopItemInfo[] CurrentItems { get; private set; }
    public uint Gold { get; private set; } = 1000;

    // ━━━ 이벤트 ━━━
    public event Action<ShopListData> OnShopOpened;
    public event Action OnShopClosed;
    public event Action<ShopResultData> OnTransactionResult;
    public event Action<uint> OnGoldChanged;

    // ━━━ 싱글톤 (Scene-bound) ━━━
    public static ShopManager Instance { get; private set; }

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
        net.OnShopList += HandleShopList;
        net.OnShopResult += HandleShopResult;
    }

    private void OnDestroy()
    {
        var net = NetworkManager.Instance;
        if (net == null) return;

        net.OnShopList -= HandleShopList;
        net.OnShopResult -= HandleShopResult;

        if (Instance == this) Instance = null;
    }

    // ━━━ 공개 API ━━━

    /// <summary>NPC 상점 열기</summary>
    public void OpenShop(uint npcId)
    {
        NetworkManager.Instance.OpenShop(npcId);
    }

    /// <summary>아이템 구매</summary>
    public void BuyItem(uint itemId, ushort count = 1)
    {
        if (!IsShopOpen) return;
        NetworkManager.Instance.ShopBuy(CurrentNpcId, itemId, count);
    }

    /// <summary>아이템 판매</summary>
    public void SellItem(byte slot, ushort count = 1)
    {
        if (!IsShopOpen) return;
        NetworkManager.Instance.ShopSell(slot, count);
    }

    /// <summary>상점 닫기 (클라 로컬)</summary>
    public void CloseShop()
    {
        IsShopOpen = false;
        CurrentNpcId = 0;
        CurrentItems = null;
        OnShopClosed?.Invoke();
    }

    // ━━━ 핸들러 ━━━

    private void HandleShopList(ShopListData data)
    {
        IsShopOpen = true;
        CurrentNpcId = data.NpcId;
        CurrentItems = data.Items;

        Debug.Log($"[ShopManager] Opened shop npc={data.NpcId}, items={data.Items.Length}");
        OnShopOpened?.Invoke(data);
    }

    private void HandleShopResult(ShopResultData data)
    {
        if (data.Result == ShopResult.SUCCESS)
        {
            Gold = data.Gold;
            OnGoldChanged?.Invoke(Gold);
        }

        Debug.Log($"[ShopManager] Transaction: {data.Result}, action={data.Action}, item={data.ItemId}, gold={data.Gold}");
        OnTransactionResult?.Invoke(data);
    }
}
