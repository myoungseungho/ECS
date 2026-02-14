// ━━━ ShopUI.cs ━━━
// 상점 UI — NPC 상점 아이템 목록, 구매/판매 버튼
// ShopManager 이벤트 구독

using UnityEngine;
using UnityEngine.UI;
using Network;

public class ShopUI : MonoBehaviour
{
    [Header("UI References")]
    [SerializeField] private GameObject shopPanel;
    [SerializeField] private Text shopTitle;
    [SerializeField] private Text itemListText;
    [SerializeField] private Text goldText;

    private void Start()
    {
        if (ShopManager.Instance != null)
        {
            ShopManager.Instance.OnShopOpened += HandleShopOpened;
            ShopManager.Instance.OnShopClosed += HandleShopClosed;
            ShopManager.Instance.OnTransactionResult += HandleTransactionResult;
            ShopManager.Instance.OnGoldChanged += HandleGoldChanged;
        }

        if (shopPanel != null)
            shopPanel.SetActive(false);
    }

    private void OnDestroy()
    {
        if (ShopManager.Instance != null)
        {
            ShopManager.Instance.OnShopOpened -= HandleShopOpened;
            ShopManager.Instance.OnShopClosed -= HandleShopClosed;
            ShopManager.Instance.OnTransactionResult -= HandleTransactionResult;
            ShopManager.Instance.OnGoldChanged -= HandleGoldChanged;
        }
    }

    private void Update()
    {
        // ESC로 상점 닫기
        if (shopPanel != null && shopPanel.activeSelf && Input.GetKeyDown(KeyCode.Escape))
        {
            ShopManager.Instance?.CloseShop();
        }
    }

    private void HandleShopOpened(ShopListData data)
    {
        if (shopPanel != null)
            shopPanel.SetActive(true);

        if (shopTitle != null)
            shopTitle.text = $"Shop (NPC #{data.NpcId})";

        RefreshItemList(data.Items);
        UpdateGoldDisplay();
    }

    private void HandleShopClosed()
    {
        if (shopPanel != null)
            shopPanel.SetActive(false);
    }

    private void HandleTransactionResult(ShopResultData data)
    {
        if (data.Result != ShopResult.SUCCESS)
        {
            Debug.Log($"[ShopUI] Transaction failed: {data.Result}");
        }

        UpdateGoldDisplay();
    }

    private void HandleGoldChanged(uint gold)
    {
        UpdateGoldDisplay();
    }

    private void RefreshItemList(ShopItemInfo[] items)
    {
        if (itemListText == null) return;

        var sb = new System.Text.StringBuilder();
        for (int i = 0; i < items.Length; i++)
        {
            string stock = items[i].Stock < 0 ? "Inf" : items[i].Stock.ToString();
            sb.AppendLine($"  [{i}] Item#{items[i].ItemId}  Price:{items[i].Price}G  Stock:{stock}");
        }

        itemListText.text = sb.ToString();
    }

    private void UpdateGoldDisplay()
    {
        if (goldText == null) return;
        var shop = ShopManager.Instance;
        if (shop != null)
            goldText.text = $"Gold: {shop.Gold}";
    }
}
