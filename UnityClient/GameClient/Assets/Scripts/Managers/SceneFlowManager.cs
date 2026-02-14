using UnityEngine;
using UnityEngine.SceneManagement;
using UnityEngine.UI;
using System.Collections;

/// <summary>
/// 씬 전환 매니저 (P0_S01_C02)
/// 씬 전환 순서: Intro → Login → ServerSelect → CharacterSelect → GameWorld
/// 페이드인/아웃 트랜지션 (0.5초 검정 오버레이)
/// DontDestroyOnLoad 싱글톤
/// </summary>
public class SceneFlowManager : MonoBehaviour
{
    public static SceneFlowManager Instance { get; private set; }

    public enum GameScene
    {
        Intro,
        Login,
        ServerSelect,
        CharacterSelect,
        GameWorld,
    }

    [SerializeField] private float fadeDuration = 0.5f;

    private Canvas _fadeCanvas;
    private Image _fadeImage;
    private bool _isTransitioning;

    public GameScene CurrentScene { get; private set; } = GameScene.Intro;

    public event System.Action<GameScene> OnSceneChanged;

    private void Awake()
    {
        if (Instance != null && Instance != this)
        {
            Destroy(gameObject);
            return;
        }
        Instance = this;
        DontDestroyOnLoad(gameObject);

        CreateFadeOverlay();
    }

    private void OnDestroy()
    {
        if (Instance == this)
            Instance = null;
    }

    /// <summary>
    /// 지정된 씬으로 페이드 전환합니다.
    /// </summary>
    public void TransitionTo(GameScene target)
    {
        if (_isTransitioning) return;
        StartCoroutine(TransitionCoroutine(target));
    }

    /// <summary>
    /// 씬 흐름 순서에 따라 다음 씬으로 전환합니다.
    /// </summary>
    public void TransitionToNext()
    {
        if (_isTransitioning) return;

        var next = CurrentScene switch
        {
            GameScene.Intro => GameScene.Login,
            GameScene.Login => GameScene.ServerSelect,
            GameScene.ServerSelect => GameScene.CharacterSelect,
            GameScene.CharacterSelect => GameScene.GameWorld,
            _ => CurrentScene,
        };

        if (next != CurrentScene)
            TransitionTo(next);
    }

    private IEnumerator TransitionCoroutine(GameScene target)
    {
        _isTransitioning = true;

        // Fade out (화면 어둡게)
        yield return FadeCoroutine(0f, 1f);

        // 씬 로드
        string sceneName = GetSceneName(target);
        var op = SceneManager.LoadSceneAsync(sceneName);
        if (op != null)
            yield return op;

        CurrentScene = target;
        OnSceneChanged?.Invoke(target);

        // Fade in (화면 밝게)
        yield return FadeCoroutine(1f, 0f);

        _isTransitioning = false;
    }

    private IEnumerator FadeCoroutine(float from, float to)
    {
        if (_fadeImage == null) yield break;

        _fadeCanvas.enabled = true;
        float elapsed = 0f;

        while (elapsed < fadeDuration)
        {
            elapsed += Time.unscaledDeltaTime;
            float t = Mathf.Clamp01(elapsed / fadeDuration);
            float alpha = Mathf.Lerp(from, to, t);
            _fadeImage.color = new Color(0f, 0f, 0f, alpha);
            yield return null;
        }

        _fadeImage.color = new Color(0f, 0f, 0f, to);

        if (to <= 0f)
            _fadeCanvas.enabled = false;
    }

    private void CreateFadeOverlay()
    {
        var fadeGo = new GameObject("FadeOverlay");
        fadeGo.transform.SetParent(transform);

        _fadeCanvas = fadeGo.AddComponent<Canvas>();
        _fadeCanvas.renderMode = RenderMode.ScreenSpaceOverlay;
        _fadeCanvas.sortingOrder = 9999;
        _fadeCanvas.enabled = false;

        var imgGo = new GameObject("FadeImage");
        imgGo.transform.SetParent(fadeGo.transform, false);

        var rt = imgGo.AddComponent<RectTransform>();
        rt.anchorMin = Vector2.zero;
        rt.anchorMax = Vector2.one;
        rt.sizeDelta = Vector2.zero;

        _fadeImage = imgGo.AddComponent<Image>();
        _fadeImage.color = new Color(0f, 0f, 0f, 0f);
        _fadeImage.raycastTarget = false;
    }

    private static string GetSceneName(GameScene scene)
    {
        return scene switch
        {
            GameScene.Intro => "IntroScene",
            GameScene.Login => "LoginScene",
            GameScene.ServerSelect => "ServerSelectScene",
            GameScene.CharacterSelect => "CharacterSelectScene",
            GameScene.GameWorld => "GameScene",
            _ => "GameScene",
        };
    }
}
