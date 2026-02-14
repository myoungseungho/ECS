// ━━━ NpcManager.cs ━━━
// NPC 인터랙션 관리 — F키로 근접 NPC와 대화, 대화 데이터 관리
// S034: NPC_INTERACT(332) → NPC_DIALOG(333)

using System;
using UnityEngine;
using Network;

public class NpcManager : MonoBehaviour
{
    // ━━━ 싱글톤 ━━━
    public static NpcManager Instance { get; private set; }

    // ━━━ 상태 ━━━
    private NpcDialogData _currentDialog;
    private bool _isDialogOpen;

    // ━━━ 이벤트 ━━━
    public event Action<NpcDialogData> OnDialogOpened;
    public event Action OnDialogClosed;

    // ━━━ 프로퍼티 ━━━
    public bool IsDialogOpen => _isDialogOpen;
    public NpcDialogData CurrentDialog => _currentDialog;

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
            NetworkManager.Instance.OnNpcDialog += HandleNpcDialog;
        }
    }

    private void OnDestroy()
    {
        if (NetworkManager.Instance != null)
        {
            NetworkManager.Instance.OnNpcDialog -= HandleNpcDialog;
        }
        if (Instance == this) Instance = null;
    }

    // ━━━ 공개 API ━━━

    /// <summary>NPC 인터랙션 요청 (F키)</summary>
    public void InteractWith(uint npcEntityId)
    {
        if (NetworkManager.Instance != null)
        {
            NetworkManager.Instance.InteractNpc(npcEntityId);
        }
    }

    /// <summary>대화 닫기</summary>
    public void CloseDialog()
    {
        _isDialogOpen = false;
        _currentDialog = null;
        OnDialogClosed?.Invoke();
    }

    // ━━━ 핸들러 ━━━

    private void HandleNpcDialog(NpcDialogData data)
    {
        _currentDialog = data;
        _isDialogOpen = true;
        OnDialogOpened?.Invoke(data);
    }
}
