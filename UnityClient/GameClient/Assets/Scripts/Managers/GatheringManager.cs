// ━━━ GatheringManager.cs ━━━
// 채집 시스템 관리 (S041 TASK 2)
// MsgType: 384-385 (채집 시작/결과)

using System;
using UnityEngine;

public class GatheringManager : MonoBehaviour
{
    // ━━━ 싱글톤 ━━━
    public static GatheringManager Instance { get; private set; }

    // ━━━ 상태 ━━━
    private ushort _energy = 200;
    private bool _isGathering;
    private float _gatherTimer;
    private byte _currentNodeType;
    private bool _isPanelOpen;

    // ━━━ 채집 노드 타입 ━━━
    public const byte NODE_HERB = 0;
    public const byte NODE_ORE = 1;
    public const byte NODE_WOOD = 2;
    public const byte NODE_FISH = 3;

    // ━━━ 채집 시간 (GDD 기준) ━━━
    private static readonly float[] GatherTimes = { 3.0f, 5.0f, 4.0f, 4.0f };

    // ━━━ 프로퍼티 ━━━
    public ushort Energy => _energy;
    public ushort MaxEnergy => 200;
    public bool IsGathering => _isGathering;
    public bool IsPanelOpen => _isPanelOpen;
    public float GatherProgress => _isGathering && _currentNodeType < GatherTimes.Length
        ? Mathf.Clamp01(_gatherTimer / GatherTimes[_currentNodeType])
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

    public void Gather(byte nodeType)
    {
        if (_isGathering) return;
        if (_energy < 5) return;

        _isGathering = true;
        _gatherTimer = 0f;
        _currentNodeType = nodeType;
        OnGatherStarted?.Invoke();
        Network.NetworkManager.Instance?.StartGather(nodeType);
    }

    public string GetNodeName(byte nodeType)
    {
        switch (nodeType)
        {
            case NODE_HERB: return "Herb";
            case NODE_ORE:  return "Ore";
            case NODE_WOOD: return "Wood";
            case NODE_FISH: return "Fish";
            default:        return "Unknown";
        }
    }
}
