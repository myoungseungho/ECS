// ━━━ AuctionUI.cs ━━━
// 거래소 UI — 목록 조회, 카테고리 필터, 정렬, 페이지네이션, 등록, 즉시구매, 입찰
// AuctionManager 이벤트 구독 (Y키 토글)

using UnityEngine;
using UnityEngine.UI;
using Network;

public class AuctionUI : MonoBehaviour
{
    // ━━━ UI 참조 (Start에서 코드 생성) ━━━
    private GameObject _panel;
    private Text _titleText;
    private Text _itemListText;
    private Text _pageText;
    private Text _statusText;
    private Button[] _categoryButtons;
    private Button[] _sortButtons;
    private Button _prevPageButton;
    private Button _nextPageButton;
    private Button _buyButton;
    private Button _bidButton;
    private Button _registerButton;
    private GameObject _confirmPopup;
    private Text _confirmText;
    private Button _confirmYesButton;
    private Button _confirmNoButton;

    private int _selectedItemIndex = -1;
    private enum ConfirmAction { None, Buy, Bid, Register }
    private ConfirmAction _pendingAction = ConfirmAction.None;
    private uint _pendingAuctionId;

    private void Start()
    {
        BuildUI();

        if (AuctionManager.Instance != null)
        {
            AuctionManager.Instance.OnListingChanged += HandleListingChanged;
            AuctionManager.Instance.OnRegisterResult += HandleRegisterResult;
            AuctionManager.Instance.OnBuyResult += HandleBuyResult;
            AuctionManager.Instance.OnBidResult += HandleBidResult;
            AuctionManager.Instance.OnPanelOpened += ShowPanel;
            AuctionManager.Instance.OnPanelClosed += HidePanel;
        }

        if (_panel != null) _panel.SetActive(false);
    }

    private void OnDestroy()
    {
        if (AuctionManager.Instance != null)
        {
            AuctionManager.Instance.OnListingChanged -= HandleListingChanged;
            AuctionManager.Instance.OnRegisterResult -= HandleRegisterResult;
            AuctionManager.Instance.OnBuyResult -= HandleBuyResult;
            AuctionManager.Instance.OnBidResult -= HandleBidResult;
            AuctionManager.Instance.OnPanelOpened -= ShowPanel;
            AuctionManager.Instance.OnPanelClosed -= HidePanel;
        }
    }

    private void Update()
    {
        // Y키로 거래소 토글
        if (Input.GetKeyDown(KeyCode.Y))
        {
            if (AuctionManager.Instance != null)
            {
                if (AuctionManager.Instance.IsPanelOpen)
                    AuctionManager.Instance.ClosePanel();
                else
                    AuctionManager.Instance.OpenPanel();
            }
        }

        // ESC로 닫기
        if (_panel != null && _panel.activeSelf && Input.GetKeyDown(KeyCode.Escape))
        {
            if (_confirmPopup != null && _confirmPopup.activeSelf)
                _confirmPopup.SetActive(false);
            else
                AuctionManager.Instance?.ClosePanel();
        }

        // 숫자키로 아이템 선택 (1~9)
        if (_panel != null && _panel.activeSelf)
        {
            for (int i = 0; i < 9; i++)
            {
                if (Input.GetKeyDown(KeyCode.Alpha1 + i))
                {
                    if (AuctionManager.Instance != null && i < AuctionManager.Instance.Listings.Count)
                    {
                        _selectedItemIndex = i;
                        RefreshItemList();
                    }
                }
            }
        }
    }

    // ━━━ UI 구성 (코드 생성) ━━━

