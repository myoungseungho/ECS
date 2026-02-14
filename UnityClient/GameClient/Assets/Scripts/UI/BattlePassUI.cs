// ━━━ BattlePassUI.cs ━━━
// 배틀패스 UI — 시즌 정보, Free/Premium 트랙, 보상 슬롯, 프리미엄 구매
// BattlePassManager 이벤트 구독

using UnityEngine;
using UnityEngine.UI;
using Network;

public class BattlePassUI : MonoBehaviour
{
    // ━━━ UI 참조 (Start에서 코드 생성) ━━━
    private GameObject _panel;
    private Text _seasonText;
    private Text _levelText;
    private Text _daysText;
    private Slider _expSlider;
    private Text _expText;
    private Text _freeTrackText;
    private Text _premiumTrackText;
    private Text _statusText;
    private Button _premiumButton;
    private Text _premiumBtnText;
    private Button[] _freeClaimButtons;
    private Button[] _premiumClaimButtons;

    private const int VISIBLE_LEVELS = 10;

    private void Start()
    {
        BuildUI();

        if (BattlePassManager.Instance != null)
        {
            BattlePassManager.Instance.OnInfoUpdated += HandleInfoUpdated;
            BattlePassManager.Instance.OnRewardClaimed += HandleRewardClaimed;
            BattlePassManager.Instance.OnPremiumPurchased += HandlePremiumPurchased;
            BattlePassManager.Instance.OnPanelOpened += ShowPanel;
            BattlePassManager.Instance.OnPanelClosed += HidePanel;
        }

        if (_panel != null) _panel.SetActive(false);
    }

    private void OnDestroy()
    {
        if (BattlePassManager.Instance != null)
        {
            BattlePassManager.Instance.OnInfoUpdated -= HandleInfoUpdated;
            BattlePassManager.Instance.OnRewardClaimed -= HandleRewardClaimed;
            BattlePassManager.Instance.OnPremiumPurchased -= HandlePremiumPurchased;
            BattlePassManager.Instance.OnPanelOpened -= ShowPanel;
            BattlePassManager.Instance.OnPanelClosed -= HidePanel;
        }
    }

    private void Update()
    {
        // F5키로 배틀패스 토글
        if (Input.GetKeyDown(KeyCode.F5))
        {
            if (BattlePassManager.Instance != null)
            {
                if (BattlePassManager.Instance.IsPanelOpen)
                    BattlePassManager.Instance.ClosePanel();
                else
                    BattlePassManager.Instance.OpenPanel();
            }
        }

        // ESC로 닫기
        if (_panel != null && _panel.activeSelf && Input.GetKeyDown(KeyCode.Escape))
        {
            BattlePassManager.Instance?.ClosePanel();
        }
    }

    // ━━━ UI 구성 (코드 생성) ━━━

