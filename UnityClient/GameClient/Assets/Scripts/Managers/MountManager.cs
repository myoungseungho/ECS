// ━━━ MountManager.cs ━━━
// 탈것 시스템 관리 — 소환/해제, 이동 속도 배율 추적
// NetworkManager 이벤트 구독 → MountUI에 이벤트 발행

using System;
using UnityEngine;
using Network;

public class MountManager : MonoBehaviour
{
    // ━━━ 상태 ━━━
    private bool _isMounted;
    private uint _currentMountId;
    private float _speedMultiplier = 1f;
    private bool _isPanelOpen;

    // ━━━ 계산 프로퍼티 ━━━
    public bool IsMounted => _isMounted;
    public uint CurrentMountId => _currentMountId;
    public float SpeedMultiplier => _speedMultiplier;
    public bool IsPanelOpen => _isPanelOpen;

    // ━━━ 이벤트 ━━━
    public event Action<MountResultData> OnMounted;
    public event Action OnDismounted;
    public event Action OnPanelOpened;
    public event Action OnPanelClosed;

    // ━━━ 싱글톤 (Scene-bound) ━━━
    public static MountManager Instance { get; private set; }

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
        net.OnMountResult += HandleMountResult;
        net.OnMountDismountResult += HandleDismountResult;
    }

    private void OnDestroy()
    {
        var net = NetworkManager.Instance;
        if (net == null) return;

        net.OnMountResult -= HandleMountResult;
        net.OnMountDismountResult -= HandleDismountResult;

        if (Instance == this) Instance = null;
    }

    // ━━━ 공개 API ━━━

    /// <summary>탈것 패널 열기</summary>
    public void OpenPanel()
    {
        _isPanelOpen = true;
        OnPanelOpened?.Invoke();
    }

    /// <summary>탈것 패널 닫기</summary>
    public void ClosePanel()
    {
        _isPanelOpen = false;
        OnPanelClosed?.Invoke();
    }

    /// <summary>탈것 소환</summary>
    public void Summon(uint mountId)
    {
        if (_isMounted) return;
        NetworkManager.Instance.SummonMount(mountId);
    }

    /// <summary>탈것 내리기</summary>
    public void Dismount()
    {
        if (!_isMounted) return;
        NetworkManager.Instance.DismountMount();
    }

    // ━━━ 핸들러 ━━━

    private void HandleMountResult(MountResultData data)
    {
        if (data.Result == MountResult.SUCCESS)
        {
            _isMounted = true;
            _currentMountId = data.MountId;
            _speedMultiplier = data.SpeedMultiplied / 100f;

            Debug.Log($"[MountManager] Mounted: id={data.MountId}, speed={_speedMultiplier}x");
            OnMounted?.Invoke(data);
        }
        else
        {
            Debug.Log($"[MountManager] Mount failed: {data.Result}");
        }
    }

    private void HandleDismountResult(byte result)
    {
        if (result == 0) // SUCCESS
        {
            _isMounted = false;
            _currentMountId = 0;
            _speedMultiplier = 1f;

            Debug.Log("[MountManager] Dismounted");
            OnDismounted?.Invoke();
        }
        else
        {
            Debug.Log($"[MountManager] Dismount failed: result={result}");
        }
    }
}
