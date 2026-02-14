// ━━━ DungeonManager.cs ━━━
// 던전 인스턴스 + 매칭 시스템 관리
// NetworkManager 이벤트 구독 → DungeonUI에 이벤트 발행

using System;
using System.Collections.Generic;
using UnityEngine;
using Network;

public class DungeonManager : MonoBehaviour
{
    // ━━━ 던전 타입 ━━━
    public enum DungeonType : uint
    {
        STORY = 1,
        PARTY = 2,
        CHAOS = 3,
        RAID = 4,
        ABYSS = 5,
    }

    // ━━━ 매칭 상태 ━━━
    public enum MatchState : byte
    {
        NONE = 0,
        QUEUED = 1,
        FOUND = 2,
        ACCEPTED = 3,
    }

    // ━━━ 런타임 데이터 ━━━
    public bool InDungeon { get; private set; }
    public uint CurrentInstanceId { get; private set; }
    public uint CurrentDungeonType { get; private set; }
    public byte PlayerCount { get; private set; }
    public byte MonsterCount { get; private set; }

    // 매칭
    public MatchState CurrentMatchState { get; private set; }
    public uint QueuedDungeonType { get; private set; }
    public uint QueuePosition { get; private set; }
    public uint PendingMatchId { get; private set; }

    // ━━━ 이벤트 ━━━
    public event Action<InstanceEnterData> OnDungeonEntered;
    public event Action OnDungeonLeft;
    public event Action<InstanceInfoData> OnDungeonInfoUpdated;
    public event Action<MatchFoundData> OnMatchFound;
    public event Action<MatchState> OnMatchStateChanged;

    // ━━━ 싱글톤 (Scene-bound) ━━━
    public static DungeonManager Instance { get; private set; }

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
        net.OnInstanceEnter += HandleInstanceEnter;
        net.OnInstanceLeaveResult += HandleInstanceLeaveResult;
        net.OnInstanceInfo += HandleInstanceInfo;
        net.OnMatchFound += HandleMatchFound;
        net.OnMatchStatus += HandleMatchStatus;
    }

    private void OnDestroy()
    {
        var net = NetworkManager.Instance;
        if (net == null) return;

        net.OnInstanceEnter -= HandleInstanceEnter;
        net.OnInstanceLeaveResult -= HandleInstanceLeaveResult;
        net.OnInstanceInfo -= HandleInstanceInfo;
        net.OnMatchFound -= HandleMatchFound;
        net.OnMatchStatus -= HandleMatchStatus;

        if (Instance == this) Instance = null;
    }

    // ━━━ 공개 API ━━━

    /// <summary>던전 직접 생성 (파티 리더용)</summary>
    public void CreateDungeon(uint dungeonType)
    {
        NetworkManager.Instance.CreateInstance(dungeonType);
    }

    /// <summary>던전 퇴장</summary>
    public void LeaveDungeon()
    {
        NetworkManager.Instance.LeaveInstance();
    }

    /// <summary>매칭 큐 등록</summary>
    public void EnqueueMatch(uint dungeonType)
    {
        QueuedDungeonType = dungeonType;
        CurrentMatchState = MatchState.QUEUED;
        NetworkManager.Instance.EnqueueMatch(dungeonType);
        OnMatchStateChanged?.Invoke(CurrentMatchState);
    }

    /// <summary>매칭 큐 해제</summary>
    public void DequeueMatch()
    {
        CurrentMatchState = MatchState.NONE;
        QueuedDungeonType = 0;
        QueuePosition = 0;
        NetworkManager.Instance.DequeueMatch();
        OnMatchStateChanged?.Invoke(CurrentMatchState);
    }

    /// <summary>매칭 수락</summary>
    public void AcceptMatch()
    {
        if (PendingMatchId == 0) return;
        CurrentMatchState = MatchState.ACCEPTED;
        NetworkManager.Instance.AcceptMatch(PendingMatchId);
        OnMatchStateChanged?.Invoke(CurrentMatchState);
    }

    // ━━━ 핸들러 ━━━

    private void HandleInstanceEnter(InstanceEnterData data)
    {
        if (data.Result == 0)
        {
            InDungeon = true;
            CurrentInstanceId = data.InstanceId;
            CurrentDungeonType = data.DungeonType;
            CurrentMatchState = MatchState.NONE;
            PendingMatchId = 0;
            Debug.Log($"[DungeonManager] Entered dungeon: instance={data.InstanceId}, type={data.DungeonType}");
        }
        OnDungeonEntered?.Invoke(data);
    }

    private void HandleInstanceLeaveResult(InstanceLeaveResultData data)
    {
        if (data.Result == 0)
        {
            InDungeon = false;
            CurrentInstanceId = 0;
            CurrentDungeonType = 0;
            PlayerCount = 0;
            MonsterCount = 0;
            Debug.Log($"[DungeonManager] Left dungeon, returning to zone={data.ZoneId}");
        }
        OnDungeonLeft?.Invoke();
    }

    private void HandleInstanceInfo(InstanceInfoData data)
    {
        CurrentInstanceId = data.InstanceId;
        CurrentDungeonType = data.DungeonType;
        PlayerCount = data.PlayerCount;
        MonsterCount = data.MonsterCount;
        OnDungeonInfoUpdated?.Invoke(data);
    }

    private void HandleMatchFound(MatchFoundData data)
    {
        PendingMatchId = data.MatchId;
        CurrentMatchState = MatchState.FOUND;
        Debug.Log($"[DungeonManager] Match found! matchId={data.MatchId}, type={data.DungeonType}, players={data.PlayerCount}");
        OnMatchFound?.Invoke(data);
        OnMatchStateChanged?.Invoke(CurrentMatchState);
    }

    private void HandleMatchStatus(MatchStatusData data)
    {
        QueuePosition = data.QueuePosition;
        if (data.Status == 0)
        {
            CurrentMatchState = MatchState.QUEUED;
        }
    }
}
