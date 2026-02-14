// ━━━ TripodManager.cs ━━━
// 비급 & 트라이포드 시스템 관리 — 목록 조회/장착/비급 사용(해금)
// NetworkManager 이벤트 구독 → TripodUI에 이벤트 발행

using System;
using System.Collections.Generic;
using UnityEngine;
using Network;

public class TripodManager : MonoBehaviour
{
    // ━━━ 상태 ━━━
    private readonly List<TripodSkillInfo> _skills = new List<TripodSkillInfo>();
    private bool _isPanelOpen;

    // ━━━ 프로퍼티 ━━━
    public IReadOnlyList<TripodSkillInfo> Skills => _skills;
    public bool IsPanelOpen => _isPanelOpen;

    // ━━━ 이벤트 ━━━
    public event Action OnTripodListChanged;
    public event Action<TripodEquipResult> OnEquipResult;
    public event Action<ScrollDiscoverResultData> OnDiscoverResult;
    public event Action OnPanelOpened;
    public event Action OnPanelClosed;

    // ━━━ 싱글톤 (Scene-bound) ━━━
    public static TripodManager Instance { get; private set; }

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
        net.OnTripodList += HandleTripodList;
        net.OnTripodEquipResult += HandleEquipResult;
        net.OnScrollDiscoverResult += HandleDiscoverResult;
    }

    private void OnDestroy()
    {
        var net = NetworkManager.Instance;
        if (net == null) return;

        net.OnTripodList -= HandleTripodList;
        net.OnTripodEquipResult -= HandleEquipResult;
        net.OnScrollDiscoverResult -= HandleDiscoverResult;

        if (Instance == this) Instance = null;
    }

    // ━━━ 공개 API ━━━

    /// <summary>트라이포드 패널 열기</summary>
    public void OpenPanel()
    {
        _isPanelOpen = true;
        NetworkManager.Instance.RequestTripodList();
        OnPanelOpened?.Invoke();
    }

    /// <summary>트라이포드 패널 닫기</summary>
    public void ClosePanel()
    {
        _isPanelOpen = false;
        OnPanelClosed?.Invoke();
    }

    /// <summary>트라이포드 목록 새로고침</summary>
    public void RefreshList()
    {
        NetworkManager.Instance.RequestTripodList();
    }

    /// <summary>트라이포드 장착 요청</summary>
    public void EquipTripod(ushort skillId, byte tier, byte optionIdx)
    {
        NetworkManager.Instance.RequestTripodEquip(skillId, tier, optionIdx);
    }

    /// <summary>비급 사용 (인벤토리 슬롯 → 트라이포드 해금)</summary>
    public void UseScroll(byte scrollSlot)
    {
        NetworkManager.Instance.RequestScrollDiscover(scrollSlot);
    }

    // ━━━ 핸들러 ━━━

    private void HandleTripodList(TripodListData data)
    {
        _skills.Clear();
        _skills.AddRange(data.Skills);

        Debug.Log($"[TripodManager] List: {data.Skills.Length} skills");
        OnTripodListChanged?.Invoke();
    }

    private void HandleEquipResult(TripodEquipResult result)
    {
        Debug.Log($"[TripodManager] Equip: result={result}");
        OnEquipResult?.Invoke(result);

        if (result == TripodEquipResult.SUCCESS)
        {
            NetworkManager.Instance.RequestTripodList();
        }
    }

    private void HandleDiscoverResult(ScrollDiscoverResultData data)
    {
        Debug.Log($"[TripodManager] Discover: result={data.Result}, skill={data.SkillId}, tier={data.Tier}, opt={data.OptionIdx}");
        OnDiscoverResult?.Invoke(data);

        if (data.Result == ScrollDiscoverResult.SUCCESS)
        {
            NetworkManager.Instance.RequestTripodList();
        }
    }
}