    private void BuildUI()
    {
        // Panel
        _panel = new GameObject("AuctionPanel");
        _panel.transform.SetParent(transform, false);
        var panelRT = _panel.AddComponent<RectTransform>();
        panelRT.anchorMin = new Vector2(0.1f, 0.05f);
        panelRT.anchorMax = new Vector2(0.9f, 0.95f);
        panelRT.offsetMin = Vector2.zero;
        panelRT.offsetMax = Vector2.zero;
        var panelBg = _panel.AddComponent<Image>();
        panelBg.color = new Color(0.07f, 0.07f, 0.1f, 0.95f);

        // Title
        var titleGo = CreateText(_panel.transform, "Title", "Auction House",
            new Vector2(0.5f, 1f), new Vector2(0.5f, 1f), new Vector2(0, -10), new Vector2(300, 35));
        _titleText = titleGo.GetComponent<Text>();
        _titleText.fontSize = 22;
        _titleText.fontStyle = FontStyle.Bold;
        _titleText.alignment = TextAnchor.MiddleCenter;
        var titleRT = titleGo.GetComponent<RectTransform>();
        titleRT.pivot = new Vector2(0.5f, 1f);

        // Category Buttons
        string[] categoryNames = { "All", "Weapon", "Armor", "Potion", "Gem", "Material", "Other" };
        byte[] categoryValues = { 0xFF, 0, 1, 2, 3, 4, 5 };
        _categoryButtons = new Button[categoryNames.Length];
        float btnWidth = 90f;
        float startX = 15f;

        for (int i = 0; i < categoryNames.Length; i++)
        {
            var btnGo = new GameObject($"Cat_{categoryNames[i]}");
            btnGo.transform.SetParent(_panel.transform, false);
            var btnRT = btnGo.AddComponent<RectTransform>();
            btnRT.anchorMin = new Vector2(0f, 1f);
            btnRT.anchorMax = new Vector2(0f, 1f);
            btnRT.pivot = new Vector2(0f, 1f);
            btnRT.anchoredPosition = new Vector2(startX + i * (btnWidth + 4), -50);
            btnRT.sizeDelta = new Vector2(btnWidth, 28);
            var btnImg = btnGo.AddComponent<Image>();
            btnImg.color = i == 0 ? new Color(0.3f, 0.2f, 0.5f) : new Color(0.2f, 0.2f, 0.25f);
            var btn = btnGo.AddComponent<Button>();
            _categoryButtons[i] = btn;

            var btnTextGo = CreateText(btnGo.transform, "Text", categoryNames[i],
                Vector2.zero, Vector2.one, Vector2.zero, Vector2.zero);
            var btnTextRT = btnTextGo.GetComponent<RectTransform>();
            btnTextRT.anchorMin = Vector2.zero;
            btnTextRT.anchorMax = Vector2.one;
            btnTextRT.offsetMin = Vector2.zero;
            btnTextRT.offsetMax = Vector2.zero;
            btnTextGo.GetComponent<Text>().alignment = TextAnchor.MiddleCenter;
            btnTextGo.GetComponent<Text>().fontSize = 12;

            byte catVal = categoryValues[i];
            int catIdx = i;
            btn.onClick.AddListener(() => OnCategoryClicked(catVal, catIdx));
        }

        // Sort Buttons
        string[] sortNames = { "Price Asc", "Price Desc", "Newest" };
        _sortButtons = new Button[sortNames.Length];
        float sortStartX = 15f;

        for (int i = 0; i < sortNames.Length; i++)
        {
            var btnGo = new GameObject($"Sort_{sortNames[i]}");
            btnGo.transform.SetParent(_panel.transform, false);
            var btnRT = btnGo.AddComponent<RectTransform>();
            btnRT.anchorMin = new Vector2(0f, 1f);
            btnRT.anchorMax = new Vector2(0f, 1f);
            btnRT.pivot = new Vector2(0f, 1f);
            btnRT.anchoredPosition = new Vector2(sortStartX + i * 105, -82);
            btnRT.sizeDelta = new Vector2(100, 24);
            var btnImg = btnGo.AddComponent<Image>();
            btnImg.color = i == 0 ? new Color(0.2f, 0.4f, 0.3f) : new Color(0.2f, 0.2f, 0.25f);
            var btn = btnGo.AddComponent<Button>();
            _sortButtons[i] = btn;

            var btnTextGo = CreateText(btnGo.transform, "Text", sortNames[i],
                Vector2.zero, Vector2.one, Vector2.zero, Vector2.zero);
            var btnTextRT = btnTextGo.GetComponent<RectTransform>();
            btnTextRT.anchorMin = Vector2.zero;
            btnTextRT.anchorMax = Vector2.one;
            btnTextRT.offsetMin = Vector2.zero;
            btnTextRT.offsetMax = Vector2.zero;
            btnTextGo.GetComponent<Text>().alignment = TextAnchor.MiddleCenter;
            btnTextGo.GetComponent<Text>().fontSize = 12;

            byte sortVal = (byte)i;
            int sortIdx = i;
            btn.onClick.AddListener(() => OnSortClicked(sortVal, sortIdx));
        }

        // Item List Area
        var listGo = CreateText(_panel.transform, "ItemList", "Open the auction house to browse listings.",
            new Vector2(0f, 0f), new Vector2(1f, 1f), Vector2.zero, Vector2.zero);
        var listRT = listGo.GetComponent<RectTransform>();
        listRT.anchorMin = new Vector2(0f, 0.15f);
        listRT.anchorMax = new Vector2(1f, 0.8f);
        listRT.offsetMin = new Vector2(15, 0);
        listRT.offsetMax = new Vector2(-15, -5);
        _itemListText = listGo.GetComponent<Text>();
        _itemListText.fontSize = 13;
        _itemListText.alignment = TextAnchor.UpperLeft;

        // Page Controls
        float bottomY = 10f;

        // Prev Page
        var prevGo = new GameObject("PrevPage");
        prevGo.transform.SetParent(_panel.transform, false);
        var prevRT = prevGo.AddComponent<RectTransform>();
        prevRT.anchorMin = new Vector2(0.3f, 0f);
        prevRT.anchorMax = new Vector2(0.3f, 0f);
        prevRT.pivot = new Vector2(0.5f, 0f);
        prevRT.anchoredPosition = new Vector2(0, bottomY);
        prevRT.sizeDelta = new Vector2(80, 28);
        var prevImg = prevGo.AddComponent<Image>();
        prevImg.color = new Color(0.25f, 0.25f, 0.3f);
        _prevPageButton = prevGo.AddComponent<Button>();
        _prevPageButton.onClick.AddListener(OnPrevPage);
        var prevTextGo = CreateText(prevGo.transform, "Text", "< Prev",
            Vector2.zero, Vector2.one, Vector2.zero, Vector2.zero);
        SetFillRT(prevTextGo);
        prevTextGo.GetComponent<Text>().alignment = TextAnchor.MiddleCenter;

        // Page Text
        var pageGo = CreateText(_panel.transform, "PageText", "Page 1/1",
            new Vector2(0.5f, 0f), new Vector2(0.5f, 0f), new Vector2(0, bottomY + 4), new Vector2(120, 24));
        _pageText = pageGo.GetComponent<Text>();
        _pageText.fontSize = 14;
        _pageText.alignment = TextAnchor.MiddleCenter;
        var pageRT = pageGo.GetComponent<RectTransform>();
        pageRT.pivot = new Vector2(0.5f, 0f);

        // Next Page
        var nextGo = new GameObject("NextPage");
        nextGo.transform.SetParent(_panel.transform, false);
        var nextRT = nextGo.AddComponent<RectTransform>();
        nextRT.anchorMin = new Vector2(0.7f, 0f);
        nextRT.anchorMax = new Vector2(0.7f, 0f);
        nextRT.pivot = new Vector2(0.5f, 0f);
        nextRT.anchoredPosition = new Vector2(0, bottomY);
        nextRT.sizeDelta = new Vector2(80, 28);
        var nextImg = nextGo.AddComponent<Image>();
        nextImg.color = new Color(0.25f, 0.25f, 0.3f);
        _nextPageButton = nextGo.AddComponent<Button>();
        _nextPageButton.onClick.AddListener(OnNextPage);
        var nextTextGo = CreateText(nextGo.transform, "Text", "Next >",
            Vector2.zero, Vector2.one, Vector2.zero, Vector2.zero);
        SetFillRT(nextTextGo);
        nextTextGo.GetComponent<Text>().alignment = TextAnchor.MiddleCenter;

        // Action Buttons (우하단)
        float actionX = -15f;

        // Buy Button
        _buyButton = CreateActionButton("BuyButton", "Buy", new Vector2(1f, 0.12f), new Vector2(actionX - 260, 0), OnBuyClicked);
        // Bid Button
        _bidButton = CreateActionButton("BidButton", "Bid", new Vector2(1f, 0.12f), new Vector2(actionX - 130, 0), OnBidClicked);
        // Register Button
        _registerButton = CreateActionButton("RegisterButton", "Register", new Vector2(1f, 0.12f), new Vector2(actionX, 0), OnRegisterClicked);

        // Status Text
        var statusGo = CreateText(_panel.transform, "StatusText", "",
            new Vector2(0f, 0.12f), new Vector2(0f, 0.12f), new Vector2(15, 0), new Vector2(400, 25));
        _statusText = statusGo.GetComponent<Text>();
        _statusText.fontSize = 14;
        _statusText.alignment = TextAnchor.MiddleLeft;
        var statusRT = statusGo.GetComponent<RectTransform>();
        statusRT.pivot = new Vector2(0f, 0.5f);

        // Confirm Popup
        BuildConfirmPopup();
    }

