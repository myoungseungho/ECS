// ━━━ ContentUnlockUI.cs ━━━
// 컨텐츠 해금 알림 팝업 — 전체 화면 오버레이 + 시스템 이름 + 설명 + 확인 버튼
// NetworkManager.OnContentUnlockNotify에 직접 구독 (매니저 없이 독립 팝업)
// OK 버튼 클릭 시 CONTENT_UNLOCK_ACK 전송
// UI를 코드로 직접 생성

using UnityEngine;
using UnityEngine.UI;
using Network;

public class ContentUnlockUI : MonoBehaviour
{
    // ━━━ 코드 생성 UI 참조 ━━━
    private GameObject _overlay;
    private GameObject _panel;
    private Text _titleText;
    private Text _systemNameText;
    private Text _descriptionText;
    private Button _okButton;

    // 현재 표시 중인 해금 타입 (ACK 전송용)
    private byte _currentUnlockType;

    // ━━━ 색상 상수 ━━━
    private static readonly Color COL_OVERLAY = new Color(0f, 0f, 0f, 0.7f);
    private static readonly Color COL_PANEL_BG = new Color(0.1f, 0.08f, 0.15f, 0.95f);
    private static readonly Color COL_OK_BTN = new Color(0.2f, 0.5f, 0.8f);
    private static readonly Color COL_GOLD = new Color(1f, 0.843f, 0f);

    private void Start()
    {
        BuildUI();

        var net = NetworkManager.Instance;
        if (net != null)
        {
            net.OnContentUnlockNotify += HandleContentUnlockNotify;
        }

        _overlay.SetActive(false);
    }

    private void OnDestroy()
    {
        var net = NetworkManager.Instance;
        if (net != null)
        {
            net.OnContentUnlockNotify -= HandleContentUnlockNotify;
        }
    }

    // ━━━ UI 빌드 (코드 생성) ━━━

    private void BuildUI()
    {
        // 전체 화면 오버레이
        _overlay = CreateRect("ContentUnlockOverlay", transform, Vector2.zero, Vector2.zero,
            Vector2.zero, Vector2.one, new Vector2(0.5f, 0.5f));
        var overlayImg = _overlay.AddComponent<Image>();
        overlayImg.color = COL_OVERLAY;
        overlayImg.raycastTarget = true;

        // 중앙 패널 (500x300)
        _panel = CreateRect("ContentUnlockPanel", _overlay.transform, Vector2.zero, new Vector2(500, 300),
            new Vector2(0.5f, 0.5f), new Vector2(0.5f, 0.5f), new Vector2(0.5f, 0.5f));
        var panelImg = _panel.AddComponent<Image>();
        panelImg.color = COL_PANEL_BG;

        // 제목 "CONTENT UNLOCKED!"
        var titleGo = CreateRect("Title", _panel.transform, new Vector2(0, -25), new Vector2(400, 35),
            new Vector2(0.5f, 1f), new Vector2(0.5f, 1f), new Vector2(0.5f, 1f));
        _titleText = titleGo.AddComponent<Text>();
        _titleText.text = "CONTENT UNLOCKED!";
        _titleText.fontSize = 26;
        _titleText.fontStyle = FontStyle.Bold;
        _titleText.color = COL_GOLD;
        _titleText.alignment = TextAnchor.MiddleCenter;
        _titleText.font = Resources.GetBuiltinResource<Font>("LegacyRuntime.ttf");

        // 구분선
        var lineGo = CreateRect("Line", _panel.transform, new Vector2(0, -55), new Vector2(400, 2),
            new Vector2(0.5f, 1f), new Vector2(0.5f, 1f), new Vector2(0.5f, 1f));
        var lineImg = lineGo.AddComponent<Image>();
        lineImg.color = new Color(0.5f, 0.5f, 0.5f, 0.5f);

        // 시스템 이름 (대형 텍스트)
        var sysNameGo = CreateRect("SystemName", _panel.transform, new Vector2(0, -90), new Vector2(450, 50),
            new Vector2(0.5f, 1f), new Vector2(0.5f, 1f), new Vector2(0.5f, 1f));
        _systemNameText = sysNameGo.AddComponent<Text>();
        _systemNameText.text = "System Name";
        _systemNameText.fontSize = 32;
        _systemNameText.fontStyle = FontStyle.Bold;
        _systemNameText.color = Color.white;
        _systemNameText.alignment = TextAnchor.MiddleCenter;
        _systemNameText.font = Resources.GetBuiltinResource<Font>("LegacyRuntime.ttf");

        // 설명 텍스트
        var descGo = CreateRect("Description", _panel.transform, new Vector2(0, -160), new Vector2(420, 60),
            new Vector2(0.5f, 1f), new Vector2(0.5f, 1f), new Vector2(0.5f, 1f));
        _descriptionText = descGo.AddComponent<Text>();
        _descriptionText.text = "Description here.";
        _descriptionText.fontSize = 16;
        _descriptionText.color = new Color(0.85f, 0.85f, 0.85f);
        _descriptionText.alignment = TextAnchor.UpperCenter;
        _descriptionText.font = Resources.GetBuiltinResource<Font>("LegacyRuntime.ttf");
        _descriptionText.horizontalOverflow = HorizontalWrapMode.Wrap;
        _descriptionText.verticalOverflow = VerticalWrapMode.Truncate;

        // OK 버튼 (하단 중앙)
        var okBtnGo = CreateRect("OKButton", _panel.transform, new Vector2(0, 25), new Vector2(140, 45),
            new Vector2(0.5f, 0f), new Vector2(0.5f, 0f), new Vector2(0.5f, 0.5f));
        var okBtnImg = okBtnGo.AddComponent<Image>();
        okBtnImg.color = COL_OK_BTN;
        _okButton = okBtnGo.AddComponent<Button>();
        _okButton.onClick.AddListener(OnOKClick);

        var okTxtGo = CreateRect("Text", okBtnGo.transform, Vector2.zero, Vector2.zero,
            Vector2.zero, Vector2.one, new Vector2(0.5f, 0.5f));
        var okTxt = okTxtGo.AddComponent<Text>();
        okTxt.text = "OK";
        okTxt.fontSize = 20;
        okTxt.fontStyle = FontStyle.Bold;
        okTxt.color = Color.white;
        okTxt.alignment = TextAnchor.MiddleCenter;
        okTxt.font = Resources.GetBuiltinResource<Font>("LegacyRuntime.ttf");
    }

    // ━━━ 이벤트 핸들러 ━━━

    private void HandleContentUnlockNotify(ContentUnlockNotifyData data)
    {
        _currentUnlockType = data.UnlockType;

        if (_systemNameText != null)
            _systemNameText.text = data.SystemName ?? "Unknown System";

        if (_descriptionText != null)
            _descriptionText.text = data.Description ?? "";

        Debug.Log($"[ContentUnlockUI] Showing: type={data.UnlockType}, system={data.SystemName}");

        if (_overlay != null)
            _overlay.SetActive(true);
    }

    // ━━━ 버튼 핸들러 ━━━

    private void OnOKClick()
    {
        // ACK 전송
        var net = NetworkManager.Instance;
        if (net != null)
        {
            net.AckContentUnlock(_currentUnlockType);
            Debug.Log($"[ContentUnlockUI] ACK sent: type={_currentUnlockType}");
        }

        // 팝업 닫기
        if (_overlay != null)
            _overlay.SetActive(false);
    }

    // ━━━ UI 생성 헬퍼 ━━━

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
