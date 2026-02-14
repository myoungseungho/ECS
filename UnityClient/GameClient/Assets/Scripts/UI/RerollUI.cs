// ━━━ RerollUI.cs ━━━
// 옵션 재감정 창 — F11 토글 (잠금 토글 + 결과 표시)
// DurabilityManager 이벤트 구독

using UnityEngine;
using UnityEngine.UI;

public class RerollUI : MonoBehaviour
{
    // ━━━ 싱글톤 ━━━
    public static RerollUI Instance { get; private set; }

    // ━━━ UI 참조 (ProjectSetup에서 코드 생성) ━━━
    [SerializeField] private GameObject _panel;
    [SerializeField] private Text _titleText;
    [SerializeField] private Text _optionsText;
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
            DurabilityManager.Instance.OnRerollComplete += HandleRerollComplete;
            DurabilityManager.Instance.OnRerollPanelOpened += ShowPanel;
            DurabilityManager.Instance.OnRerollPanelClosed += HidePanel;
        }
        if (_panel != null) _panel.SetActive(false);
    }

    private void Update()
    {
        if (Input.GetKeyDown(KeyCode.F11))
        {
            if (DurabilityManager.Instance != null)
            {
                if (DurabilityManager.Instance.IsRerollPanelOpen)
                    DurabilityManager.Instance.CloseRerollPanel();
                else
                    DurabilityManager.Instance.OpenRerollPanel();
            }
        }
    }

    private void OnDestroy()
    {
        if (DurabilityManager.Instance != null)
        {
            DurabilityManager.Instance.OnRerollComplete -= HandleRerollComplete;
            DurabilityManager.Instance.OnRerollPanelOpened -= ShowPanel;
            DurabilityManager.Instance.OnRerollPanelClosed -= HidePanel;
        }
        if (Instance == this) Instance = null;
    }

    // ━━━ 핸들러 ━━━

    private void HandleRerollComplete(Network.RerollResultData data)
    {
        if (data.Result == Network.RerollResult.SUCCESS)
        {
            if (_optionsText != null)
            {
                var sb = new System.Text.StringBuilder();
                sb.AppendLine("Random Options:");
                sb.AppendLine("─────────────────");

                for (int i = 0; i < data.Options.Length; i++)
                {
                    var opt = data.Options[i];
                    string lockIcon = opt.Locked ? "[LOCK]" : "[    ]";
                    string sign = opt.Value >= 0 ? "+" : "";
                    sb.AppendLine($"  {lockIcon} {opt.StatName} {sign}{opt.Value}");
                }
                _optionsText.text = sb.ToString();
            }

            if (_resultText != null)
            {
                _resultText.text = "Reroll complete!";
                _resultText.color = Color.cyan;
            }
        }
        else
        {
            if (_resultText != null)
            {
                _resultText.text = $"Reroll failed: {data.Result}";
                _resultText.color = Color.red;
            }
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
