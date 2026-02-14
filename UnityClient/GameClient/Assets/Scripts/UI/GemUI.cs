// ━━━ GemUI.cs ━━━
// 보석 장착/합성 UI — 보석 소켓 + 합성 패널
// GemManager 이벤트 구독

using UnityEngine;
using UnityEngine.UI;

public class GemUI : MonoBehaviour
{
    // ━━━ 싱글톤 ━━━
    public static GemUI Instance { get; private set; }

    // ━━━ UI 참조 (ProjectSetup에서 코드 생성) ━━━
    [SerializeField] private GameObject _panel;
    [SerializeField] private Text _titleText;
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
        if (GemManager.Instance != null)
        {
            GemManager.Instance.OnGemEquipped += HandleGemEquipped;
            GemManager.Instance.OnGemFused += HandleGemFused;
            GemManager.Instance.OnPanelOpened += ShowPanel;
            GemManager.Instance.OnPanelClosed += HidePanel;
        }
        if (_panel != null) _panel.SetActive(false);
    }

    private void OnDestroy()
    {
        if (GemManager.Instance != null)
        {
            GemManager.Instance.OnGemEquipped -= HandleGemEquipped;
            GemManager.Instance.OnGemFused -= HandleGemFused;
            GemManager.Instance.OnPanelOpened -= ShowPanel;
            GemManager.Instance.OnPanelClosed -= HidePanel;
        }
        if (Instance == this) Instance = null;
    }

    // ━━━ 핸들러 ━━━

    private void HandleGemEquipped(Network.GemEquipResultData data)
    {
        if (_resultText == null) return;

        if (data.Status == Network.GemResult.SUCCESS)
        {
            string gemName = GemManager.Instance != null
                ? GemManager.Instance.GetGemTypeName(data.GemType)
                : $"Type{data.GemType}";
            string tierName = GemManager.Instance != null
                ? GemManager.Instance.GetTierName(data.GemTier)
                : $"T{data.GemTier}";
            _resultText.text = $"Gem Equipped! {gemName} ({tierName}) -> Slot {data.ItemSlot}/{data.GemSlot}";
            _resultText.color = Color.cyan;
        }
        else
        {
            _resultText.text = $"Gem Equip failed: {data.Status}";
            _resultText.color = Color.red;
        }
    }

    private void HandleGemFused(Network.GemFuseResultData data)
    {
        if (_resultText == null) return;

        if (data.Status == Network.GemResult.SUCCESS)
        {
            string gemName = GemManager.Instance != null
                ? GemManager.Instance.GetGemTypeName(data.GemType)
                : $"Type{data.GemType}";
            string tierName = GemManager.Instance != null
                ? GemManager.Instance.GetTierName(data.NewTier)
                : $"T{data.NewTier}";
            _resultText.text = $"Gem Fused! {gemName} -> {tierName}";
            _resultText.color = Color.magenta;
        }
        else
        {
            _resultText.text = $"Gem Fuse failed: {data.Status}";
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
