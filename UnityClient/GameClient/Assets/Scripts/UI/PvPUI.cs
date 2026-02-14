// ━━━ PvPUI.cs ━━━
// PvP 아레나 UI — 매칭 큐 / 전적 표시 / 수락 팝업
// PvPManager 이벤트 구독으로 상태 표시
// K키 토글

using UnityEngine;
using UnityEngine.UI;
using Network;

public class PvPUI : MonoBehaviour
{
    // ━━━ UI 참조 (ProjectSetup에서 생성) ━━━
    [SerializeField] private GameObject _panel;
    [SerializeField] private Text _titleText;
    [SerializeField] private Text _statusText;
    [SerializeField] private Text _recordText;
    [SerializeField] private Button _arena1v1Btn;
    [SerializeField] private Button _arena3v3Btn;
    [SerializeField] private Button _dequeueBtn;
    [SerializeField] private Button _leaveBtn;
    [SerializeField] private Button _closeBtn;

    // ━━━ 매칭 수락 팝업 ━━━
    [SerializeField] private GameObject _matchPopup;
    [SerializeField] private Text _matchPopupText;
    [SerializeField] private Button _matchAcceptBtn;
    [SerializeField] private Button _matchDeclineBtn;

    private bool _isOpen;

    private void Start()
    {
        if (_panel != null)
            _panel.SetActive(false);
        if (_matchPopup != null)
            _matchPopup.SetActive(false);

        var pm = PvPManager.Instance;
        if (pm != null)
        {
            pm.OnStateChanged += HandleStateChanged;
            pm.OnMatchFound += HandleMatchFound;
            pm.OnMatchEnded += HandleMatchEnded;
            pm.OnRatingUpdated += HandleRatingUpdated;
        }

        // 버튼 연결
        if (_arena1v1Btn != null) _arena1v1Btn.onClick.AddListener(() => OnQueueClick(PvPManager.PvPMode.ARENA_1V1));
        if (_arena3v3Btn != null) _arena3v3Btn.onClick.AddListener(() => OnQueueClick(PvPManager.PvPMode.ARENA_3V3));
        if (_dequeueBtn != null) _dequeueBtn.onClick.AddListener(OnDequeueClick);
        if (_leaveBtn != null) _leaveBtn.onClick.AddListener(OnLeaveClick);
        if (_closeBtn != null) _closeBtn.onClick.AddListener(OnCloseClick);
        if (_matchAcceptBtn != null) _matchAcceptBtn.onClick.AddListener(OnMatchAcceptClick);
        if (_matchDeclineBtn != null) _matchDeclineBtn.onClick.AddListener(OnMatchDeclineClick);

        RefreshUI();
    }

    private void OnDestroy()
    {
        var pm = PvPManager.Instance;
        if (pm == null) return;

        pm.OnStateChanged -= HandleStateChanged;
        pm.OnMatchFound -= HandleMatchFound;
        pm.OnMatchEnded -= HandleMatchEnded;
        pm.OnRatingUpdated -= HandleRatingUpdated;
    }

    private void Update()
    {
        if (Input.GetKeyDown(KeyCode.K))
            TogglePanel();
    }

    // ━━━ 공개 API ━━━

    public void TogglePanel()
    {
        _isOpen = !_isOpen;
        if (_panel != null) _panel.SetActive(_isOpen);
        if (_isOpen) RefreshUI();
    }

    // ━━━ 버튼 핸들러 ━━━

    private void OnQueueClick(PvPManager.PvPMode mode)
    {
        PvPManager.Instance?.QueueForMatch(mode);
    }

    private void OnDequeueClick()
    {
        PvPManager.Instance?.CancelQueue();
    }

    private void OnLeaveClick()
    {
        PvPManager.Instance?.LeaveMatch();
    }

    private void OnCloseClick()
    {
        _isOpen = false;
        if (_panel != null) _panel.SetActive(false);
    }

    private void OnMatchAcceptClick()
    {
        PvPManager.Instance?.AcceptMatch();
        if (_matchPopup != null) _matchPopup.SetActive(false);
    }

    private void OnMatchDeclineClick()
    {
        PvPManager.Instance?.CancelQueue();
        if (_matchPopup != null) _matchPopup.SetActive(false);
    }

    // ━━━ 이벤트 핸들러 ━━━

    private void HandleStateChanged(PvPManager.PvPState state)
    {
        RefreshUI();
    }

    private void HandleMatchFound(PvPMatchFoundData data)
    {
        if (_matchPopup != null)
        {
            _matchPopup.SetActive(true);
            string modeStr = data.ModeId switch
            {
                1 => "Arena 1v1",
                2 => "Arena 3v3",
                _ => $"Mode {data.ModeId}"
            };
            if (_matchPopupText != null)
                _matchPopupText.text = $"PvP Match Found!\n{modeStr}\nTeam: {data.TeamId}";
        }
    }

    private void HandleMatchEnded(PvPMatchEndData data)
    {
        RefreshUI();
    }

    private void HandleRatingUpdated(PvPRatingInfoData data)
    {
        RefreshUI();
    }

    // ━━━ UI 갱신 ━━━

    private void RefreshUI()
    {
        var pm = PvPManager.Instance;
        if (pm == null) return;

        // 상태 텍스트
        if (_statusText != null)
        {
            _statusText.text = pm.CurrentState switch
            {
                PvPManager.PvPState.IDLE => "Ready for PvP",
                PvPManager.PvPState.QUEUED => $"Queued... ({pm.QueueCount} in queue)",
                PvPManager.PvPState.MATCH_FOUND => "Match Found! Accept?",
                PvPManager.PvPState.IN_MATCH => $"In Match (Time: {pm.TimeLimit}s)",
                _ => ""
            };
        }

        // 전적 텍스트
        if (_recordText != null)
        {
            _recordText.text = $"[{pm.Tier}] Rating: {pm.Rating} | W: {pm.Wins} / L: {pm.Losses}";
        }

        // 버튼 활성화
        bool canQueue = pm.CurrentState == PvPManager.PvPState.IDLE;
        bool isQueued = pm.CurrentState == PvPManager.PvPState.QUEUED;
        bool inMatch = pm.CurrentState == PvPManager.PvPState.IN_MATCH;

        if (_arena1v1Btn != null) _arena1v1Btn.gameObject.SetActive(canQueue);
        if (_arena3v3Btn != null) _arena3v3Btn.gameObject.SetActive(canQueue);
        if (_dequeueBtn != null) _dequeueBtn.gameObject.SetActive(isQueued);
        if (_leaveBtn != null) _leaveBtn.gameObject.SetActive(inMatch);
    }
}
