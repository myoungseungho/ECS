// ━━━ EnhanceManager.cs ━━━
// 장비 강화 시스템 관리 — 대장장이 NPC 연동
// S034: ENHANCE_REQ(340) → ENHANCE_RESULT(341)

using System;
using UnityEngine;
using Network;

public class EnhanceManager : MonoBehaviour
{
    // ━━━ 싱글톤 ━━━
    public static EnhanceManager Instance { get; private set; }

    // ━━━ 상태 ━━━
    private bool _isEnhancePanelOpen;

    // ━━━ 이벤트 ━━━
    public event Action<EnhanceResultData> OnEnhanceComplete;
    public event Action OnEnhancePanelOpened;
    public event Action OnEnhancePanelClosed;

    // ━━━ 프로퍼티 ━━━
    public bool IsEnhancePanelOpen => _isEnhancePanelOpen;

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
        if (NetworkManager.Instance != null)
        {
            NetworkManager.Instance.OnEnhanceResult += HandleEnhanceResult;
        }
    }

    private void OnDestroy()
    {
        if (NetworkManager.Instance != null)
        {
            NetworkManager.Instance.OnEnhanceResult -= HandleEnhanceResult;
        }
        if (Instance == this) Instance = null;
    }

    // ━━━ 공개 API ━━━

    /// <summary>강화 요청</summary>
    public void Enhance(byte slotIndex)
    {
        if (NetworkManager.Instance != null)
        {
            NetworkManager.Instance.RequestEnhance(slotIndex);
        }
    }

    /// <summary>강화 패널 열기</summary>
    public void OpenPanel()
    {
        _isEnhancePanelOpen = true;
        OnEnhancePanelOpened?.Invoke();
    }

    /// <summary>강화 패널 닫기</summary>
    public void ClosePanel()
    {
        _isEnhancePanelOpen = false;
        OnEnhancePanelClosed?.Invoke();
    }

    // ━━━ 핸들러 ━━━

    private void HandleEnhanceResult(EnhanceResultData data)
    {
        OnEnhanceComplete?.Invoke(data);
    }
}
