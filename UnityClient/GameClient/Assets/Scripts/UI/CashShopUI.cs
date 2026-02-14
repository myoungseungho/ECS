// ━━━ CashShopUI.cs ━━━
// 캐시샵 UI — 카테고리 선택, 아이템 목록, 크리스탈 잔액, 구매 확인, 월정액 표시
// CashShopManager 이벤트 구독 ($키 토글)

using UnityEngine;
using UnityEngine.UI;
using Network;

public class CashShopUI : MonoBehaviour
{
    // ━━━ UI 참조 (Start에서 코드 생성) ━━━
    private GameObject _panel;
    private Text _titleText;
    private Text _crystalText;
    private Text _itemListText;
    private Text _subscriptionText;
    private Text _statusText;
    private Button[] _categoryButtons;
    private Button _buyButton;
    private GameObject _confirmPopup;
    private Text _confirmText;
    private Button _confirmYesButton;
    private Button _confirmNoButton;

    private byte _selectedCategory;
    private int _selectedItemIndex = -1;

    private void Start()
    {
        BuildUI();

        if (CashShopManager.Instance != null)
        {
            CashShopManager.Instance.OnShopListChanged += HandleShopListChanged;
            CashShopManager.Instance.OnPurchaseResult += HandlePurchaseResult;
            CashShopManager.Instance.OnSubscriptionUpdated += HandleSubscriptionUpdated;
            CashShopManager.Instance.OnPanelOpened += ShowPanel;
            CashShopManager.Instance.OnPanelClosed += HidePanel;
        }

        if (_panel != null) _panel.SetActive(false);
    }

    private void OnDestroy()
    {
        if (CashShopManager.Instance != null)
        {
            CashShopManager.Instance.OnShopListChanged -= HandleShopListChanged;
            CashShopManager.Instance.OnPurchaseResult -= HandlePurchaseResult;
            CashShopManager.Instance.OnSubscriptionUpdated -= HandleSubscriptionUpdated;
            CashShopManager.Instance.OnPanelOpened -= ShowPanel;
            CashShopManager.Instance.OnPanelClosed -= HidePanel;
        }
    }

    private void Update()
    {
        // $키 (Alpha4 + Shift) 로 캐시샵 토글
        if (Input.GetKeyDown(KeyCode.Alpha4) && Input.GetKey(KeyCode.LeftShift))
        {
            if (CashShopManager.Instance != null)
            {
                if (CashShopManager.Instance.IsPanelOpen)
                    CashShopManager.Instance.ClosePanel();
                else
                    CashShopManager.Instance.OpenPanel();
            }
        }

        // ESC로 닫기
        if (_panel != null && _panel.activeSelf && Input.GetKeyDown(KeyCode.Escape))
        {
            if (_confirmPopup != null && _confirmPopup.activeSelf)
                _confirmPopup.SetActive(false);
            else
                CashShopManager.Instance?.ClosePanel();
        }
    }

    // ━━━ UI 구성 (코드 생성) ━━━

