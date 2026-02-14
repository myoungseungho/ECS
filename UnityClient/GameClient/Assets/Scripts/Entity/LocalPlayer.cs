using UnityEngine;
using Network;

public class LocalPlayer : MonoBehaviour
{
    [Header("Movement")]
    [SerializeField] private float moveSpeed = 5f;
    [SerializeField] private float sendInterval = 0.1f;
    [SerializeField] private float rotationSpeed = 10f;

    [Header("TPS Camera")]
    [SerializeField] private float shoulderOffsetX = 0.5f;
    [SerializeField] private float pivotHeight = 1.8f;
    [SerializeField] private float cameraDistance = 3f;
    [SerializeField] private float mouseSensitivity = 2f;
    [SerializeField] private float pitchMin = -30f;
    [SerializeField] private float pitchMax = 60f;
    [SerializeField] private float cameraCollisionRadius = 0.2f;

    [Header("Combat")]
    [SerializeField] private float attackCooldown = 1.0f;
    [SerializeField] private float attackRange = 15f;

    public ulong EntityId { get; set; }

    private Camera _mainCamera;
    private Animator _animator;
    private float _lastSendTime;
    private float _clientStartTime;

    // Camera
    private float _yaw;
    private float _pitch = 10f;
    private bool _cursorLocked = true;

    // Targeting
    private ulong _currentTarget;
    private GameObject _targetHighlight;
    private float _lastAttackTime;
    private int _tabIndex;

    private void Start()
    {
        _mainCamera = Camera.main;
        _animator = GetComponentInChildren<Animator>();
        _clientStartTime = Time.realtimeSinceStartup;

        _yaw = transform.eulerAngles.y;
        SetCursorLock(true);

        CreateTargetHighlight();

        var net = NetworkManager.Instance;
        if (net != null)
            net.OnPositionCorrection += HandlePositionCorrection;

        if (MonsterManager.Instance != null)
            MonsterManager.Instance.OnMonsterDied += HandleMonsterDied;
    }

    private void OnDestroy()
    {
        var net = NetworkManager.Instance;
        if (net != null)
            net.OnPositionCorrection -= HandlePositionCorrection;

        if (MonsterManager.Instance != null)
            MonsterManager.Instance.OnMonsterDied -= HandleMonsterDied;

        if (_targetHighlight != null)
            Destroy(_targetHighlight);
    }

    private void Update()
    {
        if (NetworkManager.Instance == null ||
            NetworkManager.Instance.State != NetworkManager.ConnectionState.InGame)
            return;

        HandleCursorToggle();
        HandleMouseLook();
        HandleMovement();
        HandleTargeting();
        HandleAttack();
        UpdateCamera();
        UpdateTargetHighlight();
    }

    // ━━━ Cursor Lock ━━━

    private void HandleCursorToggle()
    {
        if (Input.GetKeyDown(KeyCode.Escape))
            SetCursorLock(!_cursorLocked);
    }

    private void SetCursorLock(bool locked)
    {
        _cursorLocked = locked;
        Cursor.lockState = locked ? CursorLockMode.Locked : CursorLockMode.None;
        Cursor.visible = !locked;
    }

    // ━━━ Mouse Look ━━━

    private void HandleMouseLook()
    {
        if (!_cursorLocked) return;

        _yaw += Input.GetAxis("Mouse X") * mouseSensitivity;
        _pitch -= Input.GetAxis("Mouse Y") * mouseSensitivity;
        _pitch = Mathf.Clamp(_pitch, pitchMin, pitchMax);
    }

    // ━━━ Movement (Camera-relative WASD) ━━━

    private void HandleMovement()
    {
        float h = Input.GetAxis("Horizontal");
        float v = Input.GetAxis("Vertical");

        bool isMoving = Mathf.Abs(h) > 0.01f || Mathf.Abs(v) > 0.01f;
        _animator?.SetBool("IsMoving", isMoving);

        if (!isMoving) return;

        Vector3 camForward = Quaternion.Euler(0, _yaw, 0) * Vector3.forward;
        Vector3 camRight = Quaternion.Euler(0, _yaw, 0) * Vector3.right;
        Vector3 dir = (camForward * v + camRight * h).normalized;

        transform.position += dir * moveSpeed * Time.deltaTime;

        if (dir.sqrMagnitude > 0.01f)
        {
            Quaternion targetRot = Quaternion.LookRotation(dir);
            transform.rotation = Quaternion.Slerp(transform.rotation, targetRot, Time.deltaTime * rotationSpeed);
        }

        if (Time.time - _lastSendTime >= sendInterval)
        {
            _lastSendTime = Time.time;
            var (sx, sy) = CoordConverter.UnityToServer(transform.position);
            uint timestampMs = (uint)((Time.realtimeSinceStartup - _clientStartTime) * 1000f);
            NetworkManager.Instance.SendMove(sx, sy, 0f, timestampMs);
        }
    }

    // ━━━ Targeting ━━━

    private void HandleTargeting()
    {
        if (Input.GetKeyDown(KeyCode.Tab))
        {
            CycleTabTarget();
            return;
        }

        if (!_cursorLocked && Input.GetMouseButtonDown(0))
        {
            var ray = _mainCamera.ScreenPointToRay(Input.mousePosition);
            if (Physics.Raycast(ray, out var hit, 100f))
            {
                var monster = hit.collider.GetComponent<MonsterEntity>();
                if (monster == null)
                    monster = hit.collider.GetComponentInParent<MonsterEntity>();

                if (monster != null && monster.IsAlive)
                    SelectTarget(monster.EntityId);
            }
        }
    }

