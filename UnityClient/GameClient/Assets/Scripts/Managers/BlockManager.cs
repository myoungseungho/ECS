// ━━━ BlockManager.cs ━━━
// 차단 시스템 관리 — S051 TASK 5 (MsgType 416-419)
// 차단/해제/목록 관리

using System;
using System.Collections.Generic;
using UnityEngine;

public class BlockManager : MonoBehaviour
{
    // ━━━ 싱글톤 ━━━
    public static BlockManager Instance { get; private set; }

    // ━━━ 상수 ━━━
    public const int MAX_BLOCKED = 100;

    // ━━━ 상태 ━━━
    private List<string> _blockedNames = new List<string>();
    private bool _isPanelOpen;

    // ━━━ 프로퍼티 ━━━
    public IReadOnlyList<string> BlockedNames => _blockedNames;
    public bool IsPanelOpen => _isPanelOpen;

    // ━━━ 이벤트 ━━━
    public event Action OnBlockListChanged;
    public event Action<Network.BlockPlayerResult> OnBlockResultReceived;
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
            nm.OnBlockList += HandleBlockList;
            nm.OnBlockResult += HandleBlockResult;
        }
    }

    private void OnDestroy()
    {
        var nm = Network.NetworkManager.Instance;
        if (nm != null)
        {
            nm.OnBlockList -= HandleBlockList;
            nm.OnBlockResult -= HandleBlockResult;
        }
        if (Instance == this) Instance = null;
    }

    // ━━━ 이벤트 핸들러 ━━━

    private void HandleBlockList(Network.BlockListData data)
    {
        _blockedNames.Clear();
        if (data.Names != null)
            _blockedNames.AddRange(data.Names);
        OnBlockListChanged?.Invoke();
    }

    private void HandleBlockResult(Network.BlockPlayerResult result)
    {
        OnBlockResultReceived?.Invoke(result);
        if (result == Network.BlockPlayerResult.SUCCESS)
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
        Network.NetworkManager.Instance?.RequestBlockList();
    }

    public void BlockPlayer(string name)
    {
        Network.NetworkManager.Instance?.BlockPlayer(0, name);
    }

    public void UnblockPlayer(string name)
    {
        Network.NetworkManager.Instance?.BlockPlayer(1, name);
    }

    public bool IsBlocked(string name)
    {
        return _blockedNames.Contains(name);
    }
}