    private Button CreateActionButton(string name, string label, Vector2 anchor, Vector2 offset, UnityEngine.Events.UnityAction callback)
    {
        var go = new GameObject(name);
        go.transform.SetParent(_panel.transform, false);
        var rt = go.AddComponent<RectTransform>();
        rt.anchorMin = anchor;
        rt.anchorMax = anchor;
        rt.pivot = new Vector2(1f, 0.5f);
        rt.anchoredPosition = offset;
        rt.sizeDelta = new Vector2(120, 30);
        var img = go.AddComponent<Image>();
        img.color = new Color(0.2f, 0.4f, 0.6f);
        var btn = go.AddComponent<Button>();
        btn.onClick.AddListener(callback);

        var textGo = CreateText(go.transform, "Text", label,
            Vector2.zero, Vector2.one, Vector2.zero, Vector2.zero);
        SetFillRT(textGo);
        var t = textGo.GetComponent<Text>();
        t.alignment = TextAnchor.MiddleCenter;
        t.fontSize = 14;
        t.fontStyle = FontStyle.Bold;

        return btn;
    }

    private void BuildConfirmPopup()
    {
        _confirmPopup = new GameObject("ConfirmPopup");
        _confirmPopup.transform.SetParent(_panel.transform, false);
        var popRT = _confirmPopup.AddComponent<RectTransform>();
        popRT.anchorMin = new Vector2(0.25f, 0.3f);
        popRT.anchorMax = new Vector2(0.75f, 0.7f);
        popRT.offsetMin = Vector2.zero;
        popRT.offsetMax = Vector2.zero;
        var popBg = _confirmPopup.AddComponent<Image>();
        popBg.color = new Color(0.1f, 0.1f, 0.15f, 0.98f);

        var confTextGo = CreateText(_confirmPopup.transform, "ConfirmText", "Confirm action?",
            new Vector2(0.5f, 0.7f), new Vector2(0.5f, 0.7f), Vector2.zero, new Vector2(300, 60));
        _confirmText = confTextGo.GetComponent<Text>();
        _confirmText.fontSize = 16;
        _confirmText.alignment = TextAnchor.MiddleCenter;
        var confTextRT = confTextGo.GetComponent<RectTransform>();
        confTextRT.pivot = new Vector2(0.5f, 0.5f);

        // Yes Button
        var yesGo = new GameObject("YesButton");
        yesGo.transform.SetParent(_confirmPopup.transform, false);
        var yesRT = yesGo.AddComponent<RectTransform>();
        yesRT.anchorMin = new Vector2(0.15f, 0.1f);
        yesRT.anchorMax = new Vector2(0.45f, 0.35f);
        yesRT.offsetMin = Vector2.zero;
        yesRT.offsetMax = Vector2.zero;
        var yesImg = yesGo.AddComponent<Image>();
        yesImg.color = new Color(0.2f, 0.6f, 0.3f);
        _confirmYesButton = yesGo.AddComponent<Button>();
        _confirmYesButton.onClick.AddListener(OnConfirmYes);
        var yesTextGo = CreateText(yesGo.transform, "Text", "Confirm",
            Vector2.zero, Vector2.one, Vector2.zero, Vector2.zero);
        SetFillRT(yesTextGo);
        yesTextGo.GetComponent<Text>().alignment = TextAnchor.MiddleCenter;

        // No Button
        var noGo = new GameObject("NoButton");
        noGo.transform.SetParent(_confirmPopup.transform, false);
        var noRT = noGo.AddComponent<RectTransform>();
        noRT.anchorMin = new Vector2(0.55f, 0.1f);
        noRT.anchorMax = new Vector2(0.85f, 0.35f);
        noRT.offsetMin = Vector2.zero;
        noRT.offsetMax = Vector2.zero;
        var noImg = noGo.AddComponent<Image>();
        noImg.color = new Color(0.6f, 0.2f, 0.2f);
        _confirmNoButton = noGo.AddComponent<Button>();
        _confirmNoButton.onClick.AddListener(OnConfirmNo);
        var noTextGo = CreateText(noGo.transform, "Text", "Cancel",
            Vector2.zero, Vector2.one, Vector2.zero, Vector2.zero);
        SetFillRT(noTextGo);
        noTextGo.GetComponent<Text>().alignment = TextAnchor.MiddleCenter;

        _confirmPopup.SetActive(false);
    }

