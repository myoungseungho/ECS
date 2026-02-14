// ━━━ MailManager.cs ━━━
// 우편 시스템 관리 — 발송, 목록, 읽기, 첨부 수령, 삭제
// T031: MsgType 310-318

using System;
using System.Collections.Generic;
using UnityEngine;
using Network;

public class MailManager : MonoBehaviour
{
    // ━━━ 싱글톤 ━━━
    public static MailManager Instance { get; private set; }

    // ━━━ 상태 ━━━
    private List<MailListEntry> _mails = new List<MailListEntry>();
    private MailReadRespData _currentMail;

    // ━━━ 이벤트 ━━━
    public event Action OnMailListChanged;
    public event Action<MailReadRespData> OnMailOpened;
    public event Action<MailClaimResultData> OnMailClaimed;
    public event Action<MailDeleteResultData> OnMailDeleted;

    // ━━━ 공개 프로퍼티 ━━━
    public IReadOnlyList<MailListEntry> Mails => _mails;
    public MailReadRespData CurrentMail => _currentMail;
    public int UnreadCount
    {
        get
        {
            int count = 0;
            for (int i = 0; i < _mails.Count; i++)
                if (!_mails[i].IsRead) count++;
            return count;
        }
    }

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
            net.OnMailList += HandleMailList;
            net.OnMailReadResp += HandleMailReadResp;
            net.OnMailClaimResult += HandleMailClaimResult;
            net.OnMailDeleteResult += HandleMailDeleteResult;
            net.OnEnterGame += HandleEnterGame;
        }
    }

    private void OnDestroy()
    {
        var net = NetworkManager.Instance;
        if (net != null)
        {
            net.OnMailList -= HandleMailList;
            net.OnMailReadResp -= HandleMailReadResp;
            net.OnMailClaimResult -= HandleMailClaimResult;
            net.OnMailDeleteResult -= HandleMailDeleteResult;
            net.OnEnterGame -= HandleEnterGame;
        }
        if (Instance == this) Instance = null;
    }

    // ━━━ 이벤트 핸들러 ━━━

    private void HandleEnterGame(EnterGameResult result)
    {
        if (result.ResultCode == 0)
            NetworkManager.Instance.RequestMailList();
    }

    private void HandleMailList(MailListEntry[] data)
    {
        _mails.Clear();
        _mails.AddRange(data);
        OnMailListChanged?.Invoke();
    }

    private void HandleMailReadResp(MailReadRespData data)
    {
        _currentMail = data;
        if (data.Result == MailReadResult.SUCCESS)
        {
            for (int i = 0; i < _mails.Count; i++)
            {
                if (_mails[i].MailId == data.MailId)
                {
                    _mails[i].IsRead = true;
                    break;
                }
            }
        }
        OnMailOpened?.Invoke(data);
    }

    private void HandleMailClaimResult(MailClaimResultData data)
    {
        if (data.Result == MailClaimResult.SUCCESS)
        {
            for (int i = 0; i < _mails.Count; i++)
            {
                if (_mails[i].MailId == data.MailId)
                {
                    _mails[i].HasAttachment = false;
                    break;
                }
            }
        }
        OnMailClaimed?.Invoke(data);
    }

    private void HandleMailDeleteResult(MailDeleteResultData data)
    {
        if (data.Result == MailDeleteResult.SUCCESS)
        {
            for (int i = _mails.Count - 1; i >= 0; i--)
            {
                if (_mails[i].MailId == data.MailId)
                {
                    _mails.RemoveAt(i);
                    break;
                }
            }
            OnMailListChanged?.Invoke();
        }
        OnMailDeleted?.Invoke(data);
    }

    // ━━━ 공개 API ━━━

    public void SendMail(string recipient, string subject, string body, uint gold = 0, uint itemId = 0, ushort itemCount = 0)
    {
        NetworkManager.Instance.SendMail(recipient, subject, body, gold, itemId, itemCount);
    }

    public void RefreshList() { NetworkManager.Instance.RequestMailList(); }
    public void ReadMail(uint mailId) { NetworkManager.Instance.ReadMail(mailId); }
    public void ClaimAttachment(uint mailId) { NetworkManager.Instance.ClaimMail(mailId); }
    public void DeleteMail(uint mailId) { NetworkManager.Instance.DeleteMail(mailId); }
}
