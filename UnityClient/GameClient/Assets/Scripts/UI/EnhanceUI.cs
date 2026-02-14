// ━━━ EnhanceUI.cs ━━━
// 강화 패널 UI — EnhanceManager 이벤트 구독
// 대장장이 NPC 인터랙션 시 표시, ESC로 닫기

using UnityEngine;
using UnityEngine.UI;
using Network;

public class EnhanceUI : MonoBehaviour
{
    [SerializeField] private GameObject enhancePanel;
    [SerializeField] private Text resultText;
    [SerializeField] private Text slotInfoText;

    private void Start()
    {
        if (EnhanceManager.Instance != null)
        {
            EnhanceManager.Instance.OnEnhancePanelOpened += HandlePanelOpened;
            EnhanceManager.Instance.OnEnhancePanelClosed += HandlePanelClosed;
            EnhanceManager.Instance.OnEnhanceComplete += HandleEnhanceComplete;
        }

        if (enhancePanel != null)
            enhancePanel.SetActive(false);
    }

    private void OnDestroy()
    {
        if (EnhanceManager.Instance != null)
        {
            EnhanceManager.Instance.OnEnhancePanelOpened -= HandlePanelOpened;
            EnhanceManager.Instance.OnEnhancePanelClosed -= HandlePanelClosed;
            EnhanceManager.Instance.OnEnhanceComplete -= HandleEnhanceComplete;
        }
    }

    private void Update()
    {
        if (enhancePanel != null && enhancePanel.activeSelf && Input.GetKeyDown(KeyCode.Escape))
        {
            if (EnhanceManager.Instance != null)
                EnhanceManager.Instance.ClosePanel();
        }
    }

    private void HandlePanelOpened()
    {
        if (enhancePanel != null)
            enhancePanel.SetActive(true);

        if (resultText != null)
            resultText.text = "";

        if (slotInfoText != null)
            slotInfoText.text = "\uac15\ud654\ud560 \uc7a5\ube44 \uc2ac\ub86f\uc744 \uc120\ud0dd\ud558\uc138\uc694";
    }

    private void HandlePanelClosed()
    {
        if (enhancePanel != null)
            enhancePanel.SetActive(false);
    }

    private void HandleEnhanceComplete(EnhanceResultData data)
    {
        if (resultText == null) return;

        string msg = data.Result switch
        {
            EnhanceResult.SUCCESS => $"\uac15\ud654 \uc131\uacf5! +{data.NewLevel}",
            EnhanceResult.INVALID_SLOT => "\uc798\ubabb\ub41c \uc2ac\ub86f",
            EnhanceResult.NO_ITEM => "\ube48 \uc2ac\ub86f",
            EnhanceResult.MAX_LEVEL => "\ucd5c\ub300 \uac15\ud654 \ub2e8\uacc4 (+10)",
            EnhanceResult.NO_GOLD => "\uace8\ub4dc \ubd80\uc871",
            EnhanceResult.FAIL => $"\uac15\ud654 \uc2e4\ud328 (\ub2e8\uacc4 \uc720\uc9c0: +{data.NewLevel})",
            _ => "\uc54c \uc218 \uc5c6\ub294 \uacb0\uacfc"
        };

        resultText.text = msg;
        resultText.color = data.Result == EnhanceResult.SUCCESS
            ? new Color(0.2f, 1f, 0.2f)
            : new Color(1f, 0.3f, 0.3f);
    }
}
