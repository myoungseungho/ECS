// ━━━ DailyQuestUI.cs ━━━
// 일일/주간 퀘스트 UI — 퀘스트 목록 표시 + 진행도 트래커
// DailyQuestManager 이벤트 구독 (L키 토글)

using UnityEngine;
using UnityEngine.UI;
using Network;

public class DailyQuestUI : MonoBehaviour
{
    // ━━━ UI 참조 (Start에서 코드 생성) ━━━
    private GameObject _panel;
    private Text _titleText;
    private Text _questListText;
    private Text _statusText;
    private Button _refreshButton;

    private void Start()
    {
        BuildUI();

        if (DailyQuestManager.Instance != null)
        {
            DailyQuestManager.Instance.OnDailyQuestListChanged += HandleDailyQuestListChanged;
            DailyQuestManager.Instance.OnWeeklyQuestChanged += HandleWeeklyQuestChanged;
            DailyQuestManager.Instance.OnPanelOpened += ShowPanel;
            DailyQuestManager.Instance.OnPanelClosed += HidePanel;
        }

        if (_panel != null) _panel.SetActive(false);
    }

    private void OnDestroy()
    {
        if (DailyQuestManager.Instance != null)
        {
            DailyQuestManager.Instance.OnDailyQuestListChanged -= HandleDailyQuestListChanged;
            DailyQuestManager.Instance.OnWeeklyQuestChanged -= HandleWeeklyQuestChanged;
            DailyQuestManager.Instance.OnPanelOpened -= ShowPanel;
            DailyQuestManager.Instance.OnPanelClosed -= HidePanel;
        }
    }

    private void Update()
    {
        // L키로 퀘스트 패널 토글
        if (Input.GetKeyDown(KeyCode.L))
        {
            if (DailyQuestManager.Instance != null)
            {
                if (DailyQuestManager.Instance.IsPanelOpen)
                    DailyQuestManager.Instance.ClosePanel();
                else
                    DailyQuestManager.Instance.OpenPanel();
            }
        }

        // ESC로 닫기
        if (_panel != null && _panel.activeSelf && Input.GetKeyDown(KeyCode.Escape))
        {
            DailyQuestManager.Instance?.ClosePanel();
        }
    }

    // ━━━ UI 구성 (코드 생성) ━━━

    private void BuildUI()
    {
        // Panel
        _panel = new GameObject("DailyQuestPanel");
        _panel.transform.SetParent(transform, false);
        var panelRT = _panel.AddComponent<RectTransform>();
        panelRT.anchorMin = new Vector2(0.02f, 0.3f);
        panelRT.anchorMax = new Vector2(0.35f, 0.95f);
        panelRT.offsetMin = Vector2.zero;
        panelRT.offsetMax = Vector2.zero;
        var panelBg = _panel.AddComponent<Image>();
        panelBg.color = new Color(0.05f, 0.08f, 0.12f, 0.92f);

        // Title
        var titleGo = CreateText(_panel.transform, "Title", "Daily / Weekly Quests",
            new Vector2(0.5f, 1f), new Vector2(0.5f, 1f), new Vector2(0, -8), new Vector2(300, 30));
        _titleText = titleGo.GetComponent<Text>();
        _titleText.fontSize = 18;
        _titleText.fontStyle = FontStyle.Bold;
        _titleText.alignment = TextAnchor.MiddleCenter;
        _titleText.color = new Color(0.6f, 0.9f, 1f);
        var titleRT = titleGo.GetComponent<RectTransform>();
        titleRT.pivot = new Vector2(0.5f, 1f);

        // Subtitle (instructions)
        var subGo = CreateText(_panel.transform, "Subtitle",
            "[L] Toggle  |  [ESC] Close",
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
        refreshImg.color = new Color(0.15f, 0.3f, 0.4f);
        _refreshButton = refreshGo.AddComponent<Button>();
        _refreshButton.onClick.AddListener(OnRefreshClicked);
        var refreshTextGo = CreateText(refreshGo.transform, "Text", "Refresh",
            Vector2.zero, Vector2.one, Vector2.zero, Vector2.zero);
        SetFillRT(refreshTextGo);
        refreshTextGo.GetComponent<Text>().alignment = TextAnchor.MiddleCenter;
        refreshTextGo.GetComponent<Text>().fontSize = 11;

        // Quest List Display Area
        var listGo = CreateText(_panel.transform, "QuestList", "Press [L] to load quests.",
            new Vector2(0f, 0f), new Vector2(1f, 1f), Vector2.zero, Vector2.zero);
        var listRT = listGo.GetComponent<RectTransform>();
        listRT.anchorMin = new Vector2(0f, 0.06f);
        listRT.anchorMax = new Vector2(1f, 0.88f);
        listRT.offsetMin = new Vector2(12, 0);
        listRT.offsetMax = new Vector2(-12, 0);
        _questListText = listGo.GetComponent<Text>();
        _questListText.fontSize = 12;
        _questListText.alignment = TextAnchor.UpperLeft;

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

    private void HandleDailyQuestListChanged()
    {
        RefreshDisplay();
    }

    private void HandleWeeklyQuestChanged()
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
        if (_questListText == null || DailyQuestManager.Instance == null) return;

        var dailies = DailyQuestManager.Instance.DailyQuests;
        var sb = new System.Text.StringBuilder();

        // ── 일일 퀘스트 ──
        sb.AppendLine("Daily Quests:");
        sb.AppendLine("────────────────────────────────────");

        if (dailies.Count == 0)
        {
            sb.AppendLine("  No daily quests available (Lv.5+)");
        }
        else
        {
            for (int i = 0; i < dailies.Count; i++)
            {
                var q = dailies[i];
                string status = q.Completed != 0 ? "<color=#88ff88>DONE</color>" : $"{q.Progress}/{q.Count}";
                string typeTag = q.Type == "kill" ? "Kill" : q.Type == "collect" ? "Collect" : "Craft";
                sb.AppendLine($"  [{typeTag}] {q.NameKr}");
                sb.AppendLine($"    Progress: {status}  |  EXP:{q.RewardExp} Gold:{q.RewardGold}");
                sb.AppendLine($"    Rep: {q.RepFaction} +{q.RepAmount}");
                sb.AppendLine();
            }
        }

        // ── 주간 퀘스트 ──
        sb.AppendLine("Weekly Quest:");
        sb.AppendLine("────────────────────────────────────");

        if (DailyQuestManager.Instance.HasWeekly && DailyQuestManager.Instance.WeeklyQuest != null)
        {
            var w = DailyQuestManager.Instance.WeeklyQuest;
            string status = w.Completed != 0 ? "<color=#88ff88>DONE</color>" : $"{w.Progress}/{w.Count}";
            string typeTag = w.Type == "dungeon_clear" ? "Dungeon" : w.Type == "kill" ? "Boss" : "PvP";
            sb.AppendLine($"  [{typeTag}] {w.NameKr}");
            sb.AppendLine($"    Progress: {status}  |  EXP:{w.RewardExp} Gold:{w.RewardGold} Token:{w.RewardDungeonToken}");
            sb.AppendLine($"    Rep: {w.RepFaction} +{w.RepAmount}");
        }
        else
        {
            sb.AppendLine("  No weekly quest available (Lv.15+)");
        }

        _questListText.text = sb.ToString();
    }

    // ━━━ 버튼 콜백 ━━━

    private void OnRefreshClicked()
    {
        DailyQuestManager.Instance?.RefreshDailyQuests();
        DailyQuestManager.Instance?.RefreshWeeklyQuest();
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
