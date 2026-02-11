// ━━━ CombatUI.cs ━━━
// 데미지 텍스트 팝업 (WorldToScreenPoint → 떠오르며 페이드)
// 타겟 HP바 (선택된 적 정보)
// CombatManager.OnAttackFeedback 구독

using UnityEngine;
using UnityEngine.UI;
using System.Collections.Generic;
using Network;

public class CombatUI : MonoBehaviour
{
    [Header("Target Panel")]
    [SerializeField] private GameObject targetPanel;
    [SerializeField] private Text targetNameText;
    [SerializeField] private Slider targetHpSlider;

    [Header("Damage Text")]
    [SerializeField] private GameObject damageTextPrefab;
    [SerializeField] private Transform damageTextParent;

    [Header("Settings")]
    [SerializeField] private float damageTextDuration = 1.0f;
    [SerializeField] private float damageTextRiseSpeed = 80f;

    private readonly List<DamageTextEntry> _activeDamageTexts = new List<DamageTextEntry>();

    public static CombatUI Instance { get; private set; }

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
        if (CombatManager.Instance != null)
            CombatManager.Instance.OnAttackFeedback += HandleAttackFeedback;

        if (targetPanel != null)
            targetPanel.SetActive(false);
    }

    private void OnDestroy()
    {
        if (CombatManager.Instance != null)
            CombatManager.Instance.OnAttackFeedback -= HandleAttackFeedback;

        if (Instance == this) Instance = null;
    }

    private void Update()
    {
        UpdateDamageTexts();
    }

    private void HandleAttackFeedback(AttackResultData data)
    {
        // 타겟 HP바 갱신
        if (data.Result == AttackResult.SUCCESS && targetPanel != null)
        {
            ulong selectedTarget = CombatManager.Instance != null
                ? CombatManager.Instance.SelectedTarget : 0;

            if (data.TargetId == selectedTarget || data.AttackerId == NetworkManager.Instance.MyEntityId)
            {
                targetPanel.SetActive(true);
                if (targetNameText != null)
                    targetNameText.text = $"Target [{data.TargetId}]";
                if (targetHpSlider != null && data.TargetMaxHP > 0)
                    targetHpSlider.value = (float)data.TargetHP / data.TargetMaxHP;
            }
        }

        // 데미지 텍스트 생성
        if (data.Damage > 0)
        {
            SpawnDamageText(data);
        }
    }

    private void SpawnDamageText(AttackResultData data)
    {
        if (damageTextPrefab == null || damageTextParent == null) return;

        // 타겟 엔티티의 월드 위치 → 스크린 위치
        Vector3 screenPos = Vector3.zero;
        if (EntityManager.Instance != null &&
            EntityManager.Instance.EntityMap.TryGetValue(data.TargetId, out var targetGo) &&
            targetGo != null)
        {
            var worldPos = targetGo.transform.position + Vector3.up * 2f;
            var cam = Camera.main;
            if (cam != null)
                screenPos = cam.WorldToScreenPoint(worldPos);
        }
        else
        {
            // 타겟을 못 찾으면 화면 중앙 위
            screenPos = new Vector3(Screen.width * 0.5f, Screen.height * 0.6f, 0f);
        }

        var go = Instantiate(damageTextPrefab, damageTextParent);
        var rt = go.GetComponent<RectTransform>();
        if (rt != null)
            rt.position = screenPos;

        var text = go.GetComponent<Text>();
        if (text != null)
        {
            text.text = data.Damage.ToString();
            text.color = data.AttackerId == NetworkManager.Instance.MyEntityId
                ? Color.yellow
                : Color.red;
        }

        _activeDamageTexts.Add(new DamageTextEntry
        {
            Go = go,
            RemainingTime = damageTextDuration,
            TotalTime = damageTextDuration,
        });
    }

    private void UpdateDamageTexts()
    {
        for (int i = _activeDamageTexts.Count - 1; i >= 0; i--)
        {
            var entry = _activeDamageTexts[i];
            entry.RemainingTime -= Time.deltaTime;

            if (entry.Go != null)
            {
                // 떠오르기
                var rt = entry.Go.GetComponent<RectTransform>();
                if (rt != null)
                    rt.position += Vector3.up * damageTextRiseSpeed * Time.deltaTime;

                // 페이드아웃
                var text = entry.Go.GetComponent<Text>();
                if (text != null)
                {
                    float alpha = Mathf.Clamp01(entry.RemainingTime / entry.TotalTime);
                    var c = text.color;
                    c.a = alpha;
                    text.color = c;
                }
            }

            if (entry.RemainingTime <= 0f)
            {
                if (entry.Go != null) Destroy(entry.Go);
                _activeDamageTexts.RemoveAt(i);
            }
        }
    }

    /// <summary>타겟 패널 숨기기</summary>
    public void HideTargetPanel()
    {
        if (targetPanel != null)
            targetPanel.SetActive(false);
    }

    private class DamageTextEntry
    {
        internal GameObject Go;
        internal float RemainingTime;
        internal float TotalTime;
    }
}
