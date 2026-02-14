// ━━━ ChatManager.cs ━━━
// 채팅 시스템 관리 — 존/파티/귓속말/시스템 메시지
// NetworkManager 이벤트 구독 → ChatUI에 메시지 이벤트 발행

using System;
using System.Collections.Generic;
using UnityEngine;
using Network;

public class ChatManager : MonoBehaviour
{
    // ━━━ 메시지 저장 ━━━
    public struct ChatEntry
    {
        public ChatChannel Channel;
        public string SenderName;
        public string Message;
        public float Timestamp;
    }

    private readonly List<ChatEntry> _messages = new List<ChatEntry>();
    public IReadOnlyList<ChatEntry> Messages => _messages;

    public const int MAX_MESSAGES = 200;

    // ━━━ 이벤트 ━━━
    public event Action<ChatEntry> OnNewMessage;

    // ━━━ 싱글톤 (Scene-bound) ━━━
    public static ChatManager Instance { get; private set; }

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
        net.OnChatMessage += HandleChatMessage;
        net.OnWhisperResult += HandleWhisperResult;
        net.OnSystemMessage += HandleSystemMessage;
    }

    private void OnDestroy()
    {
        var net = NetworkManager.Instance;
        if (net == null) return;

        net.OnChatMessage -= HandleChatMessage;
        net.OnWhisperResult -= HandleWhisperResult;
        net.OnSystemMessage -= HandleSystemMessage;

        if (Instance == this) Instance = null;
    }

    // ━━━ 공개 API ━━━

    /// <summary>존 채팅 전송</summary>
    public void SendZoneChat(string message)
    {
        if (string.IsNullOrEmpty(message)) return;
        NetworkManager.Instance.SendChat(ChatChannel.GENERAL, message);
    }

    /// <summary>파티 채팅 전송</summary>
    public void SendPartyChat(string message)
    {
        if (string.IsNullOrEmpty(message)) return;
        NetworkManager.Instance.SendChat(ChatChannel.PARTY, message);
    }

    /// <summary>귓속말 전송</summary>
    public void SendWhisper(string targetName, string message)
    {
        if (string.IsNullOrEmpty(targetName) || string.IsNullOrEmpty(message)) return;
        NetworkManager.Instance.SendWhisper(targetName, message);
    }

    // ━━━ 핸들러 ━━━

    private void HandleChatMessage(ChatMessageData data)
    {
        AddMessage(data.Channel, data.SenderName, data.Message);
    }

    private void HandleWhisperResult(WhisperResultData data)
    {
        if (data.Result == WhisperResult.SUCCESS)
        {
            string prefix = data.Direction == WhisperDirection.SENT ? "To" : "From";
            AddMessage(ChatChannel.WHISPER, $"[{prefix}] {data.OtherName}", data.Message);
        }
        else
        {
            string error = data.Result == WhisperResult.TARGET_NOT_FOUND
                ? "대상을 찾을 수 없습니다."
                : "대상이 오프라인입니다.";
            AddMessage(ChatChannel.SYSTEM, "System", error);
        }
    }

    private void HandleSystemMessage(string message)
    {
        AddMessage(ChatChannel.SYSTEM, "System", message);
    }

    private void AddMessage(ChatChannel channel, string sender, string message)
    {
        var entry = new ChatEntry
        {
            Channel = channel,
            SenderName = sender,
            Message = message,
            Timestamp = Time.time
        };

        _messages.Add(entry);
        if (_messages.Count > MAX_MESSAGES)
            _messages.RemoveAt(0);

        OnNewMessage?.Invoke(entry);
    }
}
