// ━━━ JobChangeUI.cs ━━━
// 2차 전직 UI — NetworkManager 이벤트 직접 구독
// Lv20 이상일 때 전직 선택 패널 (직업별 2가지) + 보너스 프리뷰

using System;
using UnityEngine;
using UnityEngine.UI;
using Network;

public class JobChangeUI : MonoBehaviour
{
    // ━━━ UI 참조 ━━━
    [SerializeField] private GameObject _panel;
    [SerializeField] private Text _titleLabel;
    [SerializeField] private Text _resultLabel;
    [SerializeField] private Transform _optionContainer;
    [SerializeField] private Button _closeButton;

    // 내부 상태
    private bool _isPanelOpen;
    private bool _hasChanged;

    // ━━━ 이벤트 ━━━
    public event Action<JobChangeResultData> OnJobChanged;

    // ━━━ 싱글톤 (Scene-bound) ━━━
    public static JobChangeUI Instance { get; private set; }

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
        if (_panel != null) _panel.SetActive(false);
        if (_closeButton != null) _closeButton.onClick.AddListener(ClosePanel);

        var net = NetworkManager.Instance;
        net.OnJobChangeResult += HandleJobChangeResult;
    }

    private void OnDestroy()
    {
        var net = NetworkManager.Instance;
        if (net == null) return;

        net.OnJobChangeResult -= HandleJobChangeResult;

        if (Instance == this) Instance = null;
    }

    private void Update()
    {
        // F7키로 전직 패널 토글
        if (Input.GetKeyDown(KeyCode.F7))
        {
            TogglePanel();
        }
    }

    // ━━━ 패널 토글 ━━━

    public void TogglePanel()
    {
        if (_isPanelOpen)
            ClosePanel();
        else
            OpenPanel();
    }

    public void OpenPanel()
    {
        _isPanelOpen = true;
        if (_panel != null) _panel.SetActive(true);
        RefreshUI();
    }

    public void ClosePanel()
    {
        _isPanelOpen = false;
        if (_panel != null) _panel.SetActive(false);
    }

    // ━━━ UI 갱신 ━━━

    private void RefreshUI()
    {
        if (_titleLabel != null)
        {
            _titleLabel.text = _hasChanged ? "2차 전직 완료" : "2차 전직 선택";
        }

        if (_resultLabel != null && !_hasChanged)
        {
            _resultLabel.text = "전직할 직업을 선택하세요 (Lv20 이상 필요)";
        }
    }

    // ━━━ 핸들러 ━━━

    private void HandleJobChangeResult(JobChangeResultData data)
    {
        Debug.Log($"[JobChangeUI] Result: {data.Result}, job={data.JobName}");

        if (_resultLabel == null) return;

        if (data.Result == JobChangeResult.SUCCESS)
        {
            _hasChanged = true;
            string bonusText = "";
            foreach (var b in data.Bonuses)
            {
                string sign = b.Value >= 0 ? "+" : "";
                bonusText += $"\n  {b.Key}: {sign}{b.Value}";
            }

            string skillText = "";
            if (data.NewSkills.Length > 0)
            {
                skillText = "\n신규 스킬: ";
                for (int i = 0; i < data.NewSkills.Length; i++)
                {
                    if (i > 0) skillText += ", ";
                    skillText += $"#{data.NewSkills[i]}";
                }
            }

            _resultLabel.text = $"전직 성공! → {data.JobName}{bonusText}{skillText}";
            OnJobChanged?.Invoke(data);
        }
        else
        {
            string reason = data.Result switch
            {
                JobChangeResult.LEVEL_TOO_LOW => "레벨이 부족합니다 (Lv20 필요)",
                JobChangeResult.ALREADY_CHANGED => "이미 전직 완료",
                JobChangeResult.INVALID_JOB => "잘못된 전직 직업",
                JobChangeResult.WRONG_CLASS => "직업 계열 불일치",
                _ => $"전직 실패 ({data.Result})"
            };
            _resultLabel.text = reason;
        }
    }

    // ━━━ 외부 호출 (버튼 바인딩용) ━━━

    /// <summary>전직 요청 (jobName: "berserker", "guardian" 등)</summary>
    public void RequestJobChange(string jobName)
    {
        NetworkManager.Instance.RequestJobChange(jobName);
    }
}
