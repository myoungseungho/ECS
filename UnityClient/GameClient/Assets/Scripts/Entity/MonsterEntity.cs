// ━━━ MonsterEntity.cs ━━━
// 몬스터 엔티티 — 서버 위치로 보간 이동 + HP 추적
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

    private Vector3 _targetPos;

    public void SetTargetPosition(Vector3 pos)
    {
        _targetPos = pos;
    }

    private void Update()
    {
        if (Vector3.SqrMagnitude(transform.position - _targetPos) > 0.001f)
        {
            transform.position = Vector3.Lerp(
                transform.position, _targetPos, Time.deltaTime * lerpSpeed);
        }
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
        gameObject.name = $"Monster_{monsterId}_{entityId}";
    }
}
