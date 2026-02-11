// ━━━ DeathUI.cs ━━━
// 사망 시 풀스크린 반투명 패널 + "부활" 버튼
// CombatManager.OnEntityDied / OnRespawnComplete 구독

using UnityEngine;
using UnityEngine.UI;
using Network;

public class DeathUI : MonoBehaviour
{
    [Header("Death Panel")]
    [SerializeField] private GameObject deathPanel;
    [SerializeField] private Button respawnButton;

    public static DeathUI Instance { get; private set; }

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
        if (CombatManager.Instance != null)
        {
            CombatManager.Instance.OnEntityDied += HandleEntityDied;
            CombatManager.Instance.OnRespawnComplete += HandleRespawnComplete;
        }

        if (respawnButton != null)
            respawnButton.onClick.AddListener(OnRespawnClicked);

        if (deathPanel != null)
            deathPanel.SetActive(false);
    }

    private void OnDestroy()
    {
        if (CombatManager.Instance != null)
        {
            CombatManager.Instance.OnEntityDied -= HandleEntityDied;
            CombatManager.Instance.OnRespawnComplete -= HandleRespawnComplete;
        }

        if (respawnButton != null)
            respawnButton.onClick.RemoveListener(OnRespawnClicked);

        if (Instance == this) Instance = null;
    }

    private void HandleEntityDied(CombatDiedData data)
    {
        // 내가 죽었을 때만 패널 표시
        if (data.DeadEntityId != NetworkManager.Instance.MyEntityId) return;

        if (deathPanel != null)
            deathPanel.SetActive(true);
    }

    private void HandleRespawnComplete(RespawnResultData data)
    {
        if (data.ResultCode != 0) return;

        if (deathPanel != null)
            deathPanel.SetActive(false);
    }

    private void OnRespawnClicked()
    {
        if (CombatManager.Instance != null)
            CombatManager.Instance.Respawn();
    }
}
