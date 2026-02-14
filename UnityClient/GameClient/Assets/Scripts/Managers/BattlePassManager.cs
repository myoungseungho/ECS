// ━━━ BattlePassManager.cs ━━━
// 배틀패스 시스템 관리 — 시즌 정보/보상 수령/프리미엄 구매
// NetworkManager 이벤트 구독 → BattlePassUI에 이벤트 발행

using System;
using UnityEngine;
using Network;

public class BattlePassManager : MonoBehaviour
{
    // ━━━ 상태 ━━━
    private BattlePassInfoData _info;
    private bool _isPanelOpen;

    // ━━━ 프로퍼티 ━━━
    public BattlePassInfoData Info => _info;
    public bool IsPanelOpen => _isPanelOpen;
    public byte Level => _info != null ? _info.Level : (byte)0;
    public ushort Exp => _info != null ? _info.Exp : (ushort)0;
    public ushort MaxExp => _info != null ? _info.MaxExp : (ushort)0;
    public bool IsPremium => _info != null && _info.IsPremium;
    public float ExpRatio => _info != null && _info.MaxExp > 0 ? (float)_info.Exp / _info.MaxExp : 0f;

    // ━━━ 이벤트 ━━━
    public event Action<BattlePassInfoData> OnInfoUpdated;
    public event Action<BattlePassRewardResultData> OnRewardClaimed;
    public event Action<BattlePassBuyResultData> OnPremiumPurchased;
    public event Action OnPanelOpened;
    public event Action OnPanelClosed;

    // ━━━ 싱글톤 (Scene-bound) ━━━
    public static BattlePassManager Instance { get; private set; }

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
        net.OnBattlePassInfo += HandleBattlePassInfo;
        net.OnBattlePassRewardResult += HandleRewardResult;
        net.OnBattlePassBuyResult += HandleBuyResult;
    }

    private void OnDestroy()
    {
        var net = NetworkManager.Instance;
        if (net == null) return;

        net.OnBattlePassInfo -= HandleBattlePassInfo;
        net.OnBattlePassRewardResult -= HandleRewardResult;
        net.OnBattlePassBuyResult -= HandleBuyResult;

        if (Instance == this) Instance = null;
    }

    // ━━━ 공개 API ━━━

    public void OpenPanel()
    {
        _isPanelOpen = true;
        NetworkManager.Instance.RequestBattlePassInfo();
        OnPanelOpened?.Invoke();
    }

    public void ClosePanel()
    {
        _isPanelOpen = false;
        OnPanelClosed?.Invoke();
    }

    public void ClaimReward(byte level, BattlePassTrack track)
    {
        NetworkManager.Instance.ClaimBattlePassReward(level, (byte)track);
    }

    public void BuyPremium()
    {
        NetworkManager.Instance.BuyBattlePassPremium();
    }

    public void RefreshInfo()
    {
        NetworkManager.Instance.RequestBattlePassInfo();
    }

    // ━━━ 핸들러 ━━━

    private void HandleBattlePassInfo(BattlePassInfoData data)
    {
        _info = data;
        Debug.Log($"[BattlePassManager] Info: season={data.SeasonId}, lv={data.Level}, exp={data.Exp}/{data.MaxExp}, premium={data.IsPremium}");
        OnInfoUpdated?.Invoke(data);
    }

    private void HandleRewardResult(BattlePassRewardResultData data)
    {
        Debug.Log($"[BattlePassManager] Reward: result={data.Result}, lv={data.Level}, track={data.Track}");
        OnRewardClaimed?.Invoke(data);
    }

    private void HandleBuyResult(BattlePassBuyResultData data)
    {
        if (data.Result == 0 && _info != null)
            _info.IsPremium = true;

        Debug.Log($"[BattlePassManager] BuyPremium: result={data.Result}, crystals={data.RemainingCrystals}");
        OnPremiumPurchased?.Invoke(data);
    }
}
