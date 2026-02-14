// ━━━ WeatherManager.cs ━━━
// 날씨/시간 시스템 관리 — 날씨 전환 보간, 게임 시간 추적, 시간대 계산
// NetworkManager 이벤트 구독 → UI에 이벤트 발행

using System;
using UnityEngine;
using Network;

/// <summary>게임 내 시간대</summary>
public enum TimeOfDay : byte
{
    Dawn      = 0,  // 20~30%
    Morning   = 1,  // 30~45%
    Noon      = 2,  // 45~55%
    Afternoon = 3,  // 55~70%
    Evening   = 4,  // 70~80%
    Night     = 5,  // 80~20% (wrapping)
}

public class WeatherManager : MonoBehaviour
{
    // ━━━ 상태 ━━━
    private WeatherType _currentWeather = WeatherType.CLEAR;
    private WeatherType _previousWeather = WeatherType.CLEAR;
    private uint _gameTimeSec;
    private float _transitionTimer;
    private float _transitionDuration;
    private bool _isTransitioning;

    // ━━━ 계산 프로퍼티 ━━━
    public WeatherType CurrentWeather => _currentWeather;
    public uint GameTime => _gameTimeSec;
    public TimeOfDay TimeOfDay => GetTimeOfDay();

    /// <summary>하루 진행률 (0~1)</summary>
    public float DayProgress
    {
        get
        {
            // 게임 내 하루 = 3600초 (TIME_UPDATE 기준)
            if (_gameTimeSec == 0) return 0f;
            return Mathf.Clamp01(_gameTimeSec / 3600f);
        }
    }

    /// <summary>날씨 전환 보간 (0=이전 날씨, 1=현재 날씨)</summary>
    public float WeatherBlend
    {
        get
        {
            if (!_isTransitioning || _transitionDuration <= 0f) return 1f;
            return Mathf.Clamp01(1f - _transitionTimer / _transitionDuration);
        }
    }

    // ━━━ 이벤트 ━━━
    public event Action<WeatherType, byte> OnWeatherChanged;
    public event Action<uint> OnTimeChanged;

    // ━━━ 싱글톤 (Scene-bound) ━━━
    public static WeatherManager Instance { get; private set; }

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
        net.OnWeatherUpdate += HandleWeatherUpdate;
        net.OnTimeUpdate += HandleTimeUpdate;
    }

    private void OnDestroy()
    {
        var net = NetworkManager.Instance;
        if (net == null) return;

        net.OnWeatherUpdate -= HandleWeatherUpdate;
        net.OnTimeUpdate -= HandleTimeUpdate;

        if (Instance == this) Instance = null;
    }

    private void Update()
    {
        // 날씨 전환 타이머
        if (_isTransitioning)
        {
            _transitionTimer -= Time.deltaTime;
            if (_transitionTimer <= 0f)
            {
                _transitionTimer = 0f;
                _isTransitioning = false;
            }
        }
    }

    // ━━━ 공개 API ━━━

    /// <summary>현재 게임 시간 기반 시간대 계산</summary>
    public TimeOfDay GetTimeOfDay()
    {
        float progress = DayProgress * 100f; // 0~100 퍼센트

        // Night wraps: 80~100% AND 0~20%
        if (progress >= 80f || progress < 20f)
            return TimeOfDay.Night;
        if (progress < 30f)
            return TimeOfDay.Dawn;
        if (progress < 45f)
            return TimeOfDay.Morning;
        if (progress < 55f)
            return TimeOfDay.Noon;
        if (progress < 70f)
            return TimeOfDay.Afternoon;
        // 70~80%
        return TimeOfDay.Evening;
    }

    // ━━━ 핸들러 ━━━

    private void HandleWeatherUpdate(WeatherUpdateData data)
    {
        _previousWeather = _currentWeather;
        _currentWeather = data.Weather;
        _transitionDuration = data.TransitionSeconds;
        _transitionTimer = data.TransitionSeconds;
        _isTransitioning = data.TransitionSeconds > 0;

        Debug.Log($"[WeatherManager] Weather: {_previousWeather} -> {_currentWeather}, transition={data.TransitionSeconds}s");
        OnWeatherChanged?.Invoke(_currentWeather, data.TransitionSeconds);
    }

    private void HandleTimeUpdate(uint gameTimeSec)
    {
        _gameTimeSec = gameTimeSec;
        OnTimeChanged?.Invoke(gameTimeSec);
    }
}