    private void BuildUI()
    {
        // Panel (캔버스 위에 배치)
        _panel = new GameObject("CashShopPanel");
        _panel.transform.SetParent(transform, false);
        var panelRT = _panel.AddComponent<RectTransform>();
        panelRT.anchorMin = new Vector2(0.15f, 0.1f);
        panelRT.anchorMax = new Vector2(0.85f, 0.9f);
        panelRT.offsetMin = Vector2.zero;
        panelRT.offsetMax = Vector2.zero;
        var panelBg = _panel.AddComponent<Image>();
        panelBg.color = new Color(0.08f, 0.06f, 0.12f, 0.95f);

        // Title
        var titleGo = CreateText(_panel.transform, "Title", "Cash Shop",
            new Vector2(0.5f, 1f), new Vector2(0.5f, 1f), new Vector2(0, -10), new Vector2(300, 35));
        _titleText = titleGo.GetComponent<Text>();
        _titleText.fontSize = 22;
        _titleText.fontStyle = FontStyle.Bold;
        _titleText.alignment = TextAnchor.MiddleCenter;
        var titleRT = titleGo.GetComponent<RectTransform>();
        titleRT.pivot = new Vector2(0.5f, 1f);

        // Crystal Balance (우상단)
        var crystalGo = CreateText(_panel.transform, "CrystalText", "Crystals: 0",
            new Vector2(1f, 1f), new Vector2(1f, 1f), new Vector2(-15, -15), new Vector2(200, 25));
        _crystalText = crystalGo.GetComponent<Text>();
        _crystalText.fontSize = 16;
        _crystalText.fontStyle = FontStyle.Bold;
        _crystalText.color = new Color(0.4f, 0.8f, 1f);
        _crystalText.alignment = TextAnchor.MiddleRight;
        var crystalRT = crystalGo.GetComponent<RectTransform>();
        crystalRT.pivot = new Vector2(1f, 1f);

        // Category Buttons (상단 가로 배치)
        string[] categoryNames = { "All", "Cosmetic", "Convenience", "Mount", "Pet", "Emote" };
        _categoryButtons = new Button[categoryNames.Length];
        float btnWidth = 110f;
        float startX = 15f;

        for (int i = 0; i < categoryNames.Length; i++)
        {
            var btnGo = new GameObject($"Cat_{categoryNames[i]}");
            btnGo.transform.SetParent(_panel.transform, false);
            var btnRT = btnGo.AddComponent<RectTransform>();
            btnRT.anchorMin = new Vector2(0f, 1f);
            btnRT.anchorMax = new Vector2(0f, 1f);
            btnRT.pivot = new Vector2(0f, 1f);
            btnRT.anchoredPosition = new Vector2(startX + i * (btnWidth + 5), -50);
            btnRT.sizeDelta = new Vector2(btnWidth, 30);
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
            var btnText = btnTextGo.GetComponent<Text>();
            btnText.alignment = TextAnchor.MiddleCenter;
            btnText.fontSize = 13;

            int catIndex = i;
            btn.onClick.AddListener(() => OnCategoryClicked((byte)catIndex));
        }

        // Item List Area (중앙)
        var listGo = CreateText(_panel.transform, "ItemList", "Select a category to browse items.",
            new Vector2(0f, 0f), new Vector2(1f, 1f), Vector2.zero, Vector2.zero);
        var listRT = listGo.GetComponent<RectTransform>();
        listRT.anchorMin = new Vector2(0f, 0.15f);
        listRT.anchorMax = new Vector2(1f, 0.82f);
        listRT.offsetMin = new Vector2(15, 0);
        listRT.offsetMax = new Vector2(-15, -5);
        _itemListText = listGo.GetComponent<Text>();
        _itemListText.fontSize = 14;
        _itemListText.alignment = TextAnchor.UpperLeft;

        // Subscription Status (좌하단)
        var subGo = CreateText(_panel.transform, "SubscriptionText", "Subscription: --",
            new Vector2(0f, 0f), new Vector2(0f, 0f), new Vector2(15, 10), new Vector2(350, 25));
        _subscriptionText = subGo.GetComponent<Text>();
        _subscriptionText.fontSize = 13;
        _subscriptionText.color = new Color(0.8f, 0.7f, 0.3f);
        var subRT = subGo.GetComponent<RectTransform>();
        subRT.pivot = new Vector2(0f, 0f);

        // Status Text (하단 중앙)
        var statusGo = CreateText(_panel.transform, "StatusText", "",
            new Vector2(0.5f, 0f), new Vector2(0.5f, 0f), new Vector2(0, 40), new Vector2(400, 25));
        _statusText = statusGo.GetComponent<Text>();
        _statusText.fontSize = 14;
        _statusText.alignment = TextAnchor.MiddleCenter;
        var statusRT = statusGo.GetComponent<RectTransform>();
        statusRT.pivot = new Vector2(0.5f, 0f);

        // Buy Button (우하단)
        var buyGo = new GameObject("BuyButton");
        buyGo.transform.SetParent(_panel.transform, false);
        var buyRT = buyGo.AddComponent<RectTransform>();
        buyRT.anchorMin = new Vector2(1f, 0f);
        buyRT.anchorMax = new Vector2(1f, 0f);
        buyRT.pivot = new Vector2(1f, 0f);
        buyRT.anchoredPosition = new Vector2(-15, 10);
        buyRT.sizeDelta = new Vector2(120, 35);
        var buyImg = buyGo.AddComponent<Image>();
        buyImg.color = new Color(0.2f, 0.5f, 0.8f);
        _buyButton = buyGo.AddComponent<Button>();
        _buyButton.onClick.AddListener(OnBuyClicked);

        var buyTextGo = CreateText(buyGo.transform, "Text", "Buy",
            Vector2.zero, Vector2.one, Vector2.zero, Vector2.zero);
        var buyTextRT = buyTextGo.GetComponent<RectTransform>();
        buyTextRT.anchorMin = Vector2.zero;
        buyTextRT.anchorMax = Vector2.one;
        buyTextRT.offsetMin = Vector2.zero;
        buyTextRT.offsetMax = Vector2.zero;
        var buyText = buyTextGo.GetComponent<Text>();
        buyText.alignment = TextAnchor.MiddleCenter;
        buyText.fontSize = 16;
        buyText.fontStyle = FontStyle.Bold;

        // Confirm Popup (중앙 오버레이)
        BuildConfirmPopup();
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

        var confTextGo = CreateText(_confirmPopup.transform, "ConfirmText", "Purchase this item?",
            new Vector2(0.5f, 0.7f), new Vector2(0.5f, 0.7f), Vector2.zero, new Vector2(280, 60));
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
        var yesTextRT = yesTextGo.GetComponent<RectTransform>();
        yesTextRT.anchorMin = Vector2.zero;
        yesTextRT.anchorMax = Vector2.one;
        yesTextRT.offsetMin = Vector2.zero;
        yesTextRT.offsetMax = Vector2.zero;
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
        var noTextRT = noTextGo.GetComponent<RectTransform>();
        noTextRT.anchorMin = Vector2.zero;
        noTextRT.anchorMax = Vector2.one;
        noTextRT.offsetMin = Vector2.zero;
        noTextRT.offsetMax = Vector2.zero;
        noTextGo.GetComponent<Text>().alignment = TextAnchor.MiddleCenter;

        _confirmPopup.SetActive(false);
    }