    private void BuildUI()
    {
        // Panel
        _panel = new GameObject("BattlePassPanel");
        _panel.transform.SetParent(transform, false);
        var panelRT = _panel.AddComponent<RectTransform>();
        panelRT.anchorMin = new Vector2(0.1f, 0.1f);
        panelRT.anchorMax = new Vector2(0.9f, 0.9f);
        panelRT.offsetMin = Vector2.zero;
        panelRT.offsetMax = Vector2.zero;
        var panelBg = _panel.AddComponent<Image>();
        panelBg.color = new Color(0.06f, 0.08f, 0.12f, 0.95f);

        // ── Header Area (상단 20%) ──

        // Season Title (좌상단)
        var seasonGo = CreateText(_panel.transform, "SeasonText", "Season --",
            new Vector2(0f, 1f), new Vector2(0f, 1f), new Vector2(20, -15), new Vector2(200, 30));
        _seasonText = seasonGo.GetComponent<Text>();
        _seasonText.fontSize = 20;
        _seasonText.fontStyle = FontStyle.Bold;
        var seasonRT = seasonGo.GetComponent<RectTransform>();
        seasonRT.pivot = new Vector2(0f, 1f);

        // Level (타이틀 우측)
        var levelGo = CreateText(_panel.transform, "LevelText", "Lv. 0",
            new Vector2(0f, 1f), new Vector2(0f, 1f), new Vector2(230, -15), new Vector2(100, 30));
        _levelText = levelGo.GetComponent<Text>();
        _levelText.fontSize = 20;
        _levelText.fontStyle = FontStyle.Bold;
        _levelText.color = new Color(1f, 0.843f, 0f);
        var levelRT = levelGo.GetComponent<RectTransform>();
        levelRT.pivot = new Vector2(0f, 1f);

        // Days Remaining (우상단)
        var daysGo = CreateText(_panel.transform, "DaysText", "-- days left",
            new Vector2(1f, 1f), new Vector2(1f, 1f), new Vector2(-20, -15), new Vector2(180, 25));
        _daysText = daysGo.GetComponent<Text>();
        _daysText.fontSize = 14;
        _daysText.color = new Color(0.8f, 0.6f, 0.3f);
        _daysText.alignment = TextAnchor.MiddleRight;
        var daysRT = daysGo.GetComponent<RectTransform>();
        daysRT.pivot = new Vector2(1f, 1f);

        // EXP Bar (상단 아래)
        BuildExpBar();

        // ── Track Area (중앙) ──

        // "Free Track" Label
        var freeLabel = CreateText(_panel.transform, "FreeLabel", "FREE TRACK",
            new Vector2(0f, 1f), new Vector2(0f, 1f), new Vector2(20, -105), new Vector2(120, 20));
        var freeLabelText = freeLabel.GetComponent<Text>();
        freeLabelText.fontSize = 12;
        freeLabelText.fontStyle = FontStyle.Bold;
        freeLabelText.color = new Color(0.6f, 0.8f, 0.6f);
        var freeLabelRT = freeLabel.GetComponent<RectTransform>();
        freeLabelRT.pivot = new Vector2(0f, 1f);

        // Free Track Slots
        var freeTrackGo = CreateText(_panel.transform, "FreeTrack", "",
            new Vector2(0f, 0f), new Vector2(1f, 1f), Vector2.zero, Vector2.zero);
        var freeTrackRT = freeTrackGo.GetComponent<RectTransform>();
        freeTrackRT.anchorMin = new Vector2(0f, 0.45f);
        freeTrackRT.anchorMax = new Vector2(1f, 0.72f);
        freeTrackRT.offsetMin = new Vector2(20, 0);
        freeTrackRT.offsetMax = new Vector2(-20, 0);
        _freeTrackText = freeTrackGo.GetComponent<Text>();
        _freeTrackText.fontSize = 13;
        _freeTrackText.alignment = TextAnchor.UpperLeft;

        // Free Claim Buttons row
        _freeClaimButtons = new Button[VISIBLE_LEVELS];
        BuildClaimButtonRow(_panel.transform, _freeClaimButtons, 0.38f, 0.44f, 0);

        // "Premium Track" Label
        var premLabel = CreateText(_panel.transform, "PremiumLabel", "PREMIUM TRACK",
            new Vector2(0f, 1f), new Vector2(0f, 1f), new Vector2(20, -250), new Vector2(150, 20));
        var premLabelText = premLabel.GetComponent<Text>();
        premLabelText.fontSize = 12;
        premLabelText.fontStyle = FontStyle.Bold;
        premLabelText.color = new Color(0.9f, 0.7f, 0.2f);
        var premLabelRT = premLabel.GetComponent<RectTransform>();
        premLabelRT.pivot = new Vector2(0f, 1f);

        // Premium Track Slots
        var premTrackGo = CreateText(_panel.transform, "PremiumTrack", "",
            new Vector2(0f, 0f), new Vector2(1f, 1f), Vector2.zero, Vector2.zero);
        var premTrackRT = premTrackGo.GetComponent<RectTransform>();
        premTrackRT.anchorMin = new Vector2(0f, 0.15f);
        premTrackRT.anchorMax = new Vector2(1f, 0.37f);
        premTrackRT.offsetMin = new Vector2(20, 0);
        premTrackRT.offsetMax = new Vector2(-20, 0);
        _premiumTrackText = premTrackGo.GetComponent<Text>();
        _premiumTrackText.fontSize = 13;
        _premiumTrackText.alignment = TextAnchor.UpperLeft;

        // Premium Claim Buttons row
        _premiumClaimButtons = new Button[VISIBLE_LEVELS];
        BuildClaimButtonRow(_panel.transform, _premiumClaimButtons, 0.08f, 0.14f, 1);

        // ── Footer ──

        // Status Text
        var statusGo = CreateText(_panel.transform, "StatusText", "",
            new Vector2(0.5f, 0f), new Vector2(0.5f, 0f), new Vector2(0, 10), new Vector2(400, 25));
        _statusText = statusGo.GetComponent<Text>();
        _statusText.fontSize = 14;
        _statusText.alignment = TextAnchor.MiddleCenter;
        var statusRT = statusGo.GetComponent<RectTransform>();
        statusRT.pivot = new Vector2(0.5f, 0f);

        // Premium Upgrade Button (우하단)
        var premBtnGo = new GameObject("PremiumButton");
        premBtnGo.transform.SetParent(_panel.transform, false);
        var premBtnRT = premBtnGo.AddComponent<RectTransform>();
        premBtnRT.anchorMin = new Vector2(1f, 0f);
        premBtnRT.anchorMax = new Vector2(1f, 0f);
        premBtnRT.pivot = new Vector2(1f, 0f);
        premBtnRT.anchoredPosition = new Vector2(-20, 10);
        premBtnRT.sizeDelta = new Vector2(180, 40);
        var premBtnImg = premBtnGo.AddComponent<Image>();
        premBtnImg.color = new Color(0.7f, 0.5f, 0.1f);
        _premiumButton = premBtnGo.AddComponent<Button>();
        _premiumButton.onClick.AddListener(OnPremiumClicked);

        var premBtnTextGo = CreateText(premBtnGo.transform, "Text", "Upgrade to Premium",
            Vector2.zero, Vector2.one, Vector2.zero, Vector2.zero);
        var premBtnTextRT = premBtnTextGo.GetComponent<RectTransform>();
        premBtnTextRT.anchorMin = Vector2.zero;
        premBtnTextRT.anchorMax = Vector2.one;
        premBtnTextRT.offsetMin = Vector2.zero;
        premBtnTextRT.offsetMax = Vector2.zero;
        _premiumBtnText = premBtnTextGo.GetComponent<Text>();
        _premiumBtnText.alignment = TextAnchor.MiddleCenter;
        _premiumBtnText.fontSize = 14;
        _premiumBtnText.fontStyle = FontStyle.Bold;
    }