    private void CycleTabTarget()
    {
        if (MonsterManager.Instance == null) return;

        var monsters = MonsterManager.Instance.MonsterMap;
        if (monsters.Count == 0) return;

        var alive = new System.Collections.Generic.List<MonsterEntity>();
        foreach (var kvp in monsters)
        {
            if (kvp.Value != null && kvp.Value.IsAlive && kvp.Value.gameObject.activeSelf)
                alive.Add(kvp.Value);
        }

        if (alive.Count == 0) return;

        alive.Sort((a, b) =>
        {
            float da = Vector3.SqrMagnitude(a.transform.position - transform.position);
            float db = Vector3.SqrMagnitude(b.transform.position - transform.position);
            return da.CompareTo(db);
        });

        _tabIndex = _tabIndex % alive.Count;
        SelectTarget(alive[_tabIndex].EntityId);
        _tabIndex++;
    }

    private void SelectTarget(ulong entityId)
    {
        _currentTarget = entityId;
        if (CombatManager.Instance != null)
            CombatManager.Instance.SelectTarget(entityId);
    }

    // ━━━ Attack ━━━

    private void HandleAttack()
    {
        if (!_cursorLocked) return;
        if (!Input.GetMouseButtonDown(0)) return;
        if (_currentTarget == 0) return;
        if (Time.time - _lastAttackTime < attackCooldown) return;

        if (MonsterManager.Instance == null) return;

        var monster = MonsterManager.Instance.GetMonster(_currentTarget);
        if (monster == null || !monster.IsAlive)
        {
            _currentTarget = 0;
            return;
        }

        float dist = Vector3.Distance(transform.position, monster.transform.position);
        if (dist > attackRange) return;

        _lastAttackTime = Time.time;
        _animator?.SetTrigger("Attack");

        if (CombatManager.Instance != null)
            CombatManager.Instance.Attack(_currentTarget);
    }

    // ━━━ TPS Camera ━━━

    private void UpdateCamera()
    {
        if (_mainCamera == null) return;

        Vector3 lookTarget = transform.position + Vector3.up * 1.5f;
        Quaternion rotation = Quaternion.Euler(_pitch, _yaw, 0f);
        Vector3 right = Quaternion.Euler(0f, _yaw, 0f) * Vector3.right;

        Vector3 pivot = transform.position + Vector3.up * pivotHeight;
        Vector3 back = rotation * Vector3.back;
        Vector3 desiredPos = pivot + back * cameraDistance + right * shoulderOffsetX;

        // Camera collision
        Vector3 origin = pivot + right * shoulderOffsetX;
        Vector3 toCamera = desiredPos - origin;
        float maxDist = toCamera.magnitude;

        if (maxDist > 0.01f &&
            Physics.SphereCast(origin, cameraCollisionRadius, toCamera.normalized, out var hit, maxDist))
        {
            float safeDist = Mathf.Max(hit.distance - 0.1f, 0.3f);
            desiredPos = origin + toCamera.normalized * safeDist;
        }

        _mainCamera.transform.position = desiredPos;
        _mainCamera.transform.LookAt(lookTarget);
    }

    // ━━━ Target Highlight ━━━

    private void CreateTargetHighlight()
    {
        _targetHighlight = GameObject.CreatePrimitive(PrimitiveType.Cylinder);
        _targetHighlight.name = "TargetHighlight";
        _targetHighlight.transform.localScale = new Vector3(2f, 0.01f, 2f);

        var col = _targetHighlight.GetComponent<Collider>();
        if (col != null) Object.Destroy(col);

        var rend = _targetHighlight.GetComponent<MeshRenderer>();
        if (rend != null)
        {
            var mat = new Material(rend.sharedMaterial);
            mat.color = new Color(1f, 0f, 0f, 0.4f);
            rend.material = mat;
        }
        _targetHighlight.SetActive(false);
    }

    private void UpdateTargetHighlight()
    {
        if (_targetHighlight == null) return;

        if (_currentTarget == 0 || MonsterManager.Instance == null)
        {
            _targetHighlight.SetActive(false);
            return;
        }

        var monster = MonsterManager.Instance.GetMonster(_currentTarget);
        if (monster == null || !monster.IsAlive || !monster.gameObject.activeSelf)
        {
            _targetHighlight.SetActive(false);
            return;
        }

        _targetHighlight.SetActive(true);
        Vector3 pos = monster.transform.position;
        pos.y = 0.02f;
        _targetHighlight.transform.position = pos;
    }

    // ━━━ Callbacks ━━━

    private void HandlePositionCorrection(float x, float y, float z)
    {
        Vector3 corrected = CoordConverter.ServerToUnity(x, y);
        transform.position = corrected;
        Debug.Log($"[LocalPlayer] Position corrected to ({x},{y},{z})");
    }

    private void HandleMonsterDied(ulong entityId)
    {
        if (_currentTarget == entityId)
        {
            _currentTarget = 0;
            if (CombatManager.Instance != null)
                CombatManager.Instance.SelectTarget(0);
        }
    }
}
