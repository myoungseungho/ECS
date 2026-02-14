// ━━━ MountUI.cs ━━━
// 탈것 UI — 소환/해제 버튼, 속도 표시, 탈것 선택 목록
// MountManager 이벤트 구독

using UnityEngine;
using UnityEngine.UI;
using Network;

public class MountUI : MonoBehaviour
{
    [Header("UI References")]
    [SerializeField] private GameObject _panel;
    [SerializeField] private Text _statusText;
    [SerializeField] private Text _speedText;
    [SerializeField] private Text _mountListText;
    [SerializeField] private Button _summonBtn;
    [SerializeField] private Button _dismountBtn;
    [SerializeField] private Button _closeBtn;

    // 탈것 선택 (placeholder: 고정 목록)
    private uint _selectedMountId = 1;

    private void Start()
    {
        var mm = MountManager.Instance;
        if (mm != null)
        {
            mm.OnMounted += HandleMounted;
            mm.OnDismounted += HandleDismounted;
            mm.OnPanelOpened += HandlePanelOpened;
            mm.OnPanelClosed += HandlePanelClosed;
        }

        if (_summonBtn != null) _summonBtn.onClick.AddListener(OnSummonClick);
        if (_dismountBtn != null) _dismountBtn.onClick.AddListener(OnDismountClick);
        if (_closeBtn != null) _closeBtn.onClick.AddListener(OnCloseClick);

        if (_panel != null)
            _panel.SetActive(false);
    }

    private void OnDestroy()
    {
        var mm = MountManager.Instance;
        if (mm == null) return;

        mm.OnMounted -= HandleMounted;
        mm.OnDismounted -= HandleDismounted;
        mm.OnPanelOpened -= HandlePanelOpened;
        mm.OnPanelClosed -= HandlePanelClosed;
    }

    private void Update()
    {
        // ESC로 닫기
        if (_panel != null && _panel.activeSelf && Input.GetKeyDown(KeyCode.Escape))
        {
            MountManager.Instance?.ClosePanel();
        }
    }

    // ━━━ 버튼 핸들러 ━━━

    private void OnSummonClick()
    {
        MountManager.Instance?.Summon(_selectedMountId);
    }

    private void OnDismountClick()
    {
        MountManager.Instance?.Dismount();
    }

    private void OnCloseClick()
    {
        MountManager.Instance?.ClosePanel();
    }

    // ━━━ 이벤트 핸들러 ━━━

    private void HandlePanelOpened()
    {
        if (_panel != null)
            _panel.SetActive(true);

        RefreshUI();
    }

    private void HandlePanelClosed()
    {
        if (_panel != null)
            _panel.SetActive(false);
    }

    private void HandleMounted(MountResultData data)
    {
        RefreshUI();
    }

    private void HandleDismounted()
    {
        RefreshUI();
    }

    // ━━━ UI 갱신 ━━━

    private void RefreshUI()
    {
        var mm = MountManager.Instance;
        if (mm == null) return;

        bool mounted = mm.IsMounted;

        // 상태 텍스트
        if (_statusText != null)
        {
            _statusText.text = mounted
                ? $"Mounted (ID: {mm.CurrentMountId})"
                : "Not Mounted";
        }

        // 속도 표시
        if (_speedText != null)
        {
            _speedText.text = mounted
                ? $"Speed: {mm.SpeedMultiplier:F1}x"
                : "";
        }

        // 버튼 표시 전환
        if (_summonBtn != null)
            _summonBtn.gameObject.SetActive(!mounted);
        if (_dismountBtn != null)
            _dismountBtn.gameObject.SetActive(mounted);

        // 탈것 선택 목록 (placeholder)
        if (_mountListText != null)
        {
            if (mounted)
            {
                _mountListText.text = "";
            }
            else
            {
                var sb = new System.Text.StringBuilder();
                sb.AppendLine("Available Mounts:");
                sb.AppendLine($"  {(_selectedMountId == 1 ? ">" : " ")} [1] Horse (1.5x speed)");
                sb.AppendLine($"  {(_selectedMountId == 2 ? ">" : " ")} [2] Wolf (2.0x speed)");
                sb.AppendLine($"  {(_selectedMountId == 3 ? ">" : " ")} [3] Dragon (3.0x speed)");
                _mountListText.text = sb.ToString();
            }
        }
    }

    /// <summary>탈것 선택 (외부 호출용)</summary>
    public void SelectMount(uint mountId)
    {
        _selectedMountId = mountId;
        RefreshUI();
    }
}
