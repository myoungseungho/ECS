using UnityEngine;
using Network;

public class LocalPlayer : MonoBehaviour
{
    [Header("Movement")]
    [SerializeField] private float moveSpeed = 5f;
    [SerializeField] private float sendInterval = 0.1f;
    [SerializeField] private float rotationSpeed = 10f;

    [Header("Quarter View Camera")]
    [SerializeField] private float cameraHeight = 15f;
    [SerializeField] private float cameraBack = 10f;
    [SerializeField] private float cameraFOV = 50f;
    [SerializeField] private float cameraRotateSpeed = 120f;
    [SerializeField] private float cameraDamping = 5f;
    [SerializeField] private float zoomSpeed = 3f;
    [SerializeField] private float zoomMin = 8f;
    [SerializeField] private float zoomMax = 25f;
    [SerializeField] private float zoomSmoothSpeed = 8f;
    [SerializeField] private float cameraCollisionMinDist = 2f;

    [Header("Combat")]
    [SerializeField] private float attackRange = 15f;
    [SerializeField] private float comboResetTime = 1.0f;
    [SerializeField] private int maxComboCount = 4;

    [Header("Dash")]
    [SerializeField] private float dashSpeed = 15f;
    [SerializeField] private float dashDuration = 0.35f;
    [SerializeField] private float dashCooldown = 1.5f;

    [Header("Animation")]
    [SerializeField] private float combatExitDelay = 5f;

    public ulong EntityId { get; set; }

    private Camera _mainCamera;
    private Animator _animator;
    private float _lastSendTime;
    private float _clientStartTime;

    // Camera
    private float _yaw;
    private float _currentZoom = 15f;
    private float _targetZoom = 15f;
    private Vector3 _cameraVelocity;

    // Targeting
    private ulong _currentTarget;
    private GameObject _targetHighlight;
    private int _tabIndex;

    // Combo
    private int _comboIndex;
    private float _lastAttackTime;
    private float _lastCombatActionTime;
    private bool _inCombat;

    // Dash
    private bool _isDashing;
    private float _dashTimer;
    private float _lastDashTime;
    private Vector3 _dashDirection;

    private void Start()
    {
        _mainCamera = Camera.main;
        _animator = GetComponentInChildren<Animator>();
        _clientStartTime = Time.realtimeSinceStartup;

        _yaw = 0f;
        _currentZoom = cameraHeight;
        _targetZoom = cameraHeight;

        Cursor.lockState = CursorLockMode.None;
        Cursor.visible = true;

        if (_mainCamera != null)
            _mainCamera.fieldOfView = cameraFOV;

        CreateTargetHighlight();

        var net = NetworkManager.Instance;
        if (net != null)
            net.OnPositionCorrection += HandlePositionCorrection;

        if (MonsterManager.Instance != null)
            MonsterManager.Instance.OnMonsterDied += HandleMonsterDied;

        if (CombatManager.Instance != null)
            CombatManager.Instance.OnAttackFeedback += HandleAttackFeedback;
    }

    private void OnDestroy()
    {
        var net = NetworkManager.Instance;
        if (net != null)
            net.OnPositionCorrection -= HandlePositionCorrection;

        if (MonsterManager.Instance != null)
            MonsterManager.Instance.OnMonsterDied -= HandleMonsterDied;

        if (CombatManager.Instance != null)
            CombatManager.Instance.OnAttackFeedback -= HandleAttackFeedback;

        if (_targetHighlight != null)
            Destroy(_targetHighlight);
    }

    private void Update()
    {
        if (NetworkManager.Instance == null ||
            NetworkManager.Instance.State != NetworkManager.ConnectionState.InGame)
            return;

        HandleCameraRotation();
        HandleCameraZoom();
        HandleDash();
        HandleMovement();
        HandleTargeting();
        HandleAttack();
        UpdateCombatState();
        UpdateCamera();
        UpdateTargetHighlight();
    }

    // ━━━ Camera Rotation (Middle Mouse Drag) ━━━

    private void HandleCameraRotation()
    {
        if (Input.GetMouseButton(2))
        {
            float deltaX = Input.GetAxis("Mouse X");
            _yaw += deltaX * cameraRotateSpeed * Time.deltaTime;
        }
    }

    // ━━━ Camera Zoom (Scroll Wheel) ━━━

    private void HandleCameraZoom()
    {
        float scroll = Input.GetAxis("Mouse ScrollWheel");
        if (Mathf.Abs(scroll) > 0.01f)
        {
            _targetZoom -= scroll * zoomSpeed * 10f;
            _targetZoom = Mathf.Clamp(_targetZoom, zoomMin, zoomMax);
        }
        _currentZoom = Mathf.Lerp(_currentZoom, _targetZoom, Time.deltaTime * zoomSmoothSpeed);
    }

    // ━━━ Dash (Space) ━━━