    private void BuildExpBar()
    {
        // EXP Bar container
        var barGo = new GameObject("ExpBar");
        barGo.transform.SetParent(_panel.transform, false);
        var barRT = barGo.AddComponent<RectTransform>();
        barRT.anchorMin = new Vector2(0f, 1f);
        barRT.anchorMax = new Vector2(1f, 1f);
        barRT.pivot = new Vector2(0.5f, 1f);
        barRT.anchoredPosition = new Vector2(0, -55);
        barRT.sizeDelta = new Vector2(-40, 22);
        barRT.offsetMin = new Vector2(20, 0);
        barRT.offsetMax = new Vector2(-20, 0);

        _expSlider = barGo.AddComponent<Slider>();
        _expSlider.minValue = 0f;
        _expSlider.maxValue = 1f;
        _expSlider.value = 0f;
        _expSlider.interactable = false;

        // Background
        var bgGo = new GameObject("Background");
        bgGo.transform.SetParent(barGo.transform, false);
        var bgRT = bgGo.AddComponent<RectTransform>();
        bgRT.anchorMin = Vector2.zero;
        bgRT.anchorMax = Vector2.one;
        bgRT.sizeDelta = Vector2.zero;
        var bgImg = bgGo.AddComponent<Image>();
        bgImg.color = new Color(0.15f, 0.15f, 0.2f, 0.9f);

        // Fill Area
        var fillAreaGo = new GameObject("Fill Area");
        fillAreaGo.transform.SetParent(barGo.transform, false);
        var fillAreaRT = fillAreaGo.AddComponent<RectTransform>();
        fillAreaRT.anchorMin = Vector2.zero;
        fillAreaRT.anchorMax = Vector2.one;
        fillAreaRT.sizeDelta = Vector2.zero;

        var fillGo = new GameObject("Fill");
        fillGo.transform.SetParent(fillAreaGo.transform, false);
        var fillRT = fillGo.AddComponent<RectTransform>();
        fillRT.anchorMin = Vector2.zero;
        fillRT.anchorMax = Vector2.one;
        fillRT.sizeDelta = Vector2.zero;
        var fillImg = fillGo.AddComponent<Image>();
        fillImg.color = new Color(0.3f, 0.7f, 1f);

        _expSlider.fillRect = fillRT;

        // EXP Text overlay
        var expTextGo = CreateText(barGo.transform, "ExpText", "0 / 0",
            Vector2.zero, Vector2.one, Vector2.zero, Vector2.zero);
        var expTextRT = expTextGo.GetComponent<RectTransform>();
        expTextRT.anchorMin = Vector2.zero;
        expTextRT.anchorMax = Vector2.one;
        expTextRT.offsetMin = Vector2.zero;
        expTextRT.offsetMax = Vector2.zero;
        _expText = expTextGo.GetComponent<Text>();
        _expText.fontSize = 11;
        _expText.alignment = TextAnchor.MiddleCenter;
    }

