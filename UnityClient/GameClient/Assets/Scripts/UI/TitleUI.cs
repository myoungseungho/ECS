// ━━━ TitleUI.cs ━━━
// 칭호 목록/장착 UI — TitleManager 이벤트 구독
// H키 토글 + 칭호 목록 + 장착/해제 + 보너스 표시

using UnityEngine;
using UnityEngine.UI;
using Network;

public class TitleUI : MonoBehaviour
{
    // ━━━ UI 참조 ━━━
    [SerializeField] private GameObject _panel;
    [SerializeField] private Transform _listContainer;
    [SerializeField] private Text _equippedLabel;
    [SerializeField] private Text _bonusLabel;
    [SerializeField] private Button _closeButton;

    // 내부 상태
    private bool _isOpen;

    private void Start()
    {
        if (_panel != null) _panel.SetActive(false);
        if (_closeButton != null) _closeButton.onClick.AddListener(TogglePanel);

        var mgr = TitleManager.Instance;
        if (mgr != null)
        {
            mgr.OnTitleListChanged += RefreshUI;
            mgr.OnEquipResult += HandleEquipResult;
            mgr.OnPanelOpened += OnPanelOpened;
            mgr.OnPanelClosed += OnPanelClosed;
        }
    }

    private void OnDestroy()
    {
        var mgr = TitleManager.Instance;
        if (mgr == null) return;

        mgr.OnTitleListChanged -= RefreshUI;
        mgr.OnEquipResult -= HandleEquipResult;
        mgr.OnPanelOpened -= OnPanelOpened;
        mgr.OnPanelClosed -= OnPanelClosed;
    }

    private void Update()
    {
        if (Input.GetKeyDown(KeyCode.H))
        {
            TogglePanel();
        }
    }

    // ━━━ 토글 ━━━

    private void TogglePanel()
    {
        var mgr = TitleManager.Instance;
        if (mgr == null) return;

        if (mgr.IsPanelOpen)
            mgr.ClosePanel();
        else
            mgr.OpenPanel();
    }

    private void OnPanelOpened()
    {
        _isOpen = true;
        if (_panel != null) _panel.SetActive(true);
    }

    private void OnPanelClosed()
    {
        _isOpen = false;
        if (_panel != null) _panel.SetActive(false);
    }

    // ━━━ UI 갱신 ━━━

    private void RefreshUI()
    {
        var mgr = TitleManager.Instance;
        if (mgr == null) return;

        // 장착 칭호 표시
        string equippedName = mgr.GetEquippedTitleName();
        if (_equippedLabel != null)
        {
            _equippedLabel.text = string.IsNullOrEmpty(equippedName)
                ? "장착 칭호: 없음"
                : $"장착 칭호: {equippedName}";
        }

        // 칭호 목록 텍스트 갱신 (리스트 컨테이너에 기존 자식 갱신)
        if (_listContainer != null)
        {
            // 기존 자식 텍스트들 갱신 (ProjectSetup에서 생성)
            int childIdx = 0;
            foreach (var title in mgr.Titles)
            {
                string lockStr = title.Unlocked ? "" : " [미해금]";
                string equipStr = title.TitleId == mgr.EquippedId ? " ★" : "";
                string line = $"{title.Name}{equipStr} — {title.BonusType}+{title.BonusValue}{lockStr}";

                if (childIdx < _listContainer.childCount)
                {
                    var txt = _listContainer.GetChild(childIdx).GetComponent<Text>();
                    if (txt != null) txt.text = line;
                    _listContainer.GetChild(childIdx).gameObject.SetActive(true);
                }
                childIdx++;
            }

            // 남은 자식 숨김
            for (int i = childIdx; i < _listContainer.childCount; i++)
            {
                _listContainer.GetChild(i).gameObject.SetActive(false);
            }
        }

        // 현재 장착 보너스
        if (_bonusLabel != null)
        {
            var equipped = mgr.GetTitle(mgr.EquippedId);
            _bonusLabel.text = equipped != null
                ? $"보너스: {equipped.BonusType} +{equipped.BonusValue}"
                : "보너스: 없음";
        }
    }

    private void HandleEquipResult(TitleEquipResultData data)
    {
        if (data.Result != TitleEquipResult.SUCCESS)
        {
            Debug.LogWarning($"[TitleUI] 칭호 장착 실패: {data.Result}");
        }
    }

    // ━━━ 외부 호출 (버튼 바인딩용) ━━━

    /// <summary>칭호 장착 (UI 버튼에서 호출)</summary>
    public void OnEquipClicked(ushort titleId)
    {
        var mgr = TitleManager.Instance;
        if (mgr != null) mgr.EquipTitle(titleId);
    }

    /// <summary>칭호 해제 (UI 버튼에서 호출)</summary>
    public void OnUnequipClicked()
    {
        var mgr = TitleManager.Instance;
        if (mgr != null) mgr.UnequipTitle();
    }
}
