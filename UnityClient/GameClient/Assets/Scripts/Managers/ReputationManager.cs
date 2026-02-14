// ━━━ ReputationManager.cs ━━━
// 세력 평판 관리 — 평판 조회 + 티어 상태 추적
// NetworkManager 이벤트 구독 → ReputationUI에 이벤트 발행

using System;
using System.Collections.Generic;
using UnityEngine;
using Network;

public class ReputationManager : MonoBehaviour
{
    // ━━━ 상태 ━━━
    private readonly List<ReputationFactionInfo> _factions = new List<ReputationFactionInfo>();
    private bool _isPanelOpen;

    // ━━━ 프로퍼티 ━━━
    public IReadOnlyList<ReputationFactionInfo> Factions => _factions;
    public bool IsPanelOpen => _isPanelOpen;

    // ━━━ 이벤트 ━━━
    public event Action OnReputationChanged;
    public event Action OnPanelOpened;
    public event Action OnPanelClosed;

    // ━━━ 싱글톤 (Scene-bound) ━━━
    public static ReputationManager Instance { get; private set; }

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
        net.OnReputationInfo += HandleReputationInfo;
    }

    private void OnDestroy()
    {
        var net = NetworkManager.Instance;
        if (net == null) return;

        net.OnReputationInfo -= HandleReputationInfo;

        if (Instance == this) Instance = null;
    }

    // ━━━ 공개 API ━━━

    /// <summary>평판 패널 열기</summary>
    public void OpenPanel()
    {
        _isPanelOpen = true;
        NetworkManager.Instance.RequestReputation();
        OnPanelOpened?.Invoke();
    }

    /// <summary>평판 패널 닫기</summary>
    public void ClosePanel()
    {
        _isPanelOpen = false;
        OnPanelClosed?.Invoke();
    }

    /// <summary>평판 새로고침</summary>
    public void RefreshReputation()
    {
        NetworkManager.Instance.RequestReputation();
    }

    /// <summary>세력 이름으로 평판 정보 조회</summary>
    public ReputationFactionInfo GetFaction(string factionId)
    {
        for (int i = 0; i < _factions.Count; i++)
        {
            if (_factions[i].Faction == factionId)
                return _factions[i];
        }
        return null;
    }

    // ━━━ 핸들러 ━━━

    private void HandleReputationInfo(ReputationInfoData data)
    {
        _factions.Clear();
        _factions.AddRange(data.Factions);

        Debug.Log($"[ReputationManager] Factions: count={data.Factions.Length}");
        OnReputationChanged?.Invoke();
    }
}
