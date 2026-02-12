// ━━━ QuestUI.cs ━━━
// 퀘스트 패널 — Q키 토글, 퀘스트 리스트 + 진행 상황
// QuestManager.OnQuestListChanged 구독

using UnityEngine;
using UnityEngine.UI;
using System.Collections.Generic;
using Network;

public class QuestUI : MonoBehaviour
{
    [Header("Panel")]
    [SerializeField] private GameObject questPanel;

    [Header("Quest List")]
    [SerializeField] private Transform questListParent;
    [SerializeField] private GameObject questEntryTemplate;

    [Header("Info")]
    [SerializeField] private Text questCountText;

    private readonly List<GameObject> _questInstances = new List<GameObject>();

    public static QuestUI Instance { get; private set; }

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
        if (QuestManager.Instance != null)
            QuestManager.Instance.OnQuestListChanged += RefreshQuests;

        if (questPanel != null)
            questPanel.SetActive(false);

        if (questEntryTemplate != null)
            questEntryTemplate.SetActive(false);
    }

    private void OnDestroy()
    {
        if (QuestManager.Instance != null)
            QuestManager.Instance.OnQuestListChanged -= RefreshQuests;

        if (Instance == this) Instance = null;
    }

    private void Update()
    {
        if (Input.GetKeyDown(KeyCode.Q))
            TogglePanel();
    }

    public void TogglePanel()
    {
        if (questPanel == null) return;

        bool show = !questPanel.activeSelf;
        questPanel.SetActive(show);

        if (show) RefreshQuests();
    }

    private void RefreshQuests()
    {
        var qm = QuestManager.Instance;
        if (qm == null) return;

        // 기존 항목 제거
        foreach (var go in _questInstances)
            if (go != null) Destroy(go);
        _questInstances.Clear();

        // 퀘스트 개수
        if (questCountText != null)
            questCountText.text = $"Quests: {qm.QuestCount}";

        if (questEntryTemplate == null || questListParent == null) return;

        foreach (var kvp in qm.Quests)
        {
            var quest = kvp.Value;
            var go = Instantiate(questEntryTemplate, questListParent);
            go.SetActive(true);

            // 텍스트: "[상태] Quest#ID  (진행/목표)"
            var texts = go.GetComponentsInChildren<Text>();
            if (texts.Length > 0)
            {
                string stateStr = GetStateString(quest.State);
                string progressStr = quest.Target > 0
                    ? $"({quest.Progress}/{quest.Target})"
                    : "";
                texts[0].text = $"[{stateStr}] Quest#{quest.QuestId} {progressStr}";
            }

            // 완료 버튼 (COMPLETE 상태일 때만 활성, Button 컴포넌트가 있을 때)
            var btn = go.GetComponentInChildren<Button>();
            if (btn != null)
            {
                bool canComplete = quest.State == QuestState.COMPLETE;
                btn.gameObject.SetActive(canComplete);
                if (canComplete)
                {
                    uint qid = quest.QuestId;
                    btn.onClick.AddListener(() => OnCompleteClicked(qid));
                }
            }

            _questInstances.Add(go);
        }
    }

    private static string GetStateString(QuestState state)
    {
        switch (state)
        {
            case QuestState.ACCEPTED: return "Accepted";
            case QuestState.IN_PROGRESS: return "In Progress";
            case QuestState.COMPLETE: return "Complete!";
            case QuestState.REWARDED: return "Done";
            default: return "???";
        }
    }

    private void OnCompleteClicked(uint questId)
    {
        if (QuestManager.Instance != null)
            QuestManager.Instance.CompleteQuest(questId);
    }
}
