// ━━━ TripodUI.cs ━━━
// 비급 & 트라이포드 UI — 스킬별 3단계 트라이포드 표시, 장착/변경
// TripodManager 이벤트 구독 (T키 토글)

using UnityEngine;
using UnityEngine.UI;
using Network;

public class TripodUI : MonoBehaviour
{
    // ━━━ UI 참조 (Start에서 코드 생성) ━━━
    private GameObject _panel;
    private Text _titleText;
    private Text _skillListText;
    private Text _statusText;
    private Button _refreshButton;

    private int _selectedSkillIndex = -1;
    private int _selectedTierIndex = -1;
    private int _selectedOptionIndex = -1;

    private void Start()
    {
        BuildUI();

        if (TripodManager.Instance != null)
        {
            TripodManager.Instance.OnTripodListChanged += HandleListChanged;
            TripodManager.Instance.OnEquipResult += HandleEquipResult;
            TripodManager.Instance.OnDiscoverResult += HandleDiscoverResult;
            TripodManager.Instance.OnPanelOpened += ShowPanel;
            TripodManager.Instance.OnPanelClosed += HidePanel;
        }

        if (_panel != null) _panel.SetActive(false);
    }

    private void OnDestroy()
    {
        if (TripodManager.Instance != null)
        {
            TripodManager.Instance.OnTripodListChanged -= HandleListChanged;
            TripodManager.Instance.OnEquipResult -= HandleEquipResult;
            TripodManager.Instance.OnDiscoverResult -= HandleDiscoverResult;
            TripodManager.Instance.OnPanelOpened -= ShowPanel;
            TripodManager.Instance.OnPanelClosed -= HidePanel;
        }
    }

    private void Update()
    {
        // T키로 트라이포드 토글
        if (Input.GetKeyDown(KeyCode.T))
        {
            if (TripodManager.Instance != null)
            {
                if (TripodManager.Instance.IsPanelOpen)
                    TripodManager.Instance.ClosePanel();
                else
                    TripodManager.Instance.OpenPanel();
            }
        }

        // ESC로 닫기
        if (_panel != null && _panel.activeSelf && Input.GetKeyDown(KeyCode.Escape))
        {
            TripodManager.Instance?.ClosePanel();
        }

        // 숫자키로 스킬 선택 (1~9)
        if (_panel != null && _panel.activeSelf)
        {
            for (int i = 0; i < 9; i++)
            {
                if (Input.GetKeyDown(KeyCode.Alpha1 + i))
                {
                    if (TripodManager.Instance != null && i < TripodManager.Instance.Skills.Count)
                    {
                        _selectedSkillIndex = i;
                        _selectedTierIndex = -1;
                        _selectedOptionIndex = -1;
                        RefreshDisplay();
                    }
                }
            }

            // F1/F2/F3으로 티어 선택
            if (Input.GetKeyDown(KeyCode.F1)) SelectTier(0);
            if (Input.GetKeyDown(KeyCode.F2)) SelectTier(1);
            if (Input.GetKeyDown(KeyCode.F3)) SelectTier(2);

            // Numpad 0~7로 옵션 선택 + 장착
            for (int i = 0; i < 8; i++)
            {
                if (Input.GetKeyDown(KeyCode.Keypad0 + i))
                {
                    TryEquipOption((byte)i);
                }
            }
        }
    }

    // ━━━ UI 구성 (코드 생성) ━━━

