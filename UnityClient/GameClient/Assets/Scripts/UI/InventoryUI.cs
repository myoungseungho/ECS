// ━━━ InventoryUI.cs ━━━
// 인벤토리 패널 — I키 토글, 아이템 슬롯 리스트, 사용/장착 버튼
// InventoryManager.OnInventoryChanged 구독

using UnityEngine;
using UnityEngine.UI;
using System.Collections.Generic;
using Network;

public class InventoryUI : MonoBehaviour
{
    [Header("Panel")]
    [SerializeField] private GameObject inventoryPanel;

    [Header("Item List")]
    [SerializeField] private Transform itemListParent;
    [SerializeField] private GameObject itemSlotTemplate;

    [Header("Info")]
    [SerializeField] private Text itemCountText;

    private readonly List<GameObject> _slotInstances = new List<GameObject>();

    public static InventoryUI Instance { get; private set; }

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
        if (InventoryManager.Instance != null)
            InventoryManager.Instance.OnInventoryChanged += RefreshInventory;

        if (inventoryPanel != null)
            inventoryPanel.SetActive(false);

        if (itemSlotTemplate != null)
            itemSlotTemplate.SetActive(false);
    }

    private void OnDestroy()
    {
        if (InventoryManager.Instance != null)
            InventoryManager.Instance.OnInventoryChanged -= RefreshInventory;

        if (Instance == this) Instance = null;
    }

    private void Update()
    {
        if (Input.GetKeyDown(KeyCode.I))
            TogglePanel();
    }

    public void TogglePanel()
    {
        if (inventoryPanel == null) return;

        bool show = !inventoryPanel.activeSelf;
        inventoryPanel.SetActive(show);

        if (show) RefreshInventory();
    }

    private void RefreshInventory()
    {
        var inv = InventoryManager.Instance;
        if (inv == null) return;

        // 기존 슬롯 제거
        foreach (var go in _slotInstances)
            if (go != null) Destroy(go);
        _slotInstances.Clear();

        // 아이템 개수 표시
        if (itemCountText != null)
            itemCountText.text = $"Items: {inv.ItemCount}";

        // 아이템 슬롯 생성
        if (itemSlotTemplate == null || itemListParent == null) return;

        foreach (var kvp in inv.Items)
        {
            var item = kvp.Value;
            var go = Instantiate(itemSlotTemplate, itemListParent);
            go.SetActive(true);

            // 슬롯 텍스트: "[슬롯] 아이템ID x개수 (E=장착)"
            var text = go.GetComponentInChildren<Text>();
            if (text != null)
            {
                string equipTag = item.Equipped > 0 ? " [E]" : "";
                text.text = $"[{item.Slot}] Item#{item.ItemId} x{item.Count}{equipTag}";
            }

            // 슬롯 클릭으로 아이템 사용 (Button 컴포넌트가 있을 때)
            byte slot = item.Slot;
            byte equipped = item.Equipped;
            var btn = go.GetComponentInChildren<Button>();
            if (btn != null)
                btn.onClick.AddListener(() => OnUseClicked(slot));

            _slotInstances.Add(go);
        }
    }

    private void OnUseClicked(byte slot)
    {
        if (InventoryManager.Instance != null)
            InventoryManager.Instance.UseItem(slot);
    }

    private void OnEquipClicked(byte slot, byte currentEquipped)
    {
        if (InventoryManager.Instance == null) return;

        if (currentEquipped > 0)
            InventoryManager.Instance.UnequipItem(slot);
        else
            InventoryManager.Instance.EquipItem(slot);
    }
}
