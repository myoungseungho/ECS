// ━━━ BlockUI.cs ━━━
// 차단 목록 UI — S051 TASK 5
// Shift+B키 토글, 차단/해제 관리

using System;
using UnityEngine;
using UnityEngine.UI;

public class BlockUI : MonoBehaviour
{
    // ━━━ 싱글톤 ━━━
    public static BlockUI Instance { get; private set; }

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
        if (BlockManager.Instance != null)
        {
            BlockManager.Instance.OnBlockListChanged += HandleListChanged;
            BlockManager.Instance.OnBlockResultReceived += HandleBlockResult;
            BlockManager.Instance.OnPanelOpened += ShowPanel;
            BlockManager.Instance.OnPanelClosed += HidePanel;
        }
        if (_panel != null) _panel.SetActive(false);
    }

    private void Update()
    {
        if (Input.GetKey(KeyCode.LeftShift) && Input.GetKeyDown(KeyCode.B))
        {
            if (BlockManager.Instance != null)
            {
                if (BlockManager.Instance.IsPanelOpen)
                    BlockManager.Instance.ClosePanel();
                else
                {
                    BlockManager.Instance.OpenPanel();
                    BlockManager.Instance.RefreshList();
                }
            }
        }
    }

    private void OnDestroy()
    {
        if (BlockManager.Instance != null)
        {
            BlockManager.Instance.OnBlockListChanged -= HandleListChanged;
            BlockManager.Instance.OnBlockResultReceived -= HandleBlockResult;
            BlockManager.Instance.OnPanelOpened -= ShowPanel;
            BlockManager.Instance.OnPanelClosed -= HidePanel;
        }
        if (Instance == this) Instance = null;
    }

    // ━━━ 이벤트 핸들러 ━━━

    private void HandleListChanged()
    {
        if (_listText == null) return;
        var mgr = BlockManager.Instance;
        if (mgr == null) return;

        var sb = new System.Text.StringBuilder();
        sb.AppendLine($"Blocked: {mgr.BlockedNames.Count}/{BlockManager.MAX_BLOCKED}");
        sb.AppendLine("────────────────────");

        foreach (var name in mgr.BlockedNames)
        {
            sb.AppendLine($"  <color=red>[X]</color> {name}");
        }

        if (mgr.BlockedNames.Count == 0)
            sb.AppendLine("  (No blocked players)");

        _listText.text = sb.ToString();
    }

    private void HandleBlockResult(Network.BlockPlayerResult result)
    {
        if (_resultText == null) return;

        if (result == Network.BlockPlayerResult.SUCCESS)
        {
            _resultText.text = "Block list updated!";
            _resultText.color = Color.cyan;
        }
        else
        {
            string msg = result switch
            {
                Network.BlockPlayerResult.ALREADY => "Already blocked",
                Network.BlockPlayerResult.NOT_BLOCKED => "Player not blocked",
                Network.BlockPlayerResult.FULL => "Block list full",
                Network.BlockPlayerResult.SELF => "Cannot block yourself",
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
