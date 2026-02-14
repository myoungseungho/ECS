// ━━━ StoryManager.cs ━━━
// 스토리/메인퀘 대화 시스템 관리 — 대화 선택지, 컷씬, 챕터 진행, 메인퀘 데이터
// NetworkManager 이벤트 구독 → StoryUI에 이벤트 발행

using System;
using UnityEngine;
using Network;

public class StoryManager : MonoBehaviour
{
    // ━━━ 상태 ━━━
    private StoryProgressData _progress;
    private MainQuestDataInfo _currentQuest;
    private bool _isInCutscene;
    private ushort _currentCutsceneId;
    private bool _isDialogOpen;
    private DialogChoiceResultData _currentDialog;

    // ━━━ 프로퍼티 ━━━
    public StoryProgressData Progress => _progress;
    public MainQuestDataInfo CurrentQuest => _currentQuest;
    public bool IsInCutscene => _isInCutscene;
    public ushort CurrentCutsceneId => _currentCutsceneId;
    public bool IsDialogOpen => _isDialogOpen;
    public DialogChoiceResultData CurrentDialog => _currentDialog;
    public byte Chapter => _progress != null ? _progress.Chapter : (byte)0;

    // ━━━ 이벤트 ━━━
    public event Action<StoryProgressData> OnProgressUpdated;
    public event Action<MainQuestDataInfo> OnMainQuestLoaded;
    public event Action<DialogChoiceResultData> OnDialogReceived;
    public event Action OnDialogClosed;
    public event Action<CutsceneTriggerData> OnCutsceneStarted;
    public event Action<ushort> OnCutsceneEnded;

    // ━━━ 싱글톤 (Scene-bound) ━━━
    public static StoryManager Instance { get; private set; }

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
        net.OnStoryProgress += HandleStoryProgress;
        net.OnMainQuestData += HandleMainQuestData;
        net.OnDialogChoiceResult += HandleDialogChoice;
        net.OnCutsceneTrigger += HandleCutsceneTrigger;
        net.OnCutsceneEnd += HandleCutsceneEnd;
    }

    private void OnDestroy()
    {
        var net = NetworkManager.Instance;
        if (net == null) return;

        net.OnStoryProgress -= HandleStoryProgress;
        net.OnMainQuestData -= HandleMainQuestData;
        net.OnDialogChoiceResult -= HandleDialogChoice;
        net.OnCutsceneTrigger -= HandleCutsceneTrigger;
        net.OnCutsceneEnd -= HandleCutsceneEnd;

        if (Instance == this) Instance = null;
    }

    // ━━━ 공개 API ━━━

    public void SelectChoice(ushort npcId, byte choiceIndex)
    {
        NetworkManager.Instance.SelectDialogChoice(npcId, choiceIndex);
    }

    public void SkipCutscene()
    {
        if (!_isInCutscene) return;
        NetworkManager.Instance.SkipCutscene(_currentCutsceneId);
    }

    public void RefreshProgress()
    {
        NetworkManager.Instance.RequestStoryProgress();
    }

    public void CloseDialog()
    {
        _isDialogOpen = false;
        _currentDialog = null;
        OnDialogClosed?.Invoke();
    }

    // ━━━ 핸들러 ━━━

    private void HandleStoryProgress(StoryProgressData data)
    {
        _progress = data;
        Debug.Log($"[StoryManager] Progress: chapter={data.Chapter}, quest={data.QuestId}, state={data.QuestState}");
        OnProgressUpdated?.Invoke(data);
    }

    private void HandleMainQuestData(MainQuestDataInfo data)
    {
        _currentQuest = data;
        Debug.Log($"[StoryManager] MainQuest: id={data.QuestId}, name={data.Name}, objectives={data.Objectives.Length}");
        OnMainQuestLoaded?.Invoke(data);
    }

    private void HandleDialogChoice(DialogChoiceResultData data)
    {
        _currentDialog = data;
        _isDialogOpen = true;
        Debug.Log($"[StoryManager] Dialog: npc={data.NpcId}, lines={data.Lines.Length}, choices={data.Choices.Length}");
        OnDialogReceived?.Invoke(data);
    }

    private void HandleCutsceneTrigger(CutsceneTriggerData data)
    {
        _isInCutscene = true;
        _currentCutsceneId = data.CutsceneId;
        Debug.Log($"[StoryManager] Cutscene: id={data.CutsceneId}, duration={data.DurationSeconds}s");
        OnCutsceneStarted?.Invoke(data);
    }

    private void HandleCutsceneEnd(ushort cutsceneId)
    {
        _isInCutscene = false;
        _currentCutsceneId = 0;
        Debug.Log($"[StoryManager] CutsceneEnd: id={cutsceneId}");
        OnCutsceneEnded?.Invoke(cutsceneId);
    }
}
