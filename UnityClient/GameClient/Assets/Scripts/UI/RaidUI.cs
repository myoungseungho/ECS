// ━━━ RaidUI.cs ━━━
// 레이드 보스 UI — HP바/페이즈/기믹 알림/스태거/인레이지/보상
// RaidManager 이벤트 구독으로 상태 표시
// 레이드 중일 때 자동 표시

using UnityEngine;
using UnityEngine.UI;
using Network;

public class RaidUI : MonoBehaviour
{
    // ━━━ UI 참조 (ProjectSetup에서 생성) ━━━
    [SerializeField] private GameObject _panel;

    // 보스 정보
    [SerializeField] private Text _bossNameText;
    [SerializeField] private Text _bossHPText;
    [SerializeField] private Image _bossHPFill;
    [SerializeField] private Text _phaseText;
    [SerializeField] private Text _enrageTimerText;

    // 스태거 게이지
    [SerializeField] private Text _staggerText;
    [SerializeField] private Image _staggerFill;

    // 기믹 알림
    [SerializeField] private GameObject _mechanicPopup;
    [SerializeField] private Text _mechanicText;

    // 결과 패널
    [SerializeField] private GameObject _resultPanel;
    [SerializeField] private Text _resultText;

    private float _mechanicTimer;

    private void Start()
    {
        if (_panel != null) _panel.SetActive(false);
        if (_mechanicPopup != null) _mechanicPopup.SetActive(false);
        if (_resultPanel != null) _resultPanel.SetActive(false);

        var rm = RaidManager.Instance;
        if (rm != null)
        {
            rm.OnBossSpawned += HandleBossSpawned;
            rm.OnPhaseChanged += HandlePhaseChanged;
            rm.OnMechanicStarted += HandleMechanicStarted;
            rm.OnMechanicResult += HandleMechanicResult;
            rm.OnStaggerUpdated += HandleStaggerUpdated;
            rm.OnEnraged += HandleEnraged;
            rm.OnWiped += HandleWiped;
            rm.OnCleared += HandleCleared;
            rm.OnAttackResult += HandleAttackResult;
        }
    }

    private void OnDestroy()
    {
        var rm = RaidManager.Instance;
        if (rm == null) return;

        rm.OnBossSpawned -= HandleBossSpawned;
        rm.OnPhaseChanged -= HandlePhaseChanged;
        rm.OnMechanicStarted -= HandleMechanicStarted;
        rm.OnMechanicResult -= HandleMechanicResult;
        rm.OnStaggerUpdated -= HandleStaggerUpdated;
        rm.OnEnraged -= HandleEnraged;
        rm.OnWiped -= HandleWiped;
        rm.OnCleared -= HandleCleared;
        rm.OnAttackResult -= HandleAttackResult;
    }

    private void Update()
    {
        // 기믹 팝업 자동 숨김
        if (_mechanicTimer > 0f)
        {
            _mechanicTimer -= Time.deltaTime;
            if (_mechanicTimer <= 0f && _mechanicPopup != null)
                _mechanicPopup.SetActive(false);
        }
    }

    // ━━━ 이벤트 핸들러 ━━━

    private void HandleBossSpawned(RaidBossSpawnData data)
    {
        if (_panel != null) _panel.SetActive(true);
        if (_resultPanel != null) _resultPanel.SetActive(false);

        if (_bossNameText != null) _bossNameText.text = data.BossName;
        UpdateHP(data.CurrentHP, data.MaxHP);
        UpdatePhase(data.Phase, data.MaxPhases);
        if (_enrageTimerText != null) _enrageTimerText.text = $"Enrage: {data.EnrageTimer}s";
        UpdateStagger(0);
    }

    private void HandlePhaseChanged(RaidPhaseChangeData data)
    {
        UpdatePhase(data.Phase, data.MaxPhases);
        ShowMechanicPopup($"Phase {data.Phase}!", 3f);
    }

    private void HandleMechanicStarted(RaidMechanicData data)
    {
        string name = RaidManager.GetMechanicName(data.MechanicId);
        ShowMechanicPopup($"[MECHANIC] {name}", 5f);
    }

    private void HandleMechanicResult(RaidMechanicResultData data)
    {
        string name = RaidManager.GetMechanicName(data.MechanicId);
        string result = data.Success ? "SUCCESS" : "FAIL";
        ShowMechanicPopup($"{name}: {result}", 3f);
    }

    private void HandleStaggerUpdated(byte gauge)
    {
        UpdateStagger(gauge);
    }

    private void HandleEnraged()
    {
        if (_enrageTimerText != null) _enrageTimerText.text = "ENRAGED!";
        ShowMechanicPopup("BOSS ENRAGED!", 4f);
    }

    private void HandleWiped(RaidWipeData data)
    {
        if (_resultPanel != null) _resultPanel.SetActive(true);
        if (_resultText != null) _resultText.text = $"WIPE!\nPhase {data.Phase}";
    }

    private void HandleCleared(RaidClearData data)
    {
        if (_resultPanel != null) _resultPanel.SetActive(true);
        if (_resultText != null)
            _resultText.text = $"CLEAR!\nGold: {data.Gold}\nEXP: {data.Exp}\nTokens: {data.Tokens}";
        UpdateHP(0, 1);
    }

    private void HandleAttackResult(RaidAttackResultData data)
    {
        UpdateHP(data.CurrentHP, data.MaxHP);
    }

    // ━━━ UI 갱신 헬퍼 ━━━

    private void UpdateHP(uint current, uint max)
    {
        if (_bossHPText != null)
            _bossHPText.text = $"{current:N0} / {max:N0}";
        if (_bossHPFill != null)
            _bossHPFill.fillAmount = max > 0 ? (float)current / max : 0f;
    }

    private void UpdatePhase(byte phase, byte maxPhases)
    {
        if (_phaseText != null)
            _phaseText.text = $"Phase {phase} / {maxPhases}";
    }

    private void UpdateStagger(byte gauge)
    {
        if (_staggerText != null)
            _staggerText.text = $"Stagger: {gauge}%";
        if (_staggerFill != null)
            _staggerFill.fillAmount = gauge / 100f;
    }

    private void ShowMechanicPopup(string text, float duration)
    {
        if (_mechanicPopup != null) _mechanicPopup.SetActive(true);
        if (_mechanicText != null) _mechanicText.text = text;
        _mechanicTimer = duration;
    }
}
