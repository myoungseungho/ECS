// ━━━ CashShopManager.cs ━━━
// 캐시샵 시스템 관리 — 아이템 목록/구매/크리스탈/월정액
// NetworkManager 이벤트 구독 → CashShopUI에 이벤트 발행

using System;
using System.Collections.Generic;
using UnityEngine;
using Network;

public class CashShopManager : MonoBehaviour
{
    // ━━━ 상태 ━━━
    private readonly List<CashShopItemInfo> _items = new List<CashShopItemInfo>();
    private uint _crystals;
    private bool _isPanelOpen;
    private SubscriptionInfoData _subscription;

    // ━━━ 프로퍼티 ━━━
    public IReadOnlyList<CashShopItemInfo> Items => _items;
    public uint Crystals => _crystals;
    public bool IsPanelOpen => _isPanelOpen;
    public SubscriptionInfoData Subscription => _subscription;

    // ━━━ 이벤트 ━━━
    public event Action OnShopListChanged;
    public event Action<CashShopBuyResultData> OnPurchaseResult;
    public event Action<SubscriptionInfoData> OnSubscriptionUpdated;
    public event Action OnPanelOpened;
    public event Action OnPanelClosed;

    // ━━━ 싱글톤 (Scene-bound) ━━━
    public static CashShopManager Instance { get; private set; }

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
        net.OnCashShopList += HandleCashShopList;
        net.OnCashShopBuyResult += HandleCashShopBuyResult;
        net.OnSubscriptionInfo += HandleSubscriptionInfo;
    }

    private void OnDestroy()
    {
        var net = NetworkManager.Instance;
        if (net == null) return;

        net.OnCashShopList -= HandleCashShopList;
        net.OnCashShopBuyResult -= HandleCashShopBuyResult;
        net.OnSubscriptionInfo -= HandleSubscriptionInfo;

        if (Instance == this) Instance = null;
    }

    // ━━━ 공개 API ━━━

    /// <summary>캐시샵 패널 열기</summary>
    public void OpenPanel()
    {
        _isPanelOpen = true;
        NetworkManager.Instance.RequestCashShopList(0);
        NetworkManager.Instance.RequestSubscriptionInfo();
        OnPanelOpened?.Invoke();
    }

    /// <summary>캐시샵 패널 닫기</summary>
    public void ClosePanel()
    {
        _isPanelOpen = false;
        OnPanelClosed?.Invoke();
    }

    /// <summary>카테고리별 아이템 목록 요청</summary>
    public void RequestItems(byte category)
    {
        NetworkManager.Instance.RequestCashShopList(category);
    }

    /// <summary>아이템 구매</summary>
    public void BuyItem(uint itemId, byte count)
    {
        NetworkManager.Instance.BuyCashShopItem(itemId, count);
    }

    /// <summary>월정액 정보 요청</summary>
    public void RequestSubscription()
    {
        NetworkManager.Instance.RequestSubscriptionInfo();
    }

    // ━━━ 핸들러 ━━━

    private void HandleCashShopList(CashShopItemInfo[] items)
    {
        _items.Clear();
        _items.AddRange(items);

        Debug.Log($"[CashShopManager] Shop list: {items.Length} items");
        OnShopListChanged?.Invoke();
    }

    private void HandleCashShopBuyResult(CashShopBuyResultData data)
    {
        if (data.Result == CashShopBuyResult.SUCCESS)
        {
            _crystals = data.RemainingCrystals;
        }

        Debug.Log($"[CashShopManager] Buy: result={data.Result}, item={data.ItemId}, crystals={data.RemainingCrystals}");
        OnPurchaseResult?.Invoke(data);
    }

    private void HandleSubscriptionInfo(SubscriptionInfoData data)
    {
        _subscription = data;

        Debug.Log($"[CashShopManager] Subscription: active={data.IsActive}, days={data.DaysLeft}, daily={data.DailyCrystals}");
        OnSubscriptionUpdated?.Invoke(data);
    }
}
