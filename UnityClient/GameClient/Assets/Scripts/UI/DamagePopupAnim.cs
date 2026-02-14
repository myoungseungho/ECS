// ━━━ DamagePopupAnim.cs ━━━
// 데미지 팝업 애니메이션 — 위로 떠오르며 페이드아웃 후 자동 파괴

using UnityEngine;
using UnityEngine.UI;

public class DamagePopupAnim : MonoBehaviour
{
    private float _duration = 1.2f;
    private float _elapsed;
    private Text _text;
    private RectTransform _rt;
    private Vector3 _startPos;

    public void Initialize(float duration)
    {
        _duration = duration;
        _text = GetComponent<Text>();
        _rt = GetComponent<RectTransform>();
        _startPos = _rt != null ? _rt.localPosition : Vector3.zero;
        _elapsed = 0f;
    }

    private void Update()
    {
        _elapsed += Time.deltaTime;
        float t = Mathf.Clamp01(_elapsed / _duration);

        // 위로 이동
        if (_rt != null)
            _rt.localPosition = _startPos + Vector3.up * (t * 40f);

        // 페이드아웃 (후반 50%에서)
        if (_text != null && t > 0.5f)
        {
            float fadeT = (t - 0.5f) / 0.5f;
            var c = _text.color;
            c.a = 1f - fadeT;
            _text.color = c;
        }

        if (_elapsed >= _duration)
            Destroy(gameObject);
    }
}
