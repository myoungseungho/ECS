// ━━━ TutorialUI.cs ━━━
// P1_S01_C02: 튜토리얼 진행 UI
// 단계별 지시 텍스트 + 하이라이트 표시
// TutorialManager 이벤트를 구독하여 스텝 변경 시 UI 갱신

using UnityEngine;
using UnityEngine.UI;

public class TutorialUI : MonoBehaviour
{
    [Header("UI References")]
    [SerializeField] private GameObject tutorialPanel;
    [SerializeField] private Text instructionText;
    [SerializeField] private Text stepCountText;
    [SerializeField] private GameObject completeBanner;

    private static readonly string[] StepInstructions = {
        "WASD\uB85C \uC774\uB3D9\uD558\uC138\uC694",                   // Step 0
        "\uB9C8\uC6B0\uC2A4 \uD074\uB9AD\uC73C\uB85C \uACF5\uACA9\uD558\uC138\uC694",    // Step 1
        "1~4\uD0A4\uB85C \uC2A4\uD0AC\uC744 \uC0AC\uC6A9\uD558\uC138\uC694",    // Step 2
        "NPC\uC5D0\uAC8C \uB2E4\uAC00\uAC00\uC138\uC694 (F\uD0A4\uB85C \uB300\uD654)",  // Step 3
        "\uD018\uC2A4\uD2B8\uB97C \uC644\uB8CC\uD558\uC138\uC694!",               // Step 4
    };

    private void Start()
    {
        if (TutorialManager.Instance != null)
        {
            TutorialManager.Instance.OnStepCompleted += HandleStepCompleted;
            TutorialManager.Instance.OnTutorialFinished += HandleTutorialFinished;
        }

        if (completeBanner != null)
            completeBanner.SetActive(false);

        UpdateDisplay();
    }

    private void OnDestroy()
    {
        if (TutorialManager.Instance != null)
        {
            TutorialManager.Instance.OnStepCompleted -= HandleStepCompleted;
            TutorialManager.Instance.OnTutorialFinished -= HandleTutorialFinished;
        }
    }

    private void HandleStepCompleted(byte stepId)
    {
        UpdateDisplay();

        // 완료 배너 잠시 표시
        if (completeBanner != null)
        {
            completeBanner.SetActive(true);
            CancelInvoke(nameof(HideCompleteBanner));
            Invoke(nameof(HideCompleteBanner), 2f);
        }
    }

    private void HideCompleteBanner()
    {
        if (completeBanner != null)
            completeBanner.SetActive(false);
    }

    private void HandleTutorialFinished()
    {
        if (instructionText != null)
            instructionText.text = "\uD29C\uD1A0\uB9AC\uC5BC \uC644\uB8CC! \uBAA8\uD5D8\uC744 \uC2DC\uC791\uD558\uC138\uC694!";

        if (stepCountText != null)
            stepCountText.text = "5/5";

        // 3초 후 패널 숨김
        Invoke(nameof(HidePanel), 3f);
    }

    private void HidePanel()
    {
        if (tutorialPanel != null)
            tutorialPanel.SetActive(false);
    }

    private void UpdateDisplay()
    {
        if (TutorialManager.Instance == null) return;

        byte step = TutorialManager.Instance.CurrentStep;

        if (instructionText != null)
        {
            if (step < StepInstructions.Length)
                instructionText.text = StepInstructions[step];
            else
                instructionText.text = "";
        }

        if (stepCountText != null)
            stepCountText.text = $"{step}/{StepInstructions.Length}";
    }
}
