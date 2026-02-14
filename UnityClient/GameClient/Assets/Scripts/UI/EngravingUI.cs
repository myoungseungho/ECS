// ━━━ EngravingUI.cs ━━━
// 각인 목록/활성화 UI — F9 토글
// EngravingManager 이벤트 구독

using UnityEngine;
using UnityEngine.UI;

public class EngravingUI : MonoBehaviour
{
    // ━━━ 싱글톤 ━━━
    public static EngravingUI Instance { get; private set; }

    // ━━━ UI 참조 (ProjectSetup에서 코드 생성) ━━━
    [SerializeField] private GameObject _panel;
    [SerializeField] private Text _titleText;
    [SerializeField] private Text _listText;
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
        if (EngravingManager.Instance != null)
        {
            EngravingManager.Instance.OnEngravingListChanged += HandleListChanged;
            EngravingManager.Instance.OnEngravingChanged += HandleEngravingChanged;
            EngravingManager.Instance.OnPanelOpened += ShowPanel;
            EngravingManager.Instance.OnPanelClosed += HidePanel;
        }
        if (_panel != null) _panel.SetActive(false);
    }

    private void Update()
    {
        if (Input.GetKeyDown(KeyCode.F9))
        {
            if (EngravingManager.Instance != null)
            {
                if (EngravingManager.Instance.IsPanelOpen)
                    EngravingManager.Instance.ClosePanel();
                else
                {
                    EngravingManager.Instance.OpenPanel();
                    EngravingManager.Instance.RefreshList();
                }
            }
        }
    }

    private void OnDestroy()
    {
        if (EngravingManager.Instance != null)
        {
            EngravingManager.Instance.OnEngravingListChanged -= HandleListChanged;
            EngravingManager.Instance.OnEngravingChanged -= HandleEngravingChanged;
            EngravingManager.Instance.OnPanelOpened -= ShowPanel;
            EngravingManager.Instance.OnPanelClosed -= HidePanel;
        }
        if (Instance == this) Instance = null;
    }

    // ━━━ 핸들러 ━━━

    private void HandleListChanged()
    {
        if (_listText == null) return;

        var mgr = EngravingManager.Instance;
        if (mgr == null) return;

        var sb = new System.Text.StringBuilder();
        sb.AppendLine($"Active: {mgr.GetActiveCount()}/{EngravingManager.MAX_ACTIVE_ENGRAVINGS}");
        sb.AppendLine("─────────────────");

        foreach (var e in mgr.Engravings)
        {
            string active = e.IsActive ? "[ON]" : "[--]";
            sb.AppendLine($"{active} {e.NameKr} (Lv{e.ActiveLevel}, {e.Points}pt) {e.EffectKey}+{e.EffectValue}");
        }
        _listText.text = sb.ToString();
    }

    private void HandleEngravingChanged(Network.EngravingResultData data)
    {
        if (_resultText == null) return;

        if (data.Result == Network.EngravingResult.SUCCESS)
        {
            _resultText.text = $"Engraving changed: {data.Name} (active={data.ActiveCount})";
            _resultText.color = Color.cyan;
        }
        else
        {
            _resultText.text = $"Engraving failed: {data.Result}";
            _resultText.color = Color.red;
        }

        // Refresh list after change
        if (EngravingManager.Instance != null)
            EngravingManager.Instance.RefreshList();
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
