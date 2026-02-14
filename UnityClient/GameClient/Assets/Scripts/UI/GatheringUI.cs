// ━━━ GatheringUI.cs ━━━
// 채집 UI — 채집 진행바 + 에너지 표시
// GatheringManager 이벤트 구독

using UnityEngine;
using UnityEngine.UI;

public class GatheringUI : MonoBehaviour
{
    // ━━━ 싱글톤 ━━━
    public static GatheringUI Instance { get; private set; }

    // ━━━ UI 참조 (ProjectSetup에서 코드 생성) ━━━
    [SerializeField] private GameObject _panel;
    [SerializeField] private Text _energyText;
    [SerializeField] private Image _progressBar;
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
        if (GatheringManager.Instance != null)
        {
            GatheringManager.Instance.OnGatherComplete += HandleGatherResult;
            GatheringManager.Instance.OnGatherStarted += HandleGatherStarted;
            GatheringManager.Instance.OnEnergyChanged += RefreshEnergy;
            GatheringManager.Instance.OnPanelOpened += ShowPanel;
            GatheringManager.Instance.OnPanelClosed += HidePanel;
        }
        if (_panel != null) _panel.SetActive(false);
    }

    private void OnDestroy()
    {
        if (GatheringManager.Instance != null)
        {
            GatheringManager.Instance.OnGatherComplete -= HandleGatherResult;
            GatheringManager.Instance.OnGatherStarted -= HandleGatherStarted;
            GatheringManager.Instance.OnEnergyChanged -= RefreshEnergy;
            GatheringManager.Instance.OnPanelOpened -= ShowPanel;
            GatheringManager.Instance.OnPanelClosed -= HidePanel;
        }
        if (Instance == this) Instance = null;
    }

    private void Update()
    {
        if (_progressBar != null && GatheringManager.Instance != null && GatheringManager.Instance.IsGathering)
        {
            _progressBar.fillAmount = GatheringManager.Instance.GatherProgress;
        }
    }

    // ━━━ 핸들러 ━━━

    private void HandleGatherStarted()
    {
        if (_progressBar != null)
        {
            _progressBar.fillAmount = 0f;
            _progressBar.gameObject.SetActive(true);
        }
        if (_resultText != null)
            _resultText.text = "Gathering...";
    }

    private void HandleGatherResult(Network.GatherResultData data)
    {
        if (_progressBar != null)
            _progressBar.gameObject.SetActive(false);

        if (_resultText == null) return;

        if (data.Status == Network.GatherResult.SUCCESS)
        {
            var sb = new System.Text.StringBuilder();
            sb.Append($"Gathered {data.Drops.Length} item(s)!");
            for (int i = 0; i < data.Drops.Length; i++)
                sb.Append($" [{data.Drops[i].ItemId}]");
            _resultText.text = sb.ToString();
            _resultText.color = Color.green;
        }
        else
        {
            _resultText.text = $"Gather failed: {data.Status}";
            _resultText.color = Color.red;
        }

        RefreshEnergy();
    }

    private void RefreshEnergy()
    {
        if (_energyText == null || GatheringManager.Instance == null) return;
        _energyText.text = $"Energy: {GatheringManager.Instance.Energy}/{GatheringManager.Instance.MaxEnergy}";
    }

    private void ShowPanel()
    {
        if (_panel != null) _panel.SetActive(true);
        RefreshEnergy();
    }

    private void HidePanel()
    {
        if (_panel != null) _panel.SetActive(false);
    }
}
