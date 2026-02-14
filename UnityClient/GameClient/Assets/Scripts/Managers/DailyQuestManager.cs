// ━━━ DailyQuestManager.cs ━━━
// 일일/주간 퀘스트 관리 — 목록 조회 + 진행 상태 추적
// NetworkManager 이벤트 구독 → DailyQuestUI에 이벤트 발행

using System;
using System.Collections.Generic;
using UnityEngine;
using Network;

public class DailyQuestManager : MonoBehaviour
{
    // ━━━ 상태 ━━━
    private readonly List<DailyQuestInfo> _dailyQuests = new List<DailyQuestInfo>();
    private WeeklyQuestInfo _weeklyQuest;
    private bool _hasWeekly;
    private bool _isPanelOpen;

    // ━━━ 프로퍼티 ━━━
    public IReadOnlyList<DailyQuestInfo> DailyQuests => _dailyQuests;
    public WeeklyQuestInfo WeeklyQuest => _weeklyQuest;
    public bool HasWeekly => _hasWeekly;
    public bool IsPanelOpen => _isPanelOpen;

    // ━━━ 이벤트 ━━━
    public event Action OnDailyQuestListChanged;
    public event Action OnWeeklyQuestChanged;
    public event Action OnPanelOpened;
    public event Action OnPanelClosed;

    // ━━━ 싱글톤 (Scene-bound) ━━━
    public static DailyQuestManager Instance { get; private set; }

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
        net.OnDailyQuestList += HandleDailyQuestList;
        net.OnWeeklyQuest += HandleWeeklyQuest;
    }

    private void OnDestroy()
    {
        var net = NetworkManager.Instance;
        if (net == null) return;

        net.OnDailyQuestList -= HandleDailyQuestList;
        net.OnWeeklyQuest -= HandleWeeklyQuest;

        if (Instance == this) Instance = null;
    }

    // ━━━ 공개 API ━━━

    /// <summary>퀘스트 패널 열기 (일일+주간 동시 요청)</summary>
    public void OpenPanel()
    {
        _isPanelOpen = true;
        NetworkManager.Instance.RequestDailyQuestList();
        NetworkManager.Instance.RequestWeeklyQuest();
        OnPanelOpened?.Invoke();
    }

    /// <summary>퀘스트 패널 닫기</summary>
    public void ClosePanel()
    {
        _isPanelOpen = false;
        OnPanelClosed?.Invoke();
    }

    /// <summary>일일 퀘스트 목록 새로고침</summary>
    public void RefreshDailyQuests()
    {
        NetworkManager.Instance.RequestDailyQuestList();
    }

    /// <summary>주간 퀘스트 새로고침</summary>
    public void RefreshWeeklyQuest()
    {
        NetworkManager.Instance.RequestWeeklyQuest();
    }

    // ━━━ 핸들러 ━━━

    private void HandleDailyQuestList(DailyQuestListData data)
    {
        _dailyQuests.Clear();
        _dailyQuests.AddRange(data.Quests);

        Debug.Log($"[DailyQuestManager] DailyList: count={data.Quests.Length}");
        OnDailyQuestListChanged?.Invoke();
    }

    private void HandleWeeklyQuest(WeeklyQuestData data)
    {
        _hasWeekly = data.HasQuest;
        _weeklyQuest = data.Quest;

        Debug.Log($"[DailyQuestManager] Weekly: hasQuest={data.HasQuest}");
        OnWeeklyQuestChanged?.Invoke();
    }
}
