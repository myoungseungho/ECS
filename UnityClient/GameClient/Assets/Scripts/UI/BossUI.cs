// ━━━ BossUI.cs ━━━
// 보스 UI — 보스 체력바, 페이즈 표시, 인레이지 경고, 특수 공격 알림
// BossManager 이벤트 구독

using UnityEngine;
using UnityEngine.UI;
using Network;

public class BossUI : MonoBehaviour
{
    [Header("UI References")]
    [SerializeField] private GameObject bossPanel;
    [SerializeField] private Text bossNameText;
    [SerializeField] private Slider bossHPBar;
    [SerializeField] private Text bossHPText;
    [SerializeField] private Text phaseText;
    [SerializeField] private Text alertText;

    private ulong _currentBossEntity;
    private float _alertTimer;

    private void Start()
    {
        if (BossManager.Instance != null)
        {
            BossManager.Instance.OnBossAppeared += HandleBossAppeared;
            BossManager.Instance.OnBossPhaseChanged += HandleBossPhaseChanged;
            BossManager.Instance.OnBossSpecialAttacked += HandleBossSpecialAttack;
            BossManager.Instance.OnBossEnraged += HandleBossEnraged;
            BossManager.Instance.OnBossKilled += HandleBossKilled;
            BossManager.Instance.OnBossHPChanged += HandleBossHPChanged;
        }

        if (bossPanel != null)
            bossPanel.SetActive(false);

        if (alertText != null)
            alertText.gameObject.SetActive(false);
    }

    private void OnDestroy()
    {
        if (BossManager.Instance != null)
        {
            BossManager.Instance.OnBossAppeared -= HandleBossAppeared;
            BossManager.Instance.OnBossPhaseChanged -= HandleBossPhaseChanged;
            BossManager.Instance.OnBossSpecialAttacked -= HandleBossSpecialAttack;
            BossManager.Instance.OnBossEnraged -= HandleBossEnraged;
            BossManager.Instance.OnBossKilled -= HandleBossKilled;
            BossManager.Instance.OnBossHPChanged -= HandleBossHPChanged;
        }
    }

    private void Update()
    {
        // 알림 텍스트 자동 숨기기
        if (_alertTimer > 0f)
        {
            _alertTimer -= Time.deltaTime;
            if (_alertTimer <= 0f && alertText != null)
                alertText.gameObject.SetActive(false);
        }
    }

    private void HandleBossAppeared(BossManager.BossState boss)
    {
        _currentBossEntity = boss.EntityId;

        if (bossPanel != null)
            bossPanel.SetActive(true);

        if (bossNameText != null)
            bossNameText.text = $"{boss.Name} (Lv{boss.Level})";

        UpdateHP(boss);
        UpdatePhase(boss);
    }

    private void HandleBossPhaseChanged(BossManager.BossState boss)
    {
        if (boss.EntityId != _currentBossEntity) return;
        UpdateHP(boss);
        UpdatePhase(boss);
        ShowAlert($"Phase {boss.Phase}!", 3f);
    }

    private void HandleBossSpecialAttack(BossSpecialAttackData data)
    {
        ShowAlert($"{data.AttackType}! (-{data.Damage} HP)", 2f);
    }

    private void HandleBossEnraged(BossManager.BossState boss)
    {
        if (boss.EntityId != _currentBossEntity) return;
        ShowAlert("ENRAGE!", 5f);

        if (bossNameText != null)
            bossNameText.text = $"{boss.Name} (Lv{boss.Level}) [ENRAGED]";
    }

    private void HandleBossKilled(BossDefeatedData data)
    {
        if (data.EntityId != _currentBossEntity) return;
        ShowAlert("BOSS DEFEATED!", 5f);

        _currentBossEntity = 0;
        if (bossPanel != null)
            bossPanel.SetActive(false);
    }

    private void HandleBossHPChanged(BossManager.BossState boss)
    {
        if (boss.EntityId != _currentBossEntity) return;
        UpdateHP(boss);
    }

    private void UpdateHP(BossManager.BossState boss)
    {
        if (bossHPBar != null)
            bossHPBar.value = boss.MaxHP > 0 ? (float)boss.HP / boss.MaxHP : 0f;

        if (bossHPText != null)
            bossHPText.text = $"{boss.HP} / {boss.MaxHP}";
    }

    private void UpdatePhase(BossManager.BossState boss)
    {
        if (phaseText != null)
            phaseText.text = $"Phase {boss.Phase}";
    }

    private void ShowAlert(string message, float duration)
    {
        if (alertText == null) return;
        alertText.text = message;
        alertText.gameObject.SetActive(true);
        _alertTimer = duration;
    }
}
