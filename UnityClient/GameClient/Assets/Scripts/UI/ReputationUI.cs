// ━━━ ReputationUI.cs ━━━
// 평판 UI — 세력별 평판 표시 + 프로그레스바 + 티어
// ReputationManager 이벤트 구독 (N키 토글)

using UnityEngine;
using UnityEngine.UI;
using Network;

public class ReputationUI : MonoBehaviour
{
    // ━━━ UI 참조 (Start에서 코드 생성) ━━━
    private GameObject _panel;
    private Text _titleText;
    private Text _reputationText;
    private Text _statusText;
    private Button _refreshButton;

    private void Start()
    {
        BuildUI();

        if (ReputationManager.Instance != null)
        {
            ReputationManager.Instance.OnReputationChanged += HandleReputationChanged;
            ReputationManager.Instance.OnPanelOpened += ShowPanel;
            ReputationManager.Instance.OnPanelClosed += HidePanel;
        }

        if (_panel != null) _panel.SetActive(false);
    }

    private void OnDestroy()
    {
        if (ReputationManager.Instance != null)
        {
            ReputationManager.Instance.OnReputationChanged -= HandleReputationChanged;
            ReputationManager.Instance.OnPanelOpened -= ShowPanel;
            ReputationManager.Instance.OnPanelClosed -= HidePanel;
        }
    }

    private void Update()
    {
        // N키로 평판 패널 토글
        if (Input.GetKeyDown(KeyCode.N))
        {
            if (ReputationManager.Instance != null)
            {
                if (ReputationManager.Instance.IsPanelOpen)
                    ReputationManager.Instance.ClosePanel();
                else
                    ReputationManager.Instance.OpenPanel();
            }
        }

        // ESC로 닫기
        if (_panel != null && _panel.activeSelf && Input.GetKeyDown(KeyCode.Escape))
        {
            ReputationManager.Instance?.ClosePanel();
        }
    }

    // ━━━ UI 구성 (코드 생성) ━━━

    private void BuildUI()
    {
        // Panel
        _panel = new GameObject("ReputationPanel");
        _panel.transform.SetParent(transform, false);
        var panelRT = _panel.AddComponent<RectTransform>();
        panelRT.anchorMin = new Vector2(0.6f, 0.35f);
        panelRT.anchorMax = new Vector2(0.98f, 0.95f);
        panelRT.offsetMin = Vector2.zero;
        panelRT.offsetMax = Vector2.zero;
        var panelBg = _panel.AddComponent<Image>();
        panelBg.color = new Color(0.06f, 0.04f, 0.1f, 0.92f);

        // Title
        var titleGo = CreateText(_panel.transform, "Title", "Reputation",
            new Vector2(0.5f, 1f), new Vector2(0.5f, 1f), new Vector2(0, -8), new Vector2(200, 30));
        _titleText = titleGo.GetComponent<Text>();
        _titleText.fontSize = 18;
        _titleText.fontStyle = FontStyle.Bold;
        _titleText.alignment = TextAnchor.MiddleCenter;
        _titleText.color = new Color(0.85f, 0.7f, 1f);
        var titleRT = titleGo.GetComponent<RectTransform>();
        titleRT.pivot = new Vector2(0.5f, 1f);

        // Subtitle
        var subGo = CreateText(_panel.transform, "Subtitle",
            "[N] Toggle  |  [ESC] Close",
            new Vector2(0.5f, 1f), new Vector2(0.5f, 1f), new Vector2(0, -36), new Vector2(300, 18));
        var subText = subGo.GetComponent<Text>();
        subText.fontSize = 11;
        subText.alignment = TextAnchor.MiddleCenter;
        subText.color = new Color(0.6f, 0.6f, 0.6f);
        var subRT = subGo.GetComponent<RectTransform>();
        subRT.pivot = new Vector2(0.5f, 1f);

        // Refresh Button
        var refreshGo = new GameObject("RefreshButton");
        refreshGo.transform.SetParent(_panel.transform, false);
        var refreshRT = refreshGo.AddComponent<RectTransform>();
        refreshRT.anchorMin = new Vector2(1f, 1f);
        refreshRT.anchorMax = new Vector2(1f, 1f);
        refreshRT.pivot = new Vector2(1f, 1f);
        refreshRT.anchoredPosition = new Vector2(-10, -8);
        refreshRT.sizeDelta = new Vector2(70, 24);
        var refreshImg = refreshGo.AddComponent<Image>();
        refreshImg.color = new Color(0.3f, 0.2f, 0.4f);
        _refreshButton = refreshGo.AddComponent<Button>();
        _refreshButton.onClick.AddListener(OnRefreshClicked);
        var refreshTextGo = CreateText(refreshGo.transform, "Text", "Refresh",
            Vector2.zero, Vector2.one, Vector2.zero, Vector2.zero);
        SetFillRT(refreshTextGo);
        refreshTextGo.GetComponent<Text>().alignment = TextAnchor.MiddleCenter;
        refreshTextGo.GetComponent<Text>().fontSize = 11;

        // Reputation Display Area
        var listGo = CreateText(_panel.transform, "ReputationList", "Press [N] to view reputation.",
            new Vector2(0f, 0f), new Vector2(1f, 1f), Vector2.zero, Vector2.zero);
        var listRT = listGo.GetComponent<RectTransform>();
        listRT.anchorMin = new Vector2(0f, 0.06f);
        listRT.anchorMax = new Vector2(1f, 0.88f);
        listRT.offsetMin = new Vector2(12, 0);
        listRT.offsetMax = new Vector2(-12, 0);
        _reputationText = listGo.GetComponent<Text>();
        _reputationText.fontSize = 13;
        _reputationText.alignment = TextAnchor.UpperLeft;

        // Status Text
        var statusGo = CreateText(_panel.transform, "StatusText", "",
            new Vector2(0f, 0f), new Vector2(1f, 0.06f), Vector2.zero, Vector2.zero);
        _statusText = statusGo.GetComponent<Text>();
        _statusText.fontSize = 12;
        _statusText.alignment = TextAnchor.MiddleLeft;
        var statusRT = statusGo.GetComponent<RectTransform>();
        statusRT.anchorMin = new Vector2(0f, 0f);
        statusRT.anchorMax = new Vector2(1f, 0.06f);
        statusRT.offsetMin = new Vector2(12, 0);
        statusRT.offsetMax = new Vector2(-12, 0);
    }

