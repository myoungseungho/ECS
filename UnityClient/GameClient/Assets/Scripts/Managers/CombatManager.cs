// ━━━ CombatManager.cs ━━━
// 전투 관리 — 공격, 사망, 부활 처리
// NetworkManager 이벤트 구독 → UI에 전투 이벤트 발행

using System;
using UnityEngine;
using Network;

public class CombatManager : MonoBehaviour
{
    // ━━━ 상태 ━━━
    public bool IsDead { get; private set; }
    public ulong SelectedTarget { get; private set; }

    // ━━━ 이벤트 ━━━
    public event Action<AttackResultData> OnAttackFeedback;
    public event Action<CombatDiedData> OnEntityDied;
    public event Action<RespawnResultData> OnRespawnComplete;

    // ━━━ 싱글톤 (Scene-bound) ━━━
    public static CombatManager Instance { get; private set; }

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
        net.OnAttackResult += HandleAttackResult;
        net.OnCombatDied += HandleCombatDied;
        net.OnRespawnResult += HandleRespawnResult;
    }

    private void OnDestroy()
    {
        var net = NetworkManager.Instance;
        if (net == null) return;

        net.OnAttackResult -= HandleAttackResult;
        net.OnCombatDied -= HandleCombatDied;
        net.OnRespawnResult -= HandleRespawnResult;

        if (Instance == this) Instance = null;
    }

    // ━━━ 공개 API ━━━

    /// <summary>타겟 선택</summary>
    public void SelectTarget(ulong entityId)
    {
        SelectedTarget = entityId;
    }

    /// <summary>공격 실행</summary>
    public void Attack(ulong targetEntityId)
    {
        NetworkManager.Instance.SendAttack(targetEntityId);
    }

    /// <summary>부활 요청</summary>
    public void Respawn()
    {
        NetworkManager.Instance.RequestRespawn();
    }

    // ━━━ 핸들러 ━━━

    private void HandleAttackResult(AttackResultData data)
    {
        OnAttackFeedback?.Invoke(data);
    }

    private void HandleCombatDied(CombatDiedData data)
    {
        // 내가 죽었는지 확인
        if (data.DeadEntityId == NetworkManager.Instance.MyEntityId)
        {
            IsDead = true;
        }

        OnEntityDied?.Invoke(data);
    }

    private void HandleRespawnResult(RespawnResultData data)
    {
        if (data.ResultCode == 0)
        {
            IsDead = false;
        }

        OnRespawnComplete?.Invoke(data);
    }
}
