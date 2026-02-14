// ━━━ KeybindGuideUI.cs ━━━
// 게임 시작 시 반투명 패널에 조작법 표시
// 10초 후 또는 아무 키 누르면 자동 숨김, F1로 다시 표시

using UnityEngine;
using UnityEngine.UI;

public class KeybindGuideUI : MonoBehaviour
{
    [SerializeField] private GameObject guidePanel;
    [SerializeField] private Text guideText;

    private float _showTime;
    private bool _visible;

    private void Start()
    {
        if (guideText != null)
        {
            guideText.text =
                "<b>[ Controls ]</b>\n\n" +
                "WASD  -  Move\n" +
                "LClick  -  Select Target\n" +
                "Tab  -  Cycle Target\n" +
                "MWheel  -  Zoom In/Out\n" +
                "MMB Drag  -  Rotate Camera\n" +
                "Q/W/E/R  -  Skills\n" +
                "A/S/D/F  -  Skills\n" +
                "V  -  Ultimate\n" +
                "I  -  Inventory\n" +
                "K  -  Character\n" +
                "L  -  Skills Panel\n" +
                "J  -  Quests\n" +
                "Enter  -  Chat\n" +
                "F1  -  Show this guide";
        }

        Show();
    }

    private void Update()
    {
        if (!_visible)
        {
            if (Input.GetKeyDown(KeyCode.F1))
                Show();
            return;
        }

        // Auto-hide after 10 seconds
        if (Time.time - _showTime > 10f)
        {
            Hide();
            return;
        }

        // Hide on any key/mouse press (except F1)
        if (Input.anyKeyDown && !Input.GetKeyDown(KeyCode.F1))
            Hide();
    }

    private void Show()
    {
        _visible = true;
        _showTime = Time.time;
        if (guidePanel != null)
            guidePanel.SetActive(true);
    }

    private void Hide()
    {
        _visible = false;
        if (guidePanel != null)
            guidePanel.SetActive(false);
    }
}
