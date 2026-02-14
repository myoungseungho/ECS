// ━━━ DungeonUI.cs ━━━
// 던전 찾기 UI — 매칭 큐 / 던전 정보 / 수락 팝업
// DungeonManager 이벤트 구독으로 상태 표시
// J키 토글

using System.Collections.Generic;
using UnityEngine;
using UnityEngine.UI;
using Network;

public class DungeonUI : MonoBehaviour
{
    // ━━━ UI 참조 (ProjectSetup에서 생성) ━━━
    [SerializeField] private GameObject _panel;
    [SerializeField] private Text _titleText;
    [SerializeField] private Text _statusText;
    [SerializeField] private Text _queueInfoText;
    [SerializeField] private Button _enqueueBtn;
    [SerializeField] private Button _dequeueBtn;
    [SerializeField] private Button _leaveBtn;
    [SerializeField] private Button _acceptBtn;
    [SerializeField] private Button _closeBtn;

    // 던전 타입 버튼들
    [SerializeField] private Button _storyBtn;
    [SerializeField] private Button _partyBtn;
    [SerializeField] private Button _chaosBtn;

    // ━━━ 매칭 수락 팝업 ━━━
    [SerializeField] private GameObject _matchPopup;
    [SerializeField] private Text _matchPopupText;
    [SerializeField] private Button _matchAcceptBtn;
    [SerializeField] private Button _matchDeclineBtn;

    private bool _isOpen;
    private uint _selectedDungeonType = (uint)DungeonManager.DungeonType.PARTY;

    private void Start()
    {
        if (_panel != null)
            _panel.SetActive(false);
        if (_matchPopup != null)
            _matchPopup.SetActive(false);

        var dm = DungeonManager.Instance;
        if (dm != null)
        {
            dm.OnDungeonEntered += HandleDungeonEntered;
            dm.OnDungeonLeft += HandleDungeonLeft;
            dm.OnDungeonInfoUpdated += HandleDungeonInfo;
            dm.OnMatchFound += HandleMatchFound;
            dm.OnMatchStateChanged += HandleMatchStateChanged;
        }

        // 버튼 연결
        if (_enqueueBtn != null) _enqueueBtn.onClick.AddListener(OnEnqueueClick);
        if (_dequeueBtn != null) _dequeueBtn.onClick.AddListener(OnDequeueClick);
        if (_leaveBtn != null) _leaveBtn.onClick.AddListener(OnLeaveClick);
        if (_closeBtn != null) _closeBtn.onClick.AddListener(OnCloseClick);
        if (_matchAcceptBtn != null) _matchAcceptBtn.onClick.AddListener(OnMatchAcceptClick);
        if (_matchDeclineBtn != null) _matchDeclineBtn.onClick.AddListener(OnMatchDeclineClick);
        if (_storyBtn != null) _storyBtn.onClick.AddListener(() => SelectDungeonType((uint)DungeonManager.DungeonType.STORY));
        if (_partyBtn != null) _partyBtn.onClick.AddListener(() => SelectDungeonType((uint)DungeonManager.DungeonType.PARTY));
        if (_chaosBtn != null) _chaosBtn.onClick.AddListener(() => SelectDungeonType((uint)DungeonManager.DungeonType.CHAOS));

        RefreshUI();
    }

    private void OnDestroy()
    {
        var dm = DungeonManager.Instance;
        if (dm == null) return;

        dm.OnDungeonEntered -= HandleDungeonEntered;
        dm.OnDungeonLeft -= HandleDungeonLeft;
        dm.OnDungeonInfoUpdated -= HandleDungeonInfo;
        dm.OnMatchFound -= HandleMatchFound;
        dm.OnMatchStateChanged -= HandleMatchStateChanged;
    }

    private void Update()
    {
        if (Input.GetKeyDown(KeyCode.J))
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

    private void SelectDungeonType(uint type)
    {
        _selectedDungeonType = type;
        RefreshUI();
    }

    private void OnEnqueueClick()
    {
        DungeonManager.Instance?.EnqueueMatch(_selectedDungeonType);
    }

    private void OnDequeueClick()
    {
        DungeonManager.Instance?.DequeueMatch();
    }

    private void OnLeaveClick()
    {
        DungeonManager.Instance?.LeaveDungeon();
    }

    private void OnCloseClick()
    {
        _isOpen = false;
        if (_panel != null) _panel.SetActive(false);
    }

    private void OnMatchAcceptClick()
    {
        DungeonManager.Instance?.AcceptMatch();
        if (_matchPopup != null) _matchPopup.SetActive(false);
    }

    private void OnMatchDeclineClick()
    {
        DungeonManager.Instance?.DequeueMatch();
        if (_matchPopup != null) _matchPopup.SetActive(false);
    }

    // ━━━ 이벤트 핸들러 ━━━

    private void HandleDungeonEntered(InstanceEnterData data)
    {
        RefreshUI();
    }

    private void HandleDungeonLeft()
    {
        RefreshUI();
    }

    private void HandleDungeonInfo(InstanceInfoData data)
    {
        RefreshUI();
    }

    private void HandleMatchFound(MatchFoundData data)
    {
        // 매칭 수락 팝업 표시
        if (_matchPopup != null)
        {
            _matchPopup.SetActive(true);
            if (_matchPopupText != null)
                _matchPopupText.text = $"Match Found!\nPlayers: {data.PlayerCount}\nDungeon Type: {data.DungeonType}";
        }
    }

    private void HandleMatchStateChanged(DungeonManager.MatchState state)
    {
        RefreshUI();
    }

    // ━━━ UI 갱신 ━━━

    private void RefreshUI()
    {
        var dm = DungeonManager.Instance;
        if (dm == null) return;

        // 상태 텍스트
        if (_statusText != null)
        {
            if (dm.InDungeon)
                _statusText.text = $"In Dungeon (ID: {dm.CurrentInstanceId})\nPlayers: {dm.PlayerCount} | Monsters: {dm.MonsterCount}";
            else if (dm.CurrentMatchState == DungeonManager.MatchState.QUEUED)
                _statusText.text = $"Queued... Position: {dm.QueuePosition}";
            else
                _statusText.text = "Select a dungeon to enter";
        }

        // 큐 정보
        if (_queueInfoText != null)
        {
            string typeStr = _selectedDungeonType switch
            {
                1 => "Story",
                2 => "Party",
                3 => "Chaos",
                4 => "Raid",
                5 => "Abyss",
                _ => $"Type {_selectedDungeonType}"
            };
            _queueInfoText.text = $"Selected: {typeStr}";
        }

        // 버튼 활성화
        bool canQueue = !dm.InDungeon && dm.CurrentMatchState == DungeonManager.MatchState.NONE;
        bool isQueued = dm.CurrentMatchState == DungeonManager.MatchState.QUEUED;

        if (_enqueueBtn != null) _enqueueBtn.gameObject.SetActive(canQueue);
        if (_dequeueBtn != null) _dequeueBtn.gameObject.SetActive(isQueued);
        if (_leaveBtn != null) _leaveBtn.gameObject.SetActive(dm.InDungeon);
    }
}
