// ━━━ BuffUI.cs ━━━
// 버프 아이콘 — 우상단 가로 나열, 남은 시간 + 스택 표시
// BuffManager.OnBuffListChanged 구독

using UnityEngine;
using UnityEngine.UI;
using System.Collections.Generic;
using Network;

public class BuffUI : MonoBehaviour
{
    [Header("Buff Panel")]
    [SerializeField] private Transform buffIconParent;
    [SerializeField] private GameObject buffIconTemplate;

    private readonly List<GameObject> _buffInstances = new List<GameObject>();

    public static BuffUI Instance { get; private set; }

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
        if (BuffManager.Instance != null)
            BuffManager.Instance.OnBuffListChanged += RefreshBuffs;

        if (buffIconTemplate != null)
            buffIconTemplate.SetActive(false);
    }

    private void OnDestroy()
    {
        if (BuffManager.Instance != null)
            BuffManager.Instance.OnBuffListChanged -= RefreshBuffs;

        if (Instance == this) Instance = null;
    }

    private void Update()
    {
        // 남은 시간 실시간 갱신
        UpdateBuffTimers();
    }

    private void RefreshBuffs()
    {
        var bm = BuffManager.Instance;
        if (bm == null) return;

        // 기존 아이콘 제거
        foreach (var go in _buffInstances)
            if (go != null) Destroy(go);
        _buffInstances.Clear();

        if (buffIconTemplate == null || buffIconParent == null) return;

        foreach (var kvp in bm.Buffs)
        {
            var buff = kvp.Value;
            var go = Instantiate(buffIconTemplate, buffIconParent);
            go.SetActive(true);
            go.name = $"Buff_{buff.BuffId}";

            var text = go.GetComponentInChildren<Text>();
            if (text != null)
            {
                float sec = buff.RemainingMs / 1000f;
                string stackStr = buff.Stacks > 1 ? $" x{buff.Stacks}" : "";
                text.text = $"B{buff.BuffId}{stackStr}\n{sec:F0}s";
            }

            _buffInstances.Add(go);
        }
    }

    private void UpdateBuffTimers()
    {
        var bm = BuffManager.Instance;
        if (bm == null) return;

        int idx = 0;
        foreach (var kvp in bm.Buffs)
        {
            if (idx >= _buffInstances.Count) break;
            var go = _buffInstances[idx];
            if (go == null) { idx++; continue; }

            var text = go.GetComponentInChildren<Text>();
            if (text != null)
            {
                var buff = kvp.Value;
                float sec = buff.RemainingMs / 1000f;
                string stackStr = buff.Stacks > 1 ? $" x{buff.Stacks}" : "";
                text.text = $"B{buff.BuffId}{stackStr}\n{sec:F0}s";
            }
            idx++;
        }
    }
}
