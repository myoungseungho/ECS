// ━━━ MentorManager.cs ━━━
// 사제(師弟) 시스템 관리 (S056 TASK 18)
// MsgType: 550-560 — 사부/제자 검색, 요청, 수락, 퀘스트, 졸업, 기여도 상점

using System;
using System.Collections.Generic;
using UnityEngine;

public class MentorManager : MonoBehaviour
{
    // ━━━ 싱글톤 ━━━
    public static MentorManager Instance { get; private set; }

    // ━━━ 상수 (S056) ━━━
    public const int MASTER_MIN_LEVEL = 40;
    public const int MASTER_MAX_DISCIPLES = 3;
    public const int DISCIPLE_MIN_LEVEL = 1;
    public const int DISCIPLE_MAX_LEVEL = 20;
    public const int GRADUATION_LEVEL = 30;
    public const float EXP_BUFF_PARTY = 0.30f;
    public const float EXP_BUFF_SOLO = 0.10f;
    public const float MASTER_EXP_SHARE = 0.10f;
    public const int QUEST_WEEKLY_COUNT = 3;

    // ━━━ 상태 ━━━
    private uint _masterEid;
    private readonly List<uint> _discipleEids = new List<uint>();
    private uint _contribution;
    private Network.MentorListEntry[] _lastSearchResults;
    private Network.MentorQuestEntry[] _currentQuests;
    private Network.MentorShopItem[] _shopItems;
    private bool _hasMaster;
    private bool _isMentorUIOpen;
    private bool _isMentorShopOpen;
    private bool _pendingRequest;

    // ━━━ 프로퍼티 ━━━
    public uint MasterEid => _masterEid;
    public IReadOnlyList<uint> DiscipleEids => _discipleEids;
    public uint Contribution => _contribution;
    public Network.MentorListEntry[] LastSearchResults => _lastSearchResults;
    public Network.MentorQuestEntry[] CurrentQuests => _currentQuests;
    public Network.MentorShopItem[] ShopItems => _shopItems;
    public bool HasMaster => _hasMaster;
    public bool IsMentorUIOpen => _isMentorUIOpen;
    public bool IsMentorShopOpen => _isMentorShopOpen;
    public bool PendingRequest => _pendingRequest;

