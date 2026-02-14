// ━━━ CurrencyManager.cs ━━━
// 보조 화폐/토큰 상점 관리 (S054 TASK 10)
// MsgType: 468-473 — 화폐 조회/토큰 상점 목록/구매

using System;
using System.Collections.Generic;
using UnityEngine;

public class CurrencyManager : MonoBehaviour
{
    // ━━━ 싱글톤 ━━━
    public static CurrencyManager Instance { get; private set; }

    // ━━━ 상수 (GDD economy.yaml) ━━━
    public const uint MAX_GOLD = 999999999;
    public const uint MAX_SILVER = 99999999;
    public const uint MAX_TOKEN = 99999;

    // ━━━ 상태 ━━━
    private uint _gold;
    private uint _silver;
    private uint _dungeonToken;
    private uint _pvpToken;
    private uint _guildContribution;
    private bool _isCurrencyPanelOpen;
    private bool _isTokenShopOpen;
    private Network.TokenShopType _currentShopType;
    private Network.TokenShopItem[] _currentShopItems = new Network.TokenShopItem[0];

    // ━━━ 프로퍼티 ━━━
    public uint Gold => _gold;
    public uint Silver => _silver;
    public uint DungeonToken => _dungeonToken;
    public uint PvpToken => _pvpToken;
    public uint GuildContribution => _guildContribution;
    public bool IsCurrencyPanelOpen => _isCurrencyPanelOpen;
    public bool IsTokenShopOpen => _isTokenShopOpen;
    public Network.TokenShopType CurrentShopType => _currentShopType;
    public Network.TokenShopItem[] CurrentShopItems => _currentShopItems;

    // ━━━ 이벤트 ━━━
    public event Action<Network.CurrencyInfoData> OnCurrencyChanged;
    public event Action<Network.TokenShopData> OnTokenShopListReceived;
    public event Action<Network.TokenShopBuyResultData> OnTokenShopBuyComplete;
    public event Action OnCurrencyPanelOpened;
    public event Action OnCurrencyPanelClosed;
    public event Action OnTokenShopOpened;
    public event Action OnTokenShopClosed;

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
            nm.OnCurrencyInfo += HandleCurrencyInfo;
            nm.OnTokenShop += HandleTokenShop;
            nm.OnTokenShopBuyResult += HandleTokenShopBuyResult;
        }
    }

    private void OnDestroy()
    {
        var nm = Network.NetworkManager.Instance;
        if (nm != null)
        {
            nm.OnCurrencyInfo -= HandleCurrencyInfo;
            nm.OnTokenShop -= HandleTokenShop;
            nm.OnTokenShopBuyResult -= HandleTokenShopBuyResult;
        }
        if (Instance == this) Instance = null;
    }

    // ━━━ 핸들러 ━━━

    private void HandleCurrencyInfo(Network.CurrencyInfoData data)
    {
        _gold = data.Gold;
        _silver = data.Silver;
        _dungeonToken = data.DungeonToken;
        _pvpToken = data.PvpToken;
        _guildContribution = data.GuildContribution;
        OnCurrencyChanged?.Invoke(data);
    }

    private void HandleTokenShop(Network.TokenShopData data)
    {
        _currentShopType = data.ShopType;
        _currentShopItems = data.Items;
        OnTokenShopListReceived?.Invoke(data);
    }

    private void HandleTokenShopBuyResult(Network.TokenShopBuyResultData data)
    {
        if (data.Result == Network.TokenShopBuyResult.SUCCESS)
        {
            QueryCurrency();
        }
        OnTokenShopBuyComplete?.Invoke(data);
    }

    // ━━━ 공개 API ━━━

    public void OpenCurrencyPanel()
    {
        _isCurrencyPanelOpen = true;
        QueryCurrency();
        OnCurrencyPanelOpened?.Invoke();
    }

    public void CloseCurrencyPanel()
    {
        _isCurrencyPanelOpen = false;
        OnCurrencyPanelClosed?.Invoke();
    }

    public void OpenTokenShop(Network.TokenShopType shopType)
    {
        _isTokenShopOpen = true;
        _currentShopType = shopType;
        Network.NetworkManager.Instance?.RequestTokenShopList((byte)shopType);
        OnTokenShopOpened?.Invoke();
    }

    public void CloseTokenShop()
    {
        _isTokenShopOpen = false;
        _currentShopItems = new Network.TokenShopItem[0];
        OnTokenShopClosed?.Invoke();
    }

    public void QueryCurrency()
    {
        Network.NetworkManager.Instance?.RequestCurrencyQuery();
    }

    public void BuyTokenShopItem(ushort shopId, byte quantity)
    {
        Network.NetworkManager.Instance?.RequestTokenShopBuy(shopId, quantity);
    }

    public uint GetCurrencyByType(Network.TokenShopType shopType)
    {
        switch (shopType)
        {
            case Network.TokenShopType.DUNGEON: return _dungeonToken;
            case Network.TokenShopType.PVP: return _pvpToken;
            case Network.TokenShopType.GUILD: return _guildContribution;
            default: return 0;
        }
    }

    public string GetCurrencyName(Network.TokenShopType shopType)
    {
        switch (shopType)
        {
            case Network.TokenShopType.DUNGEON: return "Dungeon Token";
            case Network.TokenShopType.PVP: return "PvP Token";
            case Network.TokenShopType.GUILD: return "Guild Contribution";
            default: return "Unknown";
        }
    }
}
