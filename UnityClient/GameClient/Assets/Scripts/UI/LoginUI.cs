// ━━━ LoginUI.cs ━━━
// P0_S02_C01: 로그인 화면 UI
// 서버 접속 → ID/PW 입력 → LOGIN 패킷 → 결과 처리 → ServerSelect 씬 전환
// 싱글톤 아님 — LoginScene 전용 UI 컴포넌트

using UnityEngine;
using UnityEngine.UI;
using Network;

public class LoginUI : MonoBehaviour
{
    [Header("UI References")]
    [SerializeField] private InputField usernameInput;
    [SerializeField] private InputField passwordInput;
    [SerializeField] private Button loginButton;
    [SerializeField] private Button registerButton;
    [SerializeField] private Text errorText;
    [SerializeField] private Text statusText;
    [SerializeField] private GameObject loginPanel;

    [Header("Server Settings")]
    [SerializeField] private string host = "127.0.0.1";
    [SerializeField] private int port = 7777;

    private bool _isConnecting;
    private bool _isLoggingIn;

    private void Start()
    {
        if (errorText != null)
        {
            errorText.text = "";
            errorText.gameObject.SetActive(false);
        }

        if (statusText != null)
            statusText.text = "";

        if (loginButton != null)
            loginButton.onClick.AddListener(OnLoginClicked);

        if (registerButton != null)
            registerButton.interactable = false;

        if (loginPanel != null)
            loginPanel.SetActive(true);

        // 이벤트 구독
        var net = NetworkManager.Instance;
        if (net != null)
        {
            net.OnLoginResult += HandleLoginResult;
            net.OnError += HandleError;
            net.OnDisconnected += HandleDisconnected;
        }

        // 자동 서버 접속 시작
        ConnectToServer();
    }

    private void OnDestroy()
    {
        if (loginButton != null)
            loginButton.onClick.RemoveListener(OnLoginClicked);

        var net = NetworkManager.Instance;
        if (net == null) return;

        net.OnLoginResult -= HandleLoginResult;
        net.OnError -= HandleError;
        net.OnDisconnected -= HandleDisconnected;
    }

    private void Update()
    {
        // Enter키로 로그인
        if (Input.GetKeyDown(KeyCode.Return) && !_isLoggingIn)
            OnLoginClicked();

        // Tab키로 포커스 전환
        if (Input.GetKeyDown(KeyCode.Tab))
        {
            if (usernameInput != null && usernameInput.isFocused)
            {
                if (passwordInput != null)
                    passwordInput.ActivateInputField();
            }
            else if (passwordInput != null && !passwordInput.isFocused)
            {
                if (usernameInput != null)
                    usernameInput.ActivateInputField();
            }
        }
    }

    private void ConnectToServer()
    {
        var net = NetworkManager.Instance;
        if (net == null)
        {
            ShowError("NetworkManager를 찾을 수 없습니다");
            return;
        }

        if (net.State != NetworkManager.ConnectionState.Disconnected)
            return;

        _isConnecting = true;
        SetStatus("서버 접속 중...");
        SetLoginInteractable(false);

        net.ConnectDirect(host, port);

        // 접속 결과 확인 (ConnectDirect는 즉시 반환)
        Invoke(nameof(CheckConnection), 0.5f);
    }

    private void CheckConnection()
    {
        _isConnecting = false;
        var net = NetworkManager.Instance;
        if (net == null) return;

        if (net.State == NetworkManager.ConnectionState.Disconnected)
        {
            ShowError("서버에 연결할 수 없습니다");
            SetStatus("오프라인");
            SetLoginInteractable(false);
        }
        else
        {
            HideError();
            SetStatus("서버 접속 완료");
            SetLoginInteractable(true);

            // 포커스를 ID 입력란에
            if (usernameInput != null)
                usernameInput.ActivateInputField();
        }
    }

    private void OnLoginClicked()
    {
        var net = NetworkManager.Instance;
        if (net == null) return;

        // 연결 안 됐으면 재접속 시도
        if (net.State == NetworkManager.ConnectionState.Disconnected)
        {
            ConnectToServer();
            return;
        }

        string username = usernameInput != null ? usernameInput.text.Trim() : "";
        string password = passwordInput != null ? passwordInput.text : "";

        if (string.IsNullOrEmpty(username))
        {
            ShowError("아이디를 입력하세요");
            return;
        }

        if (string.IsNullOrEmpty(password))
        {
            ShowError("비밀번호를 입력하세요");
            return;
        }

        _isLoggingIn = true;
        HideError();
        SetStatus("로그인 중...");
        SetLoginInteractable(false);

        net.Login(username, password);
    }

    private void HandleLoginResult(LoginResult result, uint accountId)
    {
        _isLoggingIn = false;

        switch (result)
        {
            case LoginResult.Success:
                SetStatus("로그인 성공!");
                Debug.Log($"[LoginUI] Login success, accountId={accountId}");

                // SceneFlowManager로 다음 씬 전환 (Login → ServerSelect)
                if (SceneFlowManager.Instance != null)
                    SceneFlowManager.Instance.TransitionToNext();
                break;

            case LoginResult.AccountNotFound:
                ShowError("계정을 찾을 수 없습니다");
                SetLoginInteractable(true);
                break;

            case LoginResult.WrongPassword:
                ShowError("비밀번호가 틀렸습니다");
                SetLoginInteractable(true);
                if (passwordInput != null)
                {
                    passwordInput.text = "";
                    passwordInput.ActivateInputField();
                }
                break;

            case LoginResult.AlreadyOnline:
                ShowError("이미 접속 중인 계정입니다");
                SetLoginInteractable(true);
                break;

            default:
                ShowError("로그인 실패");
                SetLoginInteractable(true);
                break;
        }
    }

    private void HandleError(string msg)
    {
        _isLoggingIn = false;
        _isConnecting = false;
        ShowError(msg);
        SetLoginInteractable(false);
        SetStatus("오프라인");
    }

    private void HandleDisconnected()
    {
        _isLoggingIn = false;
        _isConnecting = false;
        ShowError("서버와의 연결이 끊어졌습니다");
        SetLoginInteractable(false);
        SetStatus("오프라인");
    }

    private void ShowError(string msg)
    {
        if (errorText == null) return;
        errorText.text = msg;
        errorText.gameObject.SetActive(true);
    }

    private void HideError()
    {
        if (errorText == null) return;
        errorText.text = "";
        errorText.gameObject.SetActive(false);
    }

    private void SetStatus(string msg)
    {
        if (statusText != null)
            statusText.text = msg;
    }

    private void SetLoginInteractable(bool interactable)
    {
        if (loginButton != null)
            loginButton.interactable = interactable;
    }
}
