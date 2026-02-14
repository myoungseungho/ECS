// ━━━ CollectionUI.cs ━━━
// 도감 UI — CollectionManager 이벤트 구독
// 몬스터 4카테고리 + 장비 5등급 + 완성 보너스 표시

using UnityEngine;
using UnityEngine.UI;
using Network;

public class CollectionUI : MonoBehaviour
{
    // ━━━ UI 참조 ━━━
    [SerializeField] private GameObject _panel;
    [SerializeField] private Text _monsterSummaryLabel;
    [SerializeField] private Transform _monsterListContainer;
    [SerializeField] private Text _equipSummaryLabel;
    [SerializeField] private Transform _equipListContainer;
    [SerializeField] private Button _closeButton;

    private void Start()
    {
        if (_panel != null) _panel.SetActive(false);
        if (_closeButton != null) _closeButton.onClick.AddListener(TogglePanel);

        var mgr = CollectionManager.Instance;
        if (mgr != null)
        {
            mgr.OnCollectionChanged += RefreshUI;
            mgr.OnPanelOpened += OnPanelOpened;
            mgr.OnPanelClosed += OnPanelClosed;
        }
    }

    private void OnDestroy()
    {
        var mgr = CollectionManager.Instance;
        if (mgr == null) return;

        mgr.OnCollectionChanged -= RefreshUI;
        mgr.OnPanelOpened -= OnPanelOpened;
        mgr.OnPanelClosed -= OnPanelClosed;
    }

    private void Update()
    {
        // F6키로 도감 토글
        if (Input.GetKeyDown(KeyCode.F6))
        {
            TogglePanel();
        }
    }

    // ━━━ 토글 ━━━

    private void TogglePanel()
    {
        var mgr = CollectionManager.Instance;
        if (mgr == null) return;

        if (mgr.IsPanelOpen)
            mgr.ClosePanel();
        else
            mgr.OpenPanel();
    }

    private void OnPanelOpened()
    {
        if (_panel != null) _panel.SetActive(true);
    }

    private void OnPanelClosed()
    {
        if (_panel != null) _panel.SetActive(false);
    }

    // ━━━ UI 갱신 ━━━

    private void RefreshUI()
    {
        var mgr = CollectionManager.Instance;
        if (mgr == null) return;

        // 몬스터 도감 요약
        float monsterRate = mgr.GetMonsterCompletionRate();
        if (_monsterSummaryLabel != null)
        {
            _monsterSummaryLabel.text = $"몬스터 도감 — 완성도: {monsterRate:P0}";
        }

        // 몬스터 카테고리별 상세
        if (_monsterListContainer != null)
        {
            int childIdx = 0;
            foreach (var cat in mgr.MonsterCategories)
            {
                string completeStr = cat.Completed != 0 ? " ✓완성" : "";
                string line = $"{cat.Name}: {cat.Registered}/{cat.Total}{completeStr} — {cat.BonusType}+{cat.BonusValue}";

                if (childIdx < _monsterListContainer.childCount)
                {
                    var txt = _monsterListContainer.GetChild(childIdx).GetComponent<Text>();
                    if (txt != null) txt.text = line;
                    _monsterListContainer.GetChild(childIdx).gameObject.SetActive(true);
                }
                childIdx++;
            }
            for (int i = childIdx; i < _monsterListContainer.childCount; i++)
                _monsterListContainer.GetChild(i).gameObject.SetActive(false);
        }

        // 장비 도감 요약
        int totalEquipRegistered = mgr.GetEquipTotalRegistered();
        if (_equipSummaryLabel != null)
        {
            _equipSummaryLabel.text = $"장비 도감 — 총 등록: {totalEquipRegistered}";
        }

        // 장비 등급별 상세
        if (_equipListContainer != null)
        {
            int childIdx = 0;
            foreach (var tier in mgr.EquipTiers)
            {
                string line = $"{tier.TierKr}({tier.Tier}): {tier.Registered}종 — {tier.BonusType}+{tier.BonusValue}";

                if (childIdx < _equipListContainer.childCount)
                {
                    var txt = _equipListContainer.GetChild(childIdx).GetComponent<Text>();
                    if (txt != null) txt.text = line;
                    _equipListContainer.GetChild(childIdx).gameObject.SetActive(true);
                }
                childIdx++;
            }
            for (int i = childIdx; i < _equipListContainer.childCount; i++)
                _equipListContainer.GetChild(i).gameObject.SetActive(false);
        }
    }
}
