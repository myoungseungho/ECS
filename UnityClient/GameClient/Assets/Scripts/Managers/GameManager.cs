using UnityEngine;
using Network;

public class GameManager : MonoBehaviour
{
    public enum GameState
    {
        Login,
        CharSelect,
        InGame,
    }

    public GameState CurrentState { get; private set; } = GameState.Login;

    public static GameManager Instance { get; private set; }

    private void Awake()
    {
        if (Instance != null && Instance != this)
        {
            Destroy(gameObject);
            return;
        }
        Instance = this;
        DontDestroyOnLoad(gameObject);
    }

    private void Start()
    {
        var net = NetworkManager.Instance;

        net.OnLoginResult += HandleLoginResult;
        net.OnEnterGame += HandleEnterGame;
        net.OnDisconnected += HandleDisconnected;
    }

    private void OnDestroy()
    {
        var net = NetworkManager.Instance;
        if (net == null) return;

        net.OnLoginResult -= HandleLoginResult;
        net.OnEnterGame -= HandleEnterGame;
        net.OnDisconnected -= HandleDisconnected;
    }

    private void HandleLoginResult(LoginResult result, uint accountId)
    {
        if (result == LoginResult.Success)
        {
            CurrentState = GameState.CharSelect;
            Debug.Log($"[GameManager] Login 성공, accountId={accountId}");
        }
    }

    private void HandleEnterGame(EnterGameResult result)
    {
        if (result.ResultCode == 0)
        {
            CurrentState = GameState.InGame;
            Debug.Log($"[GameManager] InGame 진입, entity={result.EntityId}, zone={result.ZoneId}");
        }
    }

    private void HandleDisconnected()
    {
        CurrentState = GameState.Login;
        Debug.Log("[GameManager] 서버 연결 끊김");
    }

    public void SetState(GameState state)
    {
        CurrentState = state;
    }
}
