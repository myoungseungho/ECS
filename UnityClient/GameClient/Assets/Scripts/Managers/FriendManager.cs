// ━━━ FriendManager.cs ━━━
// 친구 시스템 관리 — S051 TASK 5 (MsgType 410-415)
// 친구 요청/수락/거절/목록 관리

using System;
using System.Collections.Generic;
using UnityEngine;

public class FriendManager : MonoBehaviour
{
    // ━━━ 싱글톤 ━━━
    public static FriendManager Instance { get; private set; }

    // ━━━ 상수 ━━━
    public const int MAX_FRIENDS = 100;

    // ━━━ 상태 ━━━
    private List<Network.FriendInfo> _friends = new List<Network.FriendInfo>();
    private bool _isPanelOpen;

    // ━━━ 프로퍼티 ━━━
    public IReadOnlyList<Network.FriendInfo> Friends => _friends;
    public bool IsPanelOpen => _isPanelOpen;
    public int OnlineCount
    {
        get
        {
            int count = 0;
            for (int i = 0; i < _friends.Count; i++)
                if (_friends[i].IsOnline) count++;
            return count;
        }
    }

    // ━━━ 이벤트 ━━━
    public event Action OnFriendListChanged;
    public event Action<Network.FriendRequestResult> OnFriendRequestResult;
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
        var nm = Network.NetworkManager.Instance;
        if (nm != null)
        {
            nm.OnFriendList += HandleFriendList;
            nm.OnFriendRequestResult += HandleFriendRequestResult;
        }
    }

    private void OnDestroy()
    {
        var nm = Network.NetworkManager.Instance;
        if (nm != null)
        {
            nm.OnFriendList -= HandleFriendList;
            nm.OnFriendRequestResult -= HandleFriendRequestResult;
        }
        if (Instance == this) Instance = null;
    }

    // ━━━ 이벤트 핸들러 ━━━

    private void HandleFriendList(Network.FriendListData data)
    {
        _friends.Clear();
        if (data.Friends != null)
            _friends.AddRange(data.Friends);
        OnFriendListChanged?.Invoke();
    }

    private void HandleFriendRequestResult(Network.FriendRequestResult result)
    {
        OnFriendRequestResult?.Invoke(result);
        if (result == Network.FriendRequestResult.SUCCESS)
            RefreshList();
    }

    // ━━━ 공개 API ━━━

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

    public void RefreshList()
    {
        Network.NetworkManager.Instance?.RequestFriendList();
    }

    public void SendFriendRequest(string targetName)
    {
        Network.NetworkManager.Instance?.RequestFriend(targetName);
    }

    public void AcceptFriend(string fromName)
    {
        Network.NetworkManager.Instance?.AcceptFriend(fromName);
    }

    public void RejectFriend(string fromName)
    {
        Network.NetworkManager.Instance?.RejectFriend(fromName);
    }

    public Network.FriendInfo GetFriend(string name)
    {
        for (int i = 0; i < _friends.Count; i++)
            if (_friends[i].Name == name) return _friends[i];
        return null;
    }
}
