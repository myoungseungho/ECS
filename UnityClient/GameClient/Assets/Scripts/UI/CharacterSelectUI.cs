// ━━━ CharacterSelectUI.cs ━━━
// 캐릭터 선택/생성/삭제 UI
// S033: CHARACTER_LIST(323), CHARACTER_CREATE(324), CHARACTER_DELETE(326)

using UnityEngine;
using UnityEngine.UI;
using Network;

public class CharacterSelectUI : MonoBehaviour
{
    [SerializeField] private GameObject characterPanel;
    [SerializeField] private Transform characterListParent;
    [SerializeField] private GameObject characterSlotTemplate;
    [SerializeField] private Text statusText;

    // 캐릭터 생성 UI
    [SerializeField] private GameObject createPanel;
    [SerializeField] private InputField nameInputField;
    [SerializeField] private Text classSelectionText;

    private CharacterClass _selectedClass = CharacterClass.WARRIOR;

    private void Start()
    {
        if (NetworkManager.Instance != null)
        {
            NetworkManager.Instance.OnCharacterDataList += HandleCharacterList;
            NetworkManager.Instance.OnCharacterCreateResult += HandleCreateResult;
            NetworkManager.Instance.OnCharacterDeleteResult += HandleDeleteResult;
        }

        if (characterPanel != null)
            characterPanel.SetActive(false);
        if (createPanel != null)
            createPanel.SetActive(false);
    }

    private void OnDestroy()
    {
        if (NetworkManager.Instance != null)
        {
            NetworkManager.Instance.OnCharacterDataList -= HandleCharacterList;
            NetworkManager.Instance.OnCharacterCreateResult -= HandleCreateResult;
            NetworkManager.Instance.OnCharacterDeleteResult -= HandleDeleteResult;
        }
    }

    /// <summary>캐릭터 목록 요청 및 패널 표시</summary>
    public void Show()
    {
        if (characterPanel != null)
            characterPanel.SetActive(true);

        if (NetworkManager.Instance != null)
            NetworkManager.Instance.RequestCharacterList();
    }

    /// <summary>패널 숨기기</summary>
    public void Hide()
    {
        if (characterPanel != null)
            characterPanel.SetActive(false);
        if (createPanel != null)
            createPanel.SetActive(false);
    }

    /// <summary>캐릭터 생성 패널 토글</summary>
    public void ToggleCreatePanel()
    {
        if (createPanel != null)
            createPanel.SetActive(!createPanel.activeSelf);
    }

    /// <summary>직업 선택 (1=전사, 2=마법사, 3=궁수)</summary>
    public void SelectClass(int classId)
    {
        _selectedClass = (CharacterClass)classId;
        if (classSelectionText != null)
        {
            string className = _selectedClass switch
            {
                CharacterClass.WARRIOR => "\uc804\uc0ac",
                CharacterClass.MAGE => "\ub9c8\ubc95\uc0ac",
                CharacterClass.ARCHER => "\uad81\uc218",
                _ => "\ubbf8\uc815"
            };
            classSelectionText.text = className;
        }
    }

    /// <summary>캐릭터 생성 요청</summary>
    public void RequestCreate()
    {
        if (nameInputField == null || NetworkManager.Instance == null) return;

        string charName = nameInputField.text;
        if (string.IsNullOrEmpty(charName) || charName.Length < 2 || charName.Length > 8)
        {
            if (statusText != null)
                statusText.text = "\uc774\ub984\uc740 2~8\uc790 \uc785\ub2c8\ub2e4";
            return;
        }

        NetworkManager.Instance.CreateCharacter(charName, _selectedClass);
    }

    private void HandleCharacterList(CharacterData[] chars)
    {
        if (characterListParent == null || characterSlotTemplate == null) return;

        // 기존 슬롯 제거
        for (int i = characterListParent.childCount - 1; i >= 0; i--)
        {
            var child = characterListParent.GetChild(i).gameObject;
            if (child != characterSlotTemplate)
                Destroy(child);
        }

        foreach (var ch in chars)
        {
            var slotGo = Instantiate(characterSlotTemplate, characterListParent);
            slotGo.SetActive(true);

            var slotText = slotGo.GetComponentInChildren<Text>();
            if (slotText != null)
            {
                string className = ch.ClassType switch
                {
                    CharacterClass.WARRIOR => "\uc804\uc0ac",
                    CharacterClass.MAGE => "\ub9c8\ubc95\uc0ac",
                    CharacterClass.ARCHER => "\uad81\uc218",
                    _ => "???"
                };
                slotText.text = $"{ch.Name} Lv.{ch.Level} [{className}]";
            }
        }

        if (statusText != null)
            statusText.text = $"\uce90\ub9ad\ud130: {chars.Length}\uac1c";
    }

    private void HandleCreateResult(CharacterCreateResultData data)
    {
        if (statusText == null) return;

        string msg = data.Result switch
        {
            CharacterCreateResult.SUCCESS => $"\uce90\ub9ad\ud130 \uc0dd\uc131 \uc131\uacf5! (ID: {data.CharId})",
            CharacterCreateResult.NAME_EXISTS => "\uc774\ubbf8 \uc0ac\uc6a9 \uc911\uc778 \uc774\ub984\uc785\ub2c8\ub2e4",
            CharacterCreateResult.NAME_INVALID => "\uc720\ud6a8\ud558\uc9c0 \uc54a\uc740 \uc774\ub984\uc785\ub2c8\ub2e4",
            _ => "\uce90\ub9ad\ud130 \uc0dd\uc131 \uc2e4\ud328"
        };
        statusText.text = msg;

        if (data.Result == CharacterCreateResult.SUCCESS)
        {
            if (createPanel != null)
                createPanel.SetActive(false);

            // 목록 갱신
            if (NetworkManager.Instance != null)
                NetworkManager.Instance.RequestCharacterList();
        }
    }

    private void HandleDeleteResult(CharacterDeleteResultData data)
    {
        if (statusText == null) return;

        string msg = data.Result switch
        {
            CharacterDeleteResult.SUCCESS => $"\uce90\ub9ad\ud130 \uc0ad\uc81c \uc131\uacf5 (ID: {data.CharId})",
            CharacterDeleteResult.NOT_FOUND => "\uce90\ub9ad\ud130\ub97c \ucc3e\uc744 \uc218 \uc5c6\uc2b5\ub2c8\ub2e4",
            CharacterDeleteResult.NOT_LOGGED_IN => "\ub85c\uadf8\uc778\uc774 \ud544\uc694\ud569\ub2c8\ub2e4",
            _ => "\uce90\ub9ad\ud130 \uc0ad\uc81c \uc2e4\ud328"
        };
        statusText.text = msg;

        if (data.Result == CharacterDeleteResult.SUCCESS)
        {
            if (NetworkManager.Instance != null)
                NetworkManager.Instance.RequestCharacterList();
        }
    }
}
