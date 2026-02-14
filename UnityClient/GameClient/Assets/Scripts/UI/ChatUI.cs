// ━━━ ChatUI.cs ━━━
// 채팅 UI — Enter키로 입력 토글, 채널 전환, 메시지 스크롤 표시
// ChatManager 이벤트 구독

using UnityEngine;
using UnityEngine.UI;
using Network;

public class ChatUI : MonoBehaviour
{
    [Header("UI References")]
    [SerializeField] private Text messageArea;
    [SerializeField] private InputField inputField;
    [SerializeField] private Text channelLabel;

    [Header("Settings")]
    [SerializeField] private int maxDisplayLines = 12;

    private ChatChannel _currentChannel = ChatChannel.GENERAL;
    private bool _isInputActive;

    private void Start()
    {
        if (ChatManager.Instance != null)
            ChatManager.Instance.OnNewMessage += HandleNewMessage;

        if (inputField != null)
        {
            inputField.gameObject.SetActive(false);
            inputField.onEndEdit.AddListener(OnInputSubmit);
        }

        UpdateChannelLabel();
        RefreshDisplay();
    }

    private void OnDestroy()
    {
        if (ChatManager.Instance != null)
            ChatManager.Instance.OnNewMessage -= HandleNewMessage;
    }

    private void Update()
    {
        // Enter키로 입력 토글
        if (Input.GetKeyDown(KeyCode.Return))
        {
            if (!_isInputActive)
            {
                _isInputActive = true;
                if (inputField != null)
                {
                    inputField.gameObject.SetActive(true);
                    inputField.ActivateInputField();
                }
            }
        }

        // Tab키로 채널 전환 (입력 활성 시)
        if (_isInputActive && Input.GetKeyDown(KeyCode.Tab))
        {
            CycleChannel();
        }
    }

    private void OnInputSubmit(string text)
    {
        _isInputActive = false;
        if (inputField != null)
        {
            inputField.text = "";
            inputField.gameObject.SetActive(false);
        }

        if (string.IsNullOrEmpty(text)) return;

        var chatMgr = ChatManager.Instance;
        if (chatMgr == null) return;

        // /w 대상이름 메시지 형태의 귓속말
        if (text.StartsWith("/w "))
        {
            string rest = text.Substring(3);
            int spaceIdx = rest.IndexOf(' ');
            if (spaceIdx > 0)
            {
                string target = rest.Substring(0, spaceIdx);
                string msg = rest.Substring(spaceIdx + 1);
                chatMgr.SendWhisper(target, msg);
            }
            return;
        }

        switch (_currentChannel)
        {
            case ChatChannel.GENERAL:
                chatMgr.SendZoneChat(text);
                break;
            case ChatChannel.PARTY:
                chatMgr.SendPartyChat(text);
                break;
        }
    }

    private void CycleChannel()
    {
        _currentChannel = _currentChannel == ChatChannel.GENERAL
            ? ChatChannel.PARTY
            : ChatChannel.GENERAL;
        UpdateChannelLabel();
    }

    private void UpdateChannelLabel()
    {
        if (channelLabel == null) return;
        channelLabel.text = _currentChannel == ChatChannel.GENERAL ? "[Zone]" : "[Party]";
    }

    private void HandleNewMessage(ChatManager.ChatEntry entry)
    {
        RefreshDisplay();
    }

    private void RefreshDisplay()
    {
        if (messageArea == null) return;

        var chatMgr = ChatManager.Instance;
        if (chatMgr == null) return;

        var messages = chatMgr.Messages;
        int start = Mathf.Max(0, messages.Count - maxDisplayLines);
        var sb = new System.Text.StringBuilder();

        for (int i = start; i < messages.Count; i++)
        {
            var msg = messages[i];
            string prefix = msg.Channel switch
            {
                ChatChannel.GENERAL => "[Zone]",
                ChatChannel.PARTY   => "[Party]",
                ChatChannel.WHISPER => "[Whisper]",
                ChatChannel.SYSTEM  => "[System]",
                _ => ""
            };

            string color = msg.Channel switch
            {
                ChatChannel.GENERAL => "white",
                ChatChannel.PARTY   => "cyan",
                ChatChannel.WHISPER => "magenta",
                ChatChannel.SYSTEM  => "yellow",
                _ => "white"
            };

            sb.AppendLine($"<color={color}>{prefix} {msg.SenderName}: {msg.Message}</color>");
        }

        messageArea.text = sb.ToString();
    }
}
