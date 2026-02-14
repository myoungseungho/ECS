// ━━━ IntroUI.cs ━━━
// P0_S01_C01: 인트로 & 타이틀 화면
// 로고 페이드인 → 유지 → 페이드아웃 → 타이틀 표시 → 아무 키 → LoginScene 전환
// 싱글톤 아님 — IntroScene 전용 UI 컴포넌트

using UnityEngine;
using UnityEngine.UI;

public class IntroUI : MonoBehaviour
{
    [Header("UI References")]
    [SerializeField] private Text logoText;
    [SerializeField] private Text titleText;
    [SerializeField] private Text pressAnyKeyText;

    [Header("Timing")]
    [SerializeField] private float logoFadeInDuration = 1.5f;
    [SerializeField] private float logoHoldDuration = 1.0f;
    [SerializeField] private float logoFadeOutDuration = 1.0f;
    [SerializeField] private float titleFadeInDuration = 1.5f;

    private enum IntroPhase
    {
        LogoFadeIn,
        LogoHold,
        LogoFadeOut,
        TitleFadeIn,
        WaitForKey,
    }

    private IntroPhase _phase = IntroPhase.LogoFadeIn;
    private float _timer;
    private bool _transitioning;

    private void Start()
    {
        // 초기 상태: 모두 투명
        SetTextAlpha(logoText, 0f);
        SetTextAlpha(titleText, 0f);
        SetTextAlpha(pressAnyKeyText, 0f);

        _timer = 0f;
        _phase = IntroPhase.LogoFadeIn;
    }

    private void Update()
    {
        if (_transitioning) return;

        _timer += Time.deltaTime;

        switch (_phase)
        {
            case IntroPhase.LogoFadeIn:
                SetTextAlpha(logoText, Mathf.Clamp01(_timer / logoFadeInDuration));
                if (_timer >= logoFadeInDuration)
                {
                    _timer = 0f;
                    _phase = IntroPhase.LogoHold;
                }
                break;

            case IntroPhase.LogoHold:
                if (_timer >= logoHoldDuration)
                {
                    _timer = 0f;
                    _phase = IntroPhase.LogoFadeOut;
                }
                break;

            case IntroPhase.LogoFadeOut:
                SetTextAlpha(logoText, 1f - Mathf.Clamp01(_timer / logoFadeOutDuration));
                if (_timer >= logoFadeOutDuration)
                {
                    _timer = 0f;
                    _phase = IntroPhase.TitleFadeIn;
                }
                break;

            case IntroPhase.TitleFadeIn:
                float t = Mathf.Clamp01(_timer / titleFadeInDuration);
                SetTextAlpha(titleText, t);
                if (_timer >= titleFadeInDuration)
                {
                    _timer = 0f;
                    _phase = IntroPhase.WaitForKey;
                }
                break;

            case IntroPhase.WaitForKey:
                // "Press Any Key" 깜빡임 (sin 함수 alpha)
                float alpha = (Mathf.Sin(Time.time * 3f) + 1f) * 0.5f;
                SetTextAlpha(pressAnyKeyText, alpha);

                if (Input.anyKeyDown)
                {
                    _transitioning = true;
                    if (SceneFlowManager.Instance != null)
                        SceneFlowManager.Instance.TransitionToNext();
                }
                break;
        }

        // 인트로 중 아무 키 누르면 스킵 (WaitForKey 전)
        if (_phase != IntroPhase.WaitForKey && Input.anyKeyDown && !Input.GetMouseButtonDown(0))
        {
            _phase = IntroPhase.WaitForKey;
            SetTextAlpha(logoText, 0f);
            SetTextAlpha(titleText, 1f);
            _timer = 0f;
        }
    }

    private static void SetTextAlpha(Text text, float alpha)
    {
        if (text == null) return;
        var c = text.color;
        c.a = alpha;
        text.color = c;
    }
}
