// ━━━ TradeManager.cs ━━━
// 거래 시스템 관리 — 요청/수락/거절/아이템·골드 추가/확정/취소
// NetworkManager 이벤트 구독 → TradeUI에 이벤트 발행

using System;
using UnityEngine;
using Network;

public class TradeManager : MonoBehaviour
{
    // ━━━ 상태 ━━━
    public bool IsTrading { get; private set; }
    public ulong TradePartner { get; private set; }

    // ━━━ 이벤트 ━━━
    public event Action<TradeResultData> OnTradeCompleted;
    public event Action OnTradeStarted;
    public event Action OnTradeCancelled;

    // ━━━ 싱글톤 (Scene-bound) ━━━
    public static TradeManager Instance { get; private set; }

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
        net.OnTradeResult += HandleTradeResult;
    }

    private void OnDestroy()
    {
        var net = NetworkManager.Instance;
        if (net == null) return;

        net.OnTradeResult -= HandleTradeResult;

        if (Instance == this) Instance = null;
    }

    // ━━━ 공개 API ━━━

    /// <summary>거래 요청</summary>
    public void RequestTrade(ulong targetEntity)
    {
        TradePartner = targetEntity;
        NetworkManager.Instance.RequestTrade(targetEntity);
    }

    /// <summary>거래 수락</summary>
    public void AcceptTrade()
    {
        IsTrading = true;
        NetworkManager.Instance.AcceptTrade();
        OnTradeStarted?.Invoke();
    }

    /// <summary>거래 거절</summary>
    public void DeclineTrade()
    {
        NetworkManager.Instance.DeclineTrade();
    }

    /// <summary>거래에 아이템 추가</summary>
    public void AddItem(byte slotIndex)
    {
        if (!IsTrading) return;
        NetworkManager.Instance.TradeAddItem(slotIndex);
    }

    /// <summary>거래에 골드 추가</summary>
    public void AddGold(uint amount)
    {
        if (!IsTrading) return;
        NetworkManager.Instance.TradeAddGold(amount);
    }

    /// <summary>거래 확정</summary>
    public void ConfirmTrade()
    {
        if (!IsTrading) return;
        NetworkManager.Instance.ConfirmTrade();
    }

    /// <summary>거래 취소</summary>
    public void CancelTrade()
    {
        NetworkManager.Instance.CancelTrade();
        IsTrading = false;
        TradePartner = 0;
        OnTradeCancelled?.Invoke();
    }

    // ━━━ 핸들러 ━━━

    private void HandleTradeResult(TradeResultData data)
    {
        Debug.Log($"[TradeManager] Trade result: {data.Result}");

        IsTrading = false;
        TradePartner = 0;
        OnTradeCompleted?.Invoke(data);
    }
}
