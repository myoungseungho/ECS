// ━━━ GameBootstrap.cs ━━━
// GameScene Play 시 자동 접속 플로우
// ConnectDirect → Login → SelectCharacter → JoinChannel
// 싱글톤 아님 — 씬 유틸리티 컴포넌트

using UnityEngine;
using Network;

public class GameBootstrap : MonoBehaviour
{
    [Header("Auto Connect")]
    [SerializeField] private bool autoConnect = true;
    [SerializeField] private string host = "127.0.0.1";
    [SerializeField] private int port = 7777;

    [Header("Login")]
    [SerializeField] private string username = "hero";
    [SerializeField] private string password = "pass123";

    [Header("Character / Channel")]
    [SerializeField] private uint characterId = 1;
    [SerializeField] private int channelId = 1;

    private void Start()
    {
        if (!autoConnect) return;

        var net = NetworkManager.Instance;
        if (net == null)
        {
            Debug.LogError("[Bootstrap] NetworkManager not found!");
            return;
        }

        net.OnLoginResult += HandleLoginResult;
        net.OnEnterGame += HandleEnterGame;
        net.OnError += HandleError;
        net.OnDisconnected += HandleDisconnected;

        Debug.Log($"[Bootstrap] ConnectDirect to {host}:{port}");
        net.ConnectDirect(host, port);
        Invoke(nameof(DoLogin), 0.5f);
    }

    private void DoLogin()
    {
        Debug.Log($"[Bootstrap] Login as {username}");
        NetworkManager.Instance.Login(username, password);
    }

    private void HandleLoginResult(LoginResult result, uint accountId)
    {
        if (result == LoginResult.Success)
        {
            Debug.Log($"[Bootstrap] Login OK (accountId={accountId}), selecting character {characterId}");
            NetworkManager.Instance.SelectCharacter(characterId);
        }
        else
        {
            Debug.LogError($"[Bootstrap] Login FAILED: {result}");
        }
    }

    private void HandleEnterGame(EnterGameResult result)
    {
        if (result.ResultCode == 0)
        {
            Debug.Log($"[Bootstrap] EnterGame OK (entity={result.EntityId}, zone={result.ZoneId}), joining channel {channelId}");
            NetworkManager.Instance.JoinChannel(channelId);
            Debug.Log("[Bootstrap] Bootstrap complete — game is ready!");
        }
        else
        {
            Debug.LogError($"[Bootstrap] EnterGame FAILED: code={result.ResultCode}");
        }
    }

    private void HandleError(string msg)
    {
        Debug.LogError($"[Bootstrap] Network error: {msg}");
    }

    private void HandleDisconnected()
    {
        Debug.LogWarning("[Bootstrap] Disconnected from server");
    }

    private void OnDestroy()
    {
        var net = NetworkManager.Instance;
        if (net == null) return;

        net.OnLoginResult -= HandleLoginResult;
        net.OnEnterGame -= HandleEnterGame;
        net.OnError -= HandleError;
        net.OnDisconnected -= HandleDisconnected;
    }
}
