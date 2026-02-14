// ━━━ MailUI.cs ━━━
// 우편 패널 UI — M키 토글, 우편 목록/읽기/수령/삭제
// T031

using UnityEngine;
using UnityEngine.UI;
using Network;

public class MailUI : MonoBehaviour
{
    [SerializeField] private GameObject mailPanel;
    [SerializeField] private Text mailCountText;
    [SerializeField] private Transform mailListParent;
    [SerializeField] private GameObject mailEntryTemplate;
    [SerializeField] private Text mailDetailText;
    [SerializeField] private Button claimButton;
    [SerializeField] private Button deleteButton;

    private bool _isOpen;

    private void Start()
    {
        if (MailManager.Instance != null)
        {
            MailManager.Instance.OnMailListChanged += RefreshList;
            MailManager.Instance.OnMailOpened += HandleMailOpened;
            MailManager.Instance.OnMailClaimed += HandleMailClaimed;
            MailManager.Instance.OnMailDeleted += HandleMailDeleted;
        }

        if (claimButton != null)
            claimButton.onClick.AddListener(OnClaimClicked);
        if (deleteButton != null)
            deleteButton.onClick.AddListener(OnDeleteClicked);

        if (mailPanel != null) mailPanel.SetActive(false);
    }

    private void OnDestroy()
    {
        if (MailManager.Instance != null)
        {
            MailManager.Instance.OnMailListChanged -= RefreshList;
            MailManager.Instance.OnMailOpened -= HandleMailOpened;
            MailManager.Instance.OnMailClaimed -= HandleMailClaimed;
            MailManager.Instance.OnMailDeleted -= HandleMailDeleted;
        }
    }

    private void Update()
    {
        if (Input.GetKeyDown(KeyCode.M))
        {
            _isOpen = !_isOpen;
            if (mailPanel != null) mailPanel.SetActive(_isOpen);
            if (_isOpen && MailManager.Instance != null)
                MailManager.Instance.RefreshList();
        }
    }

    private void RefreshList()
    {
        if (MailManager.Instance == null) return;
        var mails = MailManager.Instance.Mails;

        if (mailCountText != null)
            mailCountText.text = $"Mail: {mails.Count} ({MailManager.Instance.UnreadCount} unread)";

        if (mailListParent == null || mailEntryTemplate == null) return;

        // 기존 엔트리 제거 (템플릿 제외)
        for (int i = mailListParent.childCount - 1; i >= 0; i--)
        {
            var child = mailListParent.GetChild(i).gameObject;
            if (child != mailEntryTemplate)
                Destroy(child);
        }

        for (int i = 0; i < mails.Count; i++)
        {
            var entry = Instantiate(mailEntryTemplate, mailListParent);
            entry.SetActive(true);
            var text = entry.GetComponent<Text>();
            if (text == null) text = entry.GetComponentInChildren<Text>();
            if (text != null)
            {
                string readMark = mails[i].IsRead ? " " : "*";
                string attachMark = mails[i].HasAttachment ? "[+]" : "";
                text.text = $"{readMark} {mails[i].SenderName}: {mails[i].Subject} {attachMark}";
            }

            int mailIndex = i;
            var btn = entry.GetComponent<Button>();
            if (btn == null) btn = entry.AddComponent<Button>();
            uint mailId = mails[i].MailId;
            btn.onClick.AddListener(() =>
            {
                if (MailManager.Instance != null)
                    MailManager.Instance.ReadMail(mailId);
            });
        }
    }

    private void HandleMailOpened(MailReadRespData data)
    {
        if (data.Result != MailReadResult.SUCCESS)
        {
            if (mailDetailText != null) mailDetailText.text = "Mail not found";
            return;
        }

        if (mailDetailText != null)
        {
            string detail = $"From: {data.SenderName}\nSubject: {data.Subject}\n\n{data.Body}";
            if (data.Gold > 0) detail += $"\n\nGold: {data.Gold}";
            if (data.ItemId > 0) detail += $"\nItem#{data.ItemId} x{data.ItemCount}";
            mailDetailText.text = detail;
        }

        if (claimButton != null)
            claimButton.gameObject.SetActive(data.Gold > 0 || data.ItemId > 0);
        if (deleteButton != null)
            deleteButton.gameObject.SetActive(true);
    }

    private void HandleMailClaimed(MailClaimResultData data)
    {
        if (data.Result == MailClaimResult.SUCCESS && claimButton != null)
            claimButton.gameObject.SetActive(false);
    }

    private void HandleMailDeleted(MailDeleteResultData data)
    {
        if (data.Result == MailDeleteResult.SUCCESS)
        {
            if (mailDetailText != null) mailDetailText.text = "";
            if (claimButton != null) claimButton.gameObject.SetActive(false);
            if (deleteButton != null) deleteButton.gameObject.SetActive(false);
        }
    }

    private void OnClaimClicked()
    {
        if (MailManager.Instance != null && MailManager.Instance.CurrentMail != null)
            MailManager.Instance.ClaimAttachment(MailManager.Instance.CurrentMail.MailId);
    }

    private void OnDeleteClicked()
    {
        if (MailManager.Instance != null && MailManager.Instance.CurrentMail != null)
            MailManager.Instance.DeleteMail(MailManager.Instance.CurrentMail.MailId);
    }
}
