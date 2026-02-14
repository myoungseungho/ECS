// ━━━ FriendUI.cs ━━━
// 친구 목록 UI — S051 TASK 5
// O키 토글, 온라인 상태 표시, 친구 요청 알림

using System;
using UnityEngine;
using UnityEngine.UI;

public class FriendUI : MonoBehaviour
{
    // ━━━ 싱글톤 ━━━
    public static FriendUI Instance { get; private set; }

    // ━━━ UI 참조 ━━━
    [SerializeField] private GameObject _panel;
    [SerializeField] private Text _titleText;
    [SerializeField] private Text _listText;
    [SerializeField] private Text _resultText;

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
        if (FriendManager.Instance != null)
        {
            FriendManager.Instance.OnFriendListChanged += HandleListChanged;
            FriendManager.Instance.OnFriendRequestResult += HandleRequestResult;
            FriendManager.Instance.OnPanelOpened += ShowPanel;
            FriendManager.Instance.OnPanelClosed += HidePanel;
        }
        if (_panel != null) _panel.SetActive(false);
    }

    private void Update()
    {
        if (Input.GetKeyDown(KeyCode.O))
        {
            if (FriendManager.Instance != null)
            {
                if (FriendManager.Instance.IsPanelOpen)
                    FriendManager.Instance.ClosePanel();
                else
                {
                    FriendManager.Instance.OpenPanel();
                    FriendManager.Instance.RefreshList();
                }
            }
        }
    }

    private void OnDestroy()
    {
        if (FriendManager.Instance != null)
        {
            FriendManager.Instance.OnFriendListChanged -= HandleListChanged;
            FriendManager.Instance.OnFriendRequestResult -= HandleRequestResult;
            FriendManager.Instance.OnPanelOpened -= ShowPanel;
            FriendManager.Instance.OnPanelClosed -= HidePanel;
        }
        if (Instance == this) Instance = null;
    }

    // ━━━ 이벤트 핸들러 ━━━

    private void HandleListChanged()
    {
        if (_listText == null) return;
        var mgr = FriendManager.Instance;
        if (mgr == null) return;

        var sb = new System.Text.StringBuilder();
        sb.AppendLine($"Friends: {mgr.Friends.Count}/{FriendManager.MAX_FRIENDS} (Online: {mgr.OnlineCount})");
        sb.AppendLine("────────────────────");

        foreach (var f in mgr.Friends)
        {
            string status = f.IsOnline ? "<color=green>[ON]</color>" : "<color=grey>[OFF]</color>";
            string zone = f.IsOnline ? $" Zone:{f.ZoneId}" : "";
            sb.AppendLine($"{status} {f.Name}{zone}");
        }

        _listText.text = sb.ToString();
    }

    private void HandleRequestResult(Network.FriendRequestResult result)
    {
        if (_resultText == null) return;

        if (result == Network.FriendRequestResult.SUCCESS)
        {
            _resultText.text = "Friend request sent!";
            _resultText.color = Color.cyan;
        }
        else
        {
            string msg = result switch
            {
                Network.FriendRequestResult.NOT_FOUND => "Player not found",
                Network.FriendRequestResult.ALREADY => "Already friends",
                Network.FriendRequestResult.BLOCKED => "Player is blocked",
                Network.FriendRequestResult.FULL => "Friend list full",
                Network.FriendRequestResult.SELF => "Cannot add yourself",
                _ => $"Error: {result}",
            };
            _resultText.text = msg;
            _resultText.color = Color.red;
        }
    }

    private void ShowPanel()
    {
        if (_panel != null) _panel.SetActive(true);
    }

    private void HidePanel()
    {
        if (_panel != null) _panel.SetActive(false);
    }
}
