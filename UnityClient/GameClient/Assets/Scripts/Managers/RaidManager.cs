// ━━━ RaidManager.cs ━━━
// 레이드 보스 시스템 관리 (S036 패킷 370-379)
// 3페이즈 보스 + 기믹6종 + 스태거 + 인레이지 + 와이프/클리어
// NetworkManager 이벤트 구독 → RaidUI에 이벤트 발행

using System;
using UnityEngine;
using Network;

public class RaidManager : MonoBehaviour
{
    // ━━━ 레이드 상태 ━━━
    public enum RaidState : byte
    {
        IDLE = 0,
        IN_RAID = 1,
        BOSS_ACTIVE = 2,
        WIPED = 3,
        CLEARED = 4,
    }

    // ━━━ 런타임 데이터 ━━━
    public RaidState CurrentState { get; private set; }
    public uint InstanceId { get; private set; }
    public string BossName { get; private set; } = "";
    public uint BossMaxHP { get; private set; }
    public uint BossCurrentHP { get; private set; }
    public byte CurrentPhase { get; private set; }
    public byte MaxPhases { get; private set; }
    public ushort EnrageTimer { get; private set; }
    public byte StaggerGauge { get; private set; }
    public bool IsEnraged { get; private set; }

    // 클리어 보상
    public uint LastClearGold { get; private set; }
    public uint LastClearExp { get; private set; }
    public ushort LastClearTokens { get; private set; }

    // ━━━ 이벤트 ━━━
    public event Action<RaidBossSpawnData> OnBossSpawned;
    public event Action<RaidPhaseChangeData> OnPhaseChanged;
    public event Action<RaidMechanicData> OnMechanicStarted;
    public event Action<RaidMechanicResultData> OnMechanicResult;
    public event Action<byte> OnStaggerUpdated;
    public event Action OnEnraged;
    public event Action<RaidWipeData> OnWiped;
    public event Action<RaidClearData> OnCleared;
    public event Action<RaidAttackResultData> OnAttackResult;

