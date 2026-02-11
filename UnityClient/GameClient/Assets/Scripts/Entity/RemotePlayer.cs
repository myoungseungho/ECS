using UnityEngine;

public class RemotePlayer : MonoBehaviour
{
    [SerializeField] private float lerpSpeed = 10f;

    public ulong EntityId { get; set; }

    private Vector3 _targetPos;

    public void SetTargetPosition(Vector3 pos)
    {
        _targetPos = pos;
    }

    private void Update()
    {
        transform.position = Vector3.Lerp(
            transform.position, _targetPos, Time.deltaTime * lerpSpeed);

        // 이동 방향으로 회전
        Vector3 dir = _targetPos - transform.position;
        if (dir.magnitude > 0.01f)
            transform.rotation = Quaternion.LookRotation(dir);
    }
}
