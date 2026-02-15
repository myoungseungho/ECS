// ━━━ StoryUI.cs ━━━
// 스토리 UI — 대화 선택지 패널 + 컷씬 오버레이 + 스토리 진행 패널
// StoryManager 이벤트 구독, UI를 코드로 직접 생성
// 1) 대화 선택지: 하단 NPC 대화 + 2~3 선택지 버튼
// 2) 컷씬 오버레이: 상하단 검은 바 + 우상단 스킵 버튼
// 3) 스토리 진행 패널: 챕터 + 메인 퀘스트 목표

using System.Collections.Generic;
using UnityEngine;
using UnityEngine.UI;
using Network;

public class StoryUI : MonoBehaviour
{
    // ━━━ 대화 선택지 UI ━━━
    private GameObject _dialogPanel;
    private Text _dialogLinesText;
    private GameObject _choiceContainer;
    private List<Button> _choiceButtons = new List<Button>();
    private List<Text> _choiceTexts = new List<Text>();
    private ushort _currentDialogNpcId;

    // ━━━ 컷씬 오버레이 UI ━━━
    private GameObject _cutsceneOverlay;
    private GameObject _topBar;
    private GameObject _bottomBar;
    private Button _skipButton;

    // ━━━ 스토리 진행 패널 UI ━━━
    private GameObject _progressPanel;
    private Text _chapterText;
    private Text _questNameText;
    private Text _questDescText;
    private Text _objectivesText;

    // ━━━ 색상 상수 ━━━
    private static readonly Color COL_DIALOG_BG = new Color(0.05f, 0.05f, 0.1f, 0.92f);
    private static readonly Color COL_CHOICE_DEFAULT = new Color(0.15f, 0.2f, 0.35f, 0.95f);
    private static readonly Color COL_CHOICE_HOVER = new Color(0.25f, 0.35f, 0.55f, 0.95f);
    private static readonly Color COL_BAR = new Color(0f, 0f, 0f, 1f);
    private static readonly Color COL_SKIP_BTN = new Color(0.6f, 0.2f, 0.2f, 0.8f);
    private static readonly Color COL_PROGRESS_BG = new Color(0.08f, 0.06f, 0.12f, 0.85f);
    private static readonly Color COL_GOLD = new Color(1f, 0.843f, 0f);

    // 최대 선택지 버튼 수
    private const int MAX_CHOICES = 3;

    private void Start()
    {
        BuildDialogUI();
        BuildCutsceneUI();
        BuildProgressUI();

        if (StoryManager.Instance != null)
        {
            StoryManager.Instance.OnDialogReceived += HandleDialogChoices;
            StoryManager.Instance.OnCutsceneStarted += HandleCutsceneStarted;
            StoryManager.Instance.OnCutsceneEnded += HandleCutsceneFinished;
            StoryManager.Instance.OnProgressUpdated += HandleStoryUpdated;
            StoryManager.Instance.OnMainQuestLoaded += HandleMainQuestUpdated;
        }

        // 초기 비활성
        _dialogPanel.SetActive(false);
        _cutsceneOverlay.SetActive(false);
        _progressPanel.SetActive(false);
    }

    private void OnDestroy()
    {
        if (StoryManager.Instance != null)
        {
            StoryManager.Instance.OnDialogReceived -= HandleDialogChoices;
            StoryManager.Instance.OnCutsceneStarted -= HandleCutsceneStarted;
            StoryManager.Instance.OnCutsceneEnded -= HandleCutsceneFinished;
            StoryManager.Instance.OnProgressUpdated -= HandleStoryUpdated;
            StoryManager.Instance.OnMainQuestLoaded -= HandleMainQuestUpdated;
        }
    }

    // ━━━ 1. 대화 선택지 패널 빌드 ━━━

