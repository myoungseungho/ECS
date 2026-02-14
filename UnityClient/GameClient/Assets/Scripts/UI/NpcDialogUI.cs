// ━━━ NpcDialogUI.cs ━━━
// NPC 대화 패널 UI — NpcManager.OnDialogOpened 구독
// F키로 열기, ESC로 닫기

using UnityEngine;
using UnityEngine.UI;
using Network;

public class NpcDialogUI : MonoBehaviour
{
    [SerializeField] private GameObject dialogPanel;
    [SerializeField] private Text npcNameText;
    [SerializeField] private Text dialogText;
    [SerializeField] private Text npcTypeText;
    [SerializeField] private Transform questListParent;
    [SerializeField] private GameObject questButtonTemplate;

    private void Start()
    {
        if (NpcManager.Instance != null)
        {
            NpcManager.Instance.OnDialogOpened += HandleDialogOpened;
            NpcManager.Instance.OnDialogClosed += HandleDialogClosed;
        }

        if (dialogPanel != null)
            dialogPanel.SetActive(false);
    }

    private void OnDestroy()
    {
        if (NpcManager.Instance != null)
        {
            NpcManager.Instance.OnDialogOpened -= HandleDialogOpened;
            NpcManager.Instance.OnDialogClosed -= HandleDialogClosed;
        }
    }

    private void Update()
    {
        if (dialogPanel != null && dialogPanel.activeSelf && Input.GetKeyDown(KeyCode.Escape))
        {
            if (NpcManager.Instance != null)
                NpcManager.Instance.CloseDialog();
        }
    }

    private void HandleDialogOpened(NpcDialogData data)
    {
        if (dialogPanel != null)
            dialogPanel.SetActive(true);

        if (npcNameText != null)
            npcNameText.text = $"NPC #{data.NpcId}";

        if (npcTypeText != null)
        {
            string typeName = data.Type switch
            {
                NpcType.QUEST => "\ud018\uc2a4\ud2b8",
                NpcType.SHOP => "\uc0c1\uc810",
                NpcType.BLACKSMITH => "\ub300\uc7a5\uc7a5\uc774",
                NpcType.SKILL => "\uc2a4\ud0ac \ud2b8\ub808\uc774\ub108",
                _ => "\ubbf8\uc815"
            };
            npcTypeText.text = typeName;
        }

        if (dialogText != null && data.Lines != null && data.Lines.Length > 0)
        {
            var sb = new System.Text.StringBuilder();
            foreach (var line in data.Lines)
            {
                sb.AppendLine($"<b>{line.Speaker}</b>: {line.Text}");
            }
            dialogText.text = sb.ToString();
        }

        // 퀘스트 버튼 목록
        if (questListParent != null && questButtonTemplate != null)
        {
            // 기존 퀘스트 버튼 제거
            for (int i = questListParent.childCount - 1; i >= 0; i--)
            {
                var child = questListParent.GetChild(i).gameObject;
                if (child != questButtonTemplate)
                    Destroy(child);
            }

            foreach (uint questId in data.QuestIds)
            {
                var btnGo = Instantiate(questButtonTemplate, questListParent);
                btnGo.SetActive(true);
                var btnText = btnGo.GetComponentInChildren<Text>();
                if (btnText != null)
                    btnText.text = $"\ud018\uc2a4\ud2b8 #{questId}";

                var btn = btnGo.GetComponent<Button>();
                if (btn != null)
                {
                    uint qid = questId;
                    btn.onClick.AddListener(() => OnQuestButtonClicked(qid));
                }
            }
        }
    }

    private void HandleDialogClosed()
    {
        if (dialogPanel != null)
            dialogPanel.SetActive(false);
    }

    private void OnQuestButtonClicked(uint questId)
    {
        if (QuestManager.Instance != null)
        {
            QuestManager.Instance.AcceptQuest(questId);
        }
    }
}
