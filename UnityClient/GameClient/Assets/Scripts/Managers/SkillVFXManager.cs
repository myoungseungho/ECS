// ━━━ SkillVFXManager.cs ━━━
// vfx.yaml 기반 — 스킬 사용 시 이펙트 + 레벨업 이펙트
// SkillManager 이벤트 구독 → 스킬 시전 위치에 ParticleSystem 스폰
// Object Pool 방식으로 파티클 재사용

using System.Collections.Generic;
using UnityEngine;
using Network;

public class SkillVFXManager : MonoBehaviour
{
    [Header("Pool")]
    [SerializeField] private int poolSize = 10;

    [Header("Skill VFX — vfx.yaml melee_effects")]
    [SerializeField] private Color skillColor = new Color(0.2f, 0.6f, 1f, 1f);
    [SerializeField] private int skillParticleCount = 15;
    [SerializeField] private float skillSpeed = 4f;
    [SerializeField] private float skillLifetime = 0.3f;
    [SerializeField] private float skillSize = 0.1f;

    [Header("Level Up VFX")]
    [SerializeField] private Color levelUpColor = new Color(1f, 0.843f, 0f, 1f); // Gold
    [SerializeField] private int levelUpParticleCount = 50;
    [SerializeField] private float levelUpSpeed = 5f;
    [SerializeField] private float levelUpLifetime = 1.5f;

    public static SkillVFXManager Instance { get; private set; }

    private readonly Queue<ParticleSystem> _skillPool = new Queue<ParticleSystem>();
    private readonly Queue<ParticleSystem> _levelUpPool = new Queue<ParticleSystem>();

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
        InitPools();

        if (SkillManager.Instance != null)
            SkillManager.Instance.OnSkillUsed += HandleSkillUsed;

