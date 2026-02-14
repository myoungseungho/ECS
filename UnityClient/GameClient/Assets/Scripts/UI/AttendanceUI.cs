// ━━━ AttendanceUI.cs ━━━
// 출석 UI — 14일 출석 그리드(2x7) + 보상 수령 버튼 + 닫기 버튼
// AttendanceManager 이벤트 구독, 로그인 시 자동 표시
// UI를 코드로 직접 생성 (Canvas popup)

using System;
using UnityEngine;
using UnityEngine.UI;
using Network;

public class AttendanceUI : MonoBehaviour
{
    // ━━━ 코드 생성 UI 참조 ━━━
    private GameObject _overlay;
    private GameObject _panel;
    private Text _titleText;
    private Text _statusText;
    private Button _claimButton;
    private Text _claimButtonText;
    private Button _closeButton;

    // 14일 그리드 셀
    private GameObject[] _dayCells = new GameObject[14];
    private Text[] _dayNumberTexts = new Text[14];
    private Image[] _dayBackgrounds = new Image[14];
    private GameObject[] _claimedChecks = new GameObject[14];
    private GameObject[] _todayBorders = new GameObject[14];

    // ━━━ 색상 상수 ━━━
    private static readonly Color COL_PANEL_BG = new Color(0.08f, 0.08f, 0.12f, 0.95f);
    private static readonly Color COL_OVERLAY = new Color(0f, 0f, 0f, 0.5f);
    private static readonly Color COL_DAY_DEFAULT = new Color(0.15f, 0.15f, 0.2f, 0.9f);
    private static readonly Color COL_DAY_CLAIMED = new Color(0.2f, 0.45f, 0.2f, 0.9f);
    private static readonly Color COL_DAY_TODAY = new Color(0.25f, 0.25f, 0.4f, 0.9f);
    private static readonly Color COL_TODAY_BORDER = new Color(1f, 0.843f, 0f, 0.8f);
    private static readonly Color COL_CHECK = new Color(0.3f, 0.9f, 0.3f);
    private static readonly Color COL_CLAIM_BTN = new Color(0.2f, 0.5f, 0.8f);
    private static readonly Color COL_CLOSE_BTN = new Color(0.5f, 0.2f, 0.2f);

    private void Start()
    {
        BuildUI();

        if (AttendanceManager.Instance != null)
        {
            AttendanceManager.Instance.OnInfoUpdated += HandleInfoUpdated;
            AttendanceManager.Instance.OnRewardClaimed += HandleRewardClaimed;
            AttendanceManager.Instance.OnPanelOpened += ShowPanel;
            AttendanceManager.Instance.OnPanelClosed += HidePanel;
        }

        _overlay.SetActive(false);
    }

    private void OnDestroy()
    {
        if (AttendanceManager.Instance != null)
        {
            AttendanceManager.Instance.OnInfoUpdated -= HandleInfoUpdated;
            AttendanceManager.Instance.OnRewardClaimed -= HandleRewardClaimed;
            AttendanceManager.Instance.OnPanelOpened -= ShowPanel;
            AttendanceManager.Instance.OnPanelClosed -= HidePanel;
        }
    }

    private void Update()
    {
        // ESC로 닫기
        if (_overlay != null && _overlay.activeSelf && Input.GetKeyDown(KeyCode.Escape))
        {
            AttendanceManager.Instance?.ClosePanel();
        }
    }

    // ━━━ UI 빌드 (코드 생성) ━━━