    private void BuildClaimButtonRow(Transform parent, Button[] buttons, float anchorYMin, float anchorYMax, byte track)
    {
        var rowGo = new GameObject(track == 0 ? "FreeClaimRow" : "PremiumClaimRow");
        rowGo.transform.SetParent(parent, false);
        var rowRT = rowGo.AddComponent<RectTransform>();
        rowRT.anchorMin = new Vector2(0f, anchorYMin);
        rowRT.anchorMax = new Vector2(1f, anchorYMax);
        rowRT.offsetMin = new Vector2(20, 0);
        rowRT.offsetMax = new Vector2(-20, 0);

        for (int i = 0; i < VISIBLE_LEVELS; i++)
        {
            float xRatio = (float)i / VISIBLE_LEVELS;
            float xEnd = (float)(i + 1) / VISIBLE_LEVELS;

            var btnGo = new GameObject($"Claim_{track}_{i + 1}");
            btnGo.transform.SetParent(rowGo.transform, false);
            var btnRT = btnGo.AddComponent<RectTransform>();
            btnRT.anchorMin = new Vector2(xRatio, 0f);
            btnRT.anchorMax = new Vector2(xEnd, 1f);
            btnRT.offsetMin = new Vector2(2, 1);
            btnRT.offsetMax = new Vector2(-2, -1);
            var btnImg = btnGo.AddComponent<Image>();
            btnImg.color = new Color(0.25f, 0.25f, 0.3f);
            var btn = btnGo.AddComponent<Button>();
            buttons[i] = btn;

            var btnTextGo = CreateText(btnGo.transform, "Text", $"Lv{i + 1}",
                Vector2.zero, Vector2.one, Vector2.zero, Vector2.zero);
            var btnTextRT = btnTextGo.GetComponent<RectTransform>();
            btnTextRT.anchorMin = Vector2.zero;
            btnTextRT.anchorMax = Vector2.one;
            btnTextRT.offsetMin = Vector2.zero;
            btnTextRT.offsetMax = Vector2.zero;
            var btnText = btnTextGo.GetComponent<Text>();
            btnText.alignment = TextAnchor.MiddleCenter;
            btnText.fontSize = 10;

            int lvl = i + 1;
            byte t = track;
            btn.onClick.AddListener(() => OnClaimClicked((byte)lvl, t));
        }
    }

    // ━━━ 이벤트 핸들러 ━━━

    private void HandleInfoUpdated(BattlePassInfoData data)
    {
        RefreshUI(data);
    }

    private void HandleRewardClaimed(BattlePassRewardResultData data)
    {
        if (_statusText == null) return;

        if (data.Result == BattlePassRewardResult.SUCCESS)
        {
            _statusText.text = $"Reward claimed! Lv{data.Level} ({(data.Track == BattlePassTrack.FREE ? "Free" : "Premium")}) - Type:{data.RewardType} x{data.RewardCount}";
            _statusText.color = Color.green;
        }
        else
        {
            _statusText.text = $"Claim failed: {data.Result}";
            _statusText.color = Color.red;
        }
    }

