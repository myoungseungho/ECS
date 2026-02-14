// ━━━ TokenShopUI.cs ━━━
// 토큰 상점 UI — Shift+F9 토글 (던전/PvP/길드 상점)
// CurrencyManager 이벤트 구독

using UnityEngine;
using UnityEngine.UI;

public class TokenShopUI : MonoBehaviour
{
    // ━━━ 싱글톤 ━━━
    public static TokenShopUI Instance { get; private set; }

    // ━━━ UI 참조 (ProjectSetup에서 코드 생성) ━━━
    [SerializeField] private GameObject _panel;
    [SerializeField] private Text _titleText;
    [SerializeField] private Text _shopListText;
    [SerializeField] private Text _currencyText;
    [SerializeField] private Text _resultText;

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
        if (CurrencyManager.Instance != null)
        {
            CurrencyManager.Instance.OnTokenShopListReceived += HandleShopList;
            CurrencyManager.Instance.OnTokenShopBuyComplete += HandleBuyResult;
            CurrencyManager.Instance.OnTokenShopOpened += ShowPanel;
            CurrencyManager.Instance.OnTokenShopClosed += HidePanel;
        }
        if (_panel != null) _panel.SetActive(false);
    }

    private void Update()
    {
        if (Input.GetKeyDown(KeyCode.F9) && (Input.GetKey(KeyCode.LeftShift) || Input.GetKey(KeyCode.RightShift)))
        {
            if (CurrencyManager.Instance != null)
            {
                if (CurrencyManager.Instance.IsTokenShopOpen)
                    CurrencyManager.Instance.CloseTokenShop();
                else
                    CurrencyManager.Instance.OpenTokenShop(Network.TokenShopType.DUNGEON);
            }
        }
    }

    private void OnDestroy()
    {
        if (CurrencyManager.Instance != null)
        {
            CurrencyManager.Instance.OnTokenShopListReceived -= HandleShopList;
            CurrencyManager.Instance.OnTokenShopBuyComplete -= HandleBuyResult;
            CurrencyManager.Instance.OnTokenShopOpened -= ShowPanel;
            CurrencyManager.Instance.OnTokenShopClosed -= HidePanel;
        }
        if (Instance == this) Instance = null;
    }

    // ━━━ 핸들러 ━━━

    private void HandleShopList(Network.TokenShopData data)
    {
        if (_titleText != null)
            _titleText.text = $"Token Shop — {CurrencyManager.Instance?.GetCurrencyName(data.ShopType) ?? "Unknown"}";

        if (_currencyText != null && CurrencyManager.Instance != null)
            _currencyText.text = $"Balance: {CurrencyManager.Instance.GetCurrencyByType(data.ShopType):N0}";

        if (_shopListText == null) return;

        var sb = new System.Text.StringBuilder();
        for (int i = 0; i < data.Items.Length; i++)
        {
            var item = data.Items[i];
            sb.AppendLine($"[{item.ShopId}] {item.Name} — {item.Price:N0}");
        }
        _shopListText.text = sb.ToString();
    }

    private void HandleBuyResult(Network.TokenShopBuyResultData data)
    {
        if (_resultText == null) return;

        if (data.Result == Network.TokenShopBuyResult.SUCCESS)
        {
            _resultText.text = $"Purchase OK! Remaining: {data.RemainingCurrency:N0}";
            _resultText.color = Color.cyan;
        }
        else
        {
            _resultText.text = $"Purchase failed: {data.Result}";
            _resultText.color = Color.red;
        }
    }

    private void ShowPanel()
    {
        if (_panel != null) _panel.SetActive(true);
    }

    private void HidePanel()
    {
        if (_panel != null) _panel.SetActive(false);
    }
}
