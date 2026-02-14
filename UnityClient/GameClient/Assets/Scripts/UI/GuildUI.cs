// ━━━ GuildUI.cs ━━━
// 문파 UI — 문파 정보, 멤버 목록, 생성/탈퇴 버튼
// GuildManager 이벤트 구독 (G키 토글)

using UnityEngine;
using UnityEngine.UI;
using Network;

public class GuildUI : MonoBehaviour
{
    [Header("UI References")]
    [SerializeField] private GameObject guildPanel;
    [SerializeField] private Text guildNameText;
    [SerializeField] private Text memberListText;
    [SerializeField] private Text guildListText;

    private void Start()
    {
        if (GuildManager.Instance != null)
        {
            GuildManager.Instance.OnGuildInfoUpdated += HandleGuildInfoUpdated;
            GuildManager.Instance.OnGuildListReceived += HandleGuildListReceived;
            GuildManager.Instance.OnGuildLeft += HandleGuildLeft;
        }

        if (guildPanel != null)
            guildPanel.SetActive(false);
    }

    private void OnDestroy()
    {
        if (GuildManager.Instance != null)
        {
            GuildManager.Instance.OnGuildInfoUpdated -= HandleGuildInfoUpdated;
            GuildManager.Instance.OnGuildListReceived -= HandleGuildListReceived;
            GuildManager.Instance.OnGuildLeft -= HandleGuildLeft;
        }
    }

    private void Update()
    {
        // G키로 문파 패널 토글
        if (Input.GetKeyDown(KeyCode.G) && !Input.GetKey(KeyCode.LeftControl))
        {
            if (guildPanel != null)
            {
                bool active = !guildPanel.activeSelf;
                guildPanel.SetActive(active);
                if (active)
                    GuildManager.Instance?.RequestGuildInfo();
            }
        }

        // ESC로 닫기
        if (guildPanel != null && guildPanel.activeSelf && Input.GetKeyDown(KeyCode.Escape))
        {
            guildPanel.SetActive(false);
        }
    }

    private void HandleGuildInfoUpdated(GuildInfoData data)
    {
        if (guildNameText != null)
            guildNameText.text = $"Guild: {data.Name} (ID: {data.GuildId})";

        if (memberListText != null)
        {
            var sb = new System.Text.StringBuilder();
            sb.AppendLine($"Members ({data.Members.Length}/20):");
            for (int i = 0; i < data.Members.Length; i++)
            {
                string rank = data.Members[i].Rank == 0 ? "Leader" : data.Members[i].Rank == 1 ? "Officer" : "Member";
                sb.AppendLine($"  Entity#{data.Members[i].EntityId} [{rank}]");
            }
            memberListText.text = sb.ToString();
        }
    }

    private void HandleGuildListReceived(GuildListEntry[] guilds)
    {
        if (guildListText != null)
        {
            var sb = new System.Text.StringBuilder();
            sb.AppendLine($"Guild List ({guilds.Length}):");
            for (int i = 0; i < guilds.Length; i++)
            {
                sb.AppendLine($"  [{guilds[i].GuildId}] {guilds[i].Name} ({guilds[i].MemberCount}/20) Leader: {guilds[i].LeaderName}");
            }
            guildListText.text = sb.ToString();
        }
    }

    private void HandleGuildLeft()
    {
        if (guildNameText != null)
            guildNameText.text = "No Guild";
        if (memberListText != null)
            memberListText.text = "";
    }
}
