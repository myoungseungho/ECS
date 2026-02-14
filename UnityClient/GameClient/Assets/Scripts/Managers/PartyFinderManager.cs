// ━━━ PartyFinderManager.cs ━━━
// 파티 찾기 시스템 관리 — S051 TASK 5 (MsgType 420-422)
// 파티 찾기 등록/목록/카테고리 필터

using System;
using System.Collections.Generic;
using UnityEngine;

public class PartyFinderManager : MonoBehaviour
{
    // ━━━ 싱글톤 ━━━
    public static PartyFinderManager Instance { get; private set; }

    // ━━━ 상수 ━━━
    public const int TITLE_MAX_LENGTH = 30;
    public const int MAX_LISTINGS_PER_PLAYER = 1;

    // ━━━ 상태 ━━━
    private List<Network.PartyFinderListingInfo> _listings = new List<Network.PartyFinderListingInfo>();
    private bool _isPanelOpen;
    private byte _currentCategoryFilter = 0xFF;

    // ━━━ 프로퍼티 ━━━
    public IReadOnlyList<Network.PartyFinderListingInfo> Listings => _listings;
    public bool IsPanelOpen => _isPanelOpen;
    public byte CurrentCategoryFilter => _currentCategoryFilter;

    // ━━━ 이벤트 ━━━
    public event Action OnListingsChanged;
    public event Action OnPanelOpened;
    public event Action OnPanelClosed;

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
            nm.OnPartyFinderList += HandlePartyFinderList;
        }
    }

    private void OnDestroy()
    {
        var nm = Network.NetworkManager.Instance;
        if (nm != null)
        {
            nm.OnPartyFinderList -= HandlePartyFinderList;
        }
        if (Instance == this) Instance = null;
    }

    // ━━━ 이벤트 핸들러 ━━━

    private void HandlePartyFinderList(Network.PartyFinderListData data)
    {
        _listings.Clear();
        if (data.Listings != null)
            _listings.AddRange(data.Listings);
        OnListingsChanged?.Invoke();
    }

    // ━━━ 공개 API ━━━

    public void OpenPanel()
    {
        _isPanelOpen = true;
        OnPanelOpened?.Invoke();
    }

    public void ClosePanel()
    {
        _isPanelOpen = false;
        OnPanelClosed?.Invoke();
    }

    public void RefreshList(byte category = 0xFF)
    {
        _currentCategoryFilter = category;
        Network.NetworkManager.Instance?.RequestPartyFinderList(category);
    }

    public void CreateListing(string title, Network.PartyFinderCategory category, byte minLevel, Network.PartyFinderRole role)
    {
        string trimmedTitle = title.Length > TITLE_MAX_LENGTH ? title.Substring(0, TITLE_MAX_LENGTH) : title;
        Network.NetworkManager.Instance?.CreatePartyFinderListing(trimmedTitle, (byte)category, minLevel, (byte)role);
    }
}
