// ━━━ MinimapUI.cs ━━━
// 미니맵 — 탑다운 오쏘그래픽 카메라 + RenderTexture + 원형 마스크
// ui.yaml hud.minimap 스펙: 우상단 (-20, -20), 200x200

using UnityEngine;
using UnityEngine.UI;

public class MinimapUI : MonoBehaviour
{
    [Header("UI References")]
    [SerializeField] private RawImage minimapImage;
    [SerializeField] private Text zoneNameText;
    [SerializeField] private Text coordText;
    [SerializeField] private Image playerArrow;

    [Header("Settings")]
    [SerializeField] private float cameraHeight = 50f;
    [SerializeField] private float orthoSize = 30f;
    [SerializeField] private int renderTextureSize = 256;

    public static MinimapUI Instance { get; private set; }

    private Camera _minimapCamera;
    private RenderTexture _renderTexture;

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
        SetupMinimapCamera();
    }

    private void OnDestroy()
    {
        if (_renderTexture != null)
        {
            _renderTexture.Release();
            Destroy(_renderTexture);
        }

        if (_minimapCamera != null)
            Destroy(_minimapCamera.gameObject);

        if (Instance == this) Instance = null;
    }

    private void LateUpdate()
    {
        UpdateCameraPosition();
        UpdateCoordDisplay();
    }

    private void SetupMinimapCamera()
    {
        // RenderTexture 생성
        _renderTexture = new RenderTexture(renderTextureSize, renderTextureSize, 16);
        _renderTexture.Create();

        // 미니맵 카메라 생성
        var camGo = new GameObject("MinimapCamera");
        camGo.transform.position = new Vector3(50f, cameraHeight, 50f);
        camGo.transform.rotation = Quaternion.Euler(90f, 0f, 0f);

        _minimapCamera = camGo.AddComponent<Camera>();
        _minimapCamera.orthographic = true;
        _minimapCamera.orthographicSize = orthoSize;
        _minimapCamera.targetTexture = _renderTexture;
        _minimapCamera.clearFlags = CameraClearFlags.SolidColor;
        _minimapCamera.backgroundColor = new Color(0.1f, 0.15f, 0.1f, 1f);
        _minimapCamera.depth = -10; // 메인 카메라보다 낮은 우선순위
        _minimapCamera.cullingMask = ~(1 << 5); // UI 레이어 제외

        // RawImage에 연결
        if (minimapImage != null)
            minimapImage.texture = _renderTexture;
    }

    private void UpdateCameraPosition()
    {
        if (_minimapCamera == null) return;

        // 로컬 플레이어 추적
        var localPlayer = FindLocalPlayer();
        if (localPlayer != null)
        {
            var pos = localPlayer.position;
            _minimapCamera.transform.position = new Vector3(pos.x, cameraHeight, pos.z);
        }
    }

    private void UpdateCoordDisplay()
    {
        var localPlayer = FindLocalPlayer();
        if (localPlayer == null) return;

        if (coordText != null)
        {
            var pos = localPlayer.position;
            coordText.text = $"({pos.x:F0}, {pos.z:F0})";
        }

        if (zoneNameText != null && Network.NetworkManager.Instance != null)
        {
            zoneNameText.text = $"Zone {Network.NetworkManager.Instance.CurrentZone}";
        }
    }

    private Transform FindLocalPlayer()
    {
        if (EntityManager.Instance == null) return null;

        // EntityManager에서 로컬 플레이어 참조
        var lp = EntityManager.Instance.LocalPlayer;
        return lp != null ? lp.transform : null;
    }
}
