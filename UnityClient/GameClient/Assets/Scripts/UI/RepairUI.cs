// ━━━ RepairUI.cs ━━━
// NPC 수리 창 — F10 토글 (단일/전체 수리)
// DurabilityManager 이벤트 구독

using UnityEngine;
using UnityEngine.UI;

public class RepairUI : MonoBehaviour
{
    // ━━━ 싱글톤 ━━━
    public static RepairUI Instance { get; private set; }

    // ━━━ UI 참조 (ProjectSetup에서 코드 생성) ━━━
    [SerializeField] private GameObject _panel;
    [SerializeField] private Text _titleText;
    [SerializeField] private Text _durabilityText;
    [SerializeField] private Text _resultText;

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
        if (DurabilityManager.Instance != null)
        {
            DurabilityManager.Instance.OnDurabilityChanged += HandleDurabilityChanged;
            DurabilityManager.Instance.OnDurabilityWarning += HandleDurabilityWarning;
            DurabilityManager.Instance.OnEquipmentBroken += HandleEquipmentBroken;
            DurabilityManager.Instance.OnRepairComplete += HandleRepairComplete;
            DurabilityManager.Instance.OnRepairPanelOpened += ShowPanel;
            DurabilityManager.Instance.OnRepairPanelClosed += HidePanel;
        }
        if (_panel != null) _panel.SetActive(false);
    }

    private void Update()
    {
        if (Input.GetKeyDown(KeyCode.F10))
        {
            if (DurabilityManager.Instance != null)
            {
                if (DurabilityManager.Instance.IsRepairPanelOpen)
                    DurabilityManager.Instance.CloseRepairPanel();
                else
                {
                    DurabilityManager.Instance.OpenRepairPanel();
                    DurabilityManager.Instance.QueryDurability();
                }
            }
        }
    }

    private void OnDestroy()
    {
        if (DurabilityManager.Instance != null)
        {
            DurabilityManager.Instance.OnDurabilityChanged -= HandleDurabilityChanged;
            DurabilityManager.Instance.OnDurabilityWarning -= HandleDurabilityWarning;
            DurabilityManager.Instance.OnEquipmentBroken -= HandleEquipmentBroken;
            DurabilityManager.Instance.OnRepairComplete -= HandleRepairComplete;
            DurabilityManager.Instance.OnRepairPanelOpened -= ShowPanel;
            DurabilityManager.Instance.OnRepairPanelClosed -= HidePanel;
        }
        if (Instance == this) Instance = null;
    }

    // ━━━ 핸들러 ━━━

    private void HandleDurabilityChanged(Network.DurabilityNotifyData data)
    {
        if (_durabilityText == null) return;

        string status = data.IsBroken ? "[BROKEN]" : (data.Durability <= DurabilityManager.WARNING_THRESHOLD ? "[LOW]" : "[OK]");
        Color color = data.IsBroken ? Color.red : (data.Durability <= DurabilityManager.WARNING_THRESHOLD ? Color.yellow : Color.white);

        _durabilityText.text = $"Slot {data.InvSlot}: {data.Durability:F1}/{DurabilityManager.MAX_DURABILITY} {status}";
        _durabilityText.color = color;
    }

    private void HandleDurabilityWarning(byte slot)
    {
        if (_resultText != null)
        {
            _resultText.text = $"Warning: Slot {slot} durability low!";
            _resultText.color = Color.yellow;
        }
    }

    private void HandleEquipmentBroken(byte slot)
    {
        if (_resultText != null)
        {
            _resultText.text = $"Slot {slot} is BROKEN! Stats reduced by 50%";
            _resultText.color = Color.red;
        }
    }

    private void HandleRepairComplete(Network.RepairResultData data)
    {
        if (_resultText == null) return;

        if (data.Result == Network.RepairResult.SUCCESS)
        {
            _resultText.text = $"Repaired {data.RepairedCount} items. Cost: {data.TotalCost}G";
            _resultText.color = Color.cyan;
        }
        else
        {
            _resultText.text = $"Repair failed: {data.Result}";
            _resultText.color = Color.red;
        }
    }

    private void ShowPanel()
    {
        if (_panel != null) _panel.SetActive(true);
    }

    private void HidePanel()
    {
        if (_panel != null) _panel.SetActive(false);
    }
}