    // ━━━ 이벤트 ━━━
    public event Action<Network.MentorListEntry[]> OnSearchResult;
    public event Action<Network.MentorRequestResult> OnRequestResult;
    public event Action<Network.MentorAcceptResultData> OnAcceptResult;
    public event Action<Network.MentorQuestEntry[]> OnQuestsUpdated;
    public event Action<Network.MentorGraduateData> OnGraduated;
    public event Action<Network.MentorShopListData> OnShopListReceived;
    public event Action<Network.MentorShopBuyResultData> OnShopBuyResult;
    public event Action OnMentorUIOpened;
    public event Action OnMentorUIClosed;
    public event Action OnMentorShopOpened;
    public event Action OnMentorShopClosed;

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
        var nm = Network.NetworkManager.Instance;
        if (nm != null)
        {
            nm.OnMentorList += HandleMentorList;
            nm.OnMentorRequestResult += HandleRequestResult;
            nm.OnMentorAcceptResult += HandleAcceptResult;
            nm.OnMentorQuests += HandleQuests;
            nm.OnMentorGraduate += HandleGraduate;
            nm.OnMentorShopList += HandleShopList;
            nm.OnMentorShopBuyResult += HandleShopBuyResult;
        }
    }

    private void OnDestroy()
    {
        var nm = Network.NetworkManager.Instance;
        if (nm != null)
        {
            nm.OnMentorList -= HandleMentorList;
            nm.OnMentorRequestResult -= HandleRequestResult;
            nm.OnMentorAcceptResult -= HandleAcceptResult;
            nm.OnMentorQuests -= HandleQuests;
            nm.OnMentorGraduate -= HandleGraduate;
            nm.OnMentorShopList -= HandleShopList;
            nm.OnMentorShopBuyResult -= HandleShopBuyResult;
        }
        if (Instance == this) Instance = null;
    }

    // ━━━ 핸들러 ━━━

    private void HandleMentorList(Network.MentorListEntry[] entries)
    {
        _lastSearchResults = entries;
        OnSearchResult?.Invoke(entries);
    }

    private void HandleRequestResult(Network.MentorRequestResult result)
    {
        _pendingRequest = result == Network.MentorRequestResult.SENT;
        OnRequestResult?.Invoke(result);
    }

    private void HandleAcceptResult(Network.MentorAcceptResultData data)
    {
        _pendingRequest = false;
        if (data.Result == Network.MentorAcceptResult.SUCCESS)
        {
            _masterEid = data.MasterEid;
            _hasMaster = data.DiscipleEid != 0;
            if (!_discipleEids.Contains(data.DiscipleEid) && data.DiscipleEid != 0)
            {
                _discipleEids.Add(data.DiscipleEid);
            }
        }
        OnAcceptResult?.Invoke(data);
    }

    private void HandleQuests(Network.MentorQuestEntry[] quests)
    {
        _currentQuests = quests;
        OnQuestsUpdated?.Invoke(quests);
    }

    private void HandleGraduate(Network.MentorGraduateData data)
    {
        if (data.Result == Network.MentorGraduateResult.SUCCESS)
        {
            _discipleEids.Remove(data.DiscipleEid);
            if (data.DiscipleEid != 0 && _masterEid == data.MasterEid)
            {
                _hasMaster = false;
                _masterEid = 0;
            }
        }
        OnGraduated?.Invoke(data);
    }

    private void HandleShopList(Network.MentorShopListData data)
    {
        _contribution = data.Contribution;
        _shopItems = data.Items;
        OnShopListReceived?.Invoke(data);
    }

    private void HandleShopBuyResult(Network.MentorShopBuyResultData data)
    {
        if (data.Result == Network.MentorShopBuyResult.SUCCESS)
        {
            _contribution = data.RemainingContribution;
        }
        OnShopBuyResult?.Invoke(data);
    }

    // ━━━ 공개 API ━━━

    /// <summary>사부/제자 검색 (searchType: 0=사부검색, 1=제자검색)</summary>
    public void SearchMentor(byte searchType)
    {
        Network.NetworkManager.Instance?.RequestMentorSearch(searchType);
    }

    /// <summary>사제 요청 (role: 0=나=제자, 1=나=사부)</summary>
    public void SendRequest(uint targetEid, byte role)
    {
        Network.NetworkManager.Instance?.RequestMentorRequest(targetEid, role);
    }

    /// <summary>사제 수락/거절 (accept: 0=거절, 1=수락)</summary>
    public void AcceptRequest(byte accept)
    {
        Network.NetworkManager.Instance?.RequestMentorAccept(accept);
    }

    /// <summary>사제 퀘스트 목록 요청</summary>
    public void RequestQuestList()
    {
        Network.NetworkManager.Instance?.RequestMentorQuestList();
    }

    /// <summary>졸업 요청 (discipleEid=0이면 자기 자신=제자)</summary>
    public void Graduate(uint discipleEid)
    {
        Network.NetworkManager.Instance?.RequestMentorGraduate(discipleEid);
    }

    /// <summary>기여도 상점 목록 요청</summary>
    public void RequestShopList()
    {
        Network.NetworkManager.Instance?.RequestMentorShopList();
    }

    /// <summary>기여도 상점 구매</summary>
    public void BuyShopItem(byte itemId)
    {
        Network.NetworkManager.Instance?.RequestMentorShopBuy(itemId);
    }

    /// <summary>사제 UI 열기</summary>
    public void OpenMentorUI()
    {
        _isMentorUIOpen = true;
        OnMentorUIOpened?.Invoke();
    }

    /// <summary>사제 UI 닫기</summary>
    public void CloseMentorUI()
    {
        _isMentorUIOpen = false;
        OnMentorUIClosed?.Invoke();
    }

    /// <summary>기여도 상점 열기</summary>
    public void OpenMentorShop()
    {
        _isMentorShopOpen = true;
        RequestShopList();
        OnMentorShopOpened?.Invoke();
    }

    /// <summary>기여도 상점 닫기</summary>
    public void CloseMentorShop()
    {
        _isMentorShopOpen = false;
        OnMentorShopClosed?.Invoke();
    }

    // ━━━ 유틸 ━━━

    public static string GetRequestResultText(Network.MentorRequestResult result)
    {
        switch (result)
        {
            case Network.MentorRequestResult.SENT: return "요청 전송됨";
            case Network.MentorRequestResult.LV_LOW: return "레벨 부족";
            case Network.MentorRequestResult.LV_HIGH: return "레벨 초과";
            case Network.MentorRequestResult.HAS_MASTER: return "이미 사부 있음";
            case Network.MentorRequestResult.FULL: return "제자 정원 초과";
            case Network.MentorRequestResult.NOT_FOUND: return "대상 없음";
            case Network.MentorRequestResult.SELF: return "자기 자신 불가";
            case Network.MentorRequestResult.ALREADY: return "이미 사제 관계";
            default: return "알 수 없음";
        }
    }

    public static string GetQuestTypeName(string type)
    {
        switch (type)
        {
            case "hunt": return "사냥";
            case "dungeon": return "던전";
            case "gather": return "채집";
            case "explore": return "탐험";
            case "boss": return "보스";
            default: return type;
        }
    }
}
