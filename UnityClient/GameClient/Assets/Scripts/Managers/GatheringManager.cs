// ━━━ GatheringManager.cs ━━━
// 채집 시스템 관리 (S043 TASK 2)
// MsgType: 384-385 (채집 시작/결과)

using System;
using UnityEngine;

public class GatheringManager : MonoBehaviour
{
    // ━━━ 싱글톤 ━━━
    public static GatheringManager Instance { get; private set; }

    // ━━━ 상태 ━━━
    private byte _energy = 200;
    private bool _isGathering;
    private float _gatherTimer;
    private byte _currentGatherType;
    private bool _isPanelOpen;

    // ━━━ 채집 타입 (S043: 1=herb, 2=mining, 3=logging) ━━━
    public const byte GATHER_HERB = 1;
    public const byte GATHER_MINING = 2;
    public const byte GATHER_LOGGING = 3;

    // ━━━ 채집 시간 (GDD 기준) ━━━
    private static readonly float[] GatherTimes = { 0f, 3.0f, 5.0f, 4.0f };

    // ━━━ 프로퍼티 ━━━
    public byte Energy => _energy;
    public byte MaxEnergy => 200;
    public bool IsGathering => _isGathering;
    public bool IsPanelOpen => _isPanelOpen;
    public float GatherProgress => _isGathering && _currentGatherType < GatherTimes.Length
        ? Mathf.Clamp01(_gatherTimer / GatherTimes[_currentGatherType])
        : 0f;

    // ━━━ 이벤트 ━━━
    public event Action<Network.GatherResultData> OnGatherComplete;
    public event Action OnGatherStarted;
    public event Action OnEnergyChanged;
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
            nm.OnGatherResult += HandleGatherResult;
        }
    }

    private void OnDestroy()
    {
        var nm = Network.NetworkManager.Instance;
        if (nm != null)
        {
            nm.OnGatherResult -= HandleGatherResult;
        }
        if (Instance == this) Instance = null;
    }

    private void Update()
    {
        if (_isGathering)
        {
            _gatherTimer += Time.deltaTime;
        }
    }

    // ━━━ 핸들러 ━━━

    private void HandleGatherResult(Network.GatherResultData data)
    {
        _isGathering = false;
        _gatherTimer = 0f;
        _energy = data.Energy;
        OnEnergyChanged?.Invoke();
        OnGatherComplete?.Invoke(data);
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

    public void Gather(byte gatherType)
    {
        if (_isGathering) return;
        if (_energy < 5) return;

        _isGathering = true;
        _gatherTimer = 0f;
        _currentGatherType = gatherType;
        OnGatherStarted?.Invoke();
        Network.NetworkManager.Instance?.StartGather(gatherType);
    }

    public string GetGatherName(byte gatherType)
    {
        switch (gatherType)
        {
            case GATHER_HERB:    return "Herbalism";
            case GATHER_MINING:  return "Mining";
            case GATHER_LOGGING: return "Logging";
            default:             return "Unknown";
        }
    }
}
