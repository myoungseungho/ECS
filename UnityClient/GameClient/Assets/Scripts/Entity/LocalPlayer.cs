using UnityEngine;
using Network;

public class LocalPlayer : MonoBehaviour
{
    [Header("Movement")]
    [SerializeField] private float moveSpeed = 5f;
    [SerializeField] private float sendInterval = 0.1f; // 서버 전송 간격 (초)

    [Header("Camera")]
    [SerializeField] private Vector3 cameraOffset = new Vector3(0f, 15f, -10f);
    [SerializeField] private float cameraSmoothSpeed = 5f;

    public ulong EntityId { get; set; }

    private Camera _mainCamera;
    private float _lastSendTime;
    private float _clientStartTime;

    private void Start()
    {
        _mainCamera = Camera.main;
        _clientStartTime = Time.realtimeSinceStartup;

        var net = NetworkManager.Instance;
        if (net != null)
            net.OnPositionCorrection += HandlePositionCorrection;
    }

    private void OnDestroy()
    {
        var net = NetworkManager.Instance;
        if (net != null)
            net.OnPositionCorrection -= HandlePositionCorrection;
    }

    private void Update()
    {
        if (NetworkManager.Instance == null ||
            NetworkManager.Instance.State != NetworkManager.ConnectionState.InGame)
            return;

        HandleMovement();
        UpdateCamera();
    }

    private void HandleMovement()
    {
        float h = Input.GetAxis("Horizontal"); // A/D
        float v = Input.GetAxis("Vertical");   // W/S

        if (Mathf.Abs(h) < 0.01f && Mathf.Abs(v) < 0.01f)
            return;

        Vector3 dir = new Vector3(h, 0f, v).normalized;
        transform.position += dir * moveSpeed * Time.deltaTime;

        // 이동 방향으로 회전
        if (dir.magnitude > 0.01f)
            transform.rotation = Quaternion.LookRotation(dir);

        // 서버에 위치 전송 (throttle, Model C: +timestamp)
        if (Time.time - _lastSendTime >= sendInterval)
        {
            _lastSendTime = Time.time;
            var (sx, sy) = CoordConverter.UnityToServer(transform.position);
            uint timestampMs = (uint)((Time.realtimeSinceStartup - _clientStartTime) * 1000f);
            NetworkManager.Instance.SendMove(sx, sy, 0f, timestampMs);
        }
    }

    /// <summary>서버 위치 보정 — 즉시 텔레포트 (Lerp 아님)</summary>
    private void HandlePositionCorrection(float x, float y, float z)
    {
        Vector3 corrected = CoordConverter.ServerToUnity(x, y);
        transform.position = corrected;
        Debug.Log($"[LocalPlayer] Position corrected to ({x},{y},{z})");
    }

    private void UpdateCamera()
    {
        if (_mainCamera == null) return;

        Vector3 targetPos = transform.position + cameraOffset;
        _mainCamera.transform.position = Vector3.Lerp(
            _mainCamera.transform.position, targetPos, Time.deltaTime * cameraSmoothSpeed);
        _mainCamera.transform.LookAt(transform.position);
    }
}
