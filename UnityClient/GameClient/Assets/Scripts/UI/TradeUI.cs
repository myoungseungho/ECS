// ━━━ TradeUI.cs ━━━
// 거래 패널 UI — 거래 요청/수락/거절, 아이템/골드 추가, 확인/취소
// T031

using UnityEngine;
using UnityEngine.UI;
using Network;

public class TradeUI : MonoBehaviour
{
    [SerializeField] private GameObject tradePanel;
    [SerializeField] private GameObject requestPanel;
    [SerializeField] private Text requestText;
    [SerializeField] private Text partnerItemsText;
    [SerializeField] private Button acceptRequestButton;
    [SerializeField] private Button declineRequestButton;
    [SerializeField] private Button confirmButton;
    [SerializeField] private Button cancelButton;

    private void Start()
    {
        if (TradeManager.Instance != null)
        {
            TradeManager.Instance.OnTradeRequested += HandleTradeRequested;
            TradeManager.Instance.OnPartnerItemAdded += HandlePartnerItemAdded;
            TradeManager.Instance.OnTradeCompleted += HandleTradeCompleted;
            TradeManager.Instance.OnTradeCancelled += HandleTradeCancelled;
        }

        if (acceptRequestButton != null)
            acceptRequestButton.onClick.AddListener(OnAcceptRequest);
        if (declineRequestButton != null)
            declineRequestButton.onClick.AddListener(OnDeclineRequest);
        if (confirmButton != null)
            confirmButton.onClick.AddListener(OnConfirm);
        if (cancelButton != null)
            cancelButton.onClick.AddListener(OnCancel);

        if (tradePanel != null) tradePanel.SetActive(false);
        if (requestPanel != null) requestPanel.SetActive(false);
    }

    private void OnDestroy()
    {
        if (TradeManager.Instance != null)
        {
            TradeManager.Instance.OnTradeRequested -= HandleTradeRequested;
            TradeManager.Instance.OnPartnerItemAdded -= HandlePartnerItemAdded;
            TradeManager.Instance.OnTradeCompleted -= HandleTradeCompleted;
            TradeManager.Instance.OnTradeCancelled -= HandleTradeCancelled;
        }
    }

    private void HandleTradeRequested(TradeRequestData data)
    {
        if (requestPanel != null) requestPanel.SetActive(true);
        if (requestText != null)
            requestText.text = $"{data.RequesterName} wants to trade";
    }

    private void HandlePartnerItemAdded(TradeAddItemData data)
    {
        RefreshPartnerItems();
    }

    private void HandleTradeCompleted(TradeResult result)
    {
        if (tradePanel != null) tradePanel.SetActive(false);
        if (partnerItemsText != null)
            partnerItemsText.text = result == TradeResult.SUCCESS ? "Trade complete!" : $"Trade failed: {result}";
    }

    private void HandleTradeCancelled()
    {
        if (tradePanel != null) tradePanel.SetActive(false);
        if (requestPanel != null) requestPanel.SetActive(false);
    }

    private void RefreshPartnerItems()
    {
        if (partnerItemsText == null || TradeManager.Instance == null) return;
        var items = TradeManager.Instance.PartnerItems;
        string text = "Partner offers:\n";
        for (int i = 0; i < items.Count; i++)
            text += $"  Item#{items[i].ItemId} x{items[i].Count}\n";
        partnerItemsText.text = text;
    }

    private void OnAcceptRequest()
    {
        if (TradeManager.Instance != null)
            TradeManager.Instance.AcceptTrade();
        if (requestPanel != null) requestPanel.SetActive(false);
        if (tradePanel != null) tradePanel.SetActive(true);
    }

    private void OnDeclineRequest()
    {
        if (TradeManager.Instance != null)
            TradeManager.Instance.DeclineTrade();
        if (requestPanel != null) requestPanel.SetActive(false);
    }

    private void OnConfirm()
    {
        if (TradeManager.Instance != null)
            TradeManager.Instance.Confirm();
    }

    private void OnCancel()
    {
        if (TradeManager.Instance != null)
            TradeManager.Instance.Cancel();
        if (tradePanel != null) tradePanel.SetActive(false);
    }
}
