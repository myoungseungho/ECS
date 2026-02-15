// ━━━ EventUI.cs ━━━
// 이벤트 UI — 이벤트 목록 패널 + 보상 수령 버튼
// EventManager 이벤트 구독, UI를 코드로 직접 생성
// 단축키: Shift+E 토글

using System.Collections.Generic;
using UnityEngine;
using UnityEngine.UI;
using Network;

public class EventUI : MonoBehaviour
{
    // ━━━ UI 요소 ━━━
    private GameObject _panel;
    private Text _titleText;
    private Text _eventListText;
    private Text _statusText;
    private List<Button> _claimButtons = new List<Button>();
    private List<Text> _claimButtonTexts = new List<Text>();

    // ━━━ 상수 ━━━
    private static readonly Color COL_BG = new Color(0.06f, 0.08f, 0.15f, 0.93f);
    private static readonly Color COL_HEADER = new Color(0.9f, 0.7f, 0.2f);
    private static readonly Color COL_CLAIM_BTN = new Color(0.2f, 0.5f, 0.2f, 0.9f);
    private const int MAX_EVENTS = 5;

    private void Start()
    {
        BuildUI();

        if (EventManager.Instance != null)
        {
            EventManager.Instance.OnEventListChanged += HandleEventListChanged;
            EventManager.Instance.OnClaimResult += HandleClaimResult;
            EventManager.Instance.OnPanelOpened += ShowPanel;
            EventManager.Instance.OnPanelClosed += HidePanel;
        }

        if (_panel != null) _panel.SetActive(false);
    }

    private void OnDestroy()
    {
        if (EventManager.Instance != null)
        {
            EventManager.Instance.OnEventListChanged -= HandleEventListChanged;
            EventManager.Instance.OnClaimResult -= HandleClaimResult;
            EventManager.Instance.OnPanelOpened -= ShowPanel;
            EventManager.Instance.OnPanelClosed -= HidePanel;
        }
    }

    private void Update()
    {
        if (Input.GetKey(KeyCode.LeftShift) && Input.GetKeyDown(KeyCode.E))
        {
            if (EventManager.Instance != null)
            {
                if (EventManager.Instance.IsPanelOpen)
                    EventManager.Instance.ClosePanel();
                else
                    EventManager.Instance.OpenPanel();
            }
        }
    }

    // ━━━ UI 빌드 ━━━

    private void BuildUI()
    {
        _panel = CreateRect("EventPanel", transform, new Vector2(-15, -80), new Vector2(320, 300),
            new Vector2(1f, 1f), new Vector2(1f, 1f), new Vector2(1f, 1f));
        var bg = _panel.AddComponent<Image>();
        bg.color = COL_BG;
        bg.raycastTarget = true;

        // 제목
        var titleGo = CreateRect("Title", _panel.transform,
            new Vector2(0, -10), new Vector2(300, 28),
            new Vector2(0.5f, 1f), new Vector2(0.5f, 1f), new Vector2(0.5f, 1f));
        _titleText = titleGo.AddComponent<Text>();
        _titleText.text = "Events (Shift+E)";
        _titleText.fontSize = 18;
        _titleText.fontStyle = FontStyle.Bold;
        _titleText.color = COL_HEADER;
        _titleText.alignment = TextAnchor.MiddleCenter;
        _titleText.font = Resources.GetBuiltinResource<Font>("LegacyRuntime.ttf");

        // 이벤트 목록 텍스트
        var listGo = CreateRect("EventList", _panel.transform,
            new Vector2(10, -45), new Vector2(200, 200),
            new Vector2(0f, 1f), new Vector2(0f, 1f), new Vector2(0f, 1f));
        _eventListText = listGo.AddComponent<Text>();
        _eventListText.text = "Loading...";
        _eventListText.fontSize = 13;
        _eventListText.color = Color.white;
        _eventListText.alignment = TextAnchor.UpperLeft;
        _eventListText.font = Resources.GetBuiltinResource<Font>("LegacyRuntime.ttf");
        _eventListText.horizontalOverflow = HorizontalWrapMode.Wrap;
        _eventListText.verticalOverflow = VerticalWrapMode.Truncate;

        // Claim 버튼 (우측에 이벤트별로)
        for (int i = 0; i < MAX_EVENTS; i++)
        {
            float yPos = -50 - i * 38;
            var btnGo = CreateRect($"ClaimBtn{i}", _panel.transform,
                new Vector2(-15, yPos), new Vector2(80, 30),
                new Vector2(1f, 1f), new Vector2(1f, 1f), new Vector2(1f, 1f));
            var btnImg = btnGo.AddComponent<Image>();
            btnImg.color = COL_CLAIM_BTN;
            var btn = btnGo.AddComponent<Button>();
            int capturedIndex = i;
            btn.onClick.AddListener(() => OnClaimClicked(capturedIndex));

            var txtGo = CreateRect("Text", btnGo.transform, Vector2.zero, Vector2.zero,
                Vector2.zero, Vector2.one, new Vector2(0.5f, 0.5f));
            var txt = txtGo.AddComponent<Text>();
            txt.text = "Claim";
            txt.fontSize = 12;
            txt.color = Color.white;
            txt.alignment = TextAnchor.MiddleCenter;
            txt.font = Resources.GetBuiltinResource<Font>("LegacyRuntime.ttf");

            _claimButtons.Add(btn);
            _claimButtonTexts.Add(txt);
            btnGo.SetActive(false);
        }

        // 상태 텍스트 (하단)
        var statusGo = CreateRect("Status", _panel.transform,
            new Vector2(0, 10), new Vector2(300, 22),
            new Vector2(0.5f, 0f), new Vector2(0.5f, 0f), new Vector2(0.5f, 0f));
        _statusText = statusGo.AddComponent<Text>();
        _statusText.text = "";
        _statusText.fontSize = 12;
        _statusText.color = Color.white;
        _statusText.alignment = TextAnchor.MiddleCenter;
        _statusText.font = Resources.GetBuiltinResource<Font>("LegacyRuntime.ttf");

        // 닫기 버튼 (우상단)
        var closeGo = CreateRect("CloseButton", _panel.transform,
            new Vector2(-5, -5), new Vector2(25, 25),
            new Vector2(1f, 1f), new Vector2(1f, 1f), new Vector2(1f, 1f));
        var closeImg = closeGo.AddComponent<Image>();
        closeImg.color = new Color(0.6f, 0.15f, 0.15f, 0.9f);
        var closeBtn = closeGo.AddComponent<Button>();
        closeBtn.onClick.AddListener(() => EventManager.Instance?.ClosePanel());
        var closeTxtGo = CreateRect("X", closeGo.transform, Vector2.zero, Vector2.zero,
            Vector2.zero, Vector2.one, new Vector2(0.5f, 0.5f));
        var closeTxt = closeTxtGo.AddComponent<Text>();
        closeTxt.text = "X";
        closeTxt.fontSize = 14;
        closeTxt.fontStyle = FontStyle.Bold;
        closeTxt.color = Color.white;
        closeTxt.alignment = TextAnchor.MiddleCenter;
        closeTxt.font = Resources.GetBuiltinResource<Font>("LegacyRuntime.ttf");
    }