    // ━━━ 이벤트 핸들러 ━━━

    private void HandleListingChanged()
    {
        RefreshItemList();
    }

    private void HandleRegisterResult(AuctionRegisterResultData data)
    {
        if (_statusText != null)
        {
            if (data.Result == AuctionRegisterResult.SUCCESS)
            {
                _statusText.text = $"Registered! Auction #{data.AuctionId}";
                _statusText.color = Color.green;
            }
            else
            {
                _statusText.text = $"Register failed: {data.Result}";
                _statusText.color = Color.red;
            }
        }
        if (_confirmPopup != null) _confirmPopup.SetActive(false);
    }

    private void HandleBuyResult(AuctionBuyResultData data)
    {
        if (_statusText != null)
        {
            if (data.Result == AuctionBuyResult.SUCCESS)
            {
                _statusText.text = $"Purchased auction #{data.AuctionId}!";
                _statusText.color = Color.green;
            }
            else
            {
                _statusText.text = $"Buy failed: {data.Result}";
                _statusText.color = Color.red;
            }
        }
        if (_confirmPopup != null) _confirmPopup.SetActive(false);
    }

    private void HandleBidResult(AuctionBidResultData data)
    {
        if (_statusText != null)
        {
            if (data.Result == AuctionBidResult.SUCCESS)
            {
                _statusText.text = $"Bid placed on auction #{data.AuctionId}!";
                _statusText.color = Color.green;
            }
            else
            {
                _statusText.text = $"Bid failed: {data.Result}";
                _statusText.color = Color.red;
            }
        }
        if (_confirmPopup != null) _confirmPopup.SetActive(false);
    }

