// ━━━ BattlegroundUI.cs ━━━
// 전장 큐/점수판/PvP시즌 UI — F7 토글 (S053 TASK 6)
// 거점점령/수레호위 모드 선택 + 큐 등록/취소 + 실시간 점수판

using UnityEngine;
using UnityEngine.UI;

public class BattlegroundUI : MonoBehaviour
{
    public static BattlegroundUI Instance { get; private set; }

    [SerializeField] private GameObject _panel;
    [SerializeField] private Text _titleText;
    [SerializeField] private Text _statusText;
    [SerializeField] private Text _scoreText;
    [SerializeField] private Text _timerText;
    [SerializeField] private Text _resultText;

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
        if (_panel != null) _panel.SetActive(false);

        if (BattlegroundManager.Instance != null)
        {
            BattlegroundManager.Instance.OnPanelOpened += HandlePanelOpened;
            BattlegroundManager.Instance.OnPanelClosed += HandlePanelClosed;
            BattlegroundManager.Instance.OnQueueStatusChanged += HandleQueueStatus;
            BattlegroundManager.Instance.OnScoreUpdated += HandleScoreUpdate;
            BattlegroundManager.Instance.OnMatchStarted += HandleMatchStarted;
            BattlegroundManager.Instance.OnMatchEnded += HandleMatchEnded;
        }
    }

    private void OnDestroy()
    {
        if (BattlegroundManager.Instance != null)
        {
            BattlegroundManager.Instance.OnPanelOpened -= HandlePanelOpened;
            BattlegroundManager.Instance.OnPanelClosed -= HandlePanelClosed;
            BattlegroundManager.Instance.OnQueueStatusChanged -= HandleQueueStatus;
            BattlegroundManager.Instance.OnScoreUpdated -= HandleScoreUpdate;
            BattlegroundManager.Instance.OnMatchStarted -= HandleMatchStarted;
            BattlegroundManager.Instance.OnMatchEnded -= HandleMatchEnded;
        }
        if (Instance == this) Instance = null;
    }

    // ━━━ Panel Toggle ━━━

    private void HandlePanelOpened()
    {
        if (_panel != null) _panel.SetActive(true);
        UpdateDisplay();
    }

    private void HandlePanelClosed()
    {
        if (_panel != null) _panel.SetActive(false);
    }

    // ━━━ Queue Status ━━━

    private void HandleQueueStatus(Network.BattlegroundStatusData data)
    {
        string modeStr = data.Mode == Network.BattlegroundMode.CAPTURE_POINT ? "거점 점령" : "수레 호위";

        switch (data.Status)
        {
            case Network.BattlegroundStatus.QUEUED:
                SetStatus($"<color=yellow>큐 대기 중 [{modeStr}] ({data.QueueCount}명)</color>");
                break;
            case Network.BattlegroundStatus.MATCH_FOUND:
                SetStatus($"<color=green>매치 발견! [{modeStr}] 팀: {GetTeamName(data.Team)}</color>");
                break;
            case Network.BattlegroundStatus.CANCELLED:
                SetStatus("큐 취소됨");
                break;
            case Network.BattlegroundStatus.ALREADY_IN_MATCH:
                SetStatus("<color=red>이미 매치 진행 중</color>");
                break;
            case Network.BattlegroundStatus.INVALID_MODE:
                SetStatus("<color=red>잘못된 전장 모드</color>");
                break;
        }
    }

    // ━━━ Score Update ━━━

    private void HandleScoreUpdate(Network.BattlegroundScoreUpdateData data)
    {
        string modeStr = data.Mode == Network.BattlegroundMode.CAPTURE_POINT ? "거점 점령" : "수레 호위";

        if (_scoreText != null)
        {
            string myTeamStr = BattlegroundManager.Instance != null ?
                GetTeamName(BattlegroundManager.Instance.MyTeam) : "???";
            _scoreText.text = $"[{modeStr}] 내 팀: {myTeamStr}\n" +
                              $"<color=red>레드: {data.RedScore}</color> vs <color=#4488FF>블루: {data.BlueScore}</color>";
        }

        if (_timerText != null)
        {
            int min = (int)(data.TimeRemaining / 60);
            int sec = (int)(data.TimeRemaining % 60);
            _timerText.text = $"남은 시간: {min:D2}:{sec:D2}";
        }
    }

    // ━━━ Match Lifecycle ━━━

    private void HandleMatchStarted()
    {
        SetStatus("<color=green>전장 시작!</color>");
        if (_resultText != null) _resultText.text = "";
    }

    private void HandleMatchEnded()
    {
        if (BattlegroundManager.Instance == null) return;

        var mgr = BattlegroundManager.Instance;
        bool myTeamRed = mgr.MyTeam == Network.BattlegroundTeam.RED;
        uint myScore = myTeamRed ? mgr.RedScore : mgr.BlueScore;
        uint enemyScore = myTeamRed ? mgr.BlueScore : mgr.RedScore;
        bool won = myScore > enemyScore;

        if (_resultText != null)
        {
            _resultText.text = won ?
                "<color=green>승리!</color>" :
                "<color=red>패배</color>";
        }

        SetStatus("전장 종료");
    }

    // ━━━ Helpers ━━━

    private void UpdateDisplay()
    {
        if (_titleText != null)
            _titleText.text = "전장 (Battleground)";

        if (BattlegroundManager.Instance == null) return;

        var mgr = BattlegroundManager.Instance;
        if (mgr.InMatch)
        {
            SetStatus($"<color=green>매치 진행 중 — {GetModeName(mgr.QueueMode)}</color>");
        }
        else if (mgr.IsQueued)
        {
            SetStatus($"<color=yellow>큐 대기 중 — {GetModeName(mgr.QueueMode)}</color>");
        }
        else
        {
            SetStatus("대기 중 — F7으로 열기/닫기");
        }
    }

    private void SetStatus(string text)
    {
        if (_statusText != null)
            _statusText.text = text;
    }

    private static string GetTeamName(Network.BattlegroundTeam team)
    {
        return team == Network.BattlegroundTeam.RED ? "<color=red>레드</color>" : "<color=#4488FF>블루</color>";
    }

    private static string GetModeName(Network.BattlegroundMode mode)
    {
        return mode == Network.BattlegroundMode.CAPTURE_POINT ? "거점 점령" : "수레 호위";
    }
}
