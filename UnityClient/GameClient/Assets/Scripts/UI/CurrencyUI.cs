// ━━━ CurrencyUI.cs ━━━
// 화폐 표시 패널 — F9 토글 (골드/실버/던전토큰/PvP토큰/길드기여도)
// CurrencyManager 이벤트 구독

using UnityEngine;
using UnityEngine.UI;

public class CurrencyUI : MonoBehaviour
{
    // ━━━ 싱글톤 ━━━
    public static CurrencyUI Instance { get; private set; }

    // ━━━ UI 참조 (ProjectSetup에서 코드 생성) ━━━
    [SerializeField] private GameObject _panel;
    [SerializeField] private Text _titleText;
    [SerializeField] private Text _goldText;
    [SerializeField] private Text _silverText;
    [SerializeField] private Text _dungeonTokenText;
    [SerializeField] private Text _pvpTokenText;
    [SerializeField] private Text _guildContribText;

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
            CurrencyManager.Instance.OnCurrencyChanged += HandleCurrencyChanged;
            CurrencyManager.Instance.OnCurrencyPanelOpened += ShowPanel;
            CurrencyManager.Instance.OnCurrencyPanelClosed += HidePanel;
        }
        if (_panel != null) _panel.SetActive(false);
    }

    private void Update()
    {
        if (Input.GetKeyDown(KeyCode.F9))
        {
            if (CurrencyManager.Instance != null)
            {
                if (CurrencyManager.Instance.IsCurrencyPanelOpen)
                    CurrencyManager.Instance.CloseCurrencyPanel();
                else
                    CurrencyManager.Instance.OpenCurrencyPanel();
            }
        }
    }

    private void OnDestroy()
    {
        if (CurrencyManager.Instance != null)
        {
            CurrencyManager.Instance.OnCurrencyChanged -= HandleCurrencyChanged;
            CurrencyManager.Instance.OnCurrencyPanelOpened -= ShowPanel;
            CurrencyManager.Instance.OnCurrencyPanelClosed -= HidePanel;
        }
        if (Instance == this) Instance = null;
    }

    // ━━━ 핸들러 ━━━

    private void HandleCurrencyChanged(Network.CurrencyInfoData data)
    {
        if (_goldText != null)
            _goldText.text = $"Gold: {data.Gold:N0}";
        if (_silverText != null)
            _silverText.text = $"Silver: {data.Silver:N0}";
        if (_dungeonTokenText != null)
            _dungeonTokenText.text = $"Dungeon Token: {data.DungeonToken:N0}";
        if (_pvpTokenText != null)
            _pvpTokenText.text = $"PvP Token: {data.PvpToken:N0}";
        if (_guildContribText != null)
            _guildContribText.text = $"Guild Contribution: {data.GuildContribution:N0}";
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
