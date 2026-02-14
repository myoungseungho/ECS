// ━━━ GuildWarManager.cs ━━━
// 길드전 관리 (S053 TASK 6, MsgType 434-435)
// 선언/수락/거절/상태조회 + 수정 크리스탈 HP 추적

using System;
using UnityEngine;

public class GuildWarManager : MonoBehaviour
{
    public static GuildWarManager Instance { get; private set; }

    // ━━━ Constants (GDD pvp.yaml) ━━━
    public const int GW_MIN_PARTICIPANTS = 10;
    public const uint GW_CRYSTAL_HP = 10000;
    public const int GW_TIME_LIMIT = 1800;

    // ━━━ State ━━━
    private bool _inWar;
    private uint _warId;
    private uint _guildAId;
    private uint _guildBId;
    private uint _crystalHpA;
    private uint _crystalHpB;
    private uint _timeRemaining;
    private Network.GuildWarStatus _lastStatus;
    private bool _isPanelOpen;

    // ━━━ Public Properties ━━━
    public bool InWar => _inWar;
    public uint WarId => _warId;
    public uint GuildAId => _guildAId;
    public uint GuildBId => _guildBId;
    public uint CrystalHpA => _crystalHpA;
    public uint CrystalHpB => _crystalHpB;
    public uint TimeRemaining => _timeRemaining;
    public Network.GuildWarStatus LastStatus => _lastStatus;
    public bool IsPanelOpen => _isPanelOpen;

    // ━━━ Events ━━━
    public event Action<Network.GuildWarStatusData> OnWarStatusChanged;
    public event Action OnWarStarted;
    public event Action OnWarEnded;
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
            Network.NetworkManager.Instance.OnGuildWarStatus += HandleGuildWarStatus;
        }
    }

    private void OnDestroy()
    {
        if (Network.NetworkManager.Instance != null)
        {
            Network.NetworkManager.Instance.OnGuildWarStatus -= HandleGuildWarStatus;
        }
        if (Instance == this) Instance = null;
    }

    private void Update()
    {
        if (Input.GetKeyDown(KeyCode.F8))
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

    public void DeclareWar(uint targetGuildId)
    {
        if (_inWar) return;
        Network.NetworkManager.Instance?.GuildWarAction((byte)Network.GuildWarAction.DECLARE, targetGuildId);
    }

    public void AcceptWar()
    {
        Network.NetworkManager.Instance?.GuildWarAction((byte)Network.GuildWarAction.ACCEPT, 0);
    }

    public void RejectWar()
    {
        Network.NetworkManager.Instance?.GuildWarAction((byte)Network.GuildWarAction.REJECT, 0);
    }

    public void QueryWarStatus()
    {
        Network.NetworkManager.Instance?.GuildWarAction((byte)Network.GuildWarAction.QUERY, 0);
    }

    // ━━━ Event Handlers ━━━

    private void HandleGuildWarStatus(Network.GuildWarStatusData data)
    {
        _lastStatus = data.Status;
        _warId = data.WarId;
        _guildAId = data.GuildAId;
        _guildBId = data.GuildBId;
        _crystalHpA = data.CrystalHpA;
        _crystalHpB = data.CrystalHpB;
        _timeRemaining = data.TimeRemaining;

        switch (data.Status)
        {
            case Network.GuildWarStatus.WAR_STARTED:
                _inWar = true;
                OnWarStarted?.Invoke();
                break;

            case Network.GuildWarStatus.WAR_REJECTED:
            case Network.GuildWarStatus.NO_WAR:
                _inWar = false;
                OnWarEnded?.Invoke();
                break;

            case Network.GuildWarStatus.NO_GUILD:
            case Network.GuildWarStatus.TOO_FEW_MEMBERS:
            case Network.GuildWarStatus.ALREADY_AT_WAR:
                break;
        }

        // 크리스탈 파괴 체크
        if (_inWar && (data.CrystalHpA == 0 || data.CrystalHpB == 0 || data.TimeRemaining == 0))
        {
            _inWar = false;
            OnWarEnded?.Invoke();
        }

        OnWarStatusChanged?.Invoke(data);
    }
}
