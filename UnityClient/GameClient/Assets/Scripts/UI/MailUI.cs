// ━━━ MailUI.cs ━━━
// 우편 UI — 우편함 목록, 읽기, 수령, 삭제
// MailManager 이벤트 구독 (M키 토글)

using UnityEngine;
using UnityEngine.UI;
using Network;

public class MailUI : MonoBehaviour
{
    [Header("UI References")]
    [SerializeField] private GameObject mailPanel;
    [SerializeField] private Text mailListText;
    [SerializeField] private Text mailContentText;
    [SerializeField] private Text mailStatusText;

    private void Start()
    {
        if (MailManager.Instance != null)
        {
            MailManager.Instance.OnMailListChanged += HandleMailListChanged;
            MailManager.Instance.OnMailOpened += HandleMailOpened;
            MailManager.Instance.OnClaimResult += HandleClaimResult;
            MailManager.Instance.OnDeleteResult += HandleDeleteResult;
        }

        if (mailPanel != null)
            mailPanel.SetActive(false);
    }

    private void OnDestroy()
    {
        if (MailManager.Instance != null)
        {
            MailManager.Instance.OnMailListChanged -= HandleMailListChanged;
            MailManager.Instance.OnMailOpened -= HandleMailOpened;
            MailManager.Instance.OnClaimResult -= HandleClaimResult;
            MailManager.Instance.OnDeleteResult -= HandleDeleteResult;
        }
    }

    private void Update()
    {
        // M키로 우편함 토글
        if (Input.GetKeyDown(KeyCode.M) && !Input.GetKey(KeyCode.LeftControl))
        {
            if (mailPanel != null)
            {
                bool active = !mailPanel.activeSelf;
                mailPanel.SetActive(active);
                if (active)
                    MailManager.Instance?.OpenMailbox();
                else
                    MailManager.Instance?.CloseMailbox();
            }
        }

        // ESC로 닫기
        if (mailPanel != null && mailPanel.activeSelf && Input.GetKeyDown(KeyCode.Escape))
        {
            mailPanel.SetActive(false);
            MailManager.Instance?.CloseMailbox();
        }
    }

    private void HandleMailListChanged()
    {
        if (mailListText == null) return;

        var mails = MailManager.Instance.Mails;
        var sb = new System.Text.StringBuilder();
        sb.AppendLine($"Mailbox ({mails.Count}/50):");
        for (int i = 0; i < mails.Count; i++)
        {
            string readMark = mails[i].IsRead ? " " : "*";
            string attach = mails[i].HasAttachment ? "[!]" : "   ";
            sb.AppendLine($"  {readMark}{attach} [{mails[i].MailId}] {mails[i].Sender}: {mails[i].Title}");
        }
        mailListText.text = sb.ToString();
    }

    private void HandleMailOpened(MailReadData data)
    {
        if (mailContentText != null)
        {
            var sb = new System.Text.StringBuilder();
            sb.AppendLine($"From: {data.Sender}");
            sb.AppendLine($"Title: {data.Title}");
            sb.AppendLine($"---");
            sb.AppendLine(data.Body);
            if (data.Gold > 0)
                sb.AppendLine($"\nAttached Gold: {data.Gold}");
            if (data.ItemId > 0)
                sb.AppendLine($"Attached Item: #{data.ItemId} x{data.ItemCount}");
            mailContentText.text = sb.ToString();
        }
    }

    private void HandleClaimResult(MailClaimResultData data)
    {
        if (mailStatusText != null)
        {
            mailStatusText.text = data.Result == MailClaimResult.SUCCESS
                ? "Attachment claimed!"
                : $"Claim failed: {data.Result}";
        }
    }

    private void HandleDeleteResult(MailDeleteResultData data)
    {
        if (mailStatusText != null)
        {
            mailStatusText.text = data.Result == MailDeleteResult.SUCCESS
                ? "Mail deleted."
                : $"Delete failed: {data.Result}";
        }
    }
}