    private void HandlePremiumPurchased(BattlePassBuyResultData data)
    {
        if (_statusText == null) return;

        if (data.Result == 0)
        {
            _statusText.text = $"Premium unlocked! Remaining crystals: {data.RemainingCrystals}";
            _statusText.color = new Color(1f, 0.843f, 0f);
        }
        else
        {
            _statusText.text = $"Premium purchase failed (result={data.Result})";
            _statusText.color = Color.red;
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

    // ━━━ UI 갱신 ━━━

    private void RefreshUI(BattlePassInfoData data)
    {
        if (data == null) return;

        if (_seasonText != null)
            _seasonText.text = $"Season {data.SeasonId}";

        if (_levelText != null)
            _levelText.text = $"Lv. {data.Level}";

        if (_daysText != null)
            _daysText.text = $"{data.DaysLeft} days left";

        if (_expSlider != null)
        {
            float ratio = data.MaxExp > 0 ? (float)data.Exp / data.MaxExp : 0f;
            _expSlider.value = ratio;
        }

        if (_expText != null)
            _expText.text = $"{data.Exp} / {data.MaxExp}";

        // Free Track display
        if (_freeTrackText != null)
        {
            var sb = new System.Text.StringBuilder();
            for (int i = 0; i < VISIBLE_LEVELS; i++)
            {
                int lv = i + 1;
                string marker = (lv == data.Level) ? ">>>" : "   ";
                string status = (lv <= data.Level) ? "[OK]" : "[  ]";
                sb.Append($"{marker} Lv{lv} {status}  ");
                if (i == 4) sb.AppendLine();
            }
            _freeTrackText.text = sb.ToString();
        }

        // Premium Track display
        if (_premiumTrackText != null)
        {
            var sb = new System.Text.StringBuilder();
            string lockIcon = data.IsPremium ? "" : " (LOCKED)";
            for (int i = 0; i < VISIBLE_LEVELS; i++)
            {
                int lv = i + 1;
                string marker = (lv == data.Level) ? ">>>" : "   ";
                string status = (lv <= data.Level && data.IsPremium) ? "[OK]" : "[  ]";
                sb.Append($"{marker} Lv{lv} {status}  ");
                if (i == 4) sb.AppendLine();
            }
            if (!data.IsPremium)
                sb.AppendLine("\n(Upgrade to Premium to unlock these rewards)");
            _premiumTrackText.text = sb.ToString();
        }

        // Highlight current level buttons
        UpdateClaimButtonColors(data);

        // Premium button
        if (_premiumButton != null)
        {
            _premiumButton.interactable = !data.IsPremium;
            if (_premiumBtnText != null)
                _premiumBtnText.text = data.IsPremium ? "Premium Active" : "Upgrade to Premium";
        }
    }

    private void UpdateClaimButtonColors(BattlePassInfoData data)
    {
        for (int i = 0; i < VISIBLE_LEVELS; i++)
        {
            int lv = i + 1;
            bool reached = lv <= data.Level;

            // Free track
            if (_freeClaimButtons[i] != null)
            {
                var img = _freeClaimButtons[i].GetComponent<Image>();
                if (img != null)
                {
                    if (lv == data.Level)
                        img.color = new Color(0.3f, 0.7f, 0.4f); // current level highlight
                    else if (reached)
                        img.color = new Color(0.2f, 0.4f, 0.25f); // claimable
                    else
                        img.color = new Color(0.25f, 0.25f, 0.3f); // locked
                }
            }

            // Premium track
            if (_premiumClaimButtons[i] != null)
            {
                var img = _premiumClaimButtons[i].GetComponent<Image>();
                if (img != null)
                {
                    if (!data.IsPremium)
                        img.color = new Color(0.2f, 0.15f, 0.1f); // premium locked
                    else if (lv == data.Level)
                        img.color = new Color(0.7f, 0.55f, 0.15f); // current level highlight
                    else if (reached)
                        img.color = new Color(0.4f, 0.35f, 0.15f); // claimable
                    else
                        img.color = new Color(0.25f, 0.25f, 0.3f); // locked
                }
            }
        }
    }

    // ━━━ 버튼 콜백 ━━━

    private void OnClaimClicked(byte level, byte track)
    {
        BattlePassManager.Instance?.ClaimReward(level, track);
    }

    private void OnPremiumClicked()
    {
        BattlePassManager.Instance?.BuyPremium();
    }

    // ━━━ 유틸 ━━━

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
