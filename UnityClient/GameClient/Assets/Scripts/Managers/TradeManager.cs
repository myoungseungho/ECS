// ━━━ TradeManager.cs ━━━
// 거래 시스템 관리 — 요청, 수락, 거절, 아이템/골드 추가, 확인, 취소
// T031: MsgType 300-307

using System;
using System.Collections.Generic;
using UnityEngine;
using Network;

public class TradeManager : MonoBehaviour
{
    // ━━━ 싱글톤 ━━━
    public static TradeManager Instance { get; private set; }

    // ━━━ 상태 ━━━
    private bool _isTrading;
    private TradeRequestData _pendingRequest;
    private List<TradeAddItemData> _partnerItems = new List<TradeAddItemData>();

    // ━━━ 이벤트 ━━━
    public event Action<TradeRequestData> OnTradeRequested;
    public event Action<TradeAddItemData> OnPartnerItemAdded;
    public event Action<TradeResult> OnTradeCompleted;
    public event Action OnTradeCancelled;

    // ━━━ 공개 프로퍼티 ━━━
    public bool IsTrading => _isTrading;
    public TradeRequestData PendingRequest => _pendingRequest;
    public IReadOnlyList<TradeAddItemData> PartnerItems => _partnerItems;

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
        if (net != null)
        {
            net.OnTradeRequest += HandleTradeRequest;
            net.OnTradeAddItem += HandleTradeAddItem;
            net.OnTradeResult += HandleTradeResult;
        }
    }

    private void OnDestroy()
    {
        var net = NetworkManager.Instance;
        if (net != null)
        {
            net.OnTradeRequest -= HandleTradeRequest;
            net.OnTradeAddItem -= HandleTradeAddItem;
            net.OnTradeResult -= HandleTradeResult;
        }
        if (Instance == this) Instance = null;
    }

    // ━━━ 이벤트 핸들러 ━━━

    private void HandleTradeRequest(TradeRequestData data)
    {
        _pendingRequest = data;
        OnTradeRequested?.Invoke(data);
    }

    private void HandleTradeAddItem(TradeAddItemData data)
    {
        _partnerItems.Add(data);
        OnPartnerItemAdded?.Invoke(data);
    }

    private void HandleTradeResult(TradeResult result)
    {
        _isTrading = false;
        _pendingRequest = null;
        _partnerItems.Clear();

        if (result == TradeResult.CANCELLED)
            OnTradeCancelled?.Invoke();
        else
            OnTradeCompleted?.Invoke(result);
    }

    // ━━━ 공개 API ━━━

    public void RequestTrade(ulong targetEntity) { NetworkManager.Instance.RequestTrade(targetEntity); }

    public void AcceptTrade()
    {
        if (_pendingRequest != null)
        {
            _isTrading = true;
            _partnerItems.Clear();
            NetworkManager.Instance.AcceptTrade(_pendingRequest.RequesterEntity);
            _pendingRequest = null;
        }
    }

    public void DeclineTrade()
    {
        _pendingRequest = null;
        NetworkManager.Instance.DeclineTrade();
    }

    public void AddItem(byte slotIndex, ushort count) { NetworkManager.Instance.TradeAddItem(slotIndex, count); }
    public void AddGold(uint amount) { NetworkManager.Instance.TradeAddGold(amount); }
    public void Confirm() { NetworkManager.Instance.ConfirmTrade(); }

    public void Cancel()
    {
        _isTrading = false;
        _partnerItems.Clear();
        NetworkManager.Instance.CancelTrade();
    }
}