    private void BuildUI()
    {
        // Panel
        _panel = new GameObject("TripodPanel");
        _panel.transform.SetParent(transform, false);
        var panelRT = _panel.AddComponent<RectTransform>();
        panelRT.anchorMin = new Vector2(0.1f, 0.05f);
        panelRT.anchorMax = new Vector2(0.9f, 0.95f);
        panelRT.offsetMin = Vector2.zero;
        panelRT.offsetMax = Vector2.zero;
        var panelBg = _panel.AddComponent<Image>();
        panelBg.color = new Color(0.05f, 0.08f, 0.12f, 0.95f);

        // Title
        var titleGo = CreateText(_panel.transform, "Title", "Tripod System",
            new Vector2(0.5f, 1f), new Vector2(0.5f, 1f), new Vector2(0, -10), new Vector2(300, 35));
        _titleText = titleGo.GetComponent<Text>();
        _titleText.fontSize = 22;
        _titleText.fontStyle = FontStyle.Bold;
        _titleText.alignment = TextAnchor.MiddleCenter;
        var titleRT = titleGo.GetComponent<RectTransform>();
        titleRT.pivot = new Vector2(0.5f, 1f);

        // Subtitle (instructions)
        var subGo = CreateText(_panel.transform, "Subtitle",
            "[1-9] Select Skill  |  [F1-F3] Select Tier  |  [Num0-7] Equip Option",
            new Vector2(0.5f, 1f), new Vector2(0.5f, 1f), new Vector2(0, -42), new Vector2(600, 22));
        var subText = subGo.GetComponent<Text>();
        subText.fontSize = 12;
        subText.alignment = TextAnchor.MiddleCenter;
        subText.color = new Color(0.7f, 0.7f, 0.8f);
        var subRT = subGo.GetComponent<RectTransform>();
        subRT.pivot = new Vector2(0.5f, 1f);

        // Refresh Button
        var refreshGo = new GameObject("RefreshButton");
        refreshGo.transform.SetParent(_panel.transform, false);
        var refreshRT = refreshGo.AddComponent<RectTransform>();
        refreshRT.anchorMin = new Vector2(1f, 1f);
        refreshRT.anchorMax = new Vector2(1f, 1f);
        refreshRT.pivot = new Vector2(1f, 1f);
        refreshRT.anchoredPosition = new Vector2(-15, -10);
        refreshRT.sizeDelta = new Vector2(80, 28);
        var refreshImg = refreshGo.AddComponent<Image>();
        refreshImg.color = new Color(0.2f, 0.35f, 0.5f);
        _refreshButton = refreshGo.AddComponent<Button>();
        _refreshButton.onClick.AddListener(OnRefreshClicked);
        var refreshTextGo = CreateText(refreshGo.transform, "Text", "Refresh",
            Vector2.zero, Vector2.one, Vector2.zero, Vector2.zero);
        SetFillRT(refreshTextGo);
        refreshTextGo.GetComponent<Text>().alignment = TextAnchor.MiddleCenter;
        refreshTextGo.GetComponent<Text>().fontSize = 12;

        // Skill + Tripod Display Area
        var listGo = CreateText(_panel.transform, "SkillList", "Open the Tripod panel to view your skills.",
            new Vector2(0f, 0f), new Vector2(1f, 1f), Vector2.zero, Vector2.zero);
        var listRT = listGo.GetComponent<RectTransform>();
        listRT.anchorMin = new Vector2(0f, 0.06f);
        listRT.anchorMax = new Vector2(1f, 0.88f);
        listRT.offsetMin = new Vector2(15, 0);
        listRT.offsetMax = new Vector2(-15, 0);
        _skillListText = listGo.GetComponent<Text>();
        _skillListText.fontSize = 13;
        _skillListText.alignment = TextAnchor.UpperLeft;

        // Status Text
        var statusGo = CreateText(_panel.transform, "StatusText", "",
            new Vector2(0f, 0f), new Vector2(1f, 0.06f), Vector2.zero, Vector2.zero);
        _statusText = statusGo.GetComponent<Text>();
        _statusText.fontSize = 14;
        _statusText.alignment = TextAnchor.MiddleLeft;
        var statusRT = statusGo.GetComponent<RectTransform>();
        statusRT.anchorMin = new Vector2(0f, 0f);
        statusRT.anchorMax = new Vector2(1f, 0.06f);
        statusRT.offsetMin = new Vector2(15, 0);
        statusRT.offsetMax = new Vector2(-15, 0);
    }

    // ━━━ 이벤트 핸들러 ━━━

    private void HandleListChanged()
    {
        RefreshDisplay();
    }

    private void HandleEquipResult(TripodEquipResult result)
    {
        if (_statusText == null) return;

        if (result == TripodEquipResult.SUCCESS)
        {
            _statusText.text = "Tripod equipped successfully!";
            _statusText.color = Color.green;
        }
        else
        {
            _statusText.text = $"Equip failed: {result}";
            _statusText.color = Color.red;
        }
    }

