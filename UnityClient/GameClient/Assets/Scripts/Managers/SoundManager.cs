// ━━━ SoundManager.cs ━━━
// 프로시저럴 오디오 생성 — 타격음, UI 클릭, 레벨업
// CombatManager/SkillManager/StatsManager 이벤트 구독

using System;
using UnityEngine;
using Network;

public class SoundManager : MonoBehaviour
{
    [Header("Volume")]
    [SerializeField] private float masterVolume = 0.5f;
    [SerializeField] private float sfxVolume = 0.7f;
    [SerializeField] private float uiVolume = 0.5f;

    public static SoundManager Instance { get; private set; }

    private AudioSource _sfxSource;
    private AudioSource _uiSource;

    // 캐싱된 프로시저럴 클립
    private AudioClip _hitClip;
    private AudioClip _critHitClip;
    private AudioClip _uiClickClip;
    private AudioClip _levelUpClip;
    private AudioClip _skillUseClip;
    private AudioClip _deathClip;

    private void Awake()
    {
        if (Instance != null && Instance != this)
        {
            Destroy(gameObject);
            return;
        }
        Instance = this;

        _sfxSource = gameObject.AddComponent<AudioSource>();
        _sfxSource.playOnAwake = false;

        _uiSource = gameObject.AddComponent<AudioSource>();
        _uiSource.playOnAwake = false;

        GenerateAllClips();
    }

    private void Start()
    {
        if (CombatManager.Instance != null)
        {
            CombatManager.Instance.OnAttackFeedback += HandleAttack;
            CombatManager.Instance.OnEntityDied += HandleDeath;
        }

        if (SkillManager.Instance != null)
            SkillManager.Instance.OnSkillUsed += HandleSkillUsed;

        if (StatsManager.Instance != null)
            StatsManager.Instance.OnStatsChanged += HandleStatsChanged;
    }

    private void OnDestroy()
    {
        if (CombatManager.Instance != null)
        {
            CombatManager.Instance.OnAttackFeedback -= HandleAttack;
            CombatManager.Instance.OnEntityDied -= HandleDeath;
        }

        if (SkillManager.Instance != null)
            SkillManager.Instance.OnSkillUsed -= HandleSkillUsed;

        if (StatsManager.Instance != null)
            StatsManager.Instance.OnStatsChanged -= HandleStatsChanged;

        if (Instance == this) Instance = null;
    }

    // ━━━ 공개 API ━━━

    public void PlayHit() => PlaySFX(_hitClip);
    public void PlayCritHit() => PlaySFX(_critHitClip);
    public void PlayUIClick() => PlayUI(_uiClickClip);
    public void PlayLevelUp() => PlaySFX(_levelUpClip);
    public void PlaySkillUse() => PlaySFX(_skillUseClip);

    // ━━━ 이벤트 핸들러 ━━━

    private int _lastLevel;

    private void HandleAttack(AttackResultData data)
    {
        if (data.Damage >= 50)
            PlayCritHit();
        else
            PlayHit();
    }

    private void HandleDeath(CombatDiedData data)
    {
        PlaySFX(_deathClip);
    }

    private void HandleSkillUsed(SkillResultData data)
    {
        if (data.Result == 0)
            PlaySkillUse();
    }

    private void HandleStatsChanged()
    {
        if (StatsManager.Instance == null) return;
        int currentLevel = StatsManager.Instance.Level;
        if (_lastLevel > 0 && currentLevel > _lastLevel)
            PlayLevelUp();
        _lastLevel = currentLevel;
    }

    // ━━━ 재생 ━━━

    private void PlaySFX(AudioClip clip)
    {
        if (clip == null || _sfxSource == null) return;
        _sfxSource.volume = masterVolume * sfxVolume;
        _sfxSource.PlayOneShot(clip);
    }

    private void PlayUI(AudioClip clip)
    {
        if (clip == null || _uiSource == null) return;
        _uiSource.volume = masterVolume * uiVolume;
        _uiSource.PlayOneShot(clip);
    }

    // ━━━ 프로시저럴 오디오 생성 ━━━

    private void GenerateAllClips()
    {
        _hitClip = GenerateHitSound(0.05f, 0.8f);
        _critHitClip = GenerateHitSound(0.08f, 1.0f);
        _uiClickClip = GenerateSineWave(0.1f, 800f, 0.3f);
        _levelUpClip = GenerateLevelUpChime();
        _skillUseClip = GenerateSineWave(0.08f, 600f, 0.4f);
        _deathClip = GenerateSineWave(0.3f, 200f, 0.5f);
    }

    /// <summary>타격음: white noise + 급격한 감쇠</summary>
    private AudioClip GenerateHitSound(float duration, float volume)
    {
        int sampleRate = 44100;
        int samples = (int)(sampleRate * duration);
        float[] data = new float[samples];
        var rng = new System.Random(42);

        for (int i = 0; i < samples; i++)
        {
            float t = (float)i / samples;
            float envelope = Mathf.Exp(-t * 30f); // 급격한 감쇠
            float noise = (float)(rng.NextDouble() * 2.0 - 1.0);
            data[i] = noise * envelope * volume;
        }

        var clip = AudioClip.Create("Hit", samples, 1, sampleRate, false);
        clip.SetData(data, 0);
        return clip;
    }

    /// <summary>사인파 톤</summary>
    private AudioClip GenerateSineWave(float duration, float frequency, float volume)
    {
        int sampleRate = 44100;
        int samples = (int)(sampleRate * duration);
        float[] data = new float[samples];

        for (int i = 0; i < samples; i++)
        {
            float t = (float)i / samples;
            float envelope = 1f - t; // 선형 감쇠
            data[i] = Mathf.Sin(2f * Mathf.PI * frequency * i / sampleRate) * envelope * volume;
        }

        var clip = AudioClip.Create("Tone", samples, 1, sampleRate, false);
        clip.SetData(data, 0);
        return clip;
    }

    /// <summary>레벨업: C5-E5-G5-C6 시퀀스</summary>
    private AudioClip GenerateLevelUpChime()
    {
        float[] notes = { 523.25f, 659.25f, 783.99f, 1046.50f }; // C5, E5, G5, C6
        float noteDuration = 0.15f;
        float totalDuration = noteDuration * notes.Length;
        int sampleRate = 44100;
        int totalSamples = (int)(sampleRate * totalDuration);
        float[] data = new float[totalSamples];

        for (int n = 0; n < notes.Length; n++)
        {
            int startSample = (int)(n * noteDuration * sampleRate);
            int noteSamples = (int)(noteDuration * sampleRate);

            for (int i = 0; i < noteSamples && (startSample + i) < totalSamples; i++)
            {
                float t = (float)i / noteSamples;
                float envelope = Mathf.Clamp01(1f - t * 1.5f);
                float sample = Mathf.Sin(2f * Mathf.PI * notes[n] * i / sampleRate);
                data[startSample + i] += sample * envelope * 0.4f;
            }
        }

        var clip = AudioClip.Create("LevelUp", totalSamples, 1, sampleRate, false);
        clip.SetData(data, 0);
        return clip;
    }
}
