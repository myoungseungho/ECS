// ━━━ PartyUI.cs ━━━
// 파티 패널 — P키 토글, 파티 멤버 리스트, 생성/탈퇴 버튼
// PartyManager.OnPartyChanged 구독

using UnityEngine;
using UnityEngine.UI;
using System.Collections.Generic;
using Network;

public class PartyUI : MonoBehaviour
{
    [Header("Panel")]
    [SerializeField] private GameObject partyPanel;

    [Header("Party Info")]
    [SerializeField] private Text partyStatusText;
    [SerializeField] private Transform memberListParent;
    [SerializeField] private GameObject memberTemplate;

    [Header("Buttons")]
    [SerializeField] private Button createButton;
    [SerializeField] private Button leaveButton;

    private readonly List<GameObject> _memberInstances = new List<GameObject>();

    public static PartyUI Instance { get; private set; }

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
        if (PartyManager.Instance != null)
            PartyManager.Instance.OnPartyChanged += RefreshParty;

        if (createButton != null)
            createButton.onClick.AddListener(OnCreateClicked);
        if (leaveButton != null)
            leaveButton.onClick.AddListener(OnLeaveClicked);

        if (partyPanel != null)
            partyPanel.SetActive(false);

        if (memberTemplate != null)
            memberTemplate.SetActive(false);
    }

    private void OnDestroy()
    {
        if (PartyManager.Instance != null)
            PartyManager.Instance.OnPartyChanged -= RefreshParty;

        if (createButton != null)
            createButton.onClick.RemoveListener(OnCreateClicked);
        if (leaveButton != null)
            leaveButton.onClick.RemoveListener(OnLeaveClicked);

        if (Instance == this) Instance = null;
    }

    private void Update()
    {
        if (Input.GetKeyDown(KeyCode.P))
            TogglePanel();
    }

    public void TogglePanel()
    {
        if (partyPanel == null) return;

        bool show = !partyPanel.activeSelf;
        partyPanel.SetActive(show);

        if (show) RefreshParty();
    }

    private void RefreshParty()
    {
        var pm = PartyManager.Instance;
        if (pm == null) return;

        // 기존 멤버 UI 제거
        foreach (var go in _memberInstances)
            if (go != null) Destroy(go);
        _memberInstances.Clear();

        // 파티 상태
        if (partyStatusText != null)
        {
            partyStatusText.text = pm.InParty
                ? $"Party #{pm.PartyId} ({pm.Members?.Length ?? 0} members)"
                : "No Party";
        }

        // 버튼 상태
        if (createButton != null) createButton.gameObject.SetActive(!pm.InParty);
        if (leaveButton != null) leaveButton.gameObject.SetActive(pm.InParty);

        // 멤버 리스트
        if (pm.Members == null || memberTemplate == null || memberListParent == null) return;

        foreach (var member in pm.Members)
        {
            var go = Instantiate(memberTemplate, memberListParent);
            go.SetActive(true);

            var text = go.GetComponentInChildren<Text>();
            if (text != null)
            {
                string leaderTag = member.EntityId == pm.LeaderId ? " [Leader]" : "";
                text.text = $"Entity#{member.EntityId} Lv.{member.Level}{leaderTag}";
            }

            _memberInstances.Add(go);
        }
    }

    private void OnCreateClicked()
    {
        if (PartyManager.Instance != null)
            PartyManager.Instance.CreateParty();
    }

    private void OnLeaveClicked()
    {
        if (PartyManager.Instance != null)
            PartyManager.Instance.LeaveParty();
    }
}