    private void HandleDiscoverResult(ScrollDiscoverResultData data)
    {
        if (_statusText == null) return;

        if (data.Result == ScrollDiscoverResult.SUCCESS)
        {
            _statusText.text = $"Scroll discovered! Skill:{data.SkillId} Tier:{data.Tier + 1} Option:{data.OptionIdx}";
            _statusText.color = Color.cyan;
        }
        else
        {
            _statusText.text = $"Discover failed: {data.Result}";
            _statusText.color = Color.red;
        }
    }

    private void ShowPanel()
    {
        if (_panel != null) _panel.SetActive(true);
        _selectedSkillIndex = -1;
        _selectedTierIndex = -1;
        _selectedOptionIndex = -1;
        RefreshDisplay();
    }

    private void HidePanel()
    {
        if (_panel != null) _panel.SetActive(false);
    }

    // ━━━ 선택 ━━━

    private void SelectTier(int tierIdx)
    {
        if (TripodManager.Instance == null) return;
        if (_selectedSkillIndex < 0 || _selectedSkillIndex >= TripodManager.Instance.Skills.Count) return;

        var skill = TripodManager.Instance.Skills[_selectedSkillIndex];
        if (tierIdx < skill.Tiers.Length)
        {
            _selectedTierIndex = tierIdx;
            _selectedOptionIndex = -1;
            RefreshDisplay();
        }
    }

    private void TryEquipOption(byte optionIdx)
    {
        if (TripodManager.Instance == null) return;
        if (_selectedSkillIndex < 0 || _selectedSkillIndex >= TripodManager.Instance.Skills.Count) return;
        if (_selectedTierIndex < 0) return;

        var skill = TripodManager.Instance.Skills[_selectedSkillIndex];
        if (_selectedTierIndex >= skill.Tiers.Length) return;

        var tier = skill.Tiers[_selectedTierIndex];
        _selectedOptionIndex = optionIdx;
        TripodManager.Instance.EquipTripod(skill.SkillId, tier.Tier, optionIdx);
    }

    // ━━━ UI 갱신 ━━━

    private void RefreshDisplay()
    {
        if (_skillListText == null || TripodManager.Instance == null) return;

        var skills = TripodManager.Instance.Skills;
        if (skills.Count == 0)
        {
            _skillListText.text = "No skills with tripods found.\nUse secret scrolls to unlock tripod options.";
            return;
        }

        var sb = new System.Text.StringBuilder();
        string[] tierNames = { "T1 (Lv10)", "T2 (Lv20)", "T3 (Lv30)" };

        sb.AppendLine($"Skills ({skills.Count}):");
        sb.AppendLine("────────────────────────────────────────────────");

        for (int i = 0; i < skills.Count; i++)
        {
            var skill = skills[i];
            string marker = (i == _selectedSkillIndex) ? ">>>" : "   ";
            sb.AppendLine($"{marker}[{i + 1}] Skill #{skill.SkillId}  —  {skill.Tiers.Length} tier(s)");

            if (i == _selectedSkillIndex)
            {
                for (int t = 0; t < skill.Tiers.Length; t++)
                {
                    var tier = skill.Tiers[t];
                    string tierName = tier.Tier < tierNames.Length ? tierNames[tier.Tier] : $"T{tier.Tier + 1}";
                    string tierMarker = (t == _selectedTierIndex) ? " >>" : "   ";
                    string equippedStr = tier.EquippedIdx < 0xFF ? $"Equipped: Opt#{tier.EquippedIdx}" : "Not equipped";

                    sb.AppendLine($"     {tierMarker}[F{t + 1}] {tierName}  |  Unlocked: {tier.UnlockedOptions.Length} opts  |  {equippedStr}");

                    if (t == _selectedTierIndex)
                    {
                        sb.Append("          Options: ");
                        if (tier.UnlockedOptions.Length == 0)
                        {
                            sb.AppendLine("(none unlocked)");
                        }
                        else
                        {
                            for (int o = 0; o < tier.UnlockedOptions.Length; o++)
                            {
                                byte optIdx = tier.UnlockedOptions[o];
                                string equipped = (optIdx == tier.EquippedIdx) ? "*" : " ";
                                sb.Append($"[Num{optIdx}]{equipped}Opt#{optIdx}  ");
                            }
                            sb.AppendLine();
                        }
                    }
                }
                sb.AppendLine();
            }
        }

        _skillListText.text = sb.ToString();
    }

    // ━━━ 버튼 콜백 ━━━

    private void OnRefreshClicked()
    {
        TripodManager.Instance?.RefreshList();
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
