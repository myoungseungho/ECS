// ━━━ MentorUI.cs ━━━
// 사제(師弟) 시스템 메인 UI (S056 TASK 18)
// Shift+M 토글 — 사부/제자 검색, 사제 요청, 퀘스트, 졸업

using System;
using UnityEngine;

public class MentorUI : MonoBehaviour
{
    // ━━━ 싱글톤 ━━━
    public static MentorUI Instance { get; private set; }

    // ━━━ UI 요소 ━━━
    [SerializeField] private GameObject _panel;
    [SerializeField] private GameObject _searchPanel;
    [SerializeField] private GameObject _questPanel;
    [SerializeField] private GameObject _requestPopup;

    // ━━━ 상태 ━━━
    private bool _isVisible;
    private string _statusText = "";
    private string _searchText = "";
    private string _questText = "";
    private byte _currentSearchType; // 0=사부, 1=제자

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
        var mm = MentorManager.Instance;
        if (mm != null)
        {
            mm.OnMentorUIOpened += HandleUIOpened;
            mm.OnMentorUIClosed += HandleUIClosed;
            mm.OnSearchResult += HandleSearchResult;
            mm.OnRequestResult += HandleRequestResult;
            mm.OnAcceptResult += HandleAcceptResult;
            mm.OnQuestsUpdated += HandleQuestsUpdated;
            mm.OnGraduated += HandleGraduated;
        }
    }

    private void OnDestroy()
    {
        var mm = MentorManager.Instance;
        if (mm != null)
        {
            mm.OnMentorUIOpened -= HandleUIOpened;
            mm.OnMentorUIClosed -= HandleUIClosed;
            mm.OnSearchResult -= HandleSearchResult;
            mm.OnRequestResult -= HandleRequestResult;
            mm.OnAcceptResult -= HandleAcceptResult;
            mm.OnQuestsUpdated -= HandleQuestsUpdated;
            mm.OnGraduated -= HandleGraduated;
        }
        if (Instance == this) Instance = null;
    }

    private void Update()
    {
        // Shift+M 토글
        if (Input.GetKey(KeyCode.LeftShift) && Input.GetKeyDown(KeyCode.M))
        {
            ToggleUI();
        }
    }

    // ━━━ UI 토글 ━━━

    private void ToggleUI()
    {
        if (_isVisible)
            MentorManager.Instance?.CloseMentorUI();
        else
            MentorManager.Instance?.OpenMentorUI();
    }

    // ━━━ 이벤트 핸들러 ━━━

    private void HandleUIOpened()
    {
        _isVisible = true;
        _statusText = "사제 시스템";
        MentorManager.Instance?.RequestQuestList();
    }

    private void HandleUIClosed()
    {
        _isVisible = false;
    }

    private void HandleSearchResult(Network.MentorListEntry[] entries)
    {
        if (entries.Length == 0)
        {
            _searchText = _currentSearchType == 0 ? "검색 결과 없음 (사부 Lv40+)" : "검색 결과 없음 (제자 Lv1~20)";
        }
        else
        {
            _searchText = "";
            for (int i = 0; i < entries.Length; i++)
            {
                var e = entries[i];
                _searchText += $"{i + 1}. {e.Name} (Lv{e.Level})\n";
            }
        }
    }

    private void HandleRequestResult(Network.MentorRequestResult result)
    {
        _statusText = MentorManager.GetRequestResultText(result);
    }

    private void HandleAcceptResult(Network.MentorAcceptResultData data)
    {
        if (data.Result == Network.MentorAcceptResult.SUCCESS)
            _statusText = $"사제 관계 성립! (사부:{data.MasterEid}, 제자:{data.DiscipleEid})";
        else
            _statusText = "사제 관계 실패";
    }

    private void HandleQuestsUpdated(Network.MentorQuestEntry[] quests)
    {
        _questText = $"사제 퀘스트 ({quests.Length}/{MentorManager.QUEST_WEEKLY_COUNT})\n";
        for (int i = 0; i < quests.Length; i++)
        {
            var q = quests[i];
            string typeName = MentorManager.GetQuestTypeName(q.Type);
            _questText += $"  [{typeName}] {q.Name}: {q.Progress}/{q.CountNeeded}\n";
        }
    }

    private void HandleGraduated(Network.MentorGraduateData data)
    {
        if (data.Result == Network.MentorGraduateResult.SUCCESS)
            _statusText = $"졸업 완료! 사부 골드:{data.MasterGold}, 제자 골드:{data.DiscipleGold}";
        else
            _statusText = data.Result == Network.MentorGraduateResult.NOT_READY ? "졸업 조건 미달 (Lv30 필요)" : "졸업 실패";
    }

    // ━━━ OnGUI ━━━

    private void OnGUI()
    {
        if (!_isVisible) return;

        float w = 420f, h = 500f;
        float x = (Screen.width - w) / 2f;
        float y = (Screen.height - h) / 2f;

        GUI.Box(new Rect(x, y, w, h), "");
        GUILayout.BeginArea(new Rect(x + 10, y + 10, w - 20, h - 20));

        GUILayout.Label("<b>사제(師弟) 시스템</b>", new GUIStyle(GUI.skin.label) { fontSize = 16, richText = true });
        GUILayout.Space(5);

        // 상태
        if (!string.IsNullOrEmpty(_statusText))
        {
            GUILayout.Label(_statusText);
            GUILayout.Space(5);
        }

        // 사부/제자 정보
        var mm = MentorManager.Instance;
        if (mm != null)
        {
            if (mm.HasMaster)
                GUILayout.Label($"사부 EID: {mm.MasterEid}");
            if (mm.DiscipleEids.Count > 0)
                GUILayout.Label($"제자 수: {mm.DiscipleEids.Count}/{MentorManager.MASTER_MAX_DISCIPLES}");
        }

        GUILayout.Space(10);

        // 검색 버튼
        GUILayout.BeginHorizontal();
        if (GUILayout.Button("사부 검색 (Lv40+)"))
        {
            _currentSearchType = 0;
            mm?.SearchMentor(0);
        }
        if (GUILayout.Button("제자 검색 (Lv1~20)"))
        {
            _currentSearchType = 1;
            mm?.SearchMentor(1);
        }
        GUILayout.EndHorizontal();

        // 검색 결과
        if (!string.IsNullOrEmpty(_searchText))
        {
            GUILayout.Label(_searchText);

            // 첫 번째 결과로 사제 요청
            var results = mm?.LastSearchResults;
            if (results != null && results.Length > 0)
            {
                GUILayout.BeginHorizontal();
                if (GUILayout.Button("제자로 요청"))
                    mm?.SendRequest(results[0].EntityId, 0);
                if (GUILayout.Button("사부로 요청"))
                    mm?.SendRequest(results[0].EntityId, 1);
                GUILayout.EndHorizontal();
            }
        }

        GUILayout.Space(10);

        // 사제 퀘스트
        if (!string.IsNullOrEmpty(_questText))
            GUILayout.Label(_questText);
        if (GUILayout.Button("퀘스트 갱신"))
            mm?.RequestQuestList();

        GUILayout.Space(10);

        // 졸업/상점
        GUILayout.BeginHorizontal();
        if (GUILayout.Button("졸업 (제자 본인)"))
            mm?.Graduate(0);
        if (GUILayout.Button("기여도 상점"))
            mm?.OpenMentorShop();
        GUILayout.EndHorizontal();

        GUILayout.Space(10);

        // 수락/거절 (대기 중인 요청이 있을 때)
        if (mm != null && mm.PendingRequest)
        {
            GUILayout.Label("<color=yellow>사제 요청이 도착했습니다!</color>", new GUIStyle(GUI.skin.label) { richText = true });
            GUILayout.BeginHorizontal();
            if (GUILayout.Button("수락"))
                mm.AcceptRequest(1);
            if (GUILayout.Button("거절"))
                mm.AcceptRequest(0);
            GUILayout.EndHorizontal();
        }

        GUILayout.FlexibleSpace();
        if (GUILayout.Button("닫기 (Shift+M)"))
            mm?.CloseMentorUI();

        GUILayout.EndArea();
    }
}
