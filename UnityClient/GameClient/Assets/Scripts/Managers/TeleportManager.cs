// ━━━ TeleportManager.cs ━━━
// 텔레포트(워프포인트) 시스템 관리 — 목록 요청/텔레포트 실행/패널 토글
// NetworkManager 이벤트 구독 → TeleportUI에 이벤트 발행

using System;
using System.Collections.Generic;
using UnityEngine;
using Network;

public class TeleportManager : MonoBehaviour
{
    // ━━━ 상태 ━━━
    private List<WaypointInfo> _waypoints = new List<WaypointInfo>();
    private bool _isPanelOpen;

    // ━━━ 계산 프로퍼티 ━━━
    public IReadOnlyList<WaypointInfo> Waypoints => _waypoints;
    public bool IsPanelOpen => _isPanelOpen;

    // ━━━ 이벤트 ━━━
    public event Action<WaypointInfo[]> OnWaypointsLoaded;
    public event Action<TeleportResultData> OnTeleportComplete;
    public event Action OnPanelOpened;
    public event Action OnPanelClosed;

    // ━━━ 싱글톤 (Scene-bound) ━━━
    public static TeleportManager Instance { get; private set; }

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
        net.OnTeleportList += HandleTeleportList;
        net.OnTeleportResult += HandleTeleportResult;
    }

    private void OnDestroy()
    {
        var net = NetworkManager.Instance;
        if (net == null) return;

        net.OnTeleportList -= HandleTeleportList;
        net.OnTeleportResult -= HandleTeleportResult;

        if (Instance == this) Instance = null;
    }

    // ━━━ 공개 API ━━━

    /// <summary>텔레포트 패널 열기</summary>
    public void OpenPanel()
    {
        _isPanelOpen = true;
        RefreshWaypoints();
        OnPanelOpened?.Invoke();
    }

    /// <summary>텔레포트 패널 닫기</summary>
    public void ClosePanel()
    {
        _isPanelOpen = false;
        OnPanelClosed?.Invoke();
    }

    /// <summary>워프포인트 목록 갱신 요청</summary>
    public void RefreshWaypoints()
    {
        NetworkManager.Instance.RequestTeleportList();
    }

    /// <summary>특정 워프포인트로 텔레포트 요청</summary>
    public void Teleport(ushort waypointId)
    {
        NetworkManager.Instance.RequestTeleport(waypointId);
    }

    // ━━━ 핸들러 ━━━

    private void HandleTeleportList(WaypointInfo[] waypoints)
    {
        _waypoints.Clear();
        _waypoints.AddRange(waypoints);

        Debug.Log($"[TeleportManager] Loaded {waypoints.Length} waypoints");
        OnWaypointsLoaded?.Invoke(waypoints);
    }

    private void HandleTeleportResult(TeleportResultData data)
    {
        Debug.Log($"[TeleportManager] Teleport result: {data.Result}, zone={data.ZoneId}");

        if (data.Result == TeleportResult.SUCCESS)
        {
            // 성공 시 패널 닫기
            ClosePanel();
        }

        OnTeleportComplete?.Invoke(data);
    }
}