    private void BuildDialogUI()
    {
        // 하단 고정 대화 패널 (화면 하단, 높이 220px)
        _dialogPanel = CreateRect("DialogPanel", transform, new Vector2(0, 0), new Vector2(0, 220),
            new Vector2(0f, 0f), new Vector2(1f, 0f), new Vector2(0.5f, 0f));
        var dialogBg = _dialogPanel.AddComponent<Image>();
        dialogBg.color = COL_DIALOG_BG;
        dialogBg.raycastTarget = true;

        // NPC 대화 텍스트 영역 (좌측, 대화 내용 표시)
        var linesGo = CreateRect("DialogLines", _dialogPanel.transform,
            new Vector2(20, -10), new Vector2(-280, -50),
            new Vector2(0f, 0f), new Vector2(0.6f, 1f), new Vector2(0f, 1f));
        var linesRT = linesGo.GetComponent<RectTransform>();
        linesRT.offsetMin = new Vector2(20, 10);
        linesRT.offsetMax = new Vector2(0, -10);
        _dialogLinesText = linesGo.AddComponent<Text>();
        _dialogLinesText.text = "";
        _dialogLinesText.fontSize = 16;
        _dialogLinesText.color = Color.white;
        _dialogLinesText.alignment = TextAnchor.UpperLeft;
        _dialogLinesText.font = Resources.GetBuiltinResource<Font>("LegacyRuntime.ttf");
        _dialogLinesText.horizontalOverflow = HorizontalWrapMode.Wrap;
        _dialogLinesText.verticalOverflow = VerticalWrapMode.Truncate;

        // 선택지 컨테이너 (우측)
        _choiceContainer = CreateRect("ChoiceContainer", _dialogPanel.transform,
            Vector2.zero, Vector2.zero,
            new Vector2(0.62f, 0f), new Vector2(1f, 1f), new Vector2(0.5f, 0.5f));
        var choiceContainerRT = _choiceContainer.GetComponent<RectTransform>();
        choiceContainerRT.offsetMin = new Vector2(10, 15);
        choiceContainerRT.offsetMax = new Vector2(-15, -15);

        // 선택지 버튼 3개 사전 생성
        for (int i = 0; i < MAX_CHOICES; i++)
        {
            float yPos = -i * 60;
            var btnGo = CreateRect($"Choice{i}", _choiceContainer.transform,
                new Vector2(0, yPos), new Vector2(0, 50),
                new Vector2(0f, 1f), new Vector2(1f, 1f), new Vector2(0.5f, 1f));
            var btnRT = btnGo.GetComponent<RectTransform>();
            btnRT.offsetMin = new Vector2(0, btnRT.offsetMin.y);
            btnRT.offsetMax = new Vector2(0, btnRT.offsetMax.y);

            var btnImg = btnGo.AddComponent<Image>();
            btnImg.color = COL_CHOICE_DEFAULT;
            var btn = btnGo.AddComponent<Button>();

            var txtGo = CreateRect("Text", btnGo.transform, Vector2.zero, Vector2.zero,
                Vector2.zero, Vector2.one, new Vector2(0.5f, 0.5f));
            var txt = txtGo.AddComponent<Text>();
            txt.text = "";
            txt.fontSize = 15;
            txt.color = Color.white;
            txt.alignment = TextAnchor.MiddleCenter;
            txt.font = Resources.GetBuiltinResource<Font>("LegacyRuntime.ttf");
            txt.horizontalOverflow = HorizontalWrapMode.Wrap;

            int capturedIndex = i; // 클로저용
            btn.onClick.AddListener(() => OnChoiceClick(capturedIndex));

            _choiceButtons.Add(btn);
            _choiceTexts.Add(txt);
            btnGo.SetActive(false);
        }
    }

    // ━━━ 2. 컷씬 오버레이 빌드 ━━━

    private void BuildCutsceneUI()
    {
        // 전체 화면 오버레이 (터치 차단)
        _cutsceneOverlay = CreateRect("CutsceneOverlay", transform, Vector2.zero, Vector2.zero,
            Vector2.zero, Vector2.one, new Vector2(0.5f, 0.5f));
        // 터치 차단을 위한 투명 이미지
        var overlayImg = _cutsceneOverlay.AddComponent<Image>();
        overlayImg.color = Color.clear;
        overlayImg.raycastTarget = true;

        // 상단 검은 바 (높이 80px)
        _topBar = CreateRect("TopBar", _cutsceneOverlay.transform, Vector2.zero, new Vector2(0, 80),
            new Vector2(0f, 1f), new Vector2(1f, 1f), new Vector2(0.5f, 1f));
        var topBarImg = _topBar.AddComponent<Image>();
        topBarImg.color = COL_BAR;

        // 하단 검은 바 (높이 80px)
        _bottomBar = CreateRect("BottomBar", _cutsceneOverlay.transform, Vector2.zero, new Vector2(0, 80),
            new Vector2(0f, 0f), new Vector2(1f, 0f), new Vector2(0.5f, 0f));
        var bottomBarImg = _bottomBar.AddComponent<Image>();
        bottomBarImg.color = COL_BAR;

        // 스킵 버튼 (우상단)
        var skipBtnGo = CreateRect("SkipButton", _cutsceneOverlay.transform,
            new Vector2(-20, -20), new Vector2(100, 35),
            new Vector2(1f, 1f), new Vector2(1f, 1f), new Vector2(1f, 1f));
        var skipBtnImg = skipBtnGo.AddComponent<Image>();
        skipBtnImg.color = COL_SKIP_BTN;
        _skipButton = skipBtnGo.AddComponent<Button>();
        _skipButton.onClick.AddListener(OnSkipClick);

        var skipTxtGo = CreateRect("Text", skipBtnGo.transform, Vector2.zero, Vector2.zero,
            Vector2.zero, Vector2.one, new Vector2(0.5f, 0.5f));
        var skipTxt = skipTxtGo.AddComponent<Text>();
        skipTxt.text = "Skip >>";
        skipTxt.fontSize = 14;
        skipTxt.fontStyle = FontStyle.Bold;
        skipTxt.color = Color.white;
        skipTxt.alignment = TextAnchor.MiddleCenter;
        skipTxt.font = Resources.GetBuiltinResource<Font>("LegacyRuntime.ttf");
    }

