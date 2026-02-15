// ━━━ MonsterEntity.cs ━━━
// 몬스터 엔티티 — 서버 위치로 보간 이동 + HP 추적 + 피격 애니메이션
// MonsterManager가 생성/관리

using UnityEngine;

public class MonsterEntity : MonoBehaviour
{
    // ━━━ 식별 ━━━
    public ulong EntityId { get; set; }
    public uint MonsterId { get; set; }
    public uint Level { get; set; }

    // ━━━ HP ━━━
    public int HP { get; set; }
    public int MaxHP { get; set; }
    public float HpRatio => MaxHP > 0 ? (float)HP / MaxHP : 0f;
    public bool IsAlive => HP > 0;

    // ━━━ 이동 보간 ━━━
    [SerializeField] private float lerpSpeed = 10f;

    // ━━━ 피격 비주얼 ━━━
    [SerializeField] private float hitFlashDuration = 0.1f;

    private Vector3 _targetPos;
    private Animator _animator;
    private Renderer[] _renderers;
    private Color[] _originalColors;
    private float _hitFlashTimer;
    private bool _isFlashing;

    public void SetTargetPosition(Vector3 pos)
    {
        _targetPos = pos;
    }

    private void Update()
    {
        float sqrDist = Vector3.SqrMagnitude(transform.position - _targetPos);
        bool isMoving = sqrDist > 0.01f;

        _animator?.SetBool("IsMoving", isMoving);
        _animator?.SetFloat("Speed", isMoving ? 1f : 0f);

        if (sqrDist > 0.001f)
        {
            Vector3 moveDir = _targetPos - transform.position;
            if (moveDir.sqrMagnitude > 0.001f)
            {
                Quaternion targetRot = Quaternion.LookRotation(moveDir);
                transform.rotation = Quaternion.Slerp(
                    transform.rotation, targetRot, Time.deltaTime * lerpSpeed);
            }

            transform.position = Vector3.Lerp(
                transform.position, _targetPos, Time.deltaTime * lerpSpeed);
        }

        // 터레인 높이 적용
        var terrain = Terrain.activeTerrain;
        if (terrain != null)
        {
            Vector3 pos = transform.position;
            pos.y = terrain.SampleHeight(pos) + terrain.transform.position.y;
            transform.position = pos;
        }

        UpdateHitFlash();
    }

    public void Initialize(ulong entityId, uint monsterId, uint level, int hp, int maxHp, Vector3 pos)
    {
        EntityId = entityId;
        MonsterId = monsterId;
        Level = level;
        HP = hp;
        MaxHP = maxHp;
        transform.position = pos;
        _targetPos = pos;
        _animator = GetComponentInChildren<Animator>();
        _renderers = GetComponentsInChildren<Renderer>();
        CacheOriginalColors();

        if (_animator != null)
        {
            _animator.SetBool("IsDead", false);
            _animator.SetFloat("Speed", 0f);
        }

        gameObject.name = $"Monster_{monsterId}_{entityId}";
    }

    public void PlayHit(float direction)
    {
        if (_animator != null)
        {
            _animator.SetFloat("HitDirection", direction);
            _animator.SetTrigger("Hit");
        }

        StartHitFlash();
    }

    public void PlayDeath()
    {
        _animator?.SetBool("IsDead", true);
    }

    // ━━━ Hit Flash ━━━

    private void CacheOriginalColors()
    {
        if (_renderers == null) return;
        _originalColors = new Color[_renderers.Length];
        for (int i = 0; i < _renderers.Length; i++)
        {
            if (_renderers[i] != null && _renderers[i].material != null)
                _originalColors[i] = _renderers[i].material.color;
        }
    }

    private void StartHitFlash()
    {
        _isFlashing = true;
        _hitFlashTimer = hitFlashDuration;

        if (_renderers == null) return;
        for (int i = 0; i < _renderers.Length; i++)
        {
            if (_renderers[i] != null && _renderers[i].material != null)
                _renderers[i].material.color = Color.red;
        }
    }

    private void UpdateHitFlash()
    {
        if (!_isFlashing) return;

        _hitFlashTimer -= Time.deltaTime;
        if (_hitFlashTimer <= 0f)
        {
            _isFlashing = false;
            RestoreOriginalColors();
        }
    }

    private void RestoreOriginalColors()
    {
        if (_renderers == null || _originalColors == null) return;
        for (int i = 0; i < _renderers.Length; i++)
        {
            if (i < _originalColors.Length && _renderers[i] != null && _renderers[i].material != null)
                _renderers[i].material.color = _originalColors[i];
        }
    }
}
