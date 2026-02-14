// ━━━ HitVFXManager.cs ━━━
// vfx.yaml hit_effects 기반 — 타격 이펙트 파티클 시스템
// CombatManager 이벤트 구독 → 피격 위치에 ParticleSystem 스폰
// Object Pool 방식으로 파티클 재사용

using System;
using System.Collections.Generic;
using UnityEngine;
using Network;

public class HitVFXManager : MonoBehaviour
{
    [Header("Pool")]
    [SerializeField] private int poolSize = 20;

    [Header("Normal Hit — vfx.yaml hit_effects.normal_hit")]
    [SerializeField] private int normalSparkCount = 8;
    [SerializeField] private float normalSparkSpeed = 3.5f;
    [SerializeField] private float normalSparkLifetime = 0.15f;
    [SerializeField] private float normalSparkSize = 0.08f;

    [Header("Critical Hit — vfx.yaml hit_effects.critical_hit")]
    [SerializeField] private int critSparkCount = 20;
    [SerializeField] private float critSparkSpeed = 5.5f;
    [SerializeField] private float critSparkLifetime = 0.2f;
    [SerializeField] private float critSparkSize = 0.12f;

    // ━━━ 싱글톤 (Scene-bound) ━━━
    public static HitVFXManager Instance { get; private set; }

    private readonly Queue<ParticleSystem> _normalPool = new Queue<ParticleSystem>();
    private readonly Queue<ParticleSystem> _critPool = new Queue<ParticleSystem>();

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

        if (CombatManager.Instance != null)
            CombatManager.Instance.OnAttackFeedback += HandleAttackFeedback;
    }

    private void OnDestroy()
    {
        if (CombatManager.Instance != null)
            CombatManager.Instance.OnAttackFeedback -= HandleAttackFeedback;

        if (Instance == this) Instance = null;
    }

    // ━━━ 공개 API ━━━

    public void PlayNormalHit(Vector3 position)
    {
        var ps = GetFromPool(_normalPool);
        if (ps == null) return;

        ps.transform.position = position + Vector3.up * 0.5f;
        ps.gameObject.SetActive(true);
        ps.Play();
    }

    public void PlayCriticalHit(Vector3 position)
    {
        var ps = GetFromPool(_critPool);
        if (ps == null) return;

        ps.transform.position = position + Vector3.up * 0.5f;
        ps.gameObject.SetActive(true);
        ps.Play();
    }

    // ━━━ 내부 ━━━

    private void HandleAttackFeedback(AttackResultData data)
    {
        // 타겟 위치에 이펙트 재생
        if (MonsterManager.Instance == null) return;

        var monster = MonsterManager.Instance.GetMonster(data.TargetId);
        if (monster == null) return;

        Vector3 hitPos = monster.transform.position;

        // 크리티컬 판정: 데미지 50 이상이면 크리티컬 연출 (서버 IsCritical 필드 추가 전 임시)
        if (data.Damage >= 50)
            PlayCriticalHit(hitPos);
        else
            PlayNormalHit(hitPos);
    }

    private void InitPools()
    {
        for (int i = 0; i < poolSize; i++)
        {
            _normalPool.Enqueue(CreateHitParticle(
                "NormalHit", normalSparkCount, normalSparkSpeed,
                normalSparkLifetime, normalSparkSize, Color.white));

            _critPool.Enqueue(CreateHitParticle(
                "CritHit", critSparkCount, critSparkSpeed,
                critSparkLifetime, critSparkSize, new Color(1f, 0.843f, 0f)));
        }
    }

    private ParticleSystem CreateHitParticle(string label, int count, float speed,
        float lifetime, float size, Color color)
    {
        var go = new GameObject($"VFX_{label}");
        go.transform.SetParent(transform);
        go.SetActive(false);

        var ps = go.AddComponent<ParticleSystem>();
        var main = ps.main;
        main.playOnAwake = false;
        main.loop = false;
        main.duration = lifetime + 0.1f;
        main.startLifetime = lifetime;
        main.startSpeed = speed;
        main.startSize = size;
        main.startColor = color;
        main.simulationSpace = ParticleSystemSimulationSpace.World;
        main.maxParticles = count * 2;
        main.stopAction = ParticleSystemStopAction.Callback;

        var emission = ps.emission;
        emission.enabled = true;
        emission.rateOverTime = 0;
        emission.SetBurst(0, new ParticleSystem.Burst(0f, (short)count));

        var shape = ps.shape;
        shape.enabled = true;
        shape.shapeType = ParticleSystemShapeType.Sphere;
        shape.radius = 0.3f;

        var colorOverLifetime = ps.colorOverLifetime;
        colorOverLifetime.enabled = true;
        var gradient = new Gradient();
        gradient.SetKeys(
            new[] { new GradientColorKey(color, 0f), new GradientColorKey(color, 1f) },
            new[] { new GradientAlphaKey(1f, 0f), new GradientAlphaKey(0f, 1f) }
        );
        colorOverLifetime.color = gradient;

        var sizeOverLifetime = ps.sizeOverLifetime;
        sizeOverLifetime.enabled = true;
        sizeOverLifetime.size = new ParticleSystem.MinMaxCurve(1f, 0f);

        // Gravity (vfx.yaml: normal_hit gravity = 0.5 implied by spark behavior)
        var velocityOverLifetime = ps.velocityOverLifetime;
        velocityOverLifetime.enabled = true;
        velocityOverLifetime.y = -2f;

        // Renderer — 기본 ParticleSystemRenderer Material 사용 (색상은 main.startColor로 제어)
        var renderer = go.GetComponent<ParticleSystemRenderer>();
        if (renderer != null)
            renderer.renderMode = ParticleSystemRenderMode.Billboard;

        // Return to pool via callback
        var callback = go.AddComponent<VFXReturnToPool>();
        callback.Setup(ps, label == "CritHit" ? _critPool : _normalPool);

        return ps;
    }

    private static ParticleSystem GetFromPool(Queue<ParticleSystem> pool)
    {
        if (pool.Count == 0) return null;

        var ps = pool.Dequeue();
        return ps;
    }
}

/// <summary>
/// ParticleSystem 정지 시 풀에 반환하는 헬퍼
/// </summary>
public class VFXReturnToPool : MonoBehaviour
{
    private ParticleSystem _ps;
    private Queue<ParticleSystem> _pool;

    public void Setup(ParticleSystem ps, Queue<ParticleSystem> pool)
    {
        _ps = ps;
        _pool = pool;
    }

    private void OnParticleSystemStopped()
    {
        gameObject.SetActive(false);
        _pool?.Enqueue(_ps);
    }
}
