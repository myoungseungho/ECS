// ━━━ GuildUI.cs ━━━
// 길드 패널 UI — G키 토글, 길드 정보/멤버/초대 표시
// T031

using UnityEngine;
using UnityEngine.UI;
using Network;

public class GuildUI : MonoBehaviour
{
    [SerializeField] private GameObject guildPanel;
    [SerializeField] private Text guildNameText;
    [SerializeField] private Text guildInfoText;
    [SerializeField] private Text inviteText;
    [SerializeField] private GameObject invitePanel;
    [SerializeField] private Button acceptButton;
    [SerializeField] private Button declineButton;
    [SerializeField] private Button createButton;
    [SerializeField] private Button leaveButton;

    private bool _isOpen;

    private void Start()
    {
        if (GuildManager.Instance != null)
        {
            GuildManager.Instance.OnGuildInfoChanged += HandleGuildInfoChanged;
            GuildManager.Instance.OnGuildInviteReceived += HandleInviteReceived;
        }

        if (acceptButton != null)
            acceptButton.onClick.AddListener(OnAcceptClicked);
        if (declineButton != null)
            declineButton.onClick.AddListener(OnDeclineClicked);
        if (createButton != null)
            createButton.onClick.AddListener(OnCreateClicked);
        if (leaveButton != null)
            leaveButton.onClick.AddListener(OnLeaveClicked);

        if (guildPanel != null) guildPanel.SetActive(false);
        if (invitePanel != null) invitePanel.SetActive(false);
    }

    private void OnDestroy()
    {
        if (GuildManager.Instance != null)
        {
            GuildManager.Instance.OnGuildInfoChanged -= HandleGuildInfoChanged;
            GuildManager.Instance.OnGuildInviteReceived -= HandleInviteReceived;
        }
    }

    private void Update()
    {
        if (Input.GetKeyDown(KeyCode.G))
        {
            _isOpen = !_isOpen;
            if (guildPanel != null) guildPanel.SetActive(_isOpen);
            if (_isOpen && GuildManager.Instance != null)
                GuildManager.Instance.RequestInfo();
        }
    }

    private void HandleGuildInfoChanged(GuildInfoData data)
    {
        if (data.Result == GuildResult.SUCCESS && data.GuildId != 0)
        {
            if (guildNameText != null) guildNameText.text = data.GuildName;
            if (guildInfoText != null)
                guildInfoText.text = $"Lv.{data.Level} | Members: {data.MemberCount}/20\nMaster: {data.MasterId}";
            if (createButton != null) createButton.gameObject.SetActive(false);
            if (leaveButton != null) leaveButton.gameObject.SetActive(true);
        }
        else
        {
            if (guildNameText != null) guildNameText.text = "No Guild";
            if (guildInfoText != null) guildInfoText.text = "Create or join a guild";
            if (createButton != null) createButton.gameObject.SetActive(true);
            if (leaveButton != null) leaveButton.gameObject.SetActive(false);
        }
    }

    private void HandleInviteReceived(GuildInviteData data)
    {
        if (invitePanel != null) invitePanel.SetActive(true);
        if (inviteText != null)
            inviteText.text = $"Guild invite: {data.GuildName}";
    }

    private void OnAcceptClicked()
    {
        if (GuildManager.Instance != null && GuildManager.Instance.PendingInvite != null)
        {
            GuildManager.Instance.AcceptInvite(GuildManager.Instance.PendingInvite.GuildId);
            if (invitePanel != null) invitePanel.SetActive(false);
        }
    }

    private void OnDeclineClicked()
    {
        if (GuildManager.Instance != null)
            GuildManager.Instance.DeclineInvite();
        if (invitePanel != null) invitePanel.SetActive(false);
    }

    private void OnCreateClicked()
    {
        if (GuildManager.Instance != null)
            GuildManager.Instance.CreateGuild("MyGuild");
    }

    private void OnLeaveClicked()
    {
        if (GuildManager.Instance != null)
            GuildManager.Instance.LeaveGuild();
    }
}