    private void BuildUI()
    {
        // 반투명 오버레이 (전체 화면)
        _overlay = CreateRect("AttendanceOverlay", transform, Vector2.zero, Vector2.zero,
            Vector2.zero, Vector2.one, new Vector2(0.5f, 0.5f));
        var overlayImg = _overlay.AddComponent<Image>();
        overlayImg.color = COL_OVERLAY;
        overlayImg.raycastTarget = true;

        // 중앙 패널 (580x380)
        _panel = CreateRect("AttendancePanel", _overlay.transform, Vector2.zero, new Vector2(580, 380),
            new Vector2(0.5f, 0.5f), new Vector2(0.5f, 0.5f), new Vector2(0.5f, 0.5f));
        var panelImg = _panel.AddComponent<Image>();
        panelImg.color = COL_PANEL_BG;

        // 제목
        var titleGo = CreateRect("Title", _panel.transform, new Vector2(0, -15), new Vector2(300, 30),
            new Vector2(0.5f, 1f), new Vector2(0.5f, 1f), new Vector2(0.5f, 1f));
        _titleText = titleGo.AddComponent<Text>();
        _titleText.text = "Attendance";
        _titleText.fontSize = 22;
        _titleText.fontStyle = FontStyle.Bold;
        _titleText.color = Color.white;
        _titleText.alignment = TextAnchor.MiddleCenter;
        _titleText.font = Resources.GetBuiltinResource<Font>("LegacyRuntime.ttf");

        // 상태 텍스트
        var statusGo = CreateRect("Status", _panel.transform, new Vector2(0, -45), new Vector2(400, 20),
            new Vector2(0.5f, 1f), new Vector2(0.5f, 1f), new Vector2(0.5f, 1f));
        _statusText = statusGo.AddComponent<Text>();
        _statusText.text = "Loading...";
        _statusText.fontSize = 14;
        _statusText.color = new Color(0.8f, 0.8f, 0.8f);
        _statusText.alignment = TextAnchor.MiddleCenter;
        _statusText.font = Resources.GetBuiltinResource<Font>("LegacyRuntime.ttf");

        // 14일 그리드 (2행 x 7열), 셀 크기 70x70, 간격 5
        float cellSize = 70f;
        float spacing = 5f;
        float gridWidth = 7 * cellSize + 6 * spacing;   // 490
        float gridHeight = 2 * cellSize + spacing;       // 145
        float gridStartX = -gridWidth / 2f + cellSize / 2f;
        float gridStartY = 30f; // 패널 중앙에서 약간 위

        for (int row = 0; row < 2; row++)
        {
            for (int col = 0; col < 7; col++)
            {
                int idx = row * 7 + col;
                float x = gridStartX + col * (cellSize + spacing);
                float y = gridStartY - row * (cellSize + spacing);

                // 셀 배경
                var cellGo = CreateRect($"Day{idx + 1}", _panel.transform,
                    new Vector2(x, y), new Vector2(cellSize, cellSize),
                    new Vector2(0.5f, 0.5f), new Vector2(0.5f, 0.5f), new Vector2(0.5f, 0.5f));
                var cellBg = cellGo.AddComponent<Image>();
                cellBg.color = COL_DAY_DEFAULT;
                _dayCells[idx] = cellGo;
                _dayBackgrounds[idx] = cellBg;

                // 일차 번호 (상단)
                var numGo = CreateRect("Num", cellGo.transform, new Vector2(0, -5), new Vector2(cellSize, 20),
                    new Vector2(0.5f, 1f), new Vector2(0.5f, 1f), new Vector2(0.5f, 1f));
                var numText = numGo.AddComponent<Text>();
                numText.text = $"Day {idx + 1}";
                numText.fontSize = 12;
                numText.fontStyle = FontStyle.Bold;
                numText.color = Color.white;
                numText.alignment = TextAnchor.MiddleCenter;
                numText.font = Resources.GetBuiltinResource<Font>("LegacyRuntime.ttf");
                _dayNumberTexts[idx] = numText;

                // 보상 아이콘 placeholder (중앙)
                var iconGo = CreateRect("Icon", cellGo.transform, Vector2.zero, new Vector2(30, 30),
                    new Vector2(0.5f, 0.5f), new Vector2(0.5f, 0.5f), new Vector2(0.5f, 0.5f));
                var iconImg = iconGo.AddComponent<Image>();
                iconImg.color = new Color(0.4f, 0.4f, 0.5f, 0.6f);

                // 수령 완료 체크마크 (우상단)
                var checkGo = CreateRect("Check", cellGo.transform, new Vector2(-5, -5), new Vector2(20, 20),
                    new Vector2(1f, 1f), new Vector2(1f, 1f), new Vector2(1f, 1f));
                var checkText = checkGo.AddComponent<Text>();
                checkText.text = "V";
                checkText.fontSize = 16;
                checkText.fontStyle = FontStyle.Bold;
                checkText.color = COL_CHECK;
                checkText.alignment = TextAnchor.MiddleCenter;
                checkText.font = Resources.GetBuiltinResource<Font>("LegacyRuntime.ttf");
                checkGo.SetActive(false);
                _claimedChecks[idx] = checkGo;

                // 오늘 테두리 (전체 셀 둘레)
                var borderGo = CreateRect("Border", cellGo.transform, Vector2.zero, Vector2.zero,
                    Vector2.zero, Vector2.one, new Vector2(0.5f, 0.5f));
                var borderRT = borderGo.GetComponent<RectTransform>();
                borderRT.offsetMin = new Vector2(-2, -2);
                borderRT.offsetMax = new Vector2(2, 2);
                var borderOutline = borderGo.AddComponent<UnityEngine.UI.Outline>();
                // Outline은 텍스트/Image에만 동작하므로 빈 Image를 사용
                var borderImg = borderGo.AddComponent<Image>();
                borderImg.color = Color.clear; // 투명 배경
                var outline = borderGo.AddComponent<UnityEngine.UI.Outline>();
                outline.effectColor = COL_TODAY_BORDER;
                outline.effectDistance = new Vector2(2, 2);
                borderGo.SetActive(false);
                _todayBorders[idx] = borderGo;
            }
        }

        // 수령 버튼 (하단 좌측)
        var claimBtnGo = CreateRect("ClaimButton", _panel.transform,
            new Vector2(-80, 20), new Vector2(140, 40),
            new Vector2(0.5f, 0f), new Vector2(0.5f, 0f), new Vector2(0.5f, 0.5f));
        var claimBtnImg = claimBtnGo.AddComponent<Image>();
        claimBtnImg.color = COL_CLAIM_BTN;
        _claimButton = claimBtnGo.AddComponent<Button>();
        _claimButton.onClick.AddListener(OnClaimClick);

        var claimTxtGo = CreateRect("Text", claimBtnGo.transform, Vector2.zero, Vector2.zero,
            Vector2.zero, Vector2.one, new Vector2(0.5f, 0.5f));
        _claimButtonText = claimTxtGo.AddComponent<Text>();
        _claimButtonText.text = "Claim Today";
        _claimButtonText.fontSize = 16;
        _claimButtonText.fontStyle = FontStyle.Bold;
        _claimButtonText.color = Color.white;
        _claimButtonText.alignment = TextAnchor.MiddleCenter;
        _claimButtonText.font = Resources.GetBuiltinResource<Font>("LegacyRuntime.ttf");

        // 닫기 버튼 (하단 우측)
        var closeBtnGo = CreateRect("CloseButton", _panel.transform,
            new Vector2(80, 20), new Vector2(100, 40),
            new Vector2(0.5f, 0f), new Vector2(0.5f, 0f), new Vector2(0.5f, 0.5f));
        var closeBtnImg = closeBtnGo.AddComponent<Image>();
        closeBtnImg.color = COL_CLOSE_BTN;
        _closeButton = closeBtnGo.AddComponent<Button>();
        _closeButton.onClick.AddListener(OnCloseClick);

        var closeTxtGo = CreateRect("Text", closeBtnGo.transform, Vector2.zero, Vector2.zero,
            Vector2.zero, Vector2.one, new Vector2(0.5f, 0.5f));
        var closeTxt = closeTxtGo.AddComponent<Text>();
        closeTxt.text = "Close";
        closeTxt.fontSize = 16;
        closeTxt.color = Color.white;
        closeTxt.alignment = TextAnchor.MiddleCenter;
        closeTxt.font = Resources.GetBuiltinResource<Font>("LegacyRuntime.ttf");
    }

