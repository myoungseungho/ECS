// ━━━ AttendanceManager.cs ━━━
// 출석 시스템 관리 — 출석 정보, 보상 수령, 일일/주간 리셋, 로그인 보상
// NetworkManager 이벤트 구독 → AttendanceUI에 이벤트 발행

using System;
using UnityEngine;
using Network;

public class AttendanceManager : MonoBehaviour
{
    // ━━━ 상태 ━━━
    private AttendanceInfoData _info;
    private bool _isPanelOpen;

    // ━━━ 이벤트 ━━━
    public event Action<AttendanceInfoData> OnInfoUpdated;
    public event Action<AttendanceClaimResultData> OnRewardClaimed;
    public event Action<DailyResetNotifyData> OnDailyReset;
    public event Action<LoginRewardNotifyData> OnLoginReward;
    public event Action OnPanelOpened;
    public event Action OnPanelClosed;

    // ━━━ 싱글톤 (Scene-bound) ━━━
    public static AttendanceManager Instance { get; private set; }

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
        net.OnAttendanceInfo += HandleAttendanceInfo;
        net.OnAttendanceClaimResult += HandleAttendanceClaimResult;
        net.OnDailyResetNotify += HandleDailyResetNotify;
        net.OnLoginRewardNotify += HandleLoginRewardNotify;
        net.OnEnterGame += HandleEnterGame;
    }

    private void OnDestroy()
    {
        var net = NetworkManager.Instance;
        if (net == null) return;

        net.OnAttendanceInfo -= HandleAttendanceInfo;
        net.OnAttendanceClaimResult -= HandleAttendanceClaimResult;
        net.OnDailyResetNotify -= HandleDailyResetNotify;
        net.OnLoginRewardNotify -= HandleLoginRewardNotify;
        net.OnEnterGame -= HandleEnterGame;

        if (Instance == this) Instance = null;
    }

    // ━━━ 공개 API ━━━

    /// <summary>출석 패널 열기</summary>
    public void OpenPanel()
    {
        _isPanelOpen = true;
        OnPanelOpened?.Invoke();
    }

    /// <summary>출석 패널 닫기</summary>
    public void ClosePanel()
    {
        _isPanelOpen = false;
        OnPanelClosed?.Invoke();
    }

    /// <summary>출석 보상 수령</summary>
    public void ClaimDay(byte day)
    {
        NetworkManager.Instance.ClaimAttendance(day);
    }

    /// <summary>출석 정보 갱신 요청</summary>
    public void RefreshInfo()
    {
        NetworkManager.Instance.RequestAttendanceInfo();
    }

    // ━━━ 계산 프로퍼티 ━━━

    /// <summary>현재 출석 정보 데이터</summary>
    public AttendanceInfoData Info => _info;

    /// <summary>패널 열림 여부</summary>
    public bool IsPanelOpen => _isPanelOpen;

    /// <summary>현재 출석 일차 (1-based)</summary>
    public byte CurrentDay => _info != null ? _info.CurrentDay : (byte)0;

    /// <summary>총 출석 일수</summary>
    public byte TotalDays => _info != null ? _info.TotalDays : (byte)0;

    // ━━━ 핸들러 ━━━

    private void HandleAttendanceInfo(AttendanceInfoData data)
    {
        _info = data;
        Debug.Log($"[AttendanceManager] Info: day={data.CurrentDay}, total={data.TotalDays}");
        OnInfoUpdated?.Invoke(data);
    }

    private void HandleAttendanceClaimResult(AttendanceClaimResultData data)
    {
        if (data.Result == AttendanceClaimResult.SUCCESS && _info != null)
        {
            // 로컬 상태 갱신: 해당 일차를 수령 완료로 표시
            if (_info.Claimed != null && data.Day > 0 && data.Day <= _info.Claimed.Length)
                _info.Claimed[data.Day - 1] = true;
        }

        Debug.Log($"[AttendanceManager] Claim: result={data.Result}, day={data.Day}, reward={data.RewardType}:{data.RewardId}x{data.RewardCount}");
        OnRewardClaimed?.Invoke(data);
    }

    private void HandleDailyResetNotify(DailyResetNotifyData data)
    {
        Debug.Log($"[AttendanceManager] DailyReset: type={data.Type}");
        OnDailyReset?.Invoke(data);

        // 리셋 후 출석 정보 자동 갱신
        RefreshInfo();
    }

    private void HandleLoginRewardNotify(LoginRewardNotifyData data)
    {
        Debug.Log($"[AttendanceManager] LoginReward: type={data.RewardType}, id={data.RewardId}, count={data.RewardCount}");
        OnLoginReward?.Invoke(data);
    }

    private void HandleEnterGame(EnterGameResult result)
    {
        if (result.ResultCode != 0) return;

        // 게임 진입 시 출석 정보 자동 요청
        NetworkManager.Instance.RequestAttendanceInfo();
    }
}
