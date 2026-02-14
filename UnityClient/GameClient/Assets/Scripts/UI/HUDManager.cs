// ━━━ HUDManager.cs ━━━
// HP바, MP바, EXP바, 레벨 표시
// StatsManager.OnStatsChanged 구독

using UnityEngine;
using UnityEngine.UI;

public class HUDManager : MonoBehaviour
{
    [Header("HP Bar")]
    [SerializeField] private Slider hpSlider;
    [SerializeField] private Text hpText;

    [Header("MP Bar")]
    [SerializeField] private Slider mpSlider;
    [SerializeField] private Text mpText;

    [Header("EXP Bar")]
    [SerializeField] private Slider expSlider;
    [SerializeField] private Text expText;

    [Header("Level")]
    [SerializeField] private Text levelText;

    [Header("Crosshair")]
    [SerializeField] private Image crosshair;

    private Image[] _crosshairBars;

    public static HUDManager Instance { get; private set; }

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
        if (StatsManager.Instance != null)
            StatsManager.Instance.OnStatsChanged += Refresh;
    }

    private void OnDestroy()
    {
        if (StatsManager.Instance != null)
            StatsManager.Instance.OnStatsChanged -= Refresh;

        if (Instance == this) Instance = null;
    }

    private void Update()
    {
        UpdateCrosshair();
    }

    private void UpdateCrosshair()
    {
        if (crosshair == null) return;

        if (_crosshairBars == null)
            _crosshairBars = crosshair.GetComponentsInChildren<Image>();

        bool hasTarget = CombatManager.Instance != null && CombatManager.Instance.SelectedTarget != 0;
        Color c = hasTarget ? Color.red : Color.white;

        for (int i = 0; i < _crosshairBars.Length; i++)
        {
            if (_crosshairBars[i] != crosshair)
                _crosshairBars[i].color = c;
        }
    }

    private void Refresh()
    {
        var s = StatsManager.Instance;
        if (s == null) return;

        if (hpSlider != null) hpSlider.value = s.HpRatio;
        if (mpSlider != null) mpSlider.value = s.MpRatio;
        if (expSlider != null) expSlider.value = s.ExpRatio;

        if (hpText != null) hpText.text = $"{s.HP} / {s.MaxHP}";
        if (mpText != null) mpText.text = $"{s.MP} / {s.MaxMP}";
        if (expText != null) expText.text = $"{s.EXP} / {s.EXPNext}";
        if (levelText != null) levelText.text = $"Lv. {s.Level}";
    }
}
