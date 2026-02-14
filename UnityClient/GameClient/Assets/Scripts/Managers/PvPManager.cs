// ━━━ PvPManager.cs ━━━
// PvP 아레나 시스템 관리 (S036 전용 패킷 350-359)
// NetworkManager 이벤트 구독 → PvPUI에 이벤트 발행

using System;
using UnityEngine;
using Network;

public class PvPManager : MonoBehaviour
{
    // ━━━ PvP 모드 ━━━
    public enum PvPMode : byte
    {
        ARENA_1V1 = 1,
        ARENA_3V3 = 2,
    }

    // ━━━ PvP 상태 ━━━
    public enum PvPState : byte
    {
        IDLE = 0,
        QUEUED = 1,
        MATCH_FOUND = 2,
        IN_MATCH = 3,
    }

    // ━━━ 런타임 데이터 ━━━
    public PvPState CurrentState { get; private set; }
    public PvPMode CurrentMode { get; private set; }
    public ushort QueueCount { get; private set; }
    public uint PendingMatchId { get; private set; }
    public byte MyTeamId { get; private set; }
    public ushort TimeLimit { get; private set; }

    // 전적/레이팅
    public ushort Rating { get; private set; } = 1000;
    public string Tier { get; private set; } = "Silver";
    public ushort Wins { get; private set; }
    public ushort Losses { get; private set; }

    // ━━━ 이벤트 ━━━
    public event Action<PvPState> OnStateChanged;
    public event Action<PvPMatchFoundData> OnMatchFound;
    public event Action<PvPMatchStartData> OnMatchStarted;
    public event Action<PvPAttackResultData> OnAttackResult;
    public event Action<PvPMatchEndData> OnMatchEnded;
    public event Action<PvPRatingInfoData> OnRatingUpdated;

    // ━━━ 싱글톤 (Scene-bound) ━━━
    public static PvPManager Instance { get; private set; }

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
        net.OnPvPQueueStatus += HandleQueueStatus;
        net.OnPvPMatchFound += HandleMatchFound;
        net.OnPvPMatchStart += HandleMatchStart;
        net.OnPvPAttackResult += HandleAttackResult;
        net.OnPvPMatchEnd += HandleMatchEnd;
        net.OnPvPRatingInfo += HandleRatingInfo;
    }

    private void OnDestroy()
    {
        var net = NetworkManager.Instance;
        if (net == null) return;

        net.OnPvPQueueStatus -= HandleQueueStatus;
        net.OnPvPMatchFound -= HandleMatchFound;
        net.OnPvPMatchStart -= HandleMatchStart;
        net.OnPvPAttackResult -= HandleAttackResult;
        net.OnPvPMatchEnd -= HandleMatchEnd;
        net.OnPvPRatingInfo -= HandleRatingInfo;

        if (Instance == this) Instance = null;
    }

    // ━━━ 공개 API ━━━

    /// <summary>PvP 매칭 큐 등록</summary>
    public void QueueForMatch(PvPMode mode)
    {
        CurrentMode = mode;
        CurrentState = PvPState.QUEUED;
        NetworkManager.Instance.PvPQueueReq((byte)mode);
        OnStateChanged?.Invoke(CurrentState);
    }

    /// <summary>매칭 큐 해제</summary>
    public void CancelQueue()
    {
        CurrentState = PvPState.IDLE;
        QueueCount = 0;
        NetworkManager.Instance.PvPQueueCancel();
        OnStateChanged?.Invoke(CurrentState);
    }

    /// <summary>매칭 수락</summary>
    public void AcceptMatch()
    {
        if (PendingMatchId == 0) return;
        NetworkManager.Instance.PvPMatchAccept(PendingMatchId);
    }

    /// <summary>PvP 공격</summary>
    public void Attack(byte targetTeam, byte targetIdx, ushort skillId, ushort damage)
    {
        if (PendingMatchId == 0) return;
        NetworkManager.Instance.PvPAttack(PendingMatchId, targetTeam, targetIdx, skillId, damage);
    }

    /// <summary>PvP 경기장 퇴장 (기존 Instance Leave 사용)</summary>
    public void LeaveMatch()
    {
        NetworkManager.Instance.LeaveInstance();
        CurrentState = PvPState.IDLE;
        PendingMatchId = 0;
        OnStateChanged?.Invoke(CurrentState);
    }

    // ━━━ 핸들러 ━━━

    private void HandleQueueStatus(PvPQueueStatusData data)
    {
        QueueCount = data.QueueCount;
        if (data.Status == PvPQueueStatus.QUEUED)
        {
            CurrentState = PvPState.QUEUED;
        }
        else if (data.Status == PvPQueueStatus.CANCELLED)
        {
            CurrentState = PvPState.IDLE;
        }
        OnStateChanged?.Invoke(CurrentState);
    }

    private void HandleMatchFound(PvPMatchFoundData data)
    {
        PendingMatchId = data.MatchId;
        MyTeamId = data.TeamId;
        CurrentState = PvPState.MATCH_FOUND;
        Debug.Log($"[PvPManager] Match found! matchId={data.MatchId}, mode={data.ModeId}, team={data.TeamId}");
        OnMatchFound?.Invoke(data);
        OnStateChanged?.Invoke(CurrentState);
    }

    private void HandleMatchStart(PvPMatchStartData data)
    {
        CurrentState = PvPState.IN_MATCH;
        TimeLimit = data.TimeLimit;
        Debug.Log($"[PvPManager] Match started! matchId={data.MatchId}, timeLimit={data.TimeLimit}s");
        OnMatchStarted?.Invoke(data);
        OnStateChanged?.Invoke(CurrentState);
    }

    private void HandleAttackResult(PvPAttackResultData data)
    {
        OnAttackResult?.Invoke(data);
    }

    private void HandleMatchEnd(PvPMatchEndData data)
    {
        bool won = data.Won == 1;
        Rating = data.NewRating;
        Tier = data.Tier;
        if (won) Wins++;
        else Losses++;

        CurrentState = PvPState.IDLE;
        PendingMatchId = 0;
        Debug.Log($"[PvPManager] Match ended! won={won}, rating={data.NewRating}, tier={data.Tier}");
        OnMatchEnded?.Invoke(data);
        OnStateChanged?.Invoke(CurrentState);
    }

    private void HandleRatingInfo(PvPRatingInfoData data)
    {
        Rating = data.Rating;
        Tier = data.Tier;
        Wins = data.Wins;
        Losses = data.Losses;
        Debug.Log($"[PvPManager] Rating={data.Rating}, Tier={data.Tier}, W={data.Wins}/L={data.Losses}");
        OnRatingUpdated?.Invoke(data);
    }
}
