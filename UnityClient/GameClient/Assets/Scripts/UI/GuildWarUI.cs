// ━━━ GuildWarUI.cs ━━━
// 길드전 선언/수락/진행 UI — F8 토글 (S053 TASK 6)
// 선전포고/수락/거절 + 수정 크리스탈 HP + 타이머

using UnityEngine;
using UnityEngine.UI;

public class GuildWarUI : MonoBehaviour
{
    public static GuildWarUI Instance { get; private set; }

    [SerializeField] private GameObject _panel;
    [SerializeField] private Text _titleText;
    [SerializeField] private Text _statusText;
    [SerializeField] private Text _crystalText;
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

        if (GuildWarManager.Instance != null)
        {
            GuildWarManager.Instance.OnPanelOpened += HandlePanelOpened;
            GuildWarManager.Instance.OnPanelClosed += HandlePanelClosed;
            GuildWarManager.Instance.OnWarStatusChanged += HandleWarStatus;
            GuildWarManager.Instance.OnWarStarted += HandleWarStarted;
            GuildWarManager.Instance.OnWarEnded += HandleWarEnded;
        }
    }

    private void OnDestroy()
    {
        if (GuildWarManager.Instance != null)
        {
            GuildWarManager.Instance.OnPanelOpened -= HandlePanelOpened;
            GuildWarManager.Instance.OnPanelClosed -= HandlePanelClosed;
            GuildWarManager.Instance.OnWarStatusChanged -= HandleWarStatus;
            GuildWarManager.Instance.OnWarStarted -= HandleWarStarted;
            GuildWarManager.Instance.OnWarEnded -= HandleWarEnded;
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

    // ━━━ War Status ━━━

    private void HandleWarStatus(Network.GuildWarStatusData data)
    {
        switch (data.Status)
        {
            case Network.GuildWarStatus.WAR_DECLARED:
                SetStatus("<color=yellow>선전포고! 상대 길드 수락 대기</color>");
                break;
            case Network.GuildWarStatus.WAR_STARTED:
                SetStatus("<color=green>길드전 시작!</color>");
                UpdateCrystalDisplay(data);
                UpdateTimer(data.TimeRemaining);
                break;
            case Network.GuildWarStatus.WAR_REJECTED:
                SetStatus("상대 길드가 거절했습니다");
                break;
            case Network.GuildWarStatus.NO_GUILD:
                SetStatus("<color=red>문파에 소속되어 있지 않습니다</color>");
                break;
            case Network.GuildWarStatus.TOO_FEW_MEMBERS:
                SetStatus($"<color=red>최소 {GuildWarManager.GW_MIN_PARTICIPANTS}명 필요</color>");
                break;
            case Network.GuildWarStatus.ALREADY_AT_WAR:
                SetStatus("<color=red>이미 길드전 진행 중</color>");
                break;
            case Network.GuildWarStatus.PENDING_INFO:
                SetStatus("<color=yellow>선전포고 수신 — 수락/거절?</color>");
                UpdateCrystalDisplay(data);
                break;
            case Network.GuildWarStatus.NO_WAR:
                SetStatus("진행 중인 길드전 없음");
                ClearCrystalDisplay();
                break;
        }

        // 진행중 전투의 HP/타이머 업데이트
        if (data.Status == Network.GuildWarStatus.WAR_STARTED)
        {
            UpdateCrystalDisplay(data);
            UpdateTimer(data.TimeRemaining);
        }
    }

    // ━━━ War Lifecycle ━━━

    private void HandleWarStarted()
    {
        SetStatus("<color=green>길드전 시작!</color>");
        if (_resultText != null) _resultText.text = "";
    }

    private void HandleWarEnded()
    {
        if (GuildWarManager.Instance == null) return;

        var mgr = GuildWarManager.Instance;
        bool crystalADestroyed = mgr.CrystalHpA == 0;
        bool crystalBDestroyed = mgr.CrystalHpB == 0;

        string result;
        if (crystalADestroyed || crystalBDestroyed)
            result = "수정 파괴로 종료!";
        else if (mgr.TimeRemaining == 0)
            result = "시간 초과 — 판정승";
        else
            result = "길드전 종료";

        if (_resultText != null)
            _resultText.text = result;

        SetStatus("길드전 종료");
    }

    // ━━━ Helpers ━━━

    private void UpdateDisplay()
    {
        if (_titleText != null)
            _titleText.text = "길드전 (Guild War)";

        if (GuildWarManager.Instance == null) return;

        var mgr = GuildWarManager.Instance;
        if (mgr.InWar)
        {
            SetStatus("<color=green>길드전 진행 중</color>");
        }
        else
        {
            SetStatus("대기 중 — F8으로 열기/닫기");
        }
    }

    private void SetStatus(string text)
    {
        if (_statusText != null)
            _statusText.text = text;
    }

    private void UpdateCrystalDisplay(Network.GuildWarStatusData data)
    {
        if (_crystalText == null) return;

        float pctA = (float)data.CrystalHpA / GuildWarManager.GW_CRYSTAL_HP * 100f;
        float pctB = (float)data.CrystalHpB / GuildWarManager.GW_CRYSTAL_HP * 100f;

        string colorA = pctA > 50 ? "green" : pctA > 20 ? "yellow" : "red";
        string colorB = pctB > 50 ? "green" : pctB > 20 ? "yellow" : "red";

        _crystalText.text = $"길드A 수정: <color={colorA}>{data.CrystalHpA}/{GuildWarManager.GW_CRYSTAL_HP} ({pctA:F0}%)</color>\n" +
                           $"길드B 수정: <color={colorB}>{data.CrystalHpB}/{GuildWarManager.GW_CRYSTAL_HP} ({pctB:F0}%)</color>";
    }

    private void ClearCrystalDisplay()
    {
        if (_crystalText != null)
            _crystalText.text = "";
    }

    private void UpdateTimer(uint timeRemaining)
    {
        if (_timerText == null) return;

        int min = (int)(timeRemaining / 60);
        int sec = (int)(timeRemaining % 60);
        _timerText.text = $"남은 시간: {min:D2}:{sec:D2}";
    }
}
