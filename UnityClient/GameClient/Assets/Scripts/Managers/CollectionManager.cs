// ━━━ CollectionManager.cs ━━━
// 도감 시스템 관리 — 몬스터 4카테고리 + 장비 5등급 도감 조회
// NetworkManager 이벤트 구독 → CollectionUI에 이벤트 발행

using System;
using System.Collections.Generic;
using UnityEngine;
using Network;

public class CollectionManager : MonoBehaviour
{
    // ━━━ 상태 ━━━
    private readonly List<MonsterCollectionCategory> _monsterCategories = new List<MonsterCollectionCategory>();
    private readonly List<EquipCollectionTier> _equipTiers = new List<EquipCollectionTier>();
    private bool _isPanelOpen;

    // ━━━ 프로퍼티 ━━━
    public IReadOnlyList<MonsterCollectionCategory> MonsterCategories => _monsterCategories;
    public IReadOnlyList<EquipCollectionTier> EquipTiers => _equipTiers;
    public bool IsPanelOpen => _isPanelOpen;

    // ━━━ 이벤트 ━━━
    public event Action OnCollectionChanged;
    public event Action OnPanelOpened;
    public event Action OnPanelClosed;

    // ━━━ 싱글톤 (Scene-bound) ━━━
    public static CollectionManager Instance { get; private set; }

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
        net.OnCollectionInfo += HandleCollectionInfo;
    }

    private void OnDestroy()
    {
        var net = NetworkManager.Instance;
        if (net == null) return;

        net.OnCollectionInfo -= HandleCollectionInfo;

        if (Instance == this) Instance = null;
    }

    // ━━━ 공개 API ━━━

    /// <summary>도감 패널 열기</summary>
    public void OpenPanel()
    {
        _isPanelOpen = true;
        NetworkManager.Instance.RequestCollection();
        OnPanelOpened?.Invoke();
    }

    /// <summary>도감 패널 닫기</summary>
    public void ClosePanel()
    {
        _isPanelOpen = false;
        OnPanelClosed?.Invoke();
    }

    /// <summary>도감 새로고침</summary>
    public void RefreshCollection()
    {
        NetworkManager.Instance.RequestCollection();
    }

    /// <summary>몬스터 카테고리 전체 완성도 계산 (0~1)</summary>
    public float GetMonsterCompletionRate()
    {
        if (_monsterCategories.Count == 0) return 0f;
        int total = 0, registered = 0;
        for (int i = 0; i < _monsterCategories.Count; i++)
        {
            total += _monsterCategories[i].Total;
            registered += _monsterCategories[i].Registered;
        }
        return total > 0 ? (float)registered / total : 0f;
    }

    /// <summary>장비 등급별 등록 수 합계</summary>
    public int GetEquipTotalRegistered()
    {
        int sum = 0;
        for (int i = 0; i < _equipTiers.Count; i++)
        {
            sum += _equipTiers[i].Registered;
        }
        return sum;
    }

    // ━━━ 핸들러 ━━━

    private void HandleCollectionInfo(CollectionInfoData data)
    {
        _monsterCategories.Clear();
        _monsterCategories.AddRange(data.MonsterCategories);
        _equipTiers.Clear();
        _equipTiers.AddRange(data.EquipTiers);

        Debug.Log($"[CollectionManager] Info: monsters={data.MonsterCategories.Length}, equips={data.EquipTiers.Length}");
        OnCollectionChanged?.Invoke();
    }
}
