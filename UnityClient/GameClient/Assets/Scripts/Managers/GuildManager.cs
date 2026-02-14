// ━━━ GuildManager.cs ━━━
// 길드 시스템 관리 — 생성, 해산, 초대, 수락, 탈퇴, 추방, 정보 조회
// T031: MsgType 290-299

using System;
using UnityEngine;
using Network;

public class GuildManager : MonoBehaviour
{
    // ━━━ 싱글톤 ━━━
    public static GuildManager Instance { get; private set; }

    // ━━━ 상태 ━━━
    private GuildInfoData _guildInfo;
    private GuildListEntry[] _guildList = Array.Empty<GuildListEntry>();
    private GuildInviteData _pendingInvite;

    // ━━━ 이벤트 ━━━
    public event Action<GuildInfoData> OnGuildInfoChanged;
    public event Action<GuildInviteData> OnGuildInviteReceived;
    public event Action<GuildListEntry[]> OnGuildListReceived;

    // ━━━ 공개 프로퍼티 ━━━
    public bool InGuild => _guildInfo != null && _guildInfo.Result == GuildResult.SUCCESS && _guildInfo.GuildId != 0;
    public GuildInfoData GuildInfo => _guildInfo;
    public GuildListEntry[] GuildList => _guildList;
    public GuildInviteData PendingInvite => _pendingInvite;

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
        var net = NetworkManager.Instance;
        if (net != null)
        {
            net.OnGuildInfo += HandleGuildInfo;
            net.OnGuildInvite += HandleGuildInvite;
            net.OnGuildList += HandleGuildList;
            net.OnEnterGame += HandleEnterGame;
        }
    }

    private void OnDestroy()
    {
        var net = NetworkManager.Instance;
        if (net != null)
        {
            net.OnGuildInfo -= HandleGuildInfo;
            net.OnGuildInvite -= HandleGuildInvite;
            net.OnGuildList -= HandleGuildList;
            net.OnEnterGame -= HandleEnterGame;
        }
        if (Instance == this) Instance = null;
    }

    // ━━━ 이벤트 핸들러 ━━━

    private void HandleEnterGame(EnterGameResult result)
    {
        if (result.ResultCode == 0)
            NetworkManager.Instance.RequestGuildInfo();
    }

    private void HandleGuildInfo(GuildInfoData data)
    {
        _guildInfo = data;
        OnGuildInfoChanged?.Invoke(data);
    }

    private void HandleGuildInvite(GuildInviteData data)
    {
        _pendingInvite = data;
        OnGuildInviteReceived?.Invoke(data);
    }

    private void HandleGuildList(GuildListEntry[] data)
    {
        _guildList = data;
        OnGuildListReceived?.Invoke(data);
    }

    // ━━━ 공개 API ━━━

    public void CreateGuild(string name) { NetworkManager.Instance.CreateGuild(name); }
    public void DisbandGuild() { NetworkManager.Instance.DisbandGuild(); }
    public void InviteMember(ulong targetEntity) { NetworkManager.Instance.InviteToGuild(targetEntity); }
    public void AcceptInvite(uint guildId) { _pendingInvite = null; NetworkManager.Instance.AcceptGuild(guildId); }
    public void DeclineInvite() { _pendingInvite = null; }
    public void LeaveGuild() { NetworkManager.Instance.LeaveGuild(); }
    public void KickMember(ulong targetEntity) { NetworkManager.Instance.KickFromGuild(targetEntity); }
    public void RequestInfo() { NetworkManager.Instance.RequestGuildInfo(); }
    public void RequestList() { NetworkManager.Instance.RequestGuildList(); }
}
