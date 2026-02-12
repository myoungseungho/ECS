// ━━━ SkillManager.cs ━━━
// 스킬 시스템 관리 — 스킬 목록, 쿨다운, 사용
// NetworkManager 이벤트 구독 → UI에 스킬 이벤트 발행

using System;
using System.Collections.Generic;
using UnityEngine;
using Network;

public class SkillManager : MonoBehaviour
{
    // ━━━ 스킬 데이터 ━━━
    private readonly Dictionary<uint, SkillInfo> _skills = new Dictionary<uint, SkillInfo>();
    private readonly Dictionary<uint, float> _cooldowns = new Dictionary<uint, float>();

    public IReadOnlyDictionary<uint, SkillInfo> Skills => _skills;

    // ━━━ 이벤트 ━━━
    public event Action OnSkillListChanged;
    public event Action<SkillResultData> OnSkillUsed;
    public event Action<uint> OnCooldownStarted;

    // ━━━ 싱글톤 (Scene-bound) ━━━
    public static SkillManager Instance { get; private set; }

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
        net.OnSkillList += HandleSkillList;
        net.OnSkillResult += HandleSkillResult;
        net.OnEnterGame += HandleEnterGame;
    }

    private void OnDestroy()
    {
        var net = NetworkManager.Instance;
        if (net == null) return;

        net.OnSkillList -= HandleSkillList;
        net.OnSkillResult -= HandleSkillResult;
        net.OnEnterGame -= HandleEnterGame;

        if (Instance == this) Instance = null;
    }

    private void Update()
    {
        // 쿨다운 틱
        if (_cooldowns.Count == 0) return;

        var expired = new List<uint>();
        var keys = new List<uint>(_cooldowns.Keys);
        foreach (var skillId in keys)
        {
            _cooldowns[skillId] -= Time.deltaTime;
            if (_cooldowns[skillId] <= 0f)
                expired.Add(skillId);
        }
        foreach (var skillId in expired)
            _cooldowns.Remove(skillId);
    }

    // ━━━ 공개 API ━━━

    public void UseSkill(uint skillId, ulong targetEntity)
    {
        if (IsOnCooldown(skillId))
        {
            Debug.Log($"[SkillManager] Skill {skillId} on cooldown");
            return;
        }

        NetworkManager.Instance.UseSkill(skillId, targetEntity);
    }

    public bool IsOnCooldown(uint skillId)
    {
        return _cooldowns.ContainsKey(skillId);
    }

    public float GetCooldownRemaining(uint skillId)
    {
        return _cooldowns.TryGetValue(skillId, out var remaining) ? remaining : 0f;
    }

    public SkillInfo GetSkill(uint skillId)
    {
        _skills.TryGetValue(skillId, out var skill);
        return skill;
    }

    // ━━━ 핸들러 ━━━

    private void HandleSkillList(SkillInfo[] skills)
    {
        _skills.Clear();
        foreach (var skill in skills)
            _skills[skill.SkillId] = skill;

        Debug.Log($"[SkillManager] Loaded {skills.Length} skills");
        OnSkillListChanged?.Invoke();
    }

    private void HandleSkillResult(SkillResultData data)
    {
        if (data.Result == 0 && _skills.TryGetValue(data.SkillId, out var skill))
        {
            float cdSec = skill.CooldownMs / 1000f;
            if (cdSec > 0f)
            {
                _cooldowns[data.SkillId] = cdSec;
                OnCooldownStarted?.Invoke(data.SkillId);
            }
        }

        OnSkillUsed?.Invoke(data);
    }

    private void HandleEnterGame(EnterGameResult result)
    {
        if (result.ResultCode != 0) return;
        NetworkManager.Instance.RequestSkillList();
    }
}
