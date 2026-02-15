// ━━━ SkillBarUI.cs ━━━
// 하단 스킬바 — 13슬롯 (LMB + QWER + V + ASDF + 1,2)
// ui.yaml hud.skill_bar 스펙: 하단중앙 (0, 20), 700x80
// SkillManager.OnSkillListChanged, OnCooldownStarted 구독

using UnityEngine;
using UnityEngine.UI;
using System.Collections.Generic;
using Network;

public class SkillBarUI : MonoBehaviour
{
    [Header("Skill Slots (13개: LMB,Q,W,E,R,V,A,S,D,F,1,2)")]
    [SerializeField] private Text[] slotNameTexts;   // 13개
    [SerializeField] private Text[] slotKeyTexts;    // 키 레이블
    [SerializeField] private Image[] cooldownOverlays; // 쿨다운 시 fillAmount

    // 슬롯 키 매핑 (순서: LMB, Q, W, E, R, V, A, S, D, F, 1, 2)
    private static readonly KeyCode[] SlotKeys =
    {
        KeyCode.Mouse0,     // 0: LMB
        KeyCode.Q,          // 1: Q
        KeyCode.W,          // 2: W (이동과 충돌 — 전투 모드에서만)
        KeyCode.E,          // 3: E
        KeyCode.R,          // 4: R
        KeyCode.V,          // 5: V (궁극기)
        KeyCode.A,          // 6: A (이동과 충돌 — 전투 모드에서만)
        KeyCode.S,          // 7: S (이동과 충돌 — 전투 모드에서만)
        KeyCode.D,          // 8: D (이동과 충돌 — 전투 모드에서만)
        KeyCode.F,          // 9: F
        KeyCode.Alpha1,     // 10: 물약1
        KeyCode.Alpha2,     // 11: 물약2
    };

    private static readonly string[] SlotLabels =
    {
        "LMB", "Q", "W", "E", "R", "V", "A", "S", "D", "F", "1", "2"
    };

    public const int SlotCount = 12;

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
        UpdateCooldowns();
        HandleKeyInput();
    }

    private void RefreshSkillBar()
    {
        var sm = SkillManager.Instance;
        if (sm == null) return;

        _slotSkillIds.Clear();
        foreach (var kvp in sm.Skills)
            _slotSkillIds.Add(kvp.Key);

        for (int i = 0; i < SlotCount; i++)
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

        for (int i = 0; i < SlotCount; i++)
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
        // LMB (Mouse0) — 기본 공격은 LocalPlayer에서 처리하므로 스킬 슬롯으로만 동작
        // QWER ASDF는 전투 스킬 전용
        for (int i = 0; i < SlotKeys.Length; i++)
        {
            // Mouse0은 GetMouseButtonDown으로 처리
            if (SlotKeys[i] == KeyCode.Mouse0)
            {
                if (Input.GetMouseButtonDown(0))
                    TryUseSlot(i);
            }
            else
            {
                if (Input.GetKeyDown(SlotKeys[i]))
                    TryUseSlot(i);
            }
        }
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
        if (data.Result == 0)
            Debug.Log($"[SkillBarUI] Skill {data.SkillId} hit for {data.Damage} dmg");
    }
}
