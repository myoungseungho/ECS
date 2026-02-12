// ━━━ BuffManager.cs ━━━
// 버프 시스템 관리 — 버프 목록, 적용, 제거, 타이머
// NetworkManager 이벤트 구독 → UI에 버프 이벤트 발행

using System;
using System.Collections.Generic;
using UnityEngine;
using Network;

public class BuffManager : MonoBehaviour
{
    // ━━━ 버프 데이터 ━━━
    private readonly Dictionary<uint, BuffInfo> _buffs = new Dictionary<uint, BuffInfo>();

    public IReadOnlyDictionary<uint, BuffInfo> Buffs => _buffs;
    public int BuffCount => _buffs.Count;

    // ━━━ 이벤트 ━━━
    public event Action OnBuffListChanged;
    public event Action<BuffResultData> OnBuffApplied;
    public event Action<uint> OnBuffRemoved;

    // ━━━ 싱글톤 (Scene-bound) ━━━
    public static BuffManager Instance { get; private set; }

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
        net.OnBuffList += HandleBuffList;
        net.OnBuffResult += HandleBuffResult;
        net.OnBuffRemoveResp += HandleBuffRemoveResp;
        net.OnEnterGame += HandleEnterGame;
    }

    private void OnDestroy()
    {
        var net = NetworkManager.Instance;
        if (net == null) return;

        net.OnBuffList -= HandleBuffList;
        net.OnBuffResult -= HandleBuffResult;
        net.OnBuffRemoveResp -= HandleBuffRemoveResp;
        net.OnEnterGame -= HandleEnterGame;

        if (Instance == this) Instance = null;
    }

    private void Update()
    {
        // 버프 타이머 틱 (remaining_ms 감소)
        if (_buffs.Count == 0) return;

        uint deltaMs = (uint)(Time.deltaTime * 1000f);
        var expired = new List<uint>();

        foreach (var kvp in _buffs)
        {
            if (kvp.Value.RemainingMs <= deltaMs)
                expired.Add(kvp.Key);
            else
                kvp.Value.RemainingMs -= deltaMs;
        }

        foreach (var buffId in expired)
        {
            _buffs.Remove(buffId);
            OnBuffRemoved?.Invoke(buffId);
        }

        if (expired.Count > 0)
            OnBuffListChanged?.Invoke();
    }

    // ━━━ 공개 API ━━━

    public void ApplyBuff(uint buffId)
    {
        NetworkManager.Instance.ApplyBuff(buffId);
    }

    public void RemoveBuff(uint buffId)
    {
        NetworkManager.Instance.RemoveBuff(buffId);
    }

    public bool HasBuff(uint buffId)
    {
        return _buffs.ContainsKey(buffId);
    }

    public BuffInfo GetBuff(uint buffId)
    {
        _buffs.TryGetValue(buffId, out var buff);
        return buff;
    }

    // ━━━ 핸들러 ━━━

    private void HandleBuffList(BuffInfo[] buffs)
    {
        _buffs.Clear();
        foreach (var buff in buffs)
            _buffs[buff.BuffId] = buff;

        Debug.Log($"[BuffManager] Loaded {buffs.Length} buffs");
        OnBuffListChanged?.Invoke();
    }

    private void HandleBuffResult(BuffResultData data)
    {
        if (data.Result == BuffResult.SUCCESS)
        {
            _buffs[data.BuffId] = new BuffInfo
            {
                BuffId = data.BuffId,
                Stacks = data.Stacks,
                RemainingMs = data.DurationMs
            };
        }

        Debug.Log($"[BuffManager] BuffResult: {data.Result}, buffId={data.BuffId}");
        OnBuffApplied?.Invoke(data);
        OnBuffListChanged?.Invoke();
    }

    private void HandleBuffRemoveResp(BuffRemoveRespData data)
    {
        if (data.Result == 0)
        {
            _buffs.Remove(data.BuffId);
            OnBuffRemoved?.Invoke(data.BuffId);
        }

        OnBuffListChanged?.Invoke();
    }

    private void HandleEnterGame(EnterGameResult result)
    {
        if (result.ResultCode != 0) return;
        NetworkManager.Instance.RequestBuffList();
    }
}
