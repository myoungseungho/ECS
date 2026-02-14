// ━━━ MonsterWorldUI.cs ━━━
// 몬스터 머리 위 World Space UI — HP바 + 이름/레벨 텍스트
// MonsterManager.HandleMonsterSpawn()에서 AddComponent + Initialize()

using UnityEngine;
using UnityEngine.UI;

public class MonsterWorldUI : MonoBehaviour
{
    private Canvas _canvas;
    private Slider _hpSlider;
    private Text _nameText;
    private MonsterEntity _monster;
    private Camera _mainCamera;
    private Image _fillImage;

    public void Initialize(MonsterEntity monster)
    {
        _monster = monster;
        _mainCamera = Camera.main;
        BuildUI();
        Refresh();
    }

    private void BuildUI()
    {
        // World Space Canvas
        var canvasGo = new GameObject("WorldCanvas");
        canvasGo.transform.SetParent(transform, false);
        canvasGo.transform.localPosition = Vector3.up * 2.5f;

        _canvas = canvasGo.AddComponent<Canvas>();
        _canvas.renderMode = RenderMode.WorldSpace;
        _canvas.sortingOrder = 10;

        var rt = canvasGo.GetComponent<RectTransform>();
        rt.sizeDelta = new Vector2(160, 40);
        rt.localScale = Vector3.one * 0.01f;

        // Name + Level Text
        var nameGo = new GameObject("NameText");
        nameGo.transform.SetParent(canvasGo.transform, false);
        var nameRT = nameGo.AddComponent<RectTransform>();
        nameRT.anchorMin = new Vector2(0, 0.5f);
        nameRT.anchorMax = new Vector2(1, 1);
        nameRT.offsetMin = Vector2.zero;
        nameRT.offsetMax = Vector2.zero;

        _nameText = nameGo.AddComponent<Text>();
        _nameText.fontSize = 16;
        _nameText.alignment = TextAnchor.MiddleCenter;
        _nameText.color = Color.white;
        _nameText.font = Resources.GetBuiltinResource<Font>("LegacyRuntime.ttf");
        _nameText.text = $"{GetMonsterName(_monster.MonsterId)} Lv.{_monster.Level}";

        // HP Slider
        var sliderGo = new GameObject("HPSlider");
        sliderGo.transform.SetParent(canvasGo.transform, false);
        var sliderRT = sliderGo.AddComponent<RectTransform>();
        sliderRT.anchorMin = new Vector2(0.1f, 0);
        sliderRT.anchorMax = new Vector2(0.9f, 0.45f);
        sliderRT.offsetMin = Vector2.zero;
        sliderRT.offsetMax = Vector2.zero;

        _hpSlider = sliderGo.AddComponent<Slider>();
        _hpSlider.minValue = 0;
        _hpSlider.maxValue = 1;
        _hpSlider.interactable = false;

        // Background
        var bgGo = new GameObject("Background");
        bgGo.transform.SetParent(sliderGo.transform, false);
        var bgRT = bgGo.AddComponent<RectTransform>();
        bgRT.anchorMin = Vector2.zero;
        bgRT.anchorMax = Vector2.one;
        bgRT.sizeDelta = Vector2.zero;
        var bgImg = bgGo.AddComponent<Image>();
        bgImg.color = new Color(0.2f, 0.2f, 0.2f, 0.8f);

        // Fill area
        var fillAreaGo = new GameObject("Fill Area");
        fillAreaGo.transform.SetParent(sliderGo.transform, false);
        var fillAreaRT = fillAreaGo.AddComponent<RectTransform>();
        fillAreaRT.anchorMin = Vector2.zero;
        fillAreaRT.anchorMax = Vector2.one;
        fillAreaRT.sizeDelta = Vector2.zero;

        var fillGo = new GameObject("Fill");
        fillGo.transform.SetParent(fillAreaGo.transform, false);
        var fillRT = fillGo.AddComponent<RectTransform>();
        fillRT.anchorMin = Vector2.zero;
        fillRT.anchorMax = Vector2.one;
        fillRT.sizeDelta = Vector2.zero;
        _fillImage = fillGo.AddComponent<Image>();
        _fillImage.color = new Color(0.8f, 0.15f, 0.15f);

        _hpSlider.fillRect = fillRT;
    }

    private void Update()
    {
        if (_monster == null || _canvas == null) return;

        // Billboard: face camera
        if (_mainCamera != null)
            _canvas.transform.forward = _mainCamera.transform.forward;

        Refresh();
    }

    private void Refresh()
    {
        if (_monster == null) return;

        // HP
        if (_hpSlider != null)
            _hpSlider.value = _monster.HpRatio;

        // Hide on death
        if (_canvas != null)
            _canvas.gameObject.SetActive(_monster.IsAlive);
    }

    public static string GetMonsterName(uint monsterId)
    {
        switch (monsterId)
        {
            case 1: return "Goblin";
            case 2: return "Wolf";
            case 3: return "Orc";
            case 4: return "Bear";
            case 5: return "Skeleton";
            default: return $"Monster#{monsterId}";
        }
    }
}
