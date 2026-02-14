// ━━━ BossManager.cs ━━━
// 보스 메카닉 관리 — 스폰/페이즈/특수공격/인레이지/처치
// NetworkManager 이벤트 구독 → BossUI에 이벤트 발행

using System;
using System.Collections.Generic;
using UnityEngine;
using Network;

public class BossManager : MonoBehaviour
{
    // ━━━ 보스 런타임 데이터 ━━━
    public class BossState
    {
        public ulong EntityId;
        public uint BossId;
        public string Name;
        public int Level;
        public int HP, MaxHP;
        public byte Phase;
        public bool IsEnraged;
    }

    private readonly Dictionary<ulong, BossState> _bosses = new Dictionary<ulong, BossState>();
    public IReadOnlyDictionary<ulong, BossState> Bosses => _bosses;

    // ━━━ 이벤트 ━━━
    public event Action<BossState> OnBossAppeared;
    public event Action<BossState> OnBossPhaseChanged;
    public event Action<BossSpecialAttackData> OnBossSpecialAttacked;
    public event Action<BossState> OnBossEnraged;
    public event Action<BossDefeatedData> OnBossKilled;
    public event Action<BossState> OnBossHPChanged;

    // ━━━ 싱글톤 (Scene-bound) ━━━
    public static BossManager Instance { get; private set; }

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
        net.OnBossSpawn += HandleBossSpawn;
        net.OnBossPhaseChange += HandleBossPhaseChange;
        net.OnBossSpecialAttack += HandleBossSpecialAttack;
        net.OnBossEnrage += HandleBossEnrage;
        net.OnBossDefeated += HandleBossDefeated;
        net.OnAttackResult += HandleAttackResult;
    }

    private void OnDestroy()
    {
        var net = NetworkManager.Instance;
        if (net == null) return;

        net.OnBossSpawn -= HandleBossSpawn;
        net.OnBossPhaseChange -= HandleBossPhaseChange;
        net.OnBossSpecialAttack -= HandleBossSpecialAttack;
        net.OnBossEnrage -= HandleBossEnrage;
        net.OnBossDefeated -= HandleBossDefeated;
        net.OnAttackResult -= HandleAttackResult;

        if (Instance == this) Instance = null;
    }

    // ━━━ 공개 API ━━━

    public BossState GetBoss(ulong entityId)
    {
        _bosses.TryGetValue(entityId, out var boss);
        return boss;
    }

    public bool IsBoss(ulong entityId)
    {
        return _bosses.ContainsKey(entityId);
    }

    // ━━━ 핸들러 ━━━

    private void HandleBossSpawn(BossSpawnData data)
    {
        var boss = new BossState
        {
            EntityId = data.EntityId,
            BossId = data.BossId,
            Name = data.Name,
            Level = data.Level,
            HP = data.HP,
            MaxHP = data.MaxHP,
            Phase = data.Phase,
            IsEnraged = false
        };

        _bosses[data.EntityId] = boss;
        Debug.Log($"[BossManager] Boss appeared: {data.Name} (Lv{data.Level}) HP={data.HP}/{data.MaxHP}");
        OnBossAppeared?.Invoke(boss);
    }

    private void HandleBossPhaseChange(BossPhaseChangeData data)
    {
        if (!_bosses.TryGetValue(data.EntityId, out var boss)) return;

        boss.Phase = data.NewPhase;
        boss.HP = data.HP;
        boss.MaxHP = data.MaxHP;

        Debug.Log($"[BossManager] Phase change: {boss.Name} → Phase {data.NewPhase}");
        OnBossPhaseChanged?.Invoke(boss);
    }

    private void HandleBossSpecialAttack(BossSpecialAttackData data)
    {
        Debug.Log($"[BossManager] Special attack: type={data.AttackType}, dmg={data.Damage}");
        OnBossSpecialAttacked?.Invoke(data);
    }

    private void HandleBossEnrage(BossEnrageData data)
    {
        if (!_bosses.TryGetValue(data.EntityId, out var boss)) return;

        boss.IsEnraged = true;
        Debug.Log($"[BossManager] ENRAGE: {boss.Name}!");
        OnBossEnraged?.Invoke(boss);
    }

    private void HandleBossDefeated(BossDefeatedData data)
    {
        if (_bosses.TryGetValue(data.EntityId, out var boss))
        {
            boss.HP = 0;
            Debug.Log($"[BossManager] Defeated: {boss.Name}");
        }

        _bosses.Remove(data.EntityId);
        OnBossKilled?.Invoke(data);
    }

    private void HandleAttackResult(AttackResultData data)
    {
        if (!_bosses.TryGetValue(data.TargetId, out var boss)) return;

        boss.HP = data.TargetHP;
        boss.MaxHP = data.TargetMaxHP;
        OnBossHPChanged?.Invoke(boss);
    }
}