    // ━━━ 버튼 핸들러 ━━━

    private void OnClaimClick()
    {
        var mgr = AttendanceManager.Instance;
        if (mgr == null || mgr.Info == null) return;
        mgr.ClaimDay(mgr.CurrentDay);
    }

    private void OnCloseClick()
    {
        AttendanceManager.Instance?.ClosePanel();
    }

    // ━━━ 이벤트 핸들러 ━━━

    private void HandleInfoUpdated(AttendanceInfoData data)
    {
        RefreshGrid(data);

        // 자동 표시: 로그인 후 출석 정보 수신 시 패널 열기
        if (!_overlay.activeSelf)
        {
            AttendanceManager.Instance?.OpenPanel();
        }
    }

    private void HandleRewardClaimed(AttendanceClaimResultData data)
    {
        if (data.Result == AttendanceClaimResult.SUCCESS)
        {
            if (_statusText != null)
                _statusText.text = $"Day {data.Day} claimed! Reward: Type{data.RewardType} #{data.RewardId} x{data.RewardCount}";

            // 그리드 갱신
            var info = AttendanceManager.Instance?.Info;
            if (info != null)
                RefreshGrid(info);
        }
        else
        {
            if (_statusText != null)
                _statusText.text = $"Claim failed: {data.Result}";
        }
    }

    private void ShowPanel()
    {
        if (_overlay != null) _overlay.SetActive(true);
    }

    private void HidePanel()
    {
        if (_overlay != null) _overlay.SetActive(false);
    }

    // ━━━ 그리드 갱신 ━━━

    private void RefreshGrid(AttendanceInfoData data)
    {
        if (data == null) return;

        if (_statusText != null)
            _statusText.text = $"Day {data.CurrentDay} / {data.TotalDays} days total";

        for (int i = 0; i < 14; i++)
        {
            bool isClaimed = data.Claimed != null && i < data.Claimed.Length && data.Claimed[i];
            bool isToday = (i + 1) == data.CurrentDay;

            // 배경색
            if (_dayBackgrounds[i] != null)
            {
                if (isClaimed)
                    _dayBackgrounds[i].color = COL_DAY_CLAIMED;
                else if (isToday)
                    _dayBackgrounds[i].color = COL_DAY_TODAY;
                else
                    _dayBackgrounds[i].color = COL_DAY_DEFAULT;
            }

            // 체크마크
            if (_claimedChecks[i] != null)
                _claimedChecks[i].SetActive(isClaimed);

            // 오늘 테두리
            if (_todayBorders[i] != null)
                _todayBorders[i].SetActive(isToday && !isClaimed);
        }

        // 수령 버튼 상태
        if (_claimButton != null)
        {
            bool canClaim = data.CurrentDay > 0 && data.CurrentDay <= 14
                && data.Claimed != null && data.CurrentDay <= data.Claimed.Length
                && !data.Claimed[data.CurrentDay - 1];
            _claimButton.interactable = canClaim;
        }
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
