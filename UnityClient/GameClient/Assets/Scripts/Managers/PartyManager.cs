// ━━━ PartyManager.cs ━━━
// 파티 시스템 관리 — 파티 생성, 초대, 수락, 탈퇴, 추방
// NetworkManager 이벤트 구독 → UI에 파티 이벤트 발행

using System;
using UnityEngine;
using Network;

public class PartyManager : MonoBehaviour
{
    // ━━━ 파티 데이터 ━━━
    public uint PartyId { get; private set; }
    public ulong LeaderId { get; private set; }
    public PartyMemberInfo[] Members { get; private set; }
    public bool InParty => PartyId != 0;
    public bool IsLeader => InParty && LeaderId == NetworkManager.Instance.MyEntityId;

    // ━━━ 이벤트 ━━━
    public event Action OnPartyChanged;

    // ━━━ 싱글톤 (Scene-bound) ━━━
    public static PartyManager Instance { get; private set; }

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
        net.OnPartyInfo += HandlePartyInfo;
    }

    private void OnDestroy()
    {
        var net = NetworkManager.Instance;
        if (net == null) return;

        net.OnPartyInfo -= HandlePartyInfo;

        if (Instance == this) Instance = null;
    }

    // ━━━ 공개 API ━━━

    public void CreateParty()
    {
        NetworkManager.Instance.CreateParty();
    }

    public void InviteToParty(ulong targetEntity)
    {
        NetworkManager.Instance.InviteToParty(targetEntity);
    }

    public void AcceptParty(uint partyId)
    {
        NetworkManager.Instance.AcceptParty(partyId);
    }

    public void LeaveParty()
    {
        NetworkManager.Instance.LeaveParty();
    }

    public void KickMember(ulong targetEntity)
    {
        NetworkManager.Instance.KickFromParty(targetEntity);
    }

    // ━━━ 핸들러 ━━━

    private void HandlePartyInfo(PartyInfoData data)
    {
        if (data.Result != 0)
        {
            Debug.Log($"[PartyManager] PartyInfo error: result={data.Result}");
            return;
        }

        PartyId = data.PartyId;
        LeaderId = data.LeaderId;
        Members = data.Members;

        // 파티 해산 (멤버 0명 또는 파티ID 0)
        if (PartyId == 0 || Members == null || Members.Length == 0)
        {
            PartyId = 0;
            LeaderId = 0;
            Members = null;
        }

        Debug.Log($"[PartyManager] Party={PartyId}, leader={LeaderId}, members={Members?.Length ?? 0}");
        OnPartyChanged?.Invoke();
    }
}
