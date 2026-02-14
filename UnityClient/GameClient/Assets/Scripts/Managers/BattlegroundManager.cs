// ━━━ BattlegroundManager.cs ━━━
// 전장/PvP시즌 관리 (S053 TASK 6, MsgType 430-433)
// 거점 점령(capture_point) / 수레 호위(payload) 전장 큐/매칭/점수
// PvP 시즌 레이팅/티어 표시

using System;
using UnityEngine;

public class BattlegroundManager : MonoBehaviour
{
    public static BattlegroundManager Instance { get; private set; }

    // ━━━ Constants (GDD pvp.yaml) ━━━
    public const int BG_TEAM_SIZE = 6;
    public const int BG_TIME_LIMIT = 900;
    public const int BG_RESPAWN_TIME = 10;
    public const int BG_CAPTURE_POINTS = 3;
    public const int BG_WIN_SCORE = 1000;
    public const int BG_PAYLOAD_PHASES = 2;
    public const int BG_CHECKPOINTS = 3;
    public const int INITIAL_RATING = 1000;

    // PvP 티어 레이팅 범위
    private static readonly int[] TierMinRating = { 0, 1000, 1300, 1600, 1900, 2200, 2500 };
    private static readonly string[] TierNames = { "브론즈", "실버", "골드", "플래티넘", "다이아", "마스터", "그랜드마스터" };

    // ━━━ State ━━━
    private bool _isQueued;
    private Network.BattlegroundMode _queueMode;
    private bool _inMatch;
    private uint _matchId;
    private Network.BattlegroundTeam _myTeam;
    private uint _redScore;
    private uint _blueScore;
    private uint _timeRemaining;
    private bool _isPanelOpen;

    // ━━━ Public Properties ━━━
    public bool IsQueued => _isQueued;
    public Network.BattlegroundMode QueueMode => _queueMode;
    public bool InMatch => _inMatch;
    public uint MatchId => _matchId;
    public Network.BattlegroundTeam MyTeam => _myTeam;
    public uint RedScore => _redScore;
    public uint BlueScore => _blueScore;
    public uint TimeRemaining => _timeRemaining;
    public bool IsPanelOpen => _isPanelOpen;

    // ━━━ Events ━━━
    public event Action<Network.BattlegroundStatusData> OnQueueStatusChanged;
    public event Action<Network.BattlegroundScoreUpdateData> OnScoreUpdated;
    public event Action OnMatchStarted;
    public event Action OnMatchEnded;
    public event Action OnPanelOpened;
    public event Action OnPanelClosed;

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
        if (Network.NetworkManager.Instance != null)
        {
            Network.NetworkManager.Instance.OnBattlegroundStatus += HandleBattlegroundStatus;
            Network.NetworkManager.Instance.OnBattlegroundScoreUpdate += HandleScoreUpdate;
        }
    }

    private void OnDestroy()
    {
        if (Network.NetworkManager.Instance != null)
        {
            Network.NetworkManager.Instance.OnBattlegroundStatus -= HandleBattlegroundStatus;
            Network.NetworkManager.Instance.OnBattlegroundScoreUpdate -= HandleScoreUpdate;
        }
        if (Instance == this) Instance = null;
    }

    private void Update()
    {
        if (Input.GetKeyDown(KeyCode.F7))
        {
            if (_isPanelOpen) ClosePanel();
            else OpenPanel();
        }
    }

    // ━━━ Public API ━━━

    public void OpenPanel()
    {
        _isPanelOpen = true;
        OnPanelOpened?.Invoke();
    }

    public void ClosePanel()
    {
        _isPanelOpen = false;
        OnPanelClosed?.Invoke();
    }

    public void EnqueueBattleground(Network.BattlegroundMode mode)
    {
        if (_isQueued || _inMatch) return;
        Network.NetworkManager.Instance?.BattlegroundQueue(0, (byte)mode);
    }

    public void CancelQueue()
    {
        if (!_isQueued) return;
        Network.NetworkManager.Instance?.BattlegroundQueue(1, (byte)_queueMode);
    }

    public void RequestScoreUpdate()
    {
        if (!_inMatch) return;
        Network.NetworkManager.Instance?.BattlegroundScoreQuery(0, 0);
    }

    public static Network.PvPTier GetTierFromRating(int rating)
    {
        for (int i = TierMinRating.Length - 1; i >= 0; i--)
        {
            if (rating >= TierMinRating[i])
                return (Network.PvPTier)i;
        }
        return Network.PvPTier.BRONZE;
    }

    public static string GetTierName(Network.PvPTier tier)
    {
        int idx = (int)tier;
        if (idx >= 0 && idx < TierNames.Length) return TierNames[idx];
        return "???";
    }

    // ━━━ Event Handlers ━━━

    private void HandleBattlegroundStatus(Network.BattlegroundStatusData data)
    {
        switch (data.Status)
        {
            case Network.BattlegroundStatus.QUEUED:
                _isQueued = true;
                _queueMode = data.Mode;
                break;

            case Network.BattlegroundStatus.MATCH_FOUND:
                _isQueued = false;
                _inMatch = true;
                _matchId = data.MatchId;
                _myTeam = data.Team;
                _queueMode = data.Mode;
                _redScore = 0;
                _blueScore = 0;
                OnMatchStarted?.Invoke();
                break;

            case Network.BattlegroundStatus.CANCELLED:
                _isQueued = false;
                break;

            case Network.BattlegroundStatus.ALREADY_IN_MATCH:
            case Network.BattlegroundStatus.INVALID_MODE:
                break;
        }

        OnQueueStatusChanged?.Invoke(data);
    }

    private void HandleScoreUpdate(Network.BattlegroundScoreUpdateData data)
    {
        _redScore = data.RedScore;
        _blueScore = data.BlueScore;
        _timeRemaining = data.TimeRemaining;

        // 매치 종료 체크 (시간 0 or 스코어 도달)
        if (data.TimeRemaining == 0 || data.RedScore >= BG_WIN_SCORE || data.BlueScore >= BG_WIN_SCORE)
        {
            _inMatch = false;
            OnMatchEnded?.Invoke();
        }

        OnScoreUpdated?.Invoke(data);
    }
}
