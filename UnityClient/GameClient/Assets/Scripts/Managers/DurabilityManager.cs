// ━━━ DurabilityManager.cs ━━━
// 내구도 시스템 관리 (S052 TASK 9)
// MsgType: 462-467 — 수리/리롤/내구도 알림/조회

using System;
using System.Collections.Generic;
using UnityEngine;

public class DurabilityManager : MonoBehaviour
{
    // ━━━ 싱글톤 ━━━
    public static DurabilityManager Instance { get; private set; }

    // ━━━ 상수 (GDD items.yaml) ━━━
    public const float MAX_DURABILITY = 100f;
    public const float WARNING_THRESHOLD = 20f;
    public const float BROKEN_THRESHOLD = 0f;
    public const float BROKEN_PENALTY = 0.5f;

    // ━━━ 상태 ━━━
    private Dictionary<byte, Network.DurabilityNotifyData> _slotDurability = new Dictionary<byte, Network.DurabilityNotifyData>();
    private bool _isRepairPanelOpen;
    private bool _isRerollPanelOpen;

    // ━━━ 프로퍼티 ━━━
    public bool IsRepairPanelOpen => _isRepairPanelOpen;
    public bool IsRerollPanelOpen => _isRerollPanelOpen;

    // ━━━ 이벤트 ━━━
    public event Action<Network.DurabilityNotifyData> OnDurabilityChanged;
    public event Action<byte> OnDurabilityWarning;
    public event Action<byte> OnEquipmentBroken;
    public event Action<Network.RepairResultData> OnRepairComplete;
    public event Action<Network.RerollResultData> OnRerollComplete;
    public event Action OnRepairPanelOpened;
    public event Action OnRepairPanelClosed;
    public event Action OnRerollPanelOpened;
    public event Action OnRerollPanelClosed;

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
            nm.OnDurabilityNotify += HandleDurabilityNotify;
            nm.OnRepairResult += HandleRepairResult;
            nm.OnRerollResult += HandleRerollResult;
        }
    }

    private void OnDestroy()
    {
        var nm = Network.NetworkManager.Instance;
        if (nm != null)
        {
            nm.OnDurabilityNotify -= HandleDurabilityNotify;
            nm.OnRepairResult -= HandleRepairResult;
            nm.OnRerollResult -= HandleRerollResult;
        }
        if (Instance == this) Instance = null;
    }

    // ━━━ 핸들러 ━━━

    private void HandleDurabilityNotify(Network.DurabilityNotifyData data)
    {
        _slotDurability[data.InvSlot] = data;
        OnDurabilityChanged?.Invoke(data);

        if (data.IsBroken)
        {
            OnEquipmentBroken?.Invoke(data.InvSlot);
        }
        else if (data.Durability <= WARNING_THRESHOLD)
        {
            OnDurabilityWarning?.Invoke(data.InvSlot);
        }
    }

    private void HandleRepairResult(Network.RepairResultData data)
    {
        OnRepairComplete?.Invoke(data);

        if (data.Result == Network.RepairResult.SUCCESS)
        {
            QueryDurability();
        }
    }

    private void HandleRerollResult(Network.RerollResultData data)
    {
        OnRerollComplete?.Invoke(data);
    }

    // ━━━ 공개 API ━━━

    public void OpenRepairPanel()
    {
        _isRepairPanelOpen = true;
        OnRepairPanelOpened?.Invoke();
    }

    public void CloseRepairPanel()
    {
        _isRepairPanelOpen = false;
        OnRepairPanelClosed?.Invoke();
    }

    public void OpenRerollPanel()
    {
        _isRerollPanelOpen = true;
        OnRerollPanelOpened?.Invoke();
    }

    public void CloseRerollPanel()
    {
        _isRerollPanelOpen = false;
        OnRerollPanelClosed?.Invoke();
    }

    public void RepairSingle(byte invSlot)
    {
        Network.NetworkManager.Instance?.RequestRepair(0, invSlot);
    }

    public void RepairAll()
    {
        Network.NetworkManager.Instance?.RequestRepair(1, 0);
    }

    public void Reroll(byte invSlot, byte[] lockIndices)
    {
        Network.NetworkManager.Instance?.RequestReroll(invSlot, lockIndices ?? new byte[0]);
    }

    public void QueryDurability()
    {
        Network.NetworkManager.Instance?.RequestDurabilityQuery();
    }

    public Network.DurabilityNotifyData GetSlotDurability(byte slot)
    {
        _slotDurability.TryGetValue(slot, out var data);
        return data;
    }

    public bool HasBrokenEquipment()
    {
        foreach (var kvp in _slotDurability)
        {
            if (kvp.Value.IsBroken) return true;
        }
        return false;
    }

    public bool HasLowDurability()
    {
        foreach (var kvp in _slotDurability)
        {
            if (kvp.Value.Durability <= WARNING_THRESHOLD && !kvp.Value.IsBroken) return true;
        }
        return false;
    }
}
