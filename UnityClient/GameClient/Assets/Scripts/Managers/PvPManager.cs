// ━━━ PvPManager.cs ━━━
// PvP 아레나/전장 시스템 관리
// 던전 매칭 시스템을 활용하여 PvP 매칭 수행
// NetworkManager 이벤트 구독 → PvPUI에 이벤트 발행

using System;
using UnityEngine;
using Network;

public class PvPManager : MonoBehaviour
{
    // ━━━ PvP 모드 ━━━
    public enum PvPMode : uint
    {
        ARENA_1V1 = 101,
        ARENA_3V3 = 102,
        BATTLEGROUND = 103,
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
    public uint QueuePosition { get; private set; }
    public uint PendingMatchId { get; private set; }
    public uint CurrentInstanceId { get; private set; }

    // ━━━ 전적 (로컬 캐시) ━━━
    public int Wins { get; private set; }
    public int Losses { get; private set; }
    public int Rating { get; private set; } = 1000;

    // ━━━ 이벤트 ━━━
    public event Action<PvPState> OnStateChanged;
    public event Action<MatchFoundData> OnMatchFound;
    public event Action OnMatchEntered;
    public event Action OnMatchLeft;

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
        // PvP 매칭은 Instance/Match 패킷 재활용 (DungeonType 100+ = PvP)
        net.OnMatchFound += HandleMatchFound;
        net.OnMatchStatus += HandleMatchStatus;
        net.OnInstanceEnter += HandleInstanceEnter;
        net.OnInstanceLeaveResult += HandleInstanceLeaveResult;
    }

    private void OnDestroy()
    {
        var net = NetworkManager.Instance;
        if (net == null) return;

        net.OnMatchFound -= HandleMatchFound;
        net.OnMatchStatus -= HandleMatchStatus;
        net.OnInstanceEnter -= HandleInstanceEnter;
        net.OnInstanceLeaveResult -= HandleInstanceLeaveResult;

        if (Instance == this) Instance = null;
    }

    // ━━━ 공개 API ━━━

    /// <summary>PvP 매칭 큐 등록</summary>
    public void QueueForMatch(PvPMode mode)
    {
        CurrentMode = mode;
        CurrentState = PvPState.QUEUED;
        NetworkManager.Instance.EnqueueMatch((uint)mode);
        OnStateChanged?.Invoke(CurrentState);
    }

    /// <summary>매칭 큐 해제</summary>
    public void DequeueMatch()
    {
        CurrentState = PvPState.IDLE;
        QueuePosition = 0;
        NetworkManager.Instance.DequeueMatch();
        OnStateChanged?.Invoke(CurrentState);
    }

    /// <summary>매칭 수락</summary>
    public void AcceptMatch()
    {
        if (PendingMatchId == 0) return;
        NetworkManager.Instance.AcceptMatch(PendingMatchId);
    }

    /// <summary>PvP 경기장 퇴장</summary>
    public void LeaveMatch()
    {
        NetworkManager.Instance.LeaveInstance();
    }

    /// <summary>PvP 모드인지 판별 (dungeonType 100+)</summary>
    public static bool IsPvPType(uint dungeonType)
    {
        return dungeonType >= 100 && dungeonType < 200;
    }

    // ━━━ 핸들러 ━━━

    private void HandleMatchFound(MatchFoundData data)
    {
        // PvP 타입 매칭만 처리
        if (!IsPvPType(data.DungeonType)) return;

        PendingMatchId = data.MatchId;
        CurrentState = PvPState.MATCH_FOUND;
        Debug.Log($"[PvPManager] Match found! matchId={data.MatchId}, mode={data.DungeonType}, players={data.PlayerCount}");
        OnMatchFound?.Invoke(data);
        OnStateChanged?.Invoke(CurrentState);
    }

    private void HandleMatchStatus(MatchStatusData data)
    {
        // 매칭 중일 때만 처리
        if (CurrentState != PvPState.QUEUED) return;
        QueuePosition = data.QueuePosition;
    }

    private void HandleInstanceEnter(InstanceEnterData data)
    {
        // PvP 인스턴스만 처리
        if (!IsPvPType(data.DungeonType)) return;
        if (data.Result != 0) return;

        CurrentInstanceId = data.InstanceId;
        CurrentState = PvPState.IN_MATCH;
        PendingMatchId = 0;
        Debug.Log($"[PvPManager] Entered PvP match: instance={data.InstanceId}, mode={data.DungeonType}");
        OnMatchEntered?.Invoke();
        OnStateChanged?.Invoke(CurrentState);
    }

    private void HandleInstanceLeaveResult(InstanceLeaveResultData data)
    {
        if (CurrentState != PvPState.IN_MATCH) return;
        if (data.Result != 0) return;

        CurrentInstanceId = 0;
        CurrentState = PvPState.IDLE;
        Debug.Log("[PvPManager] Left PvP match");
        OnMatchLeft?.Invoke();
        OnStateChanged?.Invoke(CurrentState);
    }
}
