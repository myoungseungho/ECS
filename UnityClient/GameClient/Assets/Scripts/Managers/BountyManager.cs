// ━━━ BountyManager.cs ━━━
// 강호 현상금 시스템 관리 — 목록 조회/수락/완료/랭킹/PvP 현상금
// NetworkManager 이벤트 구독 → BountyUI에 이벤트 발행

using System;
using System.Collections.Generic;
using UnityEngine;
using Network;

public class BountyManager : MonoBehaviour
{
    // ━━━ 상태 ━━━
    private readonly List<BountyInfo> _dailyBounties = new List<BountyInfo>();
    private BountyInfo _weeklyBounty;
    private bool _hasWeekly;
    private byte _acceptedCount;
    private bool _isPanelOpen;

    // ━━━ 프로퍼티 ━━━
    public IReadOnlyList<BountyInfo> DailyBounties => _dailyBounties;
    public BountyInfo WeeklyBounty => _weeklyBounty;
    public bool HasWeekly => _hasWeekly;
    public byte AcceptedCount => _acceptedCount;
    public bool IsPanelOpen => _isPanelOpen;

    // ━━━ 이벤트 ━━━
    public event Action OnBountyListChanged;
    public event Action<BountyAcceptResultData> OnAcceptResult;
    public event Action<BountyCompleteData> OnCompleteResult;
    public event Action<BountyRankingData> OnRankingReceived;
    public event Action<PvPBountyNotifyData> OnPvPBountyAlert;
    public event Action OnPanelOpened;
    public event Action OnPanelClosed;

    // ━━━ 싱글톤 (Scene-bound) ━━━
    public static BountyManager Instance { get; private set; }

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
        net.OnBountyList += HandleBountyList;
        net.OnBountyAcceptResult += HandleAcceptResult;
        net.OnBountyComplete += HandleComplete;
        net.OnBountyRanking += HandleRanking;
        net.OnPvPBountyNotify += HandlePvPBounty;
    }

    private void OnDestroy()
    {
        var net = NetworkManager.Instance;
        if (net == null) return;

        net.OnBountyList -= HandleBountyList;
        net.OnBountyAcceptResult -= HandleAcceptResult;
        net.OnBountyComplete -= HandleComplete;
        net.OnBountyRanking -= HandleRanking;
        net.OnPvPBountyNotify -= HandlePvPBounty;

        if (Instance == this) Instance = null;
    }

    // ━━━ 공개 API ━━━

    /// <summary>현상금 패널 열기</summary>
    public void OpenPanel()
    {
        _isPanelOpen = true;
        NetworkManager.Instance.RequestBountyList();
        OnPanelOpened?.Invoke();
    }

    /// <summary>현상금 패널 닫기</summary>
    public void ClosePanel()
    {
        _isPanelOpen = false;
        OnPanelClosed?.Invoke();
    }

    /// <summary>현상금 목록 새로고침</summary>
    public void RefreshList()
    {
        NetworkManager.Instance.RequestBountyList();
    }

    /// <summary>현상금 수락</summary>
    public void AcceptBounty(ushort bountyId)
    {
        NetworkManager.Instance.AcceptBounty(bountyId);
    }

    /// <summary>현상금 완료 요청 (몬스터 처치 시)</summary>
    public void CompleteBounty(ushort bountyId)
    {
        NetworkManager.Instance.CompleteBounty(bountyId);
    }

    /// <summary>랭킹 요청</summary>
    public void RequestRanking()
    {
        NetworkManager.Instance.RequestBountyRanking();
    }

    // ━━━ 핸들러 ━━━

    private void HandleBountyList(BountyListData data)
    {
        _dailyBounties.Clear();
        _dailyBounties.AddRange(data.DailyBounties);
        _hasWeekly = data.HasWeekly;
        _weeklyBounty = data.WeeklyBounty;
        _acceptedCount = data.AcceptedCount;

        Debug.Log($"[BountyManager] List: daily={data.DailyBounties.Length}, weekly={data.HasWeekly}, accepted={data.AcceptedCount}");
        OnBountyListChanged?.Invoke();
    }

    private void HandleAcceptResult(BountyAcceptResultData data)
    {
        Debug.Log($"[BountyManager] Accept: result={data.Result}, bountyId={data.BountyId}");
        OnAcceptResult?.Invoke(data);

        if (data.Result == BountyAcceptResult.SUCCESS)
        {
            NetworkManager.Instance.RequestBountyList();
        }
    }

    private void HandleComplete(BountyCompleteData data)
    {
        Debug.Log($"[BountyManager] Complete: result={data.Result}, bountyId={data.BountyId}, gold={data.Gold}, exp={data.Exp}, token={data.Token}");
        OnCompleteResult?.Invoke(data);

        if (data.Result == BountyCompleteResult.SUCCESS)
        {
            NetworkManager.Instance.RequestBountyList();
        }
    }

    private void HandleRanking(BountyRankingData data)
    {
        Debug.Log($"[BountyManager] Ranking: count={data.Rankings.Length}, myRank={data.MyRank}, myScore={data.MyScore}");
        OnRankingReceived?.Invoke(data);
    }

    private void HandlePvPBounty(PvPBountyNotifyData data)
    {
        Debug.Log($"[BountyManager] PvPBounty: target={data.TargetEntity}, tier={data.Tier}, streak={data.KillStreak}, gold={data.GoldReward}, name={data.Name}");
        OnPvPBountyAlert?.Invoke(data);
    }
}
