// ━━━ SkillBarUI.cs ━━━
// 하단 스킬바 — 스킬 슬롯 4개 (키보드 1~4), 쿨다운 오버레이
// SkillManager.OnSkillListChanged, OnCooldownStarted 구독

using UnityEngine;
using UnityEngine.UI;
using System.Collections.Generic;
using Network;

public class SkillBarUI : MonoBehaviour
{
    [Header("Skill Slots")]
    [SerializeField] private Text[] slotNameTexts;   // 4개
    [SerializeField] private Text[] slotKeyTexts;    // "1" "2" "3" "4"
    [SerializeField] private Image[] cooldownOverlays; // 쿨다운 시 fillAmount

    private readonly List<uint> _slotSkillIds = new List<uint>();

    public static SkillBarUI Instance { get; private set; }

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
        if (SkillManager.Instance != null)
        {
            SkillManager.Instance.OnSkillListChanged += RefreshSkillBar;
            SkillManager.Instance.OnSkillUsed += HandleSkillUsed;
        }
    }

    private void OnDestroy()
    {
        if (SkillManager.Instance != null)
        {
            SkillManager.Instance.OnSkillListChanged -= RefreshSkillBar;
            SkillManager.Instance.OnSkillUsed -= HandleSkillUsed;
        }

        if (Instance == this) Instance = null;
    }

    private void Update()
    {
        // 쿨다운 오버레이 갱신
        UpdateCooldowns();

        // 키보드 입력 (1~4키)
        HandleKeyInput();
    }

    private void RefreshSkillBar()
    {
        var sm = SkillManager.Instance;
        if (sm == null) return;

        _slotSkillIds.Clear();
        foreach (var kvp in sm.Skills)
            _slotSkillIds.Add(kvp.Key);

        for (int i = 0; i < 4; i++)
        {
            if (i < _slotSkillIds.Count)
            {
                var skill = sm.GetSkill(_slotSkillIds[i]);
                if (slotNameTexts != null && i < slotNameTexts.Length && slotNameTexts[i] != null)
                    slotNameTexts[i].text = skill != null ? skill.Name : "";
            }
            else
            {
                if (slotNameTexts != null && i < slotNameTexts.Length && slotNameTexts[i] != null)
                    slotNameTexts[i].text = "";
            }
        }
    }

    private void UpdateCooldowns()
    {
        var sm = SkillManager.Instance;
        if (sm == null || cooldownOverlays == null) return;

        for (int i = 0; i < 4; i++)
        {
            if (i >= cooldownOverlays.Length || cooldownOverlays[i] == null) continue;

            if (i < _slotSkillIds.Count)
            {
                uint skillId = _slotSkillIds[i];
                float remaining = sm.GetCooldownRemaining(skillId);
                var skill = sm.GetSkill(skillId);
                float total = skill != null ? skill.CooldownMs / 1000f : 1f;

                cooldownOverlays[i].fillAmount = total > 0 ? remaining / total : 0f;
                cooldownOverlays[i].gameObject.SetActive(remaining > 0f);
            }
            else
            {
                cooldownOverlays[i].gameObject.SetActive(false);
            }
        }
    }

    private void HandleKeyInput()
    {
        if (Input.GetKeyDown(KeyCode.Alpha1)) TryUseSlot(0);
        if (Input.GetKeyDown(KeyCode.Alpha2)) TryUseSlot(1);
        if (Input.GetKeyDown(KeyCode.Alpha3)) TryUseSlot(2);
        if (Input.GetKeyDown(KeyCode.Alpha4)) TryUseSlot(3);
    }

    private void TryUseSlot(int slotIndex)
    {
        if (slotIndex >= _slotSkillIds.Count) return;

        var sm = SkillManager.Instance;
        if (sm == null) return;

        ulong target = CombatManager.Instance != null
            ? CombatManager.Instance.SelectedTarget : 0;

        sm.UseSkill(_slotSkillIds[slotIndex], target);
    }

    private void HandleSkillUsed(SkillResultData data)
    {
        // 스킬 사용 피드백 (추후 이펙트 확장 가능)
        if (data.Result == 0)
            Debug.Log($"[SkillBarUI] Skill {data.SkillId} hit for {data.Damage} dmg");
    }
}
