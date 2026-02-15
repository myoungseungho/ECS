// ━━━ EventManager.cs ━━━
// 이벤트 시스템 관리 — 이벤트 목록/보상 수령 (14일출석/2배EXP/보스러시)
// NetworkManager 이벤트 구독 → EventUI에 이벤트 발행

using System;
using System.Collections.Generic;
using UnityEngine;
using Network;

public class EventManager : MonoBehaviour
{
    // ━━━ 상태 ━━━
    private readonly List<GameEventInfo> _events = new List<GameEventInfo>();
    private bool _isPanelOpen;

    // ━━━ 프로퍼티 ━━━
    public IReadOnlyList<GameEventInfo> Events => _events;
    public bool IsPanelOpen => _isPanelOpen;

    // ━━━ 이벤트 ━━━
    public event Action OnEventListChanged;
    public event Action<EventClaimResultData> OnClaimResult;
    public event Action OnPanelOpened;
    public event Action OnPanelClosed;

    // ━━━ 싱글톤 (Scene-bound) ━━━
    public static EventManager Instance { get; private set; }

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
        net.OnEventList += HandleEventList;
        net.OnEventClaimResult += HandleEventClaimResult;
    }

    private void OnDestroy()
    {
        var net = NetworkManager.Instance;
        if (net == null) return;

        net.OnEventList -= HandleEventList;
        net.OnEventClaimResult -= HandleEventClaimResult;

        if (Instance == this) Instance = null;
    }

    // ━━━ 공개 API ━━━

    /// <summary>이벤트 패널 열기</summary>
    public void OpenPanel()
    {
        _isPanelOpen = true;
        NetworkManager.Instance.RequestEventList();
        OnPanelOpened?.Invoke();
    }

    /// <summary>이벤트 패널 닫기</summary>
    public void ClosePanel()
    {
        _isPanelOpen = false;
        OnPanelClosed?.Invoke();
    }

    /// <summary>이벤트 보상 수령</summary>
    public void ClaimReward(ushort eventId)
    {
        NetworkManager.Instance.ClaimEventReward(eventId);
    }

    /// <summary>이벤트 목록 갱신</summary>
    public void RefreshEvents()
    {
        NetworkManager.Instance.RequestEventList();
    }

    // ━━━ 핸들러 ━━━

    private void HandleEventList(GameEventInfo[] events)
    {
        _events.Clear();
        _events.AddRange(events);

        Debug.Log($"[EventManager] EventList: {events.Length} events");
        OnEventListChanged?.Invoke();
    }

    private void HandleEventClaimResult(EventClaimResultData data)
    {
        string resultName;
        switch (data.Result)
        {
            case 0: resultName = "SUCCESS"; break;
            case 1: resultName = "ALREADY_CLAIMED"; break;
            case 2: resultName = "DAILY_LIMIT"; break;
            case 3: resultName = "INVALID_EVENT"; break;
            default: resultName = $"UNKNOWN({data.Result})"; break;
        }

        Debug.Log($"[EventManager] Claim: result={resultName}, event={data.EventId}, reward={data.RewardId}x{data.RewardCount}");
        OnClaimResult?.Invoke(data);
    }
}