    private void ShowPanel()
    {
        if (_panel != null) _panel.SetActive(true);
        _selectedItemIndex = -1;
        RefreshItemList();
    }

    private void HidePanel()
    {
        if (_panel != null) _panel.SetActive(false);
        if (_confirmPopup != null) _confirmPopup.SetActive(false);
    }

    // ━━━ UI 갱신 ━━━

    private void RefreshItemList()
    {
        if (_itemListText == null || AuctionManager.Instance == null) return;

        var items = AuctionManager.Instance.Listings;
        if (items.Count == 0)
        {
            _itemListText.text = "No listings found.";
            UpdatePageText();
            return;
        }

        var sb = new System.Text.StringBuilder();
        sb.AppendLine($"Listings ({AuctionManager.Instance.TotalCount} total):");
        sb.AppendLine("  #   ID      Item     Qty   Buyout      Bid       Seller");
        sb.AppendLine("──────────────────────────────────────────────────────────");
        for (int i = 0; i < items.Count; i++)
        {
            var it = items[i];
            string marker = (i == _selectedItemIndex) ? ">>>" : "   ";
            sb.AppendLine($"{marker}[{i + 1}] #{it.AuctionId,-5} Item:{it.ItemId,-5} x{it.Count}  {it.BuyoutPrice,8}g  {it.CurrentBid,8}g  {it.SellerName}");
        }
        _itemListText.text = sb.ToString();

        UpdatePageText();
    }

    private void UpdatePageText()
    {
        if (_pageText != null && AuctionManager.Instance != null)
        {
            _pageText.text = $"Page {AuctionManager.Instance.CurrentPage + 1}/{System.Math.Max(1, AuctionManager.Instance.TotalPages)}";
        }
    }

    // ━━━ 버튼 콜백 ━━━

    private void OnCategoryClicked(byte categoryValue, int btnIndex)
    {
        _selectedItemIndex = -1;

        for (int i = 0; i < _categoryButtons.Length; i++)
        {
            var img = _categoryButtons[i].GetComponent<Image>();
            if (img != null)
                img.color = (i == btnIndex) ? new Color(0.3f, 0.2f, 0.5f) : new Color(0.2f, 0.2f, 0.25f);
        }

        AuctionManager.Instance?.RequestListings(categoryValue, 0, AuctionManager.Instance.CurrentSortBy);
    }

