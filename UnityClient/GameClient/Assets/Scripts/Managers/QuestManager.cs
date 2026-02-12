// ━━━ QuestManager.cs ━━━
// 퀘스트 시스템 관리 — 퀘스트 목록, 수락, 진행, 완료
// NetworkManager 이벤트 구독 → UI에 퀘스트 이벤트 발행

using System;
using System.Collections.Generic;
using UnityEngine;
using Network;

public class QuestManager : MonoBehaviour
{
    // ━━━ 퀘스트 데이터 ━━━
    private readonly Dictionary<uint, QuestInfo> _quests = new Dictionary<uint, QuestInfo>();

    public IReadOnlyDictionary<uint, QuestInfo> Quests => _quests;
    public int QuestCount => _quests.Count;

    // ━━━ 이벤트 ━━━
    public event Action OnQuestListChanged;
    public event Action<QuestAcceptResultData> OnQuestAccepted;
    public event Action<QuestCompleteResultData> OnQuestCompleted;

    // ━━━ 싱글톤 (Scene-bound) ━━━
    public static QuestManager Instance { get; private set; }

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
        var net = NetworkManager.Instance;
        net.OnQuestList += HandleQuestList;
        net.OnQuestAcceptResult += HandleQuestAcceptResult;
        net.OnQuestCompleteResult += HandleQuestCompleteResult;
        net.OnEnterGame += HandleEnterGame;
    }

    private void OnDestroy()
    {
        var net = NetworkManager.Instance;
        if (net == null) return;

        net.OnQuestList -= HandleQuestList;
        net.OnQuestAcceptResult -= HandleQuestAcceptResult;
        net.OnQuestCompleteResult -= HandleQuestCompleteResult;
        net.OnEnterGame -= HandleEnterGame;

        if (Instance == this) Instance = null;
    }

    // ━━━ 공개 API ━━━

    public void AcceptQuest(uint questId)
    {
        NetworkManager.Instance.AcceptQuest(questId);
    }

    public void CheckProgress(uint questId)
    {
        NetworkManager.Instance.CheckQuestProgress(questId);
    }

    public void CompleteQuest(uint questId)
    {
        NetworkManager.Instance.CompleteQuest(questId);
    }

    public QuestInfo GetQuest(uint questId)
    {
        _quests.TryGetValue(questId, out var quest);
        return quest;
    }

    public bool HasQuest(uint questId)
    {
        return _quests.ContainsKey(questId);
    }

    // ━━━ 핸들러 ━━━

    private void HandleQuestList(QuestInfo[] quests)
    {
        _quests.Clear();
        foreach (var quest in quests)
            _quests[quest.QuestId] = quest;

        Debug.Log($"[QuestManager] Loaded {quests.Length} quests");
        OnQuestListChanged?.Invoke();
    }

    private void HandleQuestAcceptResult(QuestAcceptResultData data)
    {
        if (data.Result == QuestAcceptResult.SUCCESS)
        {
            _quests[data.QuestId] = new QuestInfo
            {
                QuestId = data.QuestId,
                State = QuestState.ACCEPTED,
                Progress = 0,
                Target = 0
            };
        }

        Debug.Log($"[QuestManager] QuestAccept: {data.Result}, questId={data.QuestId}");
        OnQuestAccepted?.Invoke(data);
        OnQuestListChanged?.Invoke();
    }

    private void HandleQuestCompleteResult(QuestCompleteResultData data)
    {
        if (data.Result == 0)
        {
            if (_quests.TryGetValue(data.QuestId, out var quest))
                quest.State = QuestState.REWARDED;
        }

        Debug.Log($"[QuestManager] QuestComplete: result={data.Result}, quest={data.QuestId}, exp={data.RewardExp}");
        OnQuestCompleted?.Invoke(data);
        OnQuestListChanged?.Invoke();
    }

    private void HandleEnterGame(EnterGameResult result)
    {
        if (result.ResultCode != 0) return;
        NetworkManager.Instance.RequestQuestList();
    }
}