    private void HandleDash()
    {
        if (_isDashing)
        {
            _dashTimer -= Time.deltaTime;
            transform.position += _dashDirection * dashSpeed * Time.deltaTime;

            if (_dashTimer <= 0f)
                _isDashing = false;

            return;
        }

        if (Input.GetKeyDown(KeyCode.Space) && Time.time - _lastDashTime >= dashCooldown)
        {
            float h = Input.GetAxis("Horizontal");
            float v = Input.GetAxis("Vertical");

            Vector3 camForward = Quaternion.Euler(0, _yaw, 0) * Vector3.forward;
            Vector3 camRight = Quaternion.Euler(0, _yaw, 0) * Vector3.right;
            _dashDirection = (camForward * v + camRight * h).normalized;

            if (_dashDirection.sqrMagnitude < 0.01f)
                _dashDirection = transform.forward;

            _isDashing = true;
            _dashTimer = dashDuration;
            _lastDashTime = Time.time;
            _lastCombatActionTime = Time.time;

            _animator?.SetTrigger("Dash");
        }
    }

    // ━━━ Movement (Camera-relative WASD) ━━━

    private void HandleMovement()
    {
        if (_isDashing)
        {
            _animator?.SetFloat("Speed", 2f);
            return;
        }

        float h = Input.GetAxis("Horizontal");
        float v = Input.GetAxis("Vertical");

        float inputMagnitude = new Vector2(h, v).magnitude;
        bool isMoving = inputMagnitude > 0.01f;

        _animator?.SetFloat("Speed", isMoving ? Mathf.Clamp(inputMagnitude, 0f, 2f) : 0f);
        _animator?.SetBool("IsMoving", isMoving);

        if (!isMoving) return;

        Vector3 camForward = Quaternion.Euler(0, _yaw, 0) * Vector3.forward;
        Vector3 camRight = Quaternion.Euler(0, _yaw, 0) * Vector3.right;
        Vector3 dir = (camForward * v + camRight * h).normalized;

        transform.position += dir * moveSpeed * Time.deltaTime;

        // 터레인 높이 적용
        ApplyTerrainHeight();

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

    // ━━━ Targeting (Left Click) ━━━

    private void HandleTargeting()
    {
        if (Input.GetKeyDown(KeyCode.Tab))
        {
            CycleTabTarget();
            return;
        }

        if (Input.GetMouseButtonDown(0))
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

    // ━━━ Attack (Combo System) ━━━

    private void HandleAttack()
    {
        if (_isDashing) return;
        if (!Input.GetMouseButtonDown(0)) return;
        if (_currentTarget == 0) return;

        if (MonsterManager.Instance == null) return;

        var monster = MonsterManager.Instance.GetMonster(_currentTarget);
        if (monster == null || !monster.IsAlive)
        {
            _currentTarget = 0;
            return;
        }

        float dist = Vector3.Distance(transform.position, monster.transform.position);
        if (dist > attackRange) return;

        // Combo timing: reset if too slow
        if (Time.time - _lastAttackTime > comboResetTime)
            _comboIndex = 0;

        _animator?.SetInteger("AttackIndex", _comboIndex);
        _animator?.SetTrigger("Attack");

        _lastAttackTime = Time.time;
        _lastCombatActionTime = Time.time;

        if (CombatManager.Instance != null)
            CombatManager.Instance.Attack(_currentTarget);

        _comboIndex = (_comboIndex + 1) % maxComboCount;
    }

    // ━━━ Combat State ━━━

    private void UpdateCombatState()
    {
        if (!_inCombat && _currentTarget != 0)
        {
            _inCombat = true;
            _lastCombatActionTime = Time.time;
        }

        if (_inCombat && Time.time - _lastCombatActionTime > combatExitDelay)
        {
            _inCombat = false;
            _comboIndex = 0;
        }

        _animator?.SetBool("InCombat", _inCombat);
    }

    // ━━━ Quarter View Camera ━━━

    private void UpdateCamera()
    {
        if (_mainCamera == null) return;

        float zoomRatio = _currentZoom / cameraHeight;
        float height = cameraHeight * zoomRatio;
        float back = cameraBack * zoomRatio;

        Quaternion rotation = Quaternion.Euler(0, _yaw, 0);
        Vector3 offset = rotation * new Vector3(0f, height, -back);

        Vector3 lookTarget = transform.position + Vector3.up * 1f;
        Vector3 desiredPos = transform.position + offset;

        Vector3 origin = transform.position + Vector3.up * 0.5f;
        Vector3 toCamera = desiredPos - origin;
        float maxDist = toCamera.magnitude;

        if (maxDist > 0.01f &&
            Physics.Raycast(origin, toCamera.normalized, out var hit, maxDist))
        {
            float safeDist = Mathf.Max(hit.distance - 0.5f, cameraCollisionMinDist);
            desiredPos = origin + toCamera.normalized * safeDist;
        }

        _mainCamera.transform.position = Vector3.SmoothDamp(
            _mainCamera.transform.position, desiredPos, ref _cameraVelocity,
            1f / cameraDamping);

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

    // ━━━ Terrain Height ━━━

    private void ApplyTerrainHeight()
    {
        var terrain = Terrain.activeTerrain;
        if (terrain == null) return;

        Vector3 pos = transform.position;
        pos.y = terrain.SampleHeight(pos) + terrain.transform.position.y;
        transform.position = pos;
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

    private void HandleAttackFeedback(AttackResultData data)
    {
        if (data.AttackerId != EntityId) return;

        _lastCombatActionTime = Time.time;
    }
}