    // ━━━ 이벤트 핸들러 ━━━

    private void HandleReputationChanged()
    {
        RefreshDisplay();
    }

    private void ShowPanel()
    {
        if (_panel != null) _panel.SetActive(true);
        RefreshDisplay();
    }

    private void HidePanel()
    {
        if (_panel != null) _panel.SetActive(false);
    }

    // ━━━ UI 갱신 ━━━

    private void RefreshDisplay()
    {
        if (_reputationText == null || ReputationManager.Instance == null) return;

        var factions = ReputationManager.Instance.Factions;
        var sb = new System.Text.StringBuilder();

        sb.AppendLine("Faction Reputation:");
        sb.AppendLine("════════════════════════════════════════");

        if (factions.Count == 0)
        {
            sb.AppendLine("  No reputation data.");
        }
        else
        {
            for (int i = 0; i < factions.Count; i++)
            {
                var f = factions[i];
                sb.AppendLine($"  {f.NameKr} ({f.Faction})");
                sb.AppendLine($"    Tier: {GetTierDisplay(f.TierName)}");
                sb.AppendLine($"    Points: {f.Points:N0}");

                // Progress bar toward next tier
                if (f.NextTierMin > 0)
                {
                    uint prevMin = GetPrevTierMin(f.TierName);
                    uint range = f.NextTierMin - prevMin;
                    uint current = f.Points - prevMin;
                    float pct = range > 0 ? (float)current / range : 1f;
                    int filled = (int)(pct * 20);
                    if (filled > 20) filled = 20;
                    string bar = new string('#', filled) + new string('-', 20 - filled);
                    sb.AppendLine($"    [{bar}] {(pct * 100):F0}%");
                    sb.AppendLine($"    Next: {f.NextTierMin:N0} pts");
                }
                else
                {
                    sb.AppendLine($"    [####################] MAX");
                }

                sb.AppendLine();
            }
        }

        _reputationText.text = sb.ToString();
    }

    // ━━━ 헬퍼 ━━━

    private static string GetTierDisplay(string tier)
    {
        switch (tier)
        {
            case "neutral":  return "<color=#aaaaaa>Neutral</color>";
            case "friendly": return "<color=#88cc88>Friendly</color>";
            case "honored":  return "<color=#88aaff>Honored</color>";
            case "revered":  return "<color=#cc88ff>Revered</color>";
            case "exalted":  return "<color=#ffcc44>Exalted</color>";
            default:         return tier;
        }
    }

    private static uint GetPrevTierMin(string tier)
    {
        switch (tier)
        {
            case "neutral":  return 0;
            case "friendly": return 500;
            case "honored":  return 2000;
            case "revered":  return 5000;
            case "exalted":  return 10000;
            default:         return 0;
        }
    }

    // ━━━ 버튼 콜백 ━━━

    private void OnRefreshClicked()
    {
        ReputationManager.Instance?.RefreshReputation();
    }

    // ━━━ 유틸 ━━━

    private static void SetFillRT(GameObject go)
    {
        var rt = go.GetComponent<RectTransform>();
        rt.anchorMin = Vector2.zero;
        rt.anchorMax = Vector2.one;
        rt.offsetMin = Vector2.zero;
        rt.offsetMax = Vector2.zero;
    }

    private static GameObject CreateText(Transform parent, string name, string text,
        Vector2 anchorMin, Vector2 anchorMax, Vector2 anchoredPos, Vector2 sizeDelta)
    {
        var go = new GameObject(name);
        go.transform.SetParent(parent, false);
        var rt = go.AddComponent<RectTransform>();
        rt.anchorMin = anchorMin;
        rt.anchorMax = anchorMax;
        rt.pivot = new Vector2(0f, 1f);
        rt.anchoredPosition = anchoredPos;
        rt.sizeDelta = sizeDelta;

        var t = go.AddComponent<Text>();
        t.text = text;
        t.fontSize = 14;
        t.color = Color.white;
        t.alignment = TextAnchor.UpperLeft;
        t.font = Resources.GetBuiltinResource<Font>("LegacyRuntime.ttf");

        return go;
    }
}