        if (StatsManager.Instance != null)
            StatsManager.Instance.OnStatsChanged += HandleStatsChanged;
    }

    private void OnDestroy()
    {
        if (SkillManager.Instance != null)
            SkillManager.Instance.OnSkillUsed -= HandleSkillUsed;

        if (StatsManager.Instance != null)
            StatsManager.Instance.OnStatsChanged -= HandleStatsChanged;

        if (Instance == this) Instance = null;
    }

    // ━━━ 공개 API ━━━

    public void PlaySkillEffect(Vector3 position)
    {
        var ps = GetFromPool(_skillPool);
        if (ps == null) return;

        ps.transform.position = position + Vector3.up * 0.5f;
        ps.gameObject.SetActive(true);
        ps.Play();
    }

    public void PlayLevelUpEffect(Vector3 position)
    {
        var ps = GetFromPool(_levelUpPool);
        if (ps == null) return;

        ps.transform.position = position;
        ps.gameObject.SetActive(true);
        ps.Play();
    }

    // ━━━ 이벤트 핸들러 ━━━

    private void HandleSkillUsed(SkillResultData data)
    {
        if (data.Result != 0) return;

        // 시전자 위치에 이펙트
        if (EntityManager.Instance != null)
        {
            var lp = EntityManager.Instance.LocalPlayer;
            if (lp != null)
                PlaySkillEffect(lp.transform.position);
        }
    }

    private int _lastLevel;

    private void HandleStatsChanged()
    {
        if (StatsManager.Instance == null) return;
        int currentLevel = StatsManager.Instance.Level;
        if (_lastLevel > 0 && currentLevel > _lastLevel)
        {
            if (EntityManager.Instance != null)
            {
                var lp = EntityManager.Instance.LocalPlayer;
                if (lp != null)
                    PlayLevelUpEffect(lp.transform.position);
            }
        }
        _lastLevel = currentLevel;
    }

    // ━━━ 풀 ━━━

    private void InitPools()
    {
        for (int i = 0; i < poolSize; i++)
        {
            _skillPool.Enqueue(CreateSkillParticle());
            _levelUpPool.Enqueue(CreateLevelUpParticle());
        }
    }

    private ParticleSystem CreateSkillParticle()
    {
        var go = new GameObject("VFX_Skill");
        go.transform.SetParent(transform);
        go.SetActive(false);

        var ps = go.AddComponent<ParticleSystem>();
        var main = ps.main;
        main.playOnAwake = false;
        main.loop = false;
        main.duration = skillLifetime + 0.1f;
        main.startLifetime = skillLifetime;
        main.startSpeed = skillSpeed;
        main.startSize = skillSize;
        main.startColor = skillColor;
        main.simulationSpace = ParticleSystemSimulationSpace.World;
        main.maxParticles = skillParticleCount * 2;
        main.stopAction = ParticleSystemStopAction.Callback;

        var emission = ps.emission;
        emission.enabled = true;
        emission.rateOverTime = 0;
        emission.SetBurst(0, new ParticleSystem.Burst(0f, (short)skillParticleCount));

        var shape = ps.shape;
        shape.enabled = true;
        shape.shapeType = ParticleSystemShapeType.Sphere;
        shape.radius = 0.5f;

        var colorOverLifetime = ps.colorOverLifetime;
        colorOverLifetime.enabled = true;
        var gradient = new Gradient();
        gradient.SetKeys(
            new[] { new GradientColorKey(skillColor, 0f), new GradientColorKey(Color.white, 1f) },
            new[] { new GradientAlphaKey(1f, 0f), new GradientAlphaKey(0f, 1f) }
        );
        colorOverLifetime.color = gradient;

        var sizeOverLifetime = ps.sizeOverLifetime;
        sizeOverLifetime.enabled = true;
        sizeOverLifetime.size = new ParticleSystem.MinMaxCurve(1f, 0f);

        var renderer = go.GetComponent<ParticleSystemRenderer>();
        if (renderer != null)
            renderer.renderMode = ParticleSystemRenderMode.Billboard;

        var callback = go.AddComponent<VFXReturnToPool>();
        callback.Setup(ps, _skillPool);

        return ps;
    }

    private ParticleSystem CreateLevelUpParticle()
    {
        var go = new GameObject("VFX_LevelUp");
        go.transform.SetParent(transform);
        go.SetActive(false);

        var ps = go.AddComponent<ParticleSystem>();
        var main = ps.main;
        main.playOnAwake = false;
        main.loop = false;
        main.duration = levelUpLifetime + 0.2f;
        main.startLifetime = levelUpLifetime;
        main.startSpeed = levelUpSpeed;
        main.startSize = 0.15f;
        main.startColor = levelUpColor;
        main.simulationSpace = ParticleSystemSimulationSpace.World;
        main.maxParticles = levelUpParticleCount * 2;
        main.stopAction = ParticleSystemStopAction.Callback;
        main.gravityModifier = -0.5f; // 위로 올라가는 효과

        var emission = ps.emission;
        emission.enabled = true;
        emission.rateOverTime = 0;
        emission.SetBurst(0, new ParticleSystem.Burst(0f, (short)levelUpParticleCount));

        var shape = ps.shape;
        shape.enabled = true;
        shape.shapeType = ParticleSystemShapeType.Cone;
        shape.angle = 5f;
        shape.radius = 0.3f;
        shape.rotation = new Vector3(-90f, 0f, 0f); // 위쪽 방향

        var colorOverLifetime = ps.colorOverLifetime;
        colorOverLifetime.enabled = true;
        var gradient = new Gradient();
        gradient.SetKeys(
            new[] {
                new GradientColorKey(levelUpColor, 0f),
                new GradientColorKey(Color.white, 0.5f),
                new GradientColorKey(levelUpColor, 1f)
            },
            new[] { new GradientAlphaKey(1f, 0f), new GradientAlphaKey(0f, 1f) }
        );
        colorOverLifetime.color = gradient;

        var sizeOverLifetime = ps.sizeOverLifetime;
        sizeOverLifetime.enabled = true;
        sizeOverLifetime.size = new ParticleSystem.MinMaxCurve(0.5f, 1.5f);

        var renderer = go.GetComponent<ParticleSystemRenderer>();
        if (renderer != null)
            renderer.renderMode = ParticleSystemRenderMode.Billboard;

        var callback = go.AddComponent<VFXReturnToPool>();
        callback.Setup(ps, _levelUpPool);

        return ps;
    }

    private static ParticleSystem GetFromPool(Queue<ParticleSystem> pool)
    {
        if (pool.Count == 0) return null;
        return pool.Dequeue();
    }
}
