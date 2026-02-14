// ━━━ TitleManager.cs ━━━
// 칭호 시스템 관리 — 목록 조회/장착/해제 + 보너스 표시
// NetworkManager 이벤트 구독 → TitleUI에 이벤트 발행

using System;
using System.Collections.Generic;
using UnityEngine;
using Network;

public class TitleManager : MonoBehaviour
{
    // ━━━ 상태 ━━━
    private readonly List<TitleInfo> _titles = new List<TitleInfo>();
    private ushort _equippedId;
    private bool _isPanelOpen;

    // ━━━ 프로퍼티 ━━━
    public IReadOnlyList<TitleInfo> Titles => _titles;
    public ushort EquippedId => _equippedId;
    public bool IsPanelOpen => _isPanelOpen;

    // ━━━ 이벤트 ━━━
    public event Action OnTitleListChanged;
    public event Action<TitleEquipResultData> OnEquipResult;
    public event Action OnPanelOpened;
    public event Action OnPanelClosed;

    // ━━━ 싱글톤 (Scene-bound) ━━━
    public static TitleManager Instance { get; private set; }

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
        net.OnTitleList += HandleTitleList;
        net.OnTitleEquipResult += HandleEquipResult;
    }

    private void OnDestroy()
    {
        var net = NetworkManager.Instance;
        if (net == null) return;

        net.OnTitleList -= HandleTitleList;
        net.OnTitleEquipResult -= HandleEquipResult;

        if (Instance == this) Instance = null;
    }

    // ━━━ 공개 API ━━━

    /// <summary>칭호 패널 열기</summary>
    public void OpenPanel()
    {
        _isPanelOpen = true;
        NetworkManager.Instance.RequestTitleList();
        OnPanelOpened?.Invoke();
    }

    /// <summary>칭호 패널 닫기</summary>
    public void ClosePanel()
    {
        _isPanelOpen = false;
        OnPanelClosed?.Invoke();
    }

    /// <summary>칭호 목록 새로고침</summary>
    public void RefreshList()
    {
        NetworkManager.Instance.RequestTitleList();
    }

    /// <summary>칭호 장착 (titleId=0이면 해제)</summary>
    public void EquipTitle(ushort titleId)
    {
        NetworkManager.Instance.EquipTitle(titleId);
    }

    /// <summary>칭호 해제</summary>
    public void UnequipTitle()
    {
        NetworkManager.Instance.EquipTitle(0);
    }

    /// <summary>칭호 조회</summary>
    public TitleInfo GetTitle(ushort titleId)
    {
        for (int i = 0; i < _titles.Count; i++)
        {
            if (_titles[i].TitleId == titleId) return _titles[i];
        }
        return null;
    }

    /// <summary>현재 장착된 칭호 이름</summary>
    public string GetEquippedTitleName()
    {
        if (_equippedId == 0) return "";
        var title = GetTitle(_equippedId);
        return title != null ? title.Name : "";
    }

    // ━━━ 핸들러 ━━━

    private void HandleTitleList(TitleListData data)
    {
        _titles.Clear();
        _titles.AddRange(data.Titles);
        _equippedId = data.EquippedId;

        Debug.Log($"[TitleManager] List: count={data.Titles.Length}, equipped={data.EquippedId}");
        OnTitleListChanged?.Invoke();
    }

    private void HandleEquipResult(TitleEquipResultData data)
    {
        Debug.Log($"[TitleManager] Equip: result={data.Result}, titleId={data.TitleId}");
        OnEquipResult?.Invoke(data);

        if (data.Result == TitleEquipResult.SUCCESS)
        {
            _equippedId = data.TitleId;
            OnTitleListChanged?.Invoke();
        }
    }
}
