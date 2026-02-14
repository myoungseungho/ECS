// ━━━ TeleportUI.cs ━━━
// 텔레포트 UI — 워프포인트 목록, 비용 표시, 텔레포트 확정 버튼
// TeleportManager 이벤트 구독 (;키 토글)

using System.Collections.Generic;
using UnityEngine;
using UnityEngine.UI;
using Network;

public class TeleportUI : MonoBehaviour
{
    [Header("UI References")]
    [SerializeField] private GameObject _panel;
    [SerializeField] private Text _titleText;
    [SerializeField] private Text _waypointListText;
    [SerializeField] private Text _selectedInfoText;
    [SerializeField] private Text _resultText;
    [SerializeField] private Button _teleportBtn;
    [SerializeField] private Button _refreshBtn;
    [SerializeField] private Button _closeBtn;

    private ushort _selectedWaypointId;
    private string _selectedWaypointName;
    private uint _selectedCost;

    private void Start()
    {
        var tm = TeleportManager.Instance;
        if (tm != null)
        {
            tm.OnWaypointsLoaded += HandleWaypointsLoaded;
            tm.OnTeleportComplete += HandleTeleportComplete;
            tm.OnPanelOpened += HandlePanelOpened;
            tm.OnPanelClosed += HandlePanelClosed;
        }

        if (_teleportBtn != null) _teleportBtn.onClick.AddListener(OnTeleportClick);
        if (_refreshBtn != null) _refreshBtn.onClick.AddListener(OnRefreshClick);
        if (_closeBtn != null) _closeBtn.onClick.AddListener(OnCloseClick);

        if (_panel != null)
            _panel.SetActive(false);
    }

    private void OnDestroy()
    {
        var tm = TeleportManager.Instance;
        if (tm == null) return;

        tm.OnWaypointsLoaded -= HandleWaypointsLoaded;
        tm.OnTeleportComplete -= HandleTeleportComplete;
        tm.OnPanelOpened -= HandlePanelOpened;
        tm.OnPanelClosed -= HandlePanelClosed;
    }

    private void Update()
    {
        // ;키로 텔레포트 패널 토글
        if (Input.GetKeyDown(KeyCode.Semicolon))
        {
            var tm = TeleportManager.Instance;
            if (tm == null) return;

            if (tm.IsPanelOpen)
                tm.ClosePanel();
            else
                tm.OpenPanel();
        }

        // ESC로 닫기
        if (_panel != null && _panel.activeSelf && Input.GetKeyDown(KeyCode.Escape))
        {
            TeleportManager.Instance?.ClosePanel();
        }
    }

    // ━━━ 버튼 핸들러 ━━━

    private void OnTeleportClick()
    {
        if (_selectedWaypointId == 0) return;
        TeleportManager.Instance?.Teleport(_selectedWaypointId);
    }

    private void OnRefreshClick()
    {
        TeleportManager.Instance?.RefreshWaypoints();
    }

    private void OnCloseClick()
    {
        TeleportManager.Instance?.ClosePanel();
    }

    // ━━━ 이벤트 핸들러 ━━━

    private void HandlePanelOpened()
    {
        if (_panel != null)
            _panel.SetActive(true);

        if (_resultText != null)
            _resultText.text = "";

        _selectedWaypointId = 0;
        UpdateSelectedInfo();
    }

    private void HandlePanelClosed()
    {
        if (_panel != null)
            _panel.SetActive(false);
    }

    private void HandleWaypointsLoaded(WaypointInfo[] waypoints)
    {
        if (_titleText != null)
            _titleText.text = $"Teleport ({waypoints.Length} waypoints)";

        RefreshWaypointList(waypoints);

        // 첫 번째 워프포인트 자동 선택
        if (waypoints.Length > 0)
        {
            _selectedWaypointId = waypoints[0].WaypointId;
            _selectedWaypointName = waypoints[0].Name;
            _selectedCost = waypoints[0].Cost;
        }
        else
        {
            _selectedWaypointId = 0;
            _selectedWaypointName = "";
            _selectedCost = 0;
        }

        UpdateSelectedInfo();
    }

    private void HandleTeleportComplete(TeleportResultData data)
    {
        if (_resultText == null) return;

        if (data.Result == TeleportResult.SUCCESS)
        {
            _resultText.text = "Teleport successful!";
        }
        else
        {
            string reason = data.Result switch
            {
                TeleportResult.WAYPOINT_NOT_FOUND => "Waypoint not found",
                TeleportResult.NOT_ENOUGH_GOLD => "Not enough gold",
                TeleportResult.IN_COMBAT => "Cannot teleport in combat",
                TeleportResult.COOLDOWN => "Teleport on cooldown",
                _ => $"Failed: {data.Result}"
            };
            _resultText.text = reason;
        }
    }

    // ━━━ UI 갱신 ━━━

    private void RefreshWaypointList(WaypointInfo[] waypoints)
    {
        if (_waypointListText == null) return;

        var sb = new System.Text.StringBuilder();
        sb.AppendLine("--- World Map ---");
        sb.AppendLine();

        for (int i = 0; i < waypoints.Length; i++)
        {
            var wp = waypoints[i];
            string marker = (wp.WaypointId == _selectedWaypointId) ? ">" : " ";
            sb.AppendLine($"{marker} [{wp.WaypointId}] {wp.Name} (Zone {wp.ZoneId}) - {wp.Cost}G");
        }

        if (waypoints.Length == 0)
        {
            sb.AppendLine("  No waypoints discovered.");
        }

        _waypointListText.text = sb.ToString();
    }

    private void UpdateSelectedInfo()
    {
        if (_selectedInfoText == null) return;

        if (_selectedWaypointId == 0)
        {
            _selectedInfoText.text = "Select a waypoint";
            if (_teleportBtn != null) _teleportBtn.interactable = false;
            return;
        }

        _selectedInfoText.text = $"Selected: {_selectedWaypointName}\nCost: {_selectedCost}G";
        if (_teleportBtn != null) _teleportBtn.interactable = true;
    }

    /// <summary>외부에서 워프포인트 선택 (목록 클릭 등)</summary>
    public void SelectWaypoint(ushort waypointId)
    {
        var tm = TeleportManager.Instance;
        if (tm == null) return;

        foreach (var wp in tm.Waypoints)
        {
            if (wp.WaypointId == waypointId)
            {
                _selectedWaypointId = wp.WaypointId;
                _selectedWaypointName = wp.Name;
                _selectedCost = wp.Cost;
                UpdateSelectedInfo();

                // 목록 리프레시 (선택 마커 갱신)
                var arr = new WaypointInfo[tm.Waypoints.Count];
                for (int i = 0; i < tm.Waypoints.Count; i++)
                    arr[i] = tm.Waypoints[i];
                RefreshWaypointList(arr);
                return;
            }
        }
    }
}