    // ━━━ 버튼 핸들러 ━━━

    private void OnClaimClicked(int index)
    {
        if (EventManager.Instance == null) return;
        var events = EventManager.Instance.Events;
        if (index < events.Count)
        {
            EventManager.Instance.ClaimReward(events[index].EventId);
        }
    }

    // ━━━ 이벤트 핸들러 ━━━

    private void HandleEventListChanged()
    {
        if (EventManager.Instance == null) return;
        var events = EventManager.Instance.Events;

        var sb = new System.Text.StringBuilder();
        for (int i = 0; i < events.Count && i < MAX_EVENTS; i++)
        {
            var e = events[i];
            string typeName = GetEventTypeName(e.Type);
            uint hours = e.RemainingSeconds / 3600;
            sb.AppendLine($"{typeName}: {e.Name}");
            sb.AppendLine($"  Remaining: {hours}h");
            sb.AppendLine();

            if (i < _claimButtons.Count)
                _claimButtons[i].gameObject.SetActive(true);
        }

        for (int i = events.Count; i < MAX_EVENTS && i < _claimButtons.Count; i++)
            _claimButtons[i].gameObject.SetActive(false);

        if (_eventListText != null)
            _eventListText.text = sb.ToString();
    }

    private void HandleClaimResult(EventClaimResultData data)
    {
        if (_statusText == null) return;

        if (data.Result == 0)
        {
            _statusText.text = $"Claimed! Reward x{data.RewardCount}";
            _statusText.color = new Color(1f, 0.843f, 0f);
        }
        else
        {
            string reason;
            switch (data.Result)
            {
                case 1: reason = "Already claimed"; break;
                case 2: reason = "Daily limit reached"; break;
                case 3: reason = "Invalid event"; break;
                default: reason = $"Error ({data.Result})"; break;
            }
            _statusText.text = $"Claim failed: {reason}";
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

    // ━━━ 유틸 ━━━

    private static string GetEventTypeName(GameEventType type)
    {
        switch (type)
        {
            case GameEventType.LOGIN_EVENT: return "Login";
            case GameEventType.DOUBLE_EXP:  return "2x EXP";
            case GameEventType.BOSS_RUSH:   return "Boss Rush";
            case GameEventType.SEASONAL:    return "Seasonal";
            default: return $"Event{(byte)type}";
        }
    }

    private static GameObject CreateRect(string name, Transform parent,
        Vector2 anchoredPos, Vector2 sizeDelta,
        Vector2 anchorMin, Vector2 anchorMax, Vector2 pivot)
    {
        var go = new GameObject(name);
        go.transform.SetParent(parent, false);
        var rt = go.AddComponent<RectTransform>();
        rt.anchorMin = anchorMin;
        rt.anchorMax = anchorMax;
        rt.pivot = pivot;
        rt.anchoredPosition = anchoredPos;
        rt.sizeDelta = sizeDelta;
        return go;
    }
}
