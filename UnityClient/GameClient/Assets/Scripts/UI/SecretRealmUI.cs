// ━━━ SecretRealmUI.cs ━━━
// 비경 내부 UI — 타이머/등급/보상 표시 (S055 TASK 17)
// F12키로 비경 정보 패널 토글

using System;
using UnityEngine;
using UnityEngine.UI;

public class SecretRealmUI : MonoBehaviour
{
    // ━━━ 싱글톤 ━━━
    public static SecretRealmUI Instance { get; private set; }

    // ━━━ UI 요소 ━━━
    [SerializeField] private GameObject _realmPanel;
    [SerializeField] private Text _realmTitle;
    [SerializeField] private Text _timerText;
    [SerializeField] private Text _realmTypeText;
    [SerializeField] private Text _multiplierText;
    [SerializeField] private Text _specialTag;

    // 결과 패널
    [SerializeField] private GameObject _resultPanel;
    [SerializeField] private Text _resultTitle;
    [SerializeField] private Text _resultGrade;
    [SerializeField] private Text _resultGold;
    [SerializeField] private Text _resultBonus;
    [SerializeField] private Button _resultCloseButton;

    // ━━━ 상태 ━━━
    private bool _isRealmActive;

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
            mgr.OnRealmUIOpened += HandleRealmUIOpened;
            mgr.OnRealmUIClosed += HandleRealmUIClosed;
            mgr.OnTimerUpdated += HandleTimerUpdated;
            mgr.OnRealmCompleted += HandleRealmCompleted;
            mgr.OnRealmFailed += HandleRealmFailed;
            mgr.OnEnterResult += HandleEnterResult;
        }

        if (_resultCloseButton != null) _resultCloseButton.onClick.AddListener(OnResultCloseClicked);
        if (_realmPanel != null) _realmPanel.SetActive(false);
        if (_resultPanel != null) _resultPanel.SetActive(false);
    }

    private void OnDestroy()
    {
        var mgr = SecretRealmManager.Instance;
        if (mgr != null)
        {
            mgr.OnRealmUIOpened -= HandleRealmUIOpened;
            mgr.OnRealmUIClosed -= HandleRealmUIClosed;
            mgr.OnTimerUpdated -= HandleTimerUpdated;
            mgr.OnRealmCompleted -= HandleRealmCompleted;
            mgr.OnRealmFailed -= HandleRealmFailed;
            mgr.OnEnterResult -= HandleEnterResult;
        }
        if (Instance == this) Instance = null;
    }

    private void Update()
    {
        if (Input.GetKeyDown(KeyCode.F12) && _isRealmActive)
        {
            if (_realmPanel != null)
            {
                bool active = _realmPanel.activeSelf;
                _realmPanel.SetActive(!active);
            }
        }
    }

    // ━━━ 핸들러 ━━━

    private void HandleRealmUIOpened()
    {
        _isRealmActive = true;
        if (_realmPanel != null) _realmPanel.SetActive(true);
        if (_resultPanel != null) _resultPanel.SetActive(false);
    }

    private void HandleRealmUIClosed()
    {
        _isRealmActive = false;
        if (_realmPanel != null) _realmPanel.SetActive(false);
    }

    private void HandleEnterResult(Network.SecretRealmEnterResultData data)
    {
        if (data.Result != Network.SecretRealmEnterResult.SUCCESS) return;

        var mgr = SecretRealmManager.Instance;
        if (mgr == null) return;

        string typeName = SecretRealmManager.GetRealmTypeName(data.RealmType);
        if (_realmTitle != null) _realmTitle.text = typeName;
        if (_realmTypeText != null) _realmTypeText.text = $"Type: {typeName}";
        if (_multiplierText != null)
        {
            _multiplierText.text = data.Multiplier > 1f ? $"x{data.Multiplier:F1}" : "";
        }
        if (_specialTag != null)
        {
            _specialTag.text = data.IsSpecial ? "SPECIAL" : "";
        }
        if (_timerText != null)
        {
            _timerText.text = mgr.FormatTime(data.TimeLimit);
        }
    }

    private void HandleTimerUpdated(float remaining)
    {
        var mgr = SecretRealmManager.Instance;
        if (mgr == null) return;
        if (_timerText != null) _timerText.text = mgr.FormatTime(remaining);
    }

    private void HandleRealmCompleted(Network.SecretRealmCompleteData data)
    {
        _isRealmActive = false;
        if (_realmPanel != null) _realmPanel.SetActive(false);

        string gradeName = SecretRealmManager.GetGradeName(data.Grade);
        if (_resultTitle != null) _resultTitle.text = "비경 클리어!";
        if (_resultGrade != null) _resultGrade.text = $"등급: {gradeName}";
        if (_resultGold != null) _resultGold.text = $"보상: {data.GoldReward} Gold";
        if (_resultBonus != null) _resultBonus.text = data.BonusInfo.Length > 0 ? data.BonusInfo : "";
        if (_resultPanel != null) _resultPanel.SetActive(true);
    }

    private void HandleRealmFailed(Network.SecretRealmFailData data)
    {
        _isRealmActive = false;
        if (_realmPanel != null) _realmPanel.SetActive(false);

        if (_resultTitle != null) _resultTitle.text = "비경 실패";
        if (_resultGrade != null) _resultGrade.text = "";
        if (_resultGold != null) _resultGold.text = $"위로 보상: {data.ConsolationGold} Gold";
        if (_resultBonus != null) _resultBonus.text = "";
        if (_resultPanel != null) _resultPanel.SetActive(true);
    }

    private void OnResultCloseClicked()
    {
        if (_resultPanel != null) _resultPanel.SetActive(false);
        var mgr = SecretRealmManager.Instance;
        if (mgr != null) mgr.CloseRealmUI();
    }
}