    // ━━━ 이벤트 핸들러 ━━━

    private void HandleShopListChanged()
    {
        RefreshItemList();
    }

    private void HandlePurchaseResult(CashShopBuyResultData data)
    {
        if (_crystalText != null)
            _crystalText.text = $"Crystals: {data.RemainingCrystals}";

        if (_statusText != null)
        {
            if (data.Result == CashShopBuyResult.SUCCESS)
            {
                _statusText.text = $"Purchase successful! Item #{data.ItemId}";
                _statusText.color = Color.green;
            }
            else
            {
                _statusText.text = $"Purchase failed: {data.Result}";
                _statusText.color = Color.red;
            }
        }

        if (_confirmPopup != null)
            _confirmPopup.SetActive(false);
    }

    private void HandleSubscriptionUpdated(SubscriptionInfoData data)
    {
        if (_subscriptionText != null)
        {
            if (data.IsActive)
                _subscriptionText.text = $"Subscription: ACTIVE ({data.DaysLeft}d left, +{data.DailyCrystals}/day)";
            else
                _subscriptionText.text = "Subscription: Inactive";
        }
    }

    private void ShowPanel()
    {
        if (_panel != null) _panel.SetActive(true);
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
        if (_itemListText == null || CashShopManager.Instance == null) return;

        var items = CashShopManager.Instance.Items;
        if (items.Count == 0)
        {
            _itemListText.text = "No items available.";
            return;
        }

        var sb = new System.Text.StringBuilder();
        sb.AppendLine($"Items ({items.Count}):");
        sb.AppendLine("─────────────────────────────────────────");
        for (int i = 0; i < items.Count; i++)
        {
            string cat = GetCategoryName(items[i].Category);
            string cur = items[i].Currency == CashCurrency.CRYSTAL ? "Crystal" : "Gold";
            string marker = (i == _selectedItemIndex) ? " >>>" : "    ";
            sb.AppendLine($"{marker}[{i}] {items[i].Name}  ({cat})  {items[i].Price} {cur}");
        }
        _itemListText.text = sb.ToString();

        if (_crystalText != null)
            _crystalText.text = $"Crystals: {CashShopManager.Instance.Crystals}";
    }

    // ━━━ 버튼 콜백 ━━━

    private void OnCategoryClicked(byte category)
    {
        _selectedCategory = category;
        _selectedItemIndex = -1;

        // 카테고리 버튼 하이라이트
        for (int i = 0; i < _categoryButtons.Length; i++)
        {
            var img = _categoryButtons[i].GetComponent<Image>();
            if (img != null)
                img.color = (i == category) ? new Color(0.3f, 0.2f, 0.5f) : new Color(0.2f, 0.2f, 0.25f);
        }

        CashShopManager.Instance?.RequestItems(category);
    }

    private void OnBuyClicked()
    {
        if (CashShopManager.Instance == null) return;

        var items = CashShopManager.Instance.Items;

        // 첫번째 아이템 선택 (간소화 — 실제로는 리스트 클릭)
        if (items.Count > 0)
        {
            if (_selectedItemIndex < 0) _selectedItemIndex = 0;

            var item = items[_selectedItemIndex];
            if (_confirmText != null)
            {
                string cur = item.Currency == CashCurrency.CRYSTAL ? "Crystals" : "Gold";
                _confirmText.text = $"Buy '{item.Name}' for {item.Price} {cur}?";
            }
            if (_confirmPopup != null) _confirmPopup.SetActive(true);
        }
    }

    private void OnConfirmYes()
    {
        if (CashShopManager.Instance == null) return;

        var items = CashShopManager.Instance.Items;
        if (_selectedItemIndex >= 0 && _selectedItemIndex < items.Count)
        {
            CashShopManager.Instance.BuyItem(items[_selectedItemIndex].ItemId, 1);
        }
    }

    private void OnConfirmNo()
    {
        if (_confirmPopup != null)
            _confirmPopup.SetActive(false);
    }

    // ━━━ 유틸 ━━━

    private static string GetCategoryName(CashShopCategory cat)
    {
        switch (cat)
        {
            case CashShopCategory.ALL: return "All";
            case CashShopCategory.COSMETIC: return "Cosmetic";
            case CashShopCategory.CONVENIENCE: return "Convenience";
            case CashShopCategory.MOUNT: return "Mount";
            case CashShopCategory.PET: return "Pet";
            case CashShopCategory.EMOTE: return "Emote";
            default: return "Unknown";
        }
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
