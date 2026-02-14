// ━━━ TradeUI.cs ━━━
// 거래 UI — 거래 상태 표시, 아이템/골드 추가, 확정/취소
// TradeManager 이벤트 구독

using UnityEngine;
using UnityEngine.UI;
using Network;

public class TradeUI : MonoBehaviour
{
    [Header("UI References")]
    [SerializeField] private GameObject tradePanel;
    [SerializeField] private Text tradeStatusText;
    [SerializeField] private Text tradeResultText;

    private void Start()
    {
        if (TradeManager.Instance != null)
        {
            TradeManager.Instance.OnTradeStarted += HandleTradeStarted;
            TradeManager.Instance.OnTradeCancelled += HandleTradeCancelled;
            TradeManager.Instance.OnTradeCompleted += HandleTradeCompleted;
        }

        if (tradePanel != null)
            tradePanel.SetActive(false);
    }

    private void OnDestroy()
    {
        if (TradeManager.Instance != null)
        {
            TradeManager.Instance.OnTradeStarted -= HandleTradeStarted;
            TradeManager.Instance.OnTradeCancelled -= HandleTradeCancelled;
            TradeManager.Instance.OnTradeCompleted -= HandleTradeCompleted;
        }
    }

    private void Update()
    {
        // ESC로 거래 취소
        if (tradePanel != null && tradePanel.activeSelf && Input.GetKeyDown(KeyCode.Escape))
        {
            TradeManager.Instance?.CancelTrade();
        }
    }

    private void HandleTradeStarted()
    {
        if (tradePanel != null)
            tradePanel.SetActive(true);

        if (tradeStatusText != null)
            tradeStatusText.text = "Trading...";

        if (tradeResultText != null)
            tradeResultText.text = "";
    }

    private void HandleTradeCancelled()
    {
        if (tradePanel != null)
            tradePanel.SetActive(false);
    }

    private void HandleTradeCompleted(TradeResultData data)
    {
        if (tradeResultText != null)
        {
            tradeResultText.text = data.Result == TradeResult.SUCCESS
                ? "Trade Complete!"
                : $"Trade Failed: {data.Result}";
        }

        // 2초 후 패널 닫기
        Invoke(nameof(HidePanel), 2f);
    }

    private void HidePanel()
    {
        if (tradePanel != null)
            tradePanel.SetActive(false);
    }
}
