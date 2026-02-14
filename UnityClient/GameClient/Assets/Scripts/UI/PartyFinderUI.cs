// ━━━ PartyFinderUI.cs ━━━
// 파티 찾기 UI — S051 TASK 5
// Y키 토글, 카테고리 필터 + 등록 + 목록

using System;
using UnityEngine;
using UnityEngine.UI;

public class PartyFinderUI : MonoBehaviour
{
    // ━━━ 싱글톤 ━━━
    public static PartyFinderUI Instance { get; private set; }

    // ━━━ UI 참조 ━━━
    [SerializeField] private GameObject _panel;
    [SerializeField] private Text _titleText;
    [SerializeField] private Text _listText;
    [SerializeField] private Text _filterText;

    private static readonly string[] CategoryNames = { "Dungeon", "Raid", "Field", "Quest", "Other" };
    private static readonly string[] RoleNames = { "Any", "Tank", "DPS", "Support" };

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
        if (PartyFinderManager.Instance != null)
        {
            PartyFinderManager.Instance.OnListingsChanged += HandleListingsChanged;
            PartyFinderManager.Instance.OnPanelOpened += ShowPanel;
            PartyFinderManager.Instance.OnPanelClosed += HidePanel;
        }
        if (_panel != null) _panel.SetActive(false);
    }

    private void Update()
    {
        if (Input.GetKeyDown(KeyCode.Y))
        {
            if (PartyFinderManager.Instance != null)
            {
                if (PartyFinderManager.Instance.IsPanelOpen)
                    PartyFinderManager.Instance.ClosePanel();
                else
                {
                    PartyFinderManager.Instance.OpenPanel();
                    PartyFinderManager.Instance.RefreshList();
                }
            }
        }
    }

    private void OnDestroy()
    {
        if (PartyFinderManager.Instance != null)
        {
            PartyFinderManager.Instance.OnListingsChanged -= HandleListingsChanged;
            PartyFinderManager.Instance.OnPanelOpened -= ShowPanel;
            PartyFinderManager.Instance.OnPanelClosed -= HidePanel;
        }
        if (Instance == this) Instance = null;
    }

    // ━━━ 이벤트 핸들러 ━━━

    private void HandleListingsChanged()
    {
        if (_listText == null) return;
        var mgr = PartyFinderManager.Instance;
        if (mgr == null) return;

        byte filter = mgr.CurrentCategoryFilter;
        string filterName = filter == 0xFF ? "All" : (filter < CategoryNames.Length ? CategoryNames[filter] : "?");

        var sb = new System.Text.StringBuilder();
        sb.AppendLine($"Party Finder  [Filter: {filterName}]  ({mgr.Listings.Count} listings)");
        sb.AppendLine("────────────────────────────────────");

        if (mgr.Listings.Count == 0)
        {
            sb.AppendLine("  (No listings found)");
        }
        else
        {
            foreach (var l in mgr.Listings)
            {
                string cat = (byte)l.Category < CategoryNames.Length ? CategoryNames[(byte)l.Category] : "?";
                string role = (byte)l.Role < RoleNames.Length ? RoleNames[(byte)l.Role] : "?";
                sb.AppendLine($"  [{cat}] {l.Title}");
                sb.AppendLine($"    Owner: {l.OwnerName}  Lv{l.MinLevel}+  Role: {role}");
            }
        }

        _listText.text = sb.ToString();

        if (_filterText != null)
            _filterText.text = $"Filter: {filterName}";
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