    // ━━━ 3. 스토리 진행 패널 빌드 ━━━

    private void BuildProgressUI()
    {
        // 우상단 스토리 진행 패널 (260x200)
        _progressPanel = CreateRect("StoryProgressPanel", transform,
            new Vector2(-15, -140), new Vector2(260, 200),
            new Vector2(1f, 1f), new Vector2(1f, 1f), new Vector2(1f, 1f));
        var progressBg = _progressPanel.AddComponent<Image>();
        progressBg.color = COL_PROGRESS_BG;

        // 챕터 표시
        var chapterGo = CreateRect("Chapter", _progressPanel.transform,
            new Vector2(10, -10), new Vector2(240, 25),
            new Vector2(0f, 1f), new Vector2(0f, 1f), new Vector2(0f, 1f));
        _chapterText = chapterGo.AddComponent<Text>();
        _chapterText.text = "Chapter 1";
        _chapterText.fontSize = 18;
        _chapterText.fontStyle = FontStyle.Bold;
        _chapterText.color = COL_GOLD;
        _chapterText.alignment = TextAnchor.MiddleLeft;
        _chapterText.font = Resources.GetBuiltinResource<Font>("LegacyRuntime.ttf");

        // 퀘스트 이름
        var questNameGo = CreateRect("QuestName", _progressPanel.transform,
            new Vector2(10, -38), new Vector2(240, 22),
            new Vector2(0f, 1f), new Vector2(0f, 1f), new Vector2(0f, 1f));
        _questNameText = questNameGo.AddComponent<Text>();
        _questNameText.text = "Main Quest";
        _questNameText.fontSize = 15;
        _questNameText.fontStyle = FontStyle.Bold;
        _questNameText.color = Color.white;
        _questNameText.alignment = TextAnchor.MiddleLeft;
        _questNameText.font = Resources.GetBuiltinResource<Font>("LegacyRuntime.ttf");

        // 퀘스트 설명
        var questDescGo = CreateRect("QuestDesc", _progressPanel.transform,
            new Vector2(10, -60), new Vector2(240, 36),
            new Vector2(0f, 1f), new Vector2(0f, 1f), new Vector2(0f, 1f));
        _questDescText = questDescGo.AddComponent<Text>();
        _questDescText.text = "";
        _questDescText.fontSize = 12;
        _questDescText.color = new Color(0.7f, 0.7f, 0.7f);
        _questDescText.alignment = TextAnchor.UpperLeft;
        _questDescText.font = Resources.GetBuiltinResource<Font>("LegacyRuntime.ttf");
        _questDescText.horizontalOverflow = HorizontalWrapMode.Wrap;
        _questDescText.verticalOverflow = VerticalWrapMode.Truncate;

        // 구분선
        var lineGo = CreateRect("Line", _progressPanel.transform,
            new Vector2(10, -98), new Vector2(240, 1),
            new Vector2(0f, 1f), new Vector2(0f, 1f), new Vector2(0f, 1f));
        var lineImg = lineGo.AddComponent<Image>();
        lineImg.color = new Color(0.4f, 0.4f, 0.4f, 0.5f);

        // 목표 리스트
        var objGo = CreateRect("Objectives", _progressPanel.transform,
            new Vector2(10, -105), new Vector2(240, 90),
            new Vector2(0f, 1f), new Vector2(0f, 1f), new Vector2(0f, 1f));
        _objectivesText = objGo.AddComponent<Text>();
        _objectivesText.text = "No objectives";
        _objectivesText.fontSize = 13;
        _objectivesText.color = new Color(0.85f, 0.85f, 0.85f);
        _objectivesText.alignment = TextAnchor.UpperLeft;
        _objectivesText.font = Resources.GetBuiltinResource<Font>("LegacyRuntime.ttf");
        _objectivesText.horizontalOverflow = HorizontalWrapMode.Wrap;
        _objectivesText.verticalOverflow = VerticalWrapMode.Truncate;
    }

    private void Update()
    {
        if (Input.GetKeyDown(KeyCode.J))
        {
            if (_progressPanel != null)
                _progressPanel.SetActive(!_progressPanel.activeSelf);
        }
    }

