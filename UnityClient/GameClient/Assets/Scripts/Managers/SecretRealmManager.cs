// ━━━ SecretRealmManager.cs ━━━
// 비경 탐험 시스템 관리 (S055 TASK 17)
// MsgType: 540-544 — 포탈 스폰/입장/클리어/실패

using System;
using System.Collections.Generic;
using UnityEngine;

public class SecretRealmManager : MonoBehaviour
{
    // ━━━ 싱글톤 ━━━
    public static SecretRealmManager Instance { get; private set; }

    // ━━━ 상수 (GDD secret_realm_conditions.yaml) ━━━
    public const int UNLOCK_LEVEL = 20;
    public const int DAILY_LIMIT = 3;
    public const int MAX_PARTY_SIZE = 2;

    // ━━━ 비경 이름 테이블 ━━━
    private static readonly string[] RealmTypeNames = {
        "시련의 방", "지혜의 방", "보물의 방", "수련의 방", "운명의 방"
    };
    private static readonly string[] GradeNames = { "S", "A", "B", "C" };

    // ━━━ 상태 ━━━
    private bool _isInRealm;
    private ushort _currentInstanceId;
    private Network.SecretRealmType _currentRealmType;
    private float _timeLimit;
    private float _timeRemaining;
    private bool _isSpecial;
    private float _multiplier;
    private bool _isRealmUIOpen;
    private readonly Dictionary<byte, Network.SecretRealmSpawnData> _activePortals = new Dictionary<byte, Network.SecretRealmSpawnData>();

    // ━━━ 프로퍼티 ━━━
    public bool IsInRealm => _isInRealm;
    public ushort CurrentInstanceId => _currentInstanceId;
    public Network.SecretRealmType CurrentRealmType => _currentRealmType;
    public float TimeLimit => _timeLimit;
    public float TimeRemaining => _timeRemaining;
    public bool IsSpecial => _isSpecial;
    public float Multiplier => _multiplier;
    public bool IsRealmUIOpen => _isRealmUIOpen;
    public IReadOnlyDictionary<byte, Network.SecretRealmSpawnData> ActivePortals => _activePortals;

    // ━━━ 이벤트 ━━━
    public event Action<Network.SecretRealmSpawnData> OnPortalSpawned;
    public event Action<Network.SecretRealmEnterResultData> OnEnterResult;
    public event Action<Network.SecretRealmCompleteData> OnRealmCompleted;
    public event Action<Network.SecretRealmFailData> OnRealmFailed;
    public event Action OnRealmUIOpened;
    public event Action OnRealmUIClosed;
    public event Action<float> OnTimerUpdated;

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
        var nm = Network.NetworkManager.Instance;
        if (nm != null)
        {
            nm.OnSecretRealmSpawn += HandleRealmSpawn;
            nm.OnSecretRealmEnterResult += HandleEnterResult;
            nm.OnSecretRealmComplete += HandleComplete;
            nm.OnSecretRealmFail += HandleFail;
        }
    }

    private void OnDestroy()
    {
        var nm = Network.NetworkManager.Instance;
        if (nm != null)
        {
            nm.OnSecretRealmSpawn -= HandleRealmSpawn;
            nm.OnSecretRealmEnterResult -= HandleEnterResult;
            nm.OnSecretRealmComplete -= HandleComplete;
            nm.OnSecretRealmFail -= HandleFail;
        }
        if (Instance == this) Instance = null;
    }

    private void Update()
    {
        if (_isInRealm && _timeRemaining > 0f)
        {
            _timeRemaining -= Time.deltaTime;
            if (_timeRemaining <= 0f)
            {
                _timeRemaining = 0f;
                ReportFail();
            }
            OnTimerUpdated?.Invoke(_timeRemaining);
        }
    }

    // ━━━ 핸들러 ━━━

    private void HandleRealmSpawn(Network.SecretRealmSpawnData data)
    {
        _activePortals[data.ZoneId] = data;
        OnPortalSpawned?.Invoke(data);
    }

    private void HandleEnterResult(Network.SecretRealmEnterResultData data)
    {
        if (data.Result == Network.SecretRealmEnterResult.SUCCESS)
        {
            _isInRealm = true;
            _currentInstanceId = data.InstanceId;
            _currentRealmType = data.RealmType;
            _timeLimit = data.TimeLimit;
            _timeRemaining = data.TimeLimit;
            _isSpecial = data.IsSpecial;
            _multiplier = data.Multiplier;
            _isRealmUIOpen = true;
            OnRealmUIOpened?.Invoke();
        }
        OnEnterResult?.Invoke(data);
    }

    private void HandleComplete(Network.SecretRealmCompleteData data)
    {
        _isInRealm = false;
        _timeRemaining = 0f;
        OnRealmCompleted?.Invoke(data);
    }

    private void HandleFail(Network.SecretRealmFailData data)
    {
        _isInRealm = false;
        _timeRemaining = 0f;
        OnRealmFailed?.Invoke(data);
    }

    // ━━━ 공개 API ━━━

    public void EnterRealm(byte zoneId, byte autoSpawn = 0)
    {
        Network.NetworkManager.Instance?.RequestSecretRealmEnter(zoneId, autoSpawn);
    }

    public void ReportComplete(ushort scoreValue, byte extraData)
    {
        Network.NetworkManager.Instance?.RequestSecretRealmComplete(scoreValue, extraData);
    }

    public void ReportFail()
    {
        Network.NetworkManager.Instance?.RequestSecretRealmFail();
    }

    public void CloseRealmUI()
    {
        _isRealmUIOpen = false;
        OnRealmUIClosed?.Invoke();
    }

    public bool HasPortalInZone(byte zoneId)
    {
        return _activePortals.ContainsKey(zoneId);
    }

    public void ClearPortal(byte zoneId)
    {
        _activePortals.Remove(zoneId);
    }

    public static string GetRealmTypeName(Network.SecretRealmType type)
    {
        int idx = (int)type;
        return idx >= 0 && idx < RealmTypeNames.Length ? RealmTypeNames[idx] : "Unknown";
    }

    public static string GetGradeName(Network.SecretRealmGrade grade)
    {
        int idx = (int)grade;
        return idx >= 0 && idx < GradeNames.Length ? GradeNames[idx] : "?";
    }

    public string FormatTime(float seconds)
    {
        int min = Mathf.FloorToInt(seconds / 60f);
        int sec = Mathf.FloorToInt(seconds % 60f);
        return $"{min:D2}:{sec:D2}";
    }
}
