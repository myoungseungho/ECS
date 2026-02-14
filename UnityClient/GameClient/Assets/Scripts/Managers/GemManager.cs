// ━━━ GemManager.cs ━━━
// 보석 장착/합성 시스템 관리 (S041 TASK 8)
// MsgType: 450-453

using System;
using UnityEngine;

public class GemManager : MonoBehaviour
{
    // ━━━ 싱글톤 ━━━
    public static GemManager Instance { get; private set; }

    // ━━━ 상태 ━━━
    private bool _isPanelOpen;

    // ━━━ 보석 타입 상수 ━━━
    public const byte GEM_RUBY     = 1;  // ATK
    public const byte GEM_SAPPHIRE = 2;  // MATK
    public const byte GEM_EMERALD  = 3;  // DEF
    public const byte GEM_DIAMOND  = 4;  // MAX_HP
    public const byte GEM_TOPAZ    = 5;  // CRIT_RATE
    public const byte GEM_AMETHYST = 6;  // CRIT_DMG

    // ━━━ 보석 등급 상수 ━━━
    public const byte TIER_ROUGH     = 1;
    public const byte TIER_POLISHED  = 2;
    public const byte TIER_REFINED   = 3;
    public const byte TIER_FLAWLESS  = 4;
    public const byte TIER_PERFECT   = 5;

    // ━━━ 프로퍼티 ━━━
    public bool IsPanelOpen => _isPanelOpen;

    // ━━━ 이벤트 ━━━
    public event Action<Network.GemEquipResultData> OnGemEquipped;
    public event Action<Network.GemFuseResultData> OnGemFused;
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
            nm.OnGemEquipResult += HandleGemEquipResult;
            nm.OnGemFuseResult += HandleGemFuseResult;
        }
    }

    private void OnDestroy()
    {
        var nm = Network.NetworkManager.Instance;
        if (nm != null)
        {
            nm.OnGemEquipResult -= HandleGemEquipResult;
            nm.OnGemFuseResult -= HandleGemFuseResult;
        }
        if (Instance == this) Instance = null;
    }

    // ━━━ 핸들러 ━━━

    private void HandleGemEquipResult(Network.GemEquipResultData data)
    {
        OnGemEquipped?.Invoke(data);
    }

    private void HandleGemFuseResult(Network.GemFuseResultData data)
    {
        OnGemFused?.Invoke(data);
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

    public void EquipGem(byte itemSlot, byte gemSlot, uint gemItemId)
    {
        Network.NetworkManager.Instance?.EquipGem(itemSlot, gemSlot, gemItemId);
    }

    public void FuseGems(byte gemType, byte gemTier)
    {
        Network.NetworkManager.Instance?.FuseGem(gemType, gemTier);
    }

    public string GetGemTypeName(byte gemType)
    {
        switch (gemType)
        {
            case GEM_RUBY:     return "Ruby";
            case GEM_SAPPHIRE: return "Sapphire";
            case GEM_EMERALD:  return "Emerald";
            case GEM_DIAMOND:  return "Diamond";
            case GEM_TOPAZ:    return "Topaz";
            case GEM_AMETHYST: return "Amethyst";
            default:           return "Unknown";
        }
    }

    public string GetTierName(byte tier)
    {
        switch (tier)
        {
            case TIER_ROUGH:    return "Rough";
            case TIER_POLISHED: return "Polished";
            case TIER_REFINED:  return "Refined";
            case TIER_FLAWLESS: return "Flawless";
            case TIER_PERFECT:  return "Perfect";
            default:            return "Unknown";
        }
    }
}
