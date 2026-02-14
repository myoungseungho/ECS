// ━━━ GuildManager.cs ━━━
// 문파(길드) 시스템 관리 — 생성/해산/초대/수락/탈퇴/추방/정보/목록
// NetworkManager 이벤트 구독 → GuildUI에 이벤트 발행

using System;
using UnityEngine;
using Network;

public class GuildManager : MonoBehaviour
{
    // ━━━ 상태 ━━━
    public bool InGuild { get; private set; }
    public uint GuildId { get; private set; }
    public string GuildName { get; private set; }
    public ulong LeaderId { get; private set; }
    public GuildMemberInfo[] Members { get; private set; }

    // ━━━ 이벤트 ━━━
    public event Action<GuildInfoData> OnGuildInfoUpdated;
    public event Action<GuildListEntry[]> OnGuildListReceived;
    public event Action OnGuildLeft;

    // ━━━ 싱글톤 (Scene-bound) ━━━
    public static GuildManager Instance { get; private set; }

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
        net.OnGuildInfo += HandleGuildInfo;
        net.OnGuildList += HandleGuildList;
    }

    private void OnDestroy()
    {
        var net = NetworkManager.Instance;
        if (net == null) return;

        net.OnGuildInfo -= HandleGuildInfo;
        net.OnGuildList -= HandleGuildList;

        if (Instance == this) Instance = null;
    }

    // ━━━ 공개 API ━━━

    /// <summary>문파 생성 (최대 16글자)</summary>
    public void CreateGuild(string guildName)
    {
        NetworkManager.Instance.CreateGuild(guildName);
    }

    /// <summary>문파 해산 (파장만)</summary>
    public void DisbandGuild()
    {
        NetworkManager.Instance.DisbandGuild();
    }

    /// <summary>문파 초대</summary>
    public void InviteMember(ulong targetEntity)
    {
        NetworkManager.Instance.InviteToGuild(targetEntity);
    }

    /// <summary>문파 초대 수락</summary>
    public void AcceptInvite()
    {
        NetworkManager.Instance.AcceptGuildInvite();
    }

    /// <summary>문파 탈퇴</summary>
    public void LeaveGuild()
    {
        NetworkManager.Instance.LeaveGuild();
    }

    /// <summary>문파 추방 (파장만)</summary>
    public void KickMember(ulong targetEntity)
    {
        NetworkManager.Instance.KickFromGuild(targetEntity);
    }

    /// <summary>문파 정보 요청</summary>
    public void RequestGuildInfo()
    {
        NetworkManager.Instance.RequestGuildInfo();
    }

    /// <summary>문파 목록 요청</summary>
    public void RequestGuildList()
    {
        NetworkManager.Instance.RequestGuildList();
    }

    /// <summary>내가 파장인지 확인</summary>
    public bool IsLeader
    {
        get { return InGuild && LeaderId == NetworkManager.Instance.MyEntityId; }
    }

    // ━━━ 핸들러 ━━━

    private void HandleGuildInfo(GuildInfoData data)
    {
        if (data.GuildId == 0)
        {
            InGuild = false;
            GuildId = 0;
            GuildName = null;
            LeaderId = 0;
            Members = null;
            OnGuildLeft?.Invoke();
            return;
        }

        InGuild = true;
        GuildId = data.GuildId;
        GuildName = data.Name;
        LeaderId = data.LeaderId;
        Members = data.Members;

        Debug.Log($"[GuildManager] Guild: {data.Name} (id={data.GuildId}), members={data.Members.Length}");
        OnGuildInfoUpdated?.Invoke(data);
    }

    private void HandleGuildList(GuildListEntry[] guilds)
    {
        Debug.Log($"[GuildManager] Guild list: {guilds.Length} guilds");
        OnGuildListReceived?.Invoke(guilds);
    }
}
