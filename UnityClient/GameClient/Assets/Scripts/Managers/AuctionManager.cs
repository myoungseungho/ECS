// ━━━ AuctionManager.cs ━━━
// 거래소 시스템 관리 — 목록 조회/등록/즉시구매/입찰
// NetworkManager 이벤트 구독 → AuctionUI에 이벤트 발행

using System;
using System.Collections.Generic;
using UnityEngine;
using Network;

public class AuctionManager : MonoBehaviour
{
    // ━━━ 상태 ━━━
    private readonly List<AuctionListingInfo> _listings = new List<AuctionListingInfo>();
    private ushort _totalCount;
    private byte _totalPages;
    private byte _currentPage;
    private byte _currentCategory = 0xFF;
    private byte _currentSortBy;
    private bool _isPanelOpen;

    // ━━━ 프로퍼티 ━━━
    public IReadOnlyList<AuctionListingInfo> Listings => _listings;
    public ushort TotalCount => _totalCount;
    public byte TotalPages => _totalPages;
    public byte CurrentPage => _currentPage;
    public byte CurrentCategory => _currentCategory;
    public byte CurrentSortBy => _currentSortBy;
    public bool IsPanelOpen => _isPanelOpen;

    // ━━━ 이벤트 ━━━
    public event Action OnListingChanged;
    public event Action<AuctionRegisterResultData> OnRegisterResult;
    public event Action<AuctionBuyResultData> OnBuyResult;
    public event Action<AuctionBidResultData> OnBidResult;
    public event Action OnPanelOpened;
    public event Action OnPanelClosed;

    // ━━━ 싱글톤 (Scene-bound) ━━━
    public static AuctionManager Instance { get; private set; }

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
        net.OnAuctionList += HandleAuctionList;
        net.OnAuctionRegisterResult += HandleRegisterResult;
        net.OnAuctionBuyResult += HandleBuyResult;
        net.OnAuctionBidResult += HandleBidResult;
    }

    private void OnDestroy()
    {
        var net = NetworkManager.Instance;
        if (net == null) return;

        net.OnAuctionList -= HandleAuctionList;
        net.OnAuctionRegisterResult -= HandleRegisterResult;
        net.OnAuctionBuyResult -= HandleBuyResult;
        net.OnAuctionBidResult -= HandleBidResult;

        if (Instance == this) Instance = null;
    }

    // ━━━ 공개 API ━━━

    /// <summary>거래소 패널 열기</summary>
    public void OpenPanel()
    {
        _isPanelOpen = true;
        _currentPage = 0;
        _currentCategory = 0xFF;
        _currentSortBy = 0;
        NetworkManager.Instance.RequestAuctionList(_currentCategory, _currentPage, _currentSortBy);
        OnPanelOpened?.Invoke();
    }

    /// <summary>거래소 패널 닫기</summary>
    public void ClosePanel()
    {
        _isPanelOpen = false;
        OnPanelClosed?.Invoke();
    }

    /// <summary>카테고리/정렬/페이지로 목록 요청</summary>
    public void RequestListings(byte category, byte page, byte sortBy)
    {
        _currentCategory = category;
        _currentPage = page;
        _currentSortBy = sortBy;
        NetworkManager.Instance.RequestAuctionList(category, page, sortBy);
    }

    /// <summary>다음 페이지</summary>
    public void NextPage()
    {
        if (_currentPage + 1 < _totalPages)
        {
            _currentPage++;
            NetworkManager.Instance.RequestAuctionList(_currentCategory, _currentPage, _currentSortBy);
        }
    }

    /// <summary>이전 페이지</summary>
    public void PrevPage()
    {
        if (_currentPage > 0)
        {
            _currentPage--;
            NetworkManager.Instance.RequestAuctionList(_currentCategory, _currentPage, _currentSortBy);
        }
    }

    /// <summary>아이템 등록</summary>
    public void RegisterItem(byte slotIdx, byte count, uint buyoutPrice, byte category)
    {
        NetworkManager.Instance.RegisterAuction(slotIdx, count, buyoutPrice, category);
    }

    /// <summary>즉시 구매</summary>
    public void BuyItem(uint auctionId)
    {
        NetworkManager.Instance.BuyAuction(auctionId);
    }

    /// <summary>입찰</summary>
    public void PlaceBid(uint auctionId, uint bidAmount)
    {
        NetworkManager.Instance.BidAuction(auctionId, bidAmount);
    }

    // ━━━ 핸들러 ━━━

    private void HandleAuctionList(AuctionListData data)
    {
        _totalCount = data.TotalCount;
        _totalPages = data.TotalPages;
        _currentPage = data.CurrentPage;
        _listings.Clear();
        _listings.AddRange(data.Items);

        Debug.Log($"[AuctionManager] List: {data.Items.Length} items, total={data.TotalCount}, page={data.CurrentPage}/{data.TotalPages}");
        OnListingChanged?.Invoke();
    }

    private void HandleRegisterResult(AuctionRegisterResultData data)
    {
        Debug.Log($"[AuctionManager] Register: result={data.Result}, auctionId={data.AuctionId}");
        OnRegisterResult?.Invoke(data);

        if (data.Result == AuctionRegisterResult.SUCCESS)
        {
            NetworkManager.Instance.RequestAuctionList(_currentCategory, _currentPage, _currentSortBy);
        }
    }

    private void HandleBuyResult(AuctionBuyResultData data)
    {
        Debug.Log($"[AuctionManager] Buy: result={data.Result}, auctionId={data.AuctionId}");
        OnBuyResult?.Invoke(data);

        if (data.Result == AuctionBuyResult.SUCCESS)
        {
            NetworkManager.Instance.RequestAuctionList(_currentCategory, _currentPage, _currentSortBy);
        }
    }

    private void HandleBidResult(AuctionBidResultData data)
    {
        Debug.Log($"[AuctionManager] Bid: result={data.Result}, auctionId={data.AuctionId}");
        OnBidResult?.Invoke(data);

        if (data.Result == AuctionBidResult.SUCCESS)
        {
            NetworkManager.Instance.RequestAuctionList(_currentCategory, _currentPage, _currentSortBy);
        }
    }
}
