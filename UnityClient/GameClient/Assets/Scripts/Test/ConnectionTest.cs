// ━━━ ConnectionTest.cs ━━━
// Phase 2 TCP 브릿지 연동 테스트
// Gate 경유 / DirectConnect 모드 지원

using UnityEngine;
using Network;

public class ConnectionTest : MonoBehaviour
{
    public enum ConnectionMode { Gate, DirectConnect }

    [Header("Connection")]
    [SerializeField] private ConnectionMode mode = ConnectionMode.DirectConnect;
    [SerializeField] private string directHost = "127.0.0.1";
    [SerializeField] private int directPort = 7777;

    [Header("Auto Test")]
    [SerializeField] private bool autoChatTest = true;
    [SerializeField] private float chatDelay = 2f;

    private bool _chatSent;

    void Start()
    {
        var net = NetworkManager.Instance;

        // ━━━ 기존 이벤트 ━━━
        net.OnLoginResult += (result, accountId) => {
            Debug.Log($"[Test] LOGIN_RESULT: result={result}, accountId={accountId}");
            if (result == LoginResult.Success)
                net.SelectCharacter(1);
        };

        net.OnEnterGame += (result) => {
            if (result.ResultCode == 0)
            {
                Debug.Log($"[Test] ENTER_GAME OK! entity={result.EntityId}, zone={result.ZoneId}, pos=({result.X},{result.Y},{result.Z})");
                net.JoinChannel(1);
            }
            else
            {
                Debug.LogError($"[Test] ENTER_GAME FAILED: code={result.ResultCode}");
            }
        };

        net.OnEntityAppear += (eid, x, y, z) =>
            Debug.Log($"[Test] APPEAR: entity={eid} at ({x},{y},{z})");

        net.OnEntityMove += (eid, x, y, z) =>
            Debug.Log($"[Test] MOVE: entity={eid} -> ({x},{y},{z})");

        net.OnEntityDisappear += (eid) =>
            Debug.Log($"[Test] DISAPPEAR: entity={eid}");

        // ━━━ Phase 2 추가 이벤트 ━━━
        net.OnMonsterSpawn += (data) =>
            Debug.Log($"[Test] MONSTER_SPAWN: entity={data.EntityId}, monsterId={data.MonsterId}, lv={data.Level}, hp={data.HP}/{data.MaxHP}");

        net.OnStatSync += (data) =>
            Debug.Log($"[Test] STAT_SYNC: hp={data.HP}/{data.MaxHP}, mp={data.MP}/{data.MaxMP}, lv={data.Level}, atk={data.ATK}, def={data.DEF}");

        net.OnChatMessage += (data) =>
            Debug.Log($"[Test] CHAT_MSG: ch={data.Channel}, sender={data.SenderName}, msg={data.Message}");

        net.OnSystemMessage += (msg) =>
            Debug.Log($"[Test] SYSTEM_MSG: {msg}");

        net.OnError += (msg) =>
            Debug.LogError($"[Test] NET ERROR: {msg}");

        net.OnDisconnected += () =>
            Debug.LogWarning("[Test] DISCONNECTED");

        // ━━━ 접속 시작 ━━━
        if (mode == ConnectionMode.DirectConnect)
        {
            Debug.Log($"[Test] DirectConnect to {directHost}:{directPort}");
            net.ConnectDirect(directHost, directPort);
            Invoke(nameof(DoLogin), 0.5f);
        }
        else
        {
            Debug.Log("[Test] Connecting to Gate...");
            net.ConnectToGate();
            Invoke(nameof(DoLogin), 1.0f);
        }
    }

    void DoLogin()
    {
        Debug.Log("[Test] Logging in...");
        NetworkManager.Instance.Login("hero", "pass123");
    }

    void Update()
    {
        if (NetworkManager.Instance == null ||
            NetworkManager.Instance.State != NetworkManager.ConnectionState.InGame)
            return;

        // 자동 채팅 테스트 (입장 후 chatDelay초)
        if (autoChatTest && !_chatSent)
        {
            _chatSent = true;
            Invoke(nameof(SendTestChat), chatDelay);
        }

        // Space: 랜덤 이동
        if (Input.GetKeyDown(KeyCode.Space))
        {
            float x = Random.Range(50f, 950f);
            float y = Random.Range(50f, 950f);
            NetworkManager.Instance.SendMove(x, y, 0);
            Debug.Log($"[Test] Sent MOVE: ({x},{y})");
        }

        // T: 수동 채팅
        if (Input.GetKeyDown(KeyCode.T))
        {
            SendTestChat();
        }
    }

    void SendTestChat()
    {
        Debug.Log("[Test] Sending CHAT...");
        NetworkManager.Instance.SendChat(ChatChannel.GENERAL, "Hello from Unity!");
    }
}
