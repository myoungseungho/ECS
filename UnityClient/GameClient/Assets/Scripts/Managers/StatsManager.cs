// ━━━ StatsManager.cs ━━━
// 내 캐릭터의 스탯 동기화 및 관리
// NetworkManager.OnStatSync 구독 → UI에 OnStatsChanged 발행

using System;
using UnityEngine;
using Network;

public class StatsManager : MonoBehaviour
{
    // ━━━ 스탯 데이터 ━━━
    public int Level { get; private set; }
    public int HP { get; private set; }
    public int MaxHP { get; private set; }
    public int MP { get; private set; }
    public int MaxMP { get; private set; }
    public int ATK { get; private set; }
    public int DEF { get; private set; }
    public int EXP { get; private set; }
    public int EXPNext { get; private set; }

    // ━━━ 계산 프로퍼티 ━━━
    public bool IsAlive => HP > 0;
    public float HpRatio => MaxHP > 0 ? (float)HP / MaxHP : 0f;
    public float MpRatio => MaxMP > 0 ? (float)MP / MaxMP : 0f;
    public float ExpRatio => EXPNext > 0 ? (float)EXP / EXPNext : 0f;

    // ━━━ 이벤트 ━━━
    public event Action OnStatsChanged;

    // ━━━ 싱글톤 (Scene-bound) ━━━
    public static StatsManager Instance { get; private set; }

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
        var net = NetworkManager.Instance;
        net.OnStatSync += HandleStatSync;
        net.OnEnterGame += HandleEnterGame;
    }

    private void OnDestroy()
    {
        var net = NetworkManager.Instance;
        if (net == null) return;

        net.OnStatSync -= HandleStatSync;
        net.OnEnterGame -= HandleEnterGame;

        if (Instance == this) Instance = null;
    }

    private void HandleStatSync(StatSyncData data)
    {
        Level   = data.Level;
        HP      = data.HP;
        MaxHP   = data.MaxHP;
        MP      = data.MP;
        MaxMP   = data.MaxMP;
        ATK     = data.ATK;
        DEF     = data.DEF;
        EXP     = data.EXP;
        EXPNext = data.EXPNext;

        OnStatsChanged?.Invoke();
    }

    private void HandleEnterGame(EnterGameResult result)
    {
        if (result.ResultCode != 0) return;

        // 게임 진입 시 자동 스탯 요청
        NetworkManager.Instance.RequestStatSync();
    }
}
