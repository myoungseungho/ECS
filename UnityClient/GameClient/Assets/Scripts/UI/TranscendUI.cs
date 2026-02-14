// ━━━ TranscendUI.cs ━━━
// 초월 UI — 강화 UI 확장 (EnhanceUI 내 탭 or 독립 패널)
// NetworkManager 직접 구독 (매니저 없이)

using UnityEngine;
using UnityEngine.UI;

public class TranscendUI : MonoBehaviour
{
    // ━━━ 싱글톤 ━━━
    public static TranscendUI Instance { get; private set; }

    // ━━━ UI 참조 (ProjectSetup에서 코드 생성) ━━━
    [SerializeField] private GameObject _panel;
    [SerializeField] private Text _titleText;
    [SerializeField] private Text _resultText;
    [SerializeField] private Text _infoText;

    // ━━━ 상태 ━━━
    private bool _isPanelOpen;

    // ━━━ 프로퍼티 ━━━
    public bool IsPanelOpen => _isPanelOpen;

    // ━━━ 이벤트 ━━━
    public event System.Action<Network.TranscendResultData> OnTranscendComplete;

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
            nm.OnTranscendResult += HandleTranscendResult;
        }
        if (_panel != null) _panel.SetActive(false);
    }

    private void OnDestroy()
    {
        var nm = Network.NetworkManager.Instance;
        if (nm != null)
        {
            nm.OnTranscendResult -= HandleTranscendResult;
        }
        if (Instance == this) Instance = null;
    }

    // ━━━ 핸들러 ━━━

    private void HandleTranscendResult(Network.TranscendResultData data)
    {
        if (_resultText == null) return;

        if (data.Result == Network.TranscendResult.SUCCESS)
        {
            if (data.Success)
            {
                _resultText.text = $"Transcend SUCCESS! {data.Slot} -> Lv{data.NewLevel} (cost: {data.GoldCost}G)";
                _resultText.color = Color.yellow;
            }
            else
            {
                _resultText.text = $"Transcend FAILED... {data.Slot} remains Lv{data.NewLevel} (cost: {data.GoldCost}G)";
                _resultText.color = new Color(1f, 0.5f, 0f);
            }
        }
        else
        {
            string reason = data.Result.ToString();
            _resultText.text = $"Cannot transcend: {reason}";
            _resultText.color = Color.red;
        }

        OnTranscendComplete?.Invoke(data);
    }

    // ━━━ 공개 API ━━━

    public void OpenPanel()
    {
        _isPanelOpen = true;
        if (_panel != null) _panel.SetActive(true);
        UpdateInfo();
    }

    public void ClosePanel()
    {
        _isPanelOpen = false;
        if (_panel != null) _panel.SetActive(false);
    }

    public void RequestTranscend(string slot)
    {
        Network.NetworkManager.Instance?.RequestTranscend(slot);
    }

    private void UpdateInfo()
    {
        if (_infoText == null) return;
        var sb = new System.Text.StringBuilder();
        sb.AppendLine("Equipment Transcendence");
        sb.AppendLine("─────────────────");
        sb.AppendLine("Requires: +15 enhancement");
        sb.AppendLine("Max Level: 5");
        sb.AppendLine("Each level: +10% stat bonus");
        sb.AppendLine("");
        sb.AppendLine("Success Rate:");
        sb.AppendLine("  Lv1: 50%  (50,000G)");
        sb.AppendLine("  Lv2: 30%  (100,000G)");
        sb.AppendLine("  Lv3: 20%  (200,000G)");
        sb.AppendLine("  Lv4: 10%  (500,000G)");
        sb.AppendLine("  Lv5:  5%  (1,000,000G)");
        _infoText.text = sb.ToString();
    }
}
