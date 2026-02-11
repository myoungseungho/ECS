using UnityEngine;
using Network;

public class ConnectionTest : MonoBehaviour
{
    void Start()
    {
        var net = NetworkManager.Instance;

        net.OnLoginResult += (result, accountId) => {
            Debug.Log($"Login: {result}, accountId={accountId}");
            if (result == LoginResult.Success)
                net.SelectCharacter(1);  // Warrior_Kim
        };

        net.OnEnterGame += (result) => {
            if (result.ResultCode == 0)
            {
                Debug.Log($"IN GAME! entity={result.EntityId}, zone={result.ZoneId}, pos=({result.X},{result.Y},{result.Z})");
                net.JoinChannel(1);
            }
        };

        net.OnEntityAppear += (eid, x, y, z) => {
            Debug.Log($"APPEAR: entity={eid} at ({x},{y},{z})");
        };

        net.OnEntityMove += (eid, x, y, z) => {
            Debug.Log($"MOVE: entity={eid} -> ({x},{y},{z})");
        };

        net.OnEntityDisappear += (eid) => {
            Debug.Log($"DISAPPEAR: entity={eid}");
        };

        net.OnError += (msg) => Debug.LogError($"NET ERROR: {msg}");

        // 접속 시작
        Debug.Log("Connecting to Gate...");
        net.ConnectToGate();

        // Gate 응답 후 자동으로 Field 연결됨 -> 그때 Login 호출
        Invoke(nameof(DoLogin), 1.0f);
    }

    void DoLogin()
    {
        Debug.Log("Logging in...");
        NetworkManager.Instance.Login("hero", "pass123");
    }

    void Update()
    {
        // 스페이스바로 이동 테스트
        if (Input.GetKeyDown(KeyCode.Space) &&
            NetworkManager.Instance.State == NetworkManager.ConnectionState.InGame)
        {
            float x = Random.Range(50f, 950f);
            float y = Random.Range(50f, 950f);
            NetworkManager.Instance.SendMove(x, y, 0);
            Debug.Log($"Sent MOVE: ({x},{y})");
        }
    }
}
