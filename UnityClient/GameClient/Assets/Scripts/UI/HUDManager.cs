// ━━━ HUDManager.cs ━━━
// HP바, MP바, EXP바, 레벨 표시 — ui.yaml player_info 스펙 기반
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

    [Header("Level & Name")]
    [SerializeField] private Text levelText;
    [SerializeField] private Text nameText;

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

    private void Refresh()
    {
        var s = StatsManager.Instance;
        if (s == null) return;

        if (hpSlider != null) hpSlider.value = s.HpRatio;
        if (mpSlider != null) mpSlider.value = s.MpRatio;
        if (expSlider != null) expSlider.value = s.ExpRatio;

        if (hpText != null) hpText.text = $"{s.HP}/{s.MaxHP}";
        if (mpText != null) mpText.text = $"{s.MP}/{s.MaxMP}";
        if (levelText != null) levelText.text = $"Lv.{s.Level}";
    }
}
