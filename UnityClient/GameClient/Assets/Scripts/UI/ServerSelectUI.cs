// ━━━ ServerSelectUI.cs ━━━
// 서버 선택 UI — 서버 목록 표시 + 서버 선택
// S033: SERVER_LIST_REQ(320) → SERVER_LIST(321)

using UnityEngine;
using UnityEngine.UI;
using Network;

public class ServerSelectUI : MonoBehaviour
{
    [SerializeField] private GameObject serverPanel;
    [SerializeField] private Transform serverListParent;
    [SerializeField] private GameObject serverButtonTemplate;
    [SerializeField] private Text selectedServerText;

    private string _selectedServerName;

    private void Start()
    {
        if (NetworkManager.Instance != null)
        {
            NetworkManager.Instance.OnServerList += HandleServerList;
        }

        if (serverPanel != null)
            serverPanel.SetActive(false);
    }

    private void OnDestroy()
    {
        if (NetworkManager.Instance != null)
        {
            NetworkManager.Instance.OnServerList -= HandleServerList;
        }
    }

    /// <summary>서버 목록 요청 및 패널 표시</summary>
    public void Show()
    {
        if (serverPanel != null)
            serverPanel.SetActive(true);

        if (NetworkManager.Instance != null)
            NetworkManager.Instance.RequestServerList();
    }

    /// <summary>패널 숨기기</summary>
    public void Hide()
    {
        if (serverPanel != null)
            serverPanel.SetActive(false);
    }

    private void HandleServerList(ServerInfo[] servers)
    {
        if (serverListParent == null || serverButtonTemplate == null) return;

        // 기존 버튼 제거
        for (int i = serverListParent.childCount - 1; i >= 0; i--)
        {
            var child = serverListParent.GetChild(i).gameObject;
            if (child != serverButtonTemplate)
                Destroy(child);
        }

        foreach (var server in servers)
        {
            var btnGo = Instantiate(serverButtonTemplate, serverListParent);
            btnGo.SetActive(true);

            var btnText = btnGo.GetComponentInChildren<Text>();
            if (btnText != null)
            {
                string statusStr = server.Status switch
                {
                    ServerStatus.OFF => "[OFF]",
                    ServerStatus.NORMAL => "[NORMAL]",
                    ServerStatus.BUSY => "[BUSY]",
                    ServerStatus.FULL => "[FULL]",
                    _ => "[???]"
                };
                btnText.text = $"{server.Name} {statusStr} ({server.Population})";
            }

            var btn = btnGo.GetComponent<Button>();
            if (btn != null)
            {
                string name = server.Name;
                bool available = server.Status == ServerStatus.NORMAL || server.Status == ServerStatus.BUSY;
                btn.interactable = available;
                btn.onClick.AddListener(() => OnServerSelected(name));
            }
        }
    }

    private void OnServerSelected(string serverName)
    {
        _selectedServerName = serverName;
        if (selectedServerText != null)
            selectedServerText.text = $"\uc120\ud0dd: {serverName}";

        Debug.Log($"[ServerSelect] Selected: {serverName}");
    }
}
