// ━━━ MailManager.cs ━━━
// 우편 시스템 관리 — 발송/목록/읽기/수령/삭제
// NetworkManager 이벤트 구독 → MailUI에 이벤트 발행

using System;
using System.Collections.Generic;
using UnityEngine;
using Network;

public class MailManager : MonoBehaviour
{
    // ━━━ 상태 ━━━
    public bool IsMailboxOpen { get; private set; }
    private readonly List<MailListEntry> _mails = new List<MailListEntry>();
    public IReadOnlyList<MailListEntry> Mails => _mails;

    // ━━━ 이벤트 ━━━
    public event Action OnMailListChanged;
    public event Action<MailReadData> OnMailOpened;
    public event Action<MailClaimResultData> OnClaimResult;
    public event Action<MailDeleteResultData> OnDeleteResult;

    // ━━━ 싱글톤 (Scene-bound) ━━━
    public static MailManager Instance { get; private set; }

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
        net.OnMailList += HandleMailList;
        net.OnMailRead += HandleMailRead;
        net.OnMailClaimResult += HandleMailClaimResult;
        net.OnMailDeleteResult += HandleMailDeleteResult;
    }

    private void OnDestroy()
    {
        var net = NetworkManager.Instance;
        if (net == null) return;

        net.OnMailList -= HandleMailList;
        net.OnMailRead -= HandleMailRead;
        net.OnMailClaimResult -= HandleMailClaimResult;
        net.OnMailDeleteResult -= HandleMailDeleteResult;

        if (Instance == this) Instance = null;
    }

    // ━━━ 공개 API ━━━

    /// <summary>우편 발송</summary>
    public void SendMail(string recipient, string title, string body, uint gold = 0, uint itemId = 0, ushort itemCount = 0)
    {
        NetworkManager.Instance.SendMail(recipient, title, body, gold, itemId, itemCount);
    }

    /// <summary>우편함 열기 (목록 요청)</summary>
    public void OpenMailbox()
    {
        IsMailboxOpen = true;
        NetworkManager.Instance.RequestMailList();
    }

    /// <summary>우편함 닫기</summary>
    public void CloseMailbox()
    {
        IsMailboxOpen = false;
    }

    /// <summary>우편 읽기</summary>
    public void ReadMail(uint mailId)
    {
        NetworkManager.Instance.ReadMail(mailId);
    }

    /// <summary>첨부물 수령</summary>
    public void ClaimMail(uint mailId)
    {
        NetworkManager.Instance.ClaimMail(mailId);
    }

    /// <summary>우편 삭제</summary>
    public void DeleteMail(uint mailId)
    {
        NetworkManager.Instance.DeleteMail(mailId);
    }

    /// <summary>우편함 새로고침</summary>
    public void RefreshMailbox()
    {
        NetworkManager.Instance.RequestMailList();
    }

    // ━━━ 핸들러 ━━━

    private void HandleMailList(MailListEntry[] mails)
    {
        _mails.Clear();
        _mails.AddRange(mails);

        Debug.Log($"[MailManager] Mail list: {mails.Length} mails");
        OnMailListChanged?.Invoke();
    }

    private void HandleMailRead(MailReadData data)
    {
        Debug.Log($"[MailManager] Mail read: id={data.MailId}, from={data.Sender}");
        OnMailOpened?.Invoke(data);
    }

    private void HandleMailClaimResult(MailClaimResultData data)
    {
        Debug.Log($"[MailManager] Mail claim: result={data.Result}, id={data.MailId}");
        OnClaimResult?.Invoke(data);

        if (data.Result == MailClaimResult.SUCCESS)
            RefreshMailbox();
    }

    private void HandleMailDeleteResult(MailDeleteResultData data)
    {
        Debug.Log($"[MailManager] Mail delete: result={data.Result}, id={data.MailId}");
        OnDeleteResult?.Invoke(data);

        if (data.Result == MailDeleteResult.SUCCESS)
            RefreshMailbox();
    }
}
