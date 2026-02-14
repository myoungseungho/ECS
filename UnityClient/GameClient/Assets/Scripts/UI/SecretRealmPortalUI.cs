// ━━━ SecretRealmPortalUI.cs ━━━
// 비경 포탈 스폰 알림 + 미니맵 아이콘 (S055 TASK 17)
// 포탈 스폰 브로드캐스트 수신 → 화면 중앙 팝업 + 입장 버튼

using System;
using UnityEngine;
using UnityEngine.UI;

public class SecretRealmPortalUI : MonoBehaviour
{
    // ━━━ 싱글톤 ━━━
    public static SecretRealmPortalUI Instance { get; private set; }

    // ━━━ UI 요소 ━━━
    [SerializeField] private GameObject _notifyPanel;
    [SerializeField] private Text _notifyTitle;
    [SerializeField] private Text _notifyDesc;
    [SerializeField] private Text _notifyMultiplier;
    [SerializeField] private Button _enterButton;
    [SerializeField] private Button _closeButton;

    // ━━━ 상태 ━━━
    private byte _lastSpawnZoneId;
    private float _notifyTimer;
    private const float NOTIFY_DURATION = 8f;

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
        var mgr = SecretRealmManager.Instance;
        if (mgr != null)
        {
            mgr.OnPortalSpawned += HandlePortalSpawned;
        }

        if (_enterButton != null) _enterButton.onClick.AddListener(OnEnterClicked);
        if (_closeButton != null) _closeButton.onClick.AddListener(OnCloseClicked);
        if (_notifyPanel != null) _notifyPanel.SetActive(false);
    }

    private void OnDestroy()
    {
        var mgr = SecretRealmManager.Instance;
        if (mgr != null)
        {
            mgr.OnPortalSpawned -= HandlePortalSpawned;
        }
        if (Instance == this) Instance = null;
    }

    private void Update()
    {
        if (_notifyPanel != null && _notifyPanel.activeSelf && _notifyTimer > 0f)
        {
            _notifyTimer -= Time.deltaTime;
            if (_notifyTimer <= 0f)
            {
                _notifyPanel.SetActive(false);
            }
        }
    }

    // ━━━ 핸들러 ━━━

    private void HandlePortalSpawned(Network.SecretRealmSpawnData data)
    {
        _lastSpawnZoneId = data.ZoneId;
        _notifyTimer = NOTIFY_DURATION;

        string specialTag = data.IsSpecial ? " [SPECIAL]" : "";
        string mulText = data.Multiplier > 1f ? $" x{data.Multiplier:F1}" : "";

        if (_notifyTitle != null) _notifyTitle.text = $"비경 포탈 발견!{specialTag}";
        if (_notifyDesc != null) _notifyDesc.text = $"{data.Name} (Zone {data.ZoneId})";
        if (_notifyMultiplier != null) _notifyMultiplier.text = mulText;
        if (_notifyPanel != null) _notifyPanel.SetActive(true);
    }

    private void OnEnterClicked()
    {
        var mgr = SecretRealmManager.Instance;
        if (mgr != null)
        {
            mgr.EnterRealm(_lastSpawnZoneId);
        }
        if (_notifyPanel != null) _notifyPanel.SetActive(false);
    }

    private void OnCloseClicked()
    {
        if (_notifyPanel != null) _notifyPanel.SetActive(false);
    }
}