    // ━━━ 버튼 핸들러 ━━━

    private void OnChoiceClick(int choiceIndex)
    {
        StoryManager.Instance?.SelectChoice(_currentDialogNpcId, (byte)choiceIndex);

        // 선택 후 대화 패널 숨기기 (다음 대화가 오면 다시 표시)
        if (_dialogPanel != null)
            _dialogPanel.SetActive(false);
    }

    private void OnSkipClick()
    {
        StoryManager.Instance?.SkipCutscene();
    }

    // ━━━ 이벤트 핸들러 ━━━

    private void HandleDialogChoices(DialogChoiceResultData data)
    {
        _currentDialogNpcId = data.NpcId;

        // 대화 텍스트 조합
        if (_dialogLinesText != null)
        {
            var sb = new System.Text.StringBuilder();
            if (data.Lines != null)
            {
                for (int i = 0; i < data.Lines.Length; i++)
                {
                    var line = data.Lines[i];
                    if (!string.IsNullOrEmpty(line.Speaker))
                        sb.Append($"<color=#FFD700>{line.Speaker}</color>: ");
                    sb.AppendLine(line.Text);
                }
            }
            _dialogLinesText.text = sb.ToString();
        }

        // 선택지 버튼 갱신
        for (int i = 0; i < MAX_CHOICES; i++)
        {
            if (data.Choices != null && i < data.Choices.Length)
            {
                _choiceButtons[i].gameObject.SetActive(true);
                _choiceTexts[i].text = data.Choices[i];
            }
            else
            {
                _choiceButtons[i].gameObject.SetActive(false);
            }
        }

        // 대화 패널 표시
        if (_dialogPanel != null)
            _dialogPanel.SetActive(true);
    }

    private void HandleCutsceneStarted(CutsceneTriggerData data)
    {
        if (_cutsceneOverlay != null)
            _cutsceneOverlay.SetActive(true);

        // 컷씬 중에는 대화 패널 숨김
        if (_dialogPanel != null)
            _dialogPanel.SetActive(false);
    }

    private void HandleCutsceneFinished(ushort cutsceneId)
    {
        if (_cutsceneOverlay != null)
            _cutsceneOverlay.SetActive(false);
    }

    private void HandleStoryUpdated(StoryProgressData data)
    {
        if (_chapterText != null)
            _chapterText.text = $"Chapter {data.Chapter}";
    }

    private void HandleMainQuestUpdated(MainQuestDataInfo data)
    {
        if (_questNameText != null)
            _questNameText.text = data.Name ?? "Unknown Quest";

        if (_questDescText != null)
            _questDescText.text = data.Description ?? "";

        // 목표 리스트 갱신
        if (_objectivesText != null && data.Objectives != null)
        {
            var sb = new System.Text.StringBuilder();
            for (int i = 0; i < data.Objectives.Length; i++)
            {
                var obj = data.Objectives[i];
                string typeName = GetObjectiveTypeName(obj.Type);
                bool completed = obj.Current >= obj.Required;
                string mark = completed ? "<color=#00FF00>[V]</color>" : "[ ]";
                sb.AppendLine($"  {mark} {typeName}: {obj.Current}/{obj.Required}");
            }
            _objectivesText.text = sb.ToString();
        }
    }

    private void ShowProgressPanel()
    {
        if (_progressPanel != null)
            _progressPanel.SetActive(true);
    }

    private void HideProgressPanel()
    {
        if (_progressPanel != null)
            _progressPanel.SetActive(false);
    }

    // ━━━ 유틸 ━━━

    private static string GetObjectiveTypeName(MainQuestObjectiveType type)
    {
        switch (type)
        {
            case MainQuestObjectiveType.KILL:    return "Kill";
            case MainQuestObjectiveType.COLLECT: return "Collect";
            case MainQuestObjectiveType.TALK:    return "Talk";
            case MainQuestObjectiveType.EXPLORE: return "Explore";
            case MainQuestObjectiveType.DUNGEON: return "Dungeon";
            default: return $"Type{(byte)type}";
        }
    }

    // ━━━ UI 생성 헬퍼 ━━━

    private static GameObject CreateRect(string name, Transform parent,
        Vector2 anchoredPos, Vector2 sizeDelta,
        Vector2 anchorMin, Vector2 anchorMax, Vector2 pivot)
    {
        var go = new GameObject(name);
        go.transform.SetParent(parent, false);
        var rt = go.AddComponent<RectTransform>();
        rt.anchorMin = anchorMin;
        rt.anchorMax = anchorMax;
        rt.pivot = pivot;
        rt.anchoredPosition = anchoredPos;
        rt.sizeDelta = sizeDelta;
        return go;
    }
}
