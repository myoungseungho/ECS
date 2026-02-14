using UnityEngine;

public class RemotePlayer : MonoBehaviour
{
    [SerializeField] private float lerpSpeed = 10f;

    public ulong EntityId { get; set; }

    private Vector3 _targetPos;
    private Animator _animator;

    private void Start()
    {
        _animator = GetComponentInChildren<Animator>();
    }

    public void SetTargetPosition(Vector3 pos)
    {
        _targetPos = pos;
    }

    private void Update()
    {
        float distance = Vector3.Distance(transform.position, _targetPos);
        _animator?.SetBool("IsMoving", distance > 0.1f);

        transform.position = Vector3.Lerp(
            transform.position, _targetPos, Time.deltaTime * lerpSpeed);

        // 이동 방향으로 회전
        Vector3 dir = _targetPos - transform.position;
        if (dir.magnitude > 0.01f)
            transform.rotation = Quaternion.LookRotation(dir);
    }
}