    private void OnSortClicked(byte sortValue, int btnIndex)
    {
        _selectedItemIndex = -1;

        for (int i = 0; i < _sortButtons.Length; i++)
        {
            var img = _sortButtons[i].GetComponent<Image>();
            if (img != null)
                img.color = (i == btnIndex) ? new Color(0.2f, 0.4f, 0.3f) : new Color(0.2f, 0.2f, 0.25f);
        }

        AuctionManager.Instance?.RequestListings(AuctionManager.Instance.CurrentCategory, 0, sortValue);
    }

    private void OnPrevPage()
    {
        AuctionManager.Instance?.PrevPage();
    }

    private void OnNextPage()
    {
        AuctionManager.Instance?.NextPage();
    }

    private void OnBuyClicked()
    {
        if (AuctionManager.Instance == null) return;
        var items = AuctionManager.Instance.Listings;
        if (_selectedItemIndex < 0 || _selectedItemIndex >= items.Count) return;

        var item = items[_selectedItemIndex];
        _pendingAction = ConfirmAction.Buy;
        _pendingAuctionId = item.AuctionId;
        if (_confirmText != null)
            _confirmText.text = $"Buy Item:{item.ItemId} x{item.Count} for {item.BuyoutPrice}g?";
        if (_confirmPopup != null) _confirmPopup.SetActive(true);
    }

    private void OnBidClicked()
    {
        if (AuctionManager.Instance == null) return;
        var items = AuctionManager.Instance.Listings;
        if (_selectedItemIndex < 0 || _selectedItemIndex >= items.Count) return;

        var item = items[_selectedItemIndex];
        uint bidAmount = item.CurrentBid > 0 ? item.CurrentBid + 100 : item.BuyoutPrice / 2;
        _pendingAction = ConfirmAction.Bid;
        _pendingAuctionId = item.AuctionId;
        if (_confirmText != null)
            _confirmText.text = $"Bid {bidAmount}g on Item:{item.ItemId}?";
        if (_confirmPopup != null) _confirmPopup.SetActive(true);
    }

    private void OnRegisterClicked()
    {
        _pendingAction = ConfirmAction.Register;
        if (_confirmText != null)
            _confirmText.text = "Register slot 0 item for 1000g?";
        if (_confirmPopup != null) _confirmPopup.SetActive(true);
    }

    private void OnConfirmYes()
    {
        if (AuctionManager.Instance == null) return;

        switch (_pendingAction)
        {
            case ConfirmAction.Buy:
                AuctionManager.Instance.BuyItem(_pendingAuctionId);
                break;
            case ConfirmAction.Bid:
            {
                var items = AuctionManager.Instance.Listings;
                if (_selectedItemIndex >= 0 && _selectedItemIndex < items.Count)
                {
                    var item = items[_selectedItemIndex];
                    uint bidAmount = item.CurrentBid > 0 ? item.CurrentBid + 100 : item.BuyoutPrice / 2;
                    AuctionManager.Instance.PlaceBid(_pendingAuctionId, bidAmount);
                }
                break;
            }
            case ConfirmAction.Register:
                AuctionManager.Instance.RegisterItem(0, 1, 1000, 0xFF);
                break;
        }

        _pendingAction = ConfirmAction.None;
    }

    private void OnConfirmNo()
    {
        _pendingAction = ConfirmAction.None;
        if (_confirmPopup != null)
            _confirmPopup.SetActive(false);
    }

    // ━━━ 유틸 ━━━

    private static void SetFillRT(GameObject go)
    {
        var rt = go.GetComponent<RectTransform>();
        rt.anchorMin = Vector2.zero;
        rt.anchorMax = Vector2.one;
        rt.offsetMin = Vector2.zero;
        rt.offsetMax = Vector2.zero;
    }

    private static GameObject CreateText(Transform parent, string name, string text,
        Vector2 anchorMin, Vector2 anchorMax, Vector2 anchoredPos, Vector2 sizeDelta)
    {
        var go = new GameObject(name);
        go.transform.SetParent(parent, false);
        var rt = go.AddComponent<RectTransform>();
        rt.anchorMin = anchorMin;
        rt.anchorMax = anchorMax;
        rt.pivot = new Vector2(0f, 1f);
        rt.anchoredPosition = anchoredPos;
        rt.sizeDelta = sizeDelta;

        var t = go.AddComponent<Text>();
        t.text = text;
        t.fontSize = 14;
        t.color = Color.white;
        t.alignment = TextAnchor.UpperLeft;
        t.font = Resources.GetBuiltinResource<Font>("LegacyRuntime.ttf");

        return go;
    }
}
