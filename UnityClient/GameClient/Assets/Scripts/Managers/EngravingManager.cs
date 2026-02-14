// ━━━ EngravingManager.cs ━━━
// 각인 시스템 관리 (S050 TASK 8 Enhancement)
// MsgType: 454-457

using System;
using System.Collections.Generic;
using UnityEngine;

public class EngravingManager : MonoBehaviour
{
    // ━━━ 싱글톤 ━━━
    public static EngravingManager Instance { get; private set; }

    // ━━━ 상태 ━━━
    private List<Network.EngravingInfo> _engravings = new List<Network.EngravingInfo>();
    private bool _isPanelOpen;

    // ━━━ 상수 ━━━
    public const byte MAX_ACTIVE_ENGRAVINGS = 6;
    public const byte LEVEL1_THRESHOLD = 5;
    public const byte LEVEL2_THRESHOLD = 10;
    public const byte LEVEL3_THRESHOLD = 15;

    // ━━━ 프로퍼티 ━━━
    public IReadOnlyList<Network.EngravingInfo> Engravings => _engravings;
    public bool IsPanelOpen => _isPanelOpen;

    // ━━━ 이벤트 ━━━
    public event Action OnEngravingListChanged;
    public event Action<Network.EngravingResultData> OnEngravingChanged;
    public event Action OnPanelOpened;
    public event Action OnPanelClosed;

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
        var nm = Network.NetworkManager.Instance;
        if (nm != null)
        {
            nm.OnEngravingList += HandleEngravingList;
            nm.OnEngravingResult += HandleEngravingResult;
        }
    }

    private void OnDestroy()
    {
        var nm = Network.NetworkManager.Instance;
        if (nm != null)
        {
            nm.OnEngravingList -= HandleEngravingList;
            nm.OnEngravingResult -= HandleEngravingResult;
        }
        if (Instance == this) Instance = null;
    }

    // ━━━ 핸들러 ━━━

    private void HandleEngravingList(Network.EngravingListData data)
    {
        _engravings.Clear();
        if (data.Engravings != null)
        {
            _engravings.AddRange(data.Engravings);
        }
        OnEngravingListChanged?.Invoke();
    }

    private void HandleEngravingResult(Network.EngravingResultData data)
    {
        OnEngravingChanged?.Invoke(data);
    }

    // ━━━ 공개 API ━━━

    public void OpenPanel()
    {
        _isPanelOpen = true;
        OnPanelOpened?.Invoke();
    }

    public void ClosePanel()
    {
        _isPanelOpen = false;
        OnPanelClosed?.Invoke();
    }

    public void RefreshList()
    {
        Network.NetworkManager.Instance?.RequestEngravingList();
    }

    public void ActivateEngraving(string name)
    {
        Network.NetworkManager.Instance?.EquipEngraving(0, name);
    }

    public void DeactivateEngraving(string name)
    {
        Network.NetworkManager.Instance?.EquipEngraving(1, name);
    }

    public Network.EngravingInfo GetEngraving(string name)
    {
        for (int i = 0; i < _engravings.Count; i++)
        {
            if (_engravings[i].Name == name) return _engravings[i];
        }
        return null;
    }

    public int GetActiveCount()
    {
        int count = 0;
        for (int i = 0; i < _engravings.Count; i++)
        {
            if (_engravings[i].IsActive) count++;
        }
        return count;
    }
}