    // ━━━ 싱글톤 (Scene-bound) ━━━
    public static RaidManager Instance { get; private set; }

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
        net.OnRaidBossSpawn += HandleBossSpawn;
        net.OnRaidPhaseChange += HandlePhaseChange;
        net.OnRaidMechanic += HandleMechanic;
        net.OnRaidMechanicResult += HandleMechanicResult;
        net.OnRaidStagger += HandleStagger;
        net.OnRaidEnrage += HandleEnrage;
        net.OnRaidWipe += HandleWipe;
        net.OnRaidClear += HandleClear;
        net.OnRaidAttackResult += HandleAttackResult;
        net.OnInstanceEnter += HandleInstanceEnter;
        net.OnInstanceLeaveResult += HandleInstanceLeave;
    }

    private void OnDestroy()
    {
        var net = NetworkManager.Instance;
        if (net == null) return;

        net.OnRaidBossSpawn -= HandleBossSpawn;
        net.OnRaidPhaseChange -= HandlePhaseChange;
        net.OnRaidMechanic -= HandleMechanic;
        net.OnRaidMechanicResult -= HandleMechanicResult;
        net.OnRaidStagger -= HandleStagger;
        net.OnRaidEnrage -= HandleEnrage;
        net.OnRaidWipe -= HandleWipe;
        net.OnRaidClear -= HandleClear;
        net.OnRaidAttackResult -= HandleAttackResult;
        net.OnInstanceEnter -= HandleInstanceEnter;
        net.OnInstanceLeaveResult -= HandleInstanceLeave;

        if (Instance == this) Instance = null;
    }

    // ━━━ 공개 API ━━━

    /// <summary>레이드 보스 공격</summary>
    public void AttackBoss(ushort skillId, uint damage)
    {
        if (InstanceId == 0 || CurrentState != RaidState.BOSS_ACTIVE) return;
        NetworkManager.Instance.RaidAttack(InstanceId, skillId, damage);
    }

    /// <summary>레이드 퇴장</summary>
    public void LeaveRaid()
    {
        NetworkManager.Instance.LeaveInstance();
    }

    /// <summary>보스 HP 비율 (0~1)</summary>
    public float BossHPRatio
    {
        get
        {
            if (BossMaxHP == 0) return 0f;
            return (float)BossCurrentHP / BossMaxHP;
        }
    }

    /// <summary>기믹 이름 (한국어)</summary>
    public static string GetMechanicName(RaidMechanicId id)
    {
        return id switch
        {
            RaidMechanicId.SAFE_ZONE => "안전 지대",
            RaidMechanicId.STAGGER_CHECK => "무력화 판정",
            RaidMechanicId.COUNTER_ATTACK => "반격 기회",
            RaidMechanicId.POSITION_SWAP => "자리 교대",
            RaidMechanicId.DPS_CHECK => "딜 체크",
            RaidMechanicId.COOPERATION => "협동 기믹",
            _ => $"기믹 {(byte)id}"
        };
    }

    // ━━━ 핸들러 ━━━

    private void HandleInstanceEnter(InstanceEnterData data)
    {
        // 레이드 던전 타입(4=Raid)이 아니면 무시
        if (data.Result != 0 || data.DungeonType != 4) return;
        InstanceId = data.InstanceId;
        CurrentState = RaidState.IN_RAID;
        IsEnraged = false;
        StaggerGauge = 0;
        Debug.Log($"[RaidManager] Entered raid instance={data.InstanceId}");
    }

    private void HandleInstanceLeave(InstanceLeaveResultData data)
    {
        if (data.Result != 0) return;
        if (CurrentState == RaidState.IDLE) return;
        ResetState();
        Debug.Log("[RaidManager] Left raid");
    }

    private void HandleBossSpawn(RaidBossSpawnData data)
    {
        InstanceId = data.InstanceId;
        BossName = data.BossName;
        BossMaxHP = data.MaxHP;
        BossCurrentHP = data.CurrentHP;
        CurrentPhase = data.Phase;
        MaxPhases = data.MaxPhases;
        EnrageTimer = data.EnrageTimer;
        IsEnraged = false;
        StaggerGauge = 0;
        CurrentState = RaidState.BOSS_ACTIVE;
        Debug.Log($"[RaidManager] Boss spawned: {data.BossName}, HP={data.CurrentHP}/{data.MaxHP}, phase={data.Phase}/{data.MaxPhases}, enrage={data.EnrageTimer}s");
        OnBossSpawned?.Invoke(data);
    }

    private void HandlePhaseChange(RaidPhaseChangeData data)
    {
        CurrentPhase = data.Phase;
        MaxPhases = data.MaxPhases;
        Debug.Log($"[RaidManager] Phase changed: {data.Phase}/{data.MaxPhases}");
        OnPhaseChanged?.Invoke(data);
    }

    private void HandleMechanic(RaidMechanicData data)
    {
        Debug.Log($"[RaidManager] Mechanic started: {GetMechanicName(data.MechanicId)} (phase {data.Phase})");
        OnMechanicStarted?.Invoke(data);
    }

    private void HandleMechanicResult(RaidMechanicResultData data)
    {
        Debug.Log($"[RaidManager] Mechanic result: {GetMechanicName(data.MechanicId)} = {(data.Success ? "SUCCESS" : "FAIL")}");
        OnMechanicResult?.Invoke(data);
    }

    private void HandleStagger(RaidStaggerData data)
    {
        StaggerGauge = data.StaggerGauge;
        OnStaggerUpdated?.Invoke(data.StaggerGauge);
    }

    private void HandleEnrage(uint instanceId)
    {
        IsEnraged = true;
        Debug.Log("[RaidManager] Boss ENRAGED!");
        OnEnraged?.Invoke();
    }

    private void HandleWipe(RaidWipeData data)
    {
        CurrentState = RaidState.WIPED;
        Debug.Log($"[RaidManager] WIPE at phase {data.Phase}");
        OnWiped?.Invoke(data);
    }

    private void HandleClear(RaidClearData data)
    {
        CurrentState = RaidState.CLEARED;
        LastClearGold = data.Gold;
        LastClearExp = data.Exp;
        LastClearTokens = data.Tokens;
        BossCurrentHP = 0;
        Debug.Log($"[RaidManager] CLEAR! gold={data.Gold}, exp={data.Exp}, tokens={data.Tokens}");
        OnCleared?.Invoke(data);
    }

    private void HandleAttackResult(RaidAttackResultData data)
    {
        BossCurrentHP = data.CurrentHP;
        BossMaxHP = data.MaxHP;
        OnAttackResult?.Invoke(data);
    }

    private void ResetState()
    {
        CurrentState = RaidState.IDLE;
        InstanceId = 0;
        BossName = "";
        BossMaxHP = 0;
        BossCurrentHP = 0;
        CurrentPhase = 0;
        MaxPhases = 0;
        EnrageTimer = 0;
        StaggerGauge = 0;
        IsEnraged = false;
    }
}
