// ━━━ ProjectSetup.cs ━━━
// Menu: "ECS Game > Setup All"
// 원클릭으로 Materials, Prefabs, Scenes, Build Settings 자동 구성
// 멱등성 보장 — 이미 존재하는 에셋은 스킵

using UnityEngine;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine.SceneManagement;
using UnityEngine.UI;
using System.IO;

public static class ProjectSetup
{
    // ━━━ 경로 상수 ━━━
    private const string MaterialsDir   = "Assets/Materials";
    private const string PrefabsDir     = "Assets/Prefabs";
    private const string ScenesDir      = "Assets/Scenes";

    private const string LocalMatPath    = MaterialsDir + "/LocalPlayer.mat";
    private const string RemoteMatPath   = MaterialsDir + "/RemotePlayer.mat";
    private const string MonsterMatPath  = MaterialsDir + "/Monster.mat";
    private const string LocalPrefabPath   = PrefabsDir + "/LocalPlayer.prefab";
    private const string RemotePrefabPath  = PrefabsDir + "/RemotePlayer.prefab";
    private const string MonsterPrefabPath = PrefabsDir + "/Monster.prefab";
    private const string GameScenePath  = ScenesDir + "/GameScene.unity";
    private const string TestScenePath  = ScenesDir + "/TestScene.unity";

    // URP Lit 셰이더 이름
    private const string URPLitShader = "Universal Render Pipeline/Lit";

    [MenuItem("ECS Game/Setup All", priority = 1)]
    public static void SetupAll()
    {
        Debug.Log("━━━ [ProjectSetup] 시작 ━━━");

        CreateDirectories();
        CreateMaterials();
        CreatePrefabs();
        CreateGameScene();
        CreateTestScene();
        RegisterBuildScenes();

        AssetDatabase.SaveAssets();
        AssetDatabase.Refresh();

        Debug.Log("━━━ [ProjectSetup] 완료! ━━━");
        EditorUtility.DisplayDialog("Setup Complete",
            "프로젝트 세팅 완료!\n\n" +
            "- Materials: LocalPlayer (파랑), RemotePlayer (초록)\n" +
            "- Prefabs: LocalPlayer, RemotePlayer\n" +
            "- Scenes: GameScene, TestScene\n" +
            "- Build Settings 등록 완료\n\n" +
            "'ECS Game > Validate Setup'으로 검증할 수 있습니다.",
            "OK");
    }

    // ━━━ 1. 디렉토리 ━━━

    private static void CreateDirectories()
    {
        EnsureDirectory(MaterialsDir);
        EnsureDirectory(PrefabsDir);
        EnsureDirectory(ScenesDir);
    }

    private static void EnsureDirectory(string path)
    {
        if (!AssetDatabase.IsValidFolder(path))
        {
            string parent = Path.GetDirectoryName(path).Replace("\\", "/");
            string folder = Path.GetFileName(path);
            AssetDatabase.CreateFolder(parent, folder);
            Debug.Log($"  [Dir] {path} 생성");
        }
    }

    // ━━━ 2. Materials ━━━

    private static void CreateMaterials()
    {
        CreateMaterial(LocalMatPath,  new Color(0.2f, 0.4f, 1.0f), "LocalPlayer (파랑)");
        CreateMaterial(RemoteMatPath, new Color(0.2f, 0.8f, 0.3f), "RemotePlayer (초록)");
        CreateMaterial(MonsterMatPath, new Color(0.9f, 0.2f, 0.2f), "Monster (빨강)");
    }

    private static void CreateMaterial(string path, Color color, string label)
    {
        if (AssetDatabase.LoadAssetAtPath<Material>(path) != null)
        {
            Debug.Log($"  [Material] {label} — 이미 존재, 스킵");
            return;
        }

        var shader = Shader.Find(URPLitShader);
        if (shader == null)
        {
            // URP가 아닌 프로젝트 폴백
            shader = Shader.Find("Standard");
            Debug.LogWarning($"  [Material] URP/Lit 셰이더 없음 — Standard 폴백");
        }

        var mat = new Material(shader);
        mat.SetColor("_BaseColor", color);
        AssetDatabase.CreateAsset(mat, path);
        Debug.Log($"  [Material] {label} 생성 완료");
    }

    // ━━━ 3. Prefabs ━━━

    private static void CreatePrefabs()
    {
        CreatePlayerPrefab(
            LocalPrefabPath,
            LocalMatPath,
            typeof(LocalPlayer),
            "LocalPlayer"
        );

        CreatePlayerPrefab(
            RemotePrefabPath,
            RemoteMatPath,
            typeof(RemotePlayer),
            "RemotePlayer"
        );

        CreateMonsterPrefab();
    }

    private static void CreateMonsterPrefab()
    {
        if (AssetDatabase.LoadAssetAtPath<GameObject>(MonsterPrefabPath) != null)
        {
            Debug.Log("  [Prefab] Monster — 이미 존재, 스킵");
            return;
        }

        var go = GameObject.CreatePrimitive(PrimitiveType.Cube);
        go.name = "Monster";
        go.transform.localScale = new Vector3(0.8f, 0.8f, 0.8f);

        var mat = AssetDatabase.LoadAssetAtPath<Material>(MonsterMatPath);
        if (mat != null)
        {
            var renderer = go.GetComponent<MeshRenderer>();
            renderer.sharedMaterial = mat;
        }

        go.AddComponent<MonsterEntity>();

        PrefabUtility.SaveAsPrefabAsset(go, MonsterPrefabPath);
        Object.DestroyImmediate(go);
        Debug.Log("  [Prefab] Monster 생성 완료");
    }

    private static void CreatePlayerPrefab(
        string prefabPath, string matPath, System.Type componentType, string label)
    {
        if (AssetDatabase.LoadAssetAtPath<GameObject>(prefabPath) != null)
        {
            Debug.Log($"  [Prefab] {label} — 이미 존재, 스킵");
            return;
        }

        // Capsule 프리미티브 생성
        var go = GameObject.CreatePrimitive(PrimitiveType.Capsule);
        go.name = label;

        // Material 적용
        var mat = AssetDatabase.LoadAssetAtPath<Material>(matPath);
        if (mat != null)
        {
            var renderer = go.GetComponent<MeshRenderer>();
            renderer.sharedMaterial = mat;
        }

        // 컴포넌트 부착
        go.AddComponent(componentType);

        // Prefab 저장
        PrefabUtility.SaveAsPrefabAsset(go, prefabPath);
        Object.DestroyImmediate(go);
        Debug.Log($"  [Prefab] {label} 생성 완료");
    }

    // ━━━ 4. GameScene ━━━

    private static void CreateGameScene()
    {
        if (File.Exists(GameScenePath))
        {
            Debug.Log("  [Scene] GameScene — 이미 존재, 스킵");
            return;
        }

        var scene = EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Single);

        // --- Floor ---
        var floor = GameObject.CreatePrimitive(PrimitiveType.Plane);
        floor.name = "Floor";
        floor.transform.position = new Vector3(50f, 0f, 50f);
        floor.transform.localScale = new Vector3(10f, 1f, 10f);

        // --- Directional Light ---
        var lightGo = new GameObject("Directional Light");
        var light = lightGo.AddComponent<Light>();
        light.type = LightType.Directional;
        light.color = new Color(1f, 0.95f, 0.84f);
        light.intensity = 1.0f;
        lightGo.transform.rotation = Quaternion.Euler(50f, -30f, 0f);

        // --- Main Camera ---
        var camGo = new GameObject("Main Camera");
        camGo.tag = "MainCamera";
        camGo.AddComponent<Camera>();
        camGo.transform.position = new Vector3(50f, 40f, -10f);
        camGo.transform.rotation = Quaternion.Euler(60f, 0f, 0f);

        // --- Managers ---
        var networkGo = CreateManagerObject("NetworkManager", typeof(Network.NetworkManager));
        var gameManagerGo = CreateManagerObject("GameManager", typeof(GameManager));
        var entityManagerGo = CreateManagerObject("EntityManager", typeof(EntityManager));
        var entityPoolGo = CreateManagerObject("EntityPool", typeof(EntityPool));
        var statsManagerGo = CreateManagerObject("StatsManager", typeof(StatsManager));
        var combatManagerGo = CreateManagerObject("CombatManager", typeof(CombatManager));
        var monsterManagerGo = CreateManagerObject("MonsterManager", typeof(MonsterManager));

        // --- UI Canvas ---
        CreateUICanvas(scene);

        // --- Prefab 참조 연결 (SerializedObject API) ---
        var localPrefab = AssetDatabase.LoadAssetAtPath<GameObject>(LocalPrefabPath);
        var remotePrefab = AssetDatabase.LoadAssetAtPath<GameObject>(RemotePrefabPath);
        var monsterPrefab = AssetDatabase.LoadAssetAtPath<GameObject>(MonsterPrefabPath);

        // EntityManager: localPlayerPrefab, remotePlayerPrefab
        ConnectPrefabRef(entityManagerGo, typeof(EntityManager),
            "localPlayerPrefab", localPrefab);
        ConnectPrefabRef(entityManagerGo, typeof(EntityManager),
            "remotePlayerPrefab", remotePrefab);

        // EntityPool: prefab (RemotePlayer)
        ConnectPrefabRef(entityPoolGo, typeof(EntityPool),
            "prefab", remotePrefab);

        // MonsterManager: monsterPrefab (Monster)
        ConnectPrefabRef(monsterManagerGo, typeof(MonsterManager),
            "monsterPrefab", monsterPrefab);

        // Scene 저장
        EditorSceneManager.SaveScene(scene, GameScenePath);
        Debug.Log("  [Scene] GameScene 생성 완료");
    }

    // ━━━ 5. TestScene ━━━

    private static void CreateTestScene()
    {
        if (File.Exists(TestScenePath))
        {
            Debug.Log("  [Scene] TestScene — 이미 존재, 스킵");
            return;
        }

        var scene = EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Single);

        // Camera
        var camGo = new GameObject("Main Camera");
        camGo.tag = "MainCamera";
        camGo.AddComponent<Camera>();
        camGo.transform.position = new Vector3(0f, 5f, -10f);

        // NetworkManager
        CreateManagerObject("NetworkManager", typeof(Network.NetworkManager));

        // ConnectionTest
        var testGo = new GameObject("ConnectionTest");
        testGo.AddComponent<ConnectionTest>();

        EditorSceneManager.SaveScene(scene, TestScenePath);
        Debug.Log("  [Scene] TestScene 생성 완료");
    }

    // ━━━ 6. Build Settings ━━━

    private static void RegisterBuildScenes()
    {
        var scenes = EditorBuildSettings.scenes;
        bool hasGame = false;
        bool hasTest = false;

        foreach (var s in scenes)
        {
            if (s.path == GameScenePath) hasGame = true;
            if (s.path == TestScenePath) hasTest = true;
        }

        if (hasGame && hasTest)
        {
            Debug.Log("  [Build] Scene 이미 등록됨, 스킵");
            return;
        }

        var list = new System.Collections.Generic.List<EditorBuildSettingsScene>(scenes);
        if (!hasGame) list.Add(new EditorBuildSettingsScene(GameScenePath, true));
        if (!hasTest) list.Add(new EditorBuildSettingsScene(TestScenePath, true));
        EditorBuildSettings.scenes = list.ToArray();
        Debug.Log("  [Build] Scene 등록 완료");
    }

    // ━━━ 7. UI Canvas ━━━

    private static void CreateUICanvas(Scene scene)
    {
        // Canvas
        var canvasGo = new GameObject("Canvas");
        var canvas = canvasGo.AddComponent<Canvas>();
        canvas.renderMode = RenderMode.ScreenSpaceOverlay;
        canvasGo.AddComponent<CanvasScaler>();
        canvasGo.AddComponent<GraphicRaycaster>();

        // --- HUD Panel (좌상단) ---
        var hudGo = new GameObject("HUDPanel");
        hudGo.transform.SetParent(canvasGo.transform, false);
        var hudManager = hudGo.AddComponent<HUDManager>();

        var levelGo = CreateUIText(hudGo.transform, "LevelText", "Lv. 1",
            new Vector2(10, -10), new Vector2(120, 30), TextAnchor.UpperLeft);
        var hpBarGo = CreateUISlider(hudGo.transform, "HPBar",
            new Vector2(10, -40), new Vector2(200, 20), new Color(0.8f, 0.2f, 0.2f));
        var mpBarGo = CreateUISlider(hudGo.transform, "MPBar",
            new Vector2(10, -65), new Vector2(200, 20), new Color(0.2f, 0.4f, 0.9f));
        var expBarGo = CreateUISlider(hudGo.transform, "EXPBar",
            new Vector2(10, -90), new Vector2(200, 20), new Color(0.9f, 0.8f, 0.2f));

        // HUDManager SerializedField 연결
        var hudSO = new SerializedObject(hudManager);
        SetSliderRef(hudSO, "hpSlider", hpBarGo);
        SetSliderRef(hudSO, "mpSlider", mpBarGo);
        SetSliderRef(hudSO, "expSlider", expBarGo);
        SetTextRef(hudSO, "levelText", levelGo);
        SetTextRef(hudSO, "hpText", CreateUIText(hudGo.transform, "HPText", "100 / 100",
            new Vector2(215, -40), new Vector2(100, 20), TextAnchor.MiddleLeft));
        SetTextRef(hudSO, "mpText", CreateUIText(hudGo.transform, "MPText", "50 / 50",
            new Vector2(215, -65), new Vector2(100, 20), TextAnchor.MiddleLeft));
        SetTextRef(hudSO, "expText", CreateUIText(hudGo.transform, "EXPText", "0 / 100",
            new Vector2(215, -90), new Vector2(100, 20), TextAnchor.MiddleLeft));
        hudSO.ApplyModifiedPropertiesWithoutUndo();

        // --- Target Panel (상단 중앙) ---
        var targetGo = new GameObject("TargetPanel");
        targetGo.transform.SetParent(canvasGo.transform, false);
        var targetRT = targetGo.AddComponent<RectTransform>();
        targetRT.anchorMin = new Vector2(0.5f, 1f);
        targetRT.anchorMax = new Vector2(0.5f, 1f);
        targetRT.pivot = new Vector2(0.5f, 1f);
        targetRT.anchoredPosition = new Vector2(0, -10);
        targetRT.sizeDelta = new Vector2(300, 50);

        var combatUI = targetGo.AddComponent<CombatUI>();
        var targetNameGo = CreateUIText(targetGo.transform, "TargetName", "Target",
            new Vector2(0, 0), new Vector2(200, 25), TextAnchor.MiddleCenter);
        var targetHpGo = CreateUISlider(targetGo.transform, "TargetHPBar",
            new Vector2(0, -25), new Vector2(250, 15), new Color(0.8f, 0.2f, 0.2f));

        // DamageText prefab container
        var dmgParentGo = new GameObject("DamageTextPool");
        dmgParentGo.transform.SetParent(canvasGo.transform, false);
        var dmgParentRT = dmgParentGo.AddComponent<RectTransform>();
        dmgParentRT.anchorMin = Vector2.zero;
        dmgParentRT.anchorMax = Vector2.one;
        dmgParentRT.sizeDelta = Vector2.zero;

        // DamageText template (비활성 프리팹 역할)
        var dmgTextGo = new GameObject("DamageText");
        dmgTextGo.transform.SetParent(dmgParentGo.transform, false);
        var dmgText = dmgTextGo.AddComponent<Text>();
        dmgText.text = "0";
        dmgText.fontSize = 24;
        dmgText.fontStyle = FontStyle.Bold;
        dmgText.alignment = TextAnchor.MiddleCenter;
        dmgText.font = Resources.GetBuiltinResource<Font>("LegacyRuntime.ttf");
        var dmgRT = dmgTextGo.GetComponent<RectTransform>();
        dmgRT.sizeDelta = new Vector2(100, 30);
        dmgTextGo.SetActive(false);

        var combatSO = new SerializedObject(combatUI);
        var tpProp = combatSO.FindProperty("targetPanel");
        if (tpProp != null) tpProp.objectReferenceValue = targetGo;
        SetTextRef(combatSO, "targetNameText", targetNameGo);
        SetSliderRef(combatSO, "targetHpSlider", targetHpGo);
        var dmgPrefabProp = combatSO.FindProperty("damageTextPrefab");
        if (dmgPrefabProp != null) dmgPrefabProp.objectReferenceValue = dmgTextGo;
        var dmgParentProp = combatSO.FindProperty("damageTextParent");
        if (dmgParentProp != null) dmgParentProp.objectReferenceValue = dmgParentGo.transform;
        combatSO.ApplyModifiedPropertiesWithoutUndo();

        // --- Death Panel (전체화면) ---
        var deathGo = new GameObject("DeathPanel");
        deathGo.transform.SetParent(canvasGo.transform, false);
        var deathRT = deathGo.AddComponent<RectTransform>();
        deathRT.anchorMin = Vector2.zero;
        deathRT.anchorMax = Vector2.one;
        deathRT.sizeDelta = Vector2.zero;

        var deathBg = deathGo.AddComponent<Image>();
        deathBg.color = new Color(0, 0, 0, 0.6f);

        var deathTextGo = CreateUIText(deathGo.transform, "DeathText", "\xC0AC\xB9DD",
            new Vector2(0, 30), new Vector2(200, 60), TextAnchor.MiddleCenter);
        var deathTextRT = deathTextGo.GetComponent<RectTransform>();
        deathTextRT.anchorMin = new Vector2(0.5f, 0.5f);
        deathTextRT.anchorMax = new Vector2(0.5f, 0.5f);
        var dt = deathTextGo.GetComponent<Text>();
        if (dt != null) dt.fontSize = 48;

        var respawnBtnGo = new GameObject("RespawnButton");
        respawnBtnGo.transform.SetParent(deathGo.transform, false);
        var respawnRT = respawnBtnGo.AddComponent<RectTransform>();
        respawnRT.anchorMin = new Vector2(0.5f, 0.5f);
        respawnRT.anchorMax = new Vector2(0.5f, 0.5f);
        respawnRT.pivot = new Vector2(0.5f, 0.5f);
        respawnRT.anchoredPosition = new Vector2(0, -40);
        respawnRT.sizeDelta = new Vector2(160, 50);
        var respawnImg = respawnBtnGo.AddComponent<Image>();
        respawnImg.color = new Color(0.3f, 0.6f, 0.3f);
        var respawnBtn = respawnBtnGo.AddComponent<Button>();
        var btnTextGo = CreateUIText(respawnBtnGo.transform, "Text", "\xBD80\xD65C",
            Vector2.zero, new Vector2(160, 50), TextAnchor.MiddleCenter);
        var btnTextRT = btnTextGo.GetComponent<RectTransform>();
        btnTextRT.anchorMin = Vector2.zero;
        btnTextRT.anchorMax = Vector2.one;
        btnTextRT.sizeDelta = Vector2.zero;
        btnTextRT.anchoredPosition = Vector2.zero;

        var deathUI = deathGo.AddComponent<DeathUI>();
        var deathSO = new SerializedObject(deathUI);
        var dpProp = deathSO.FindProperty("deathPanel");
        if (dpProp != null) dpProp.objectReferenceValue = deathGo;
        var rbProp = deathSO.FindProperty("respawnButton");
        if (rbProp != null) rbProp.objectReferenceValue = respawnBtn;
        deathSO.ApplyModifiedPropertiesWithoutUndo();

        Debug.Log("  [UI] Canvas + HUD + Target + Death + DamageText 생성 완료");
    }

    // ━━━ UI 헬퍼 ━━━

    private static GameObject CreateUIText(Transform parent, string name, string text,
        Vector2 anchoredPos, Vector2 sizeDelta, TextAnchor alignment)
    {
        var go = new GameObject(name);
        go.transform.SetParent(parent, false);
        var rt = go.AddComponent<RectTransform>();
        rt.anchorMin = new Vector2(0, 1);
        rt.anchorMax = new Vector2(0, 1);
        rt.pivot = new Vector2(0, 1);
        rt.anchoredPosition = anchoredPos;
        rt.sizeDelta = sizeDelta;

        var t = go.AddComponent<Text>();
        t.text = text;
        t.fontSize = 14;
        t.color = Color.white;
        t.alignment = alignment;
        t.font = Resources.GetBuiltinResource<Font>("LegacyRuntime.ttf");

        return go;
    }

    private static GameObject CreateUISlider(Transform parent, string name,
        Vector2 anchoredPos, Vector2 sizeDelta, Color fillColor)
    {
        var go = new GameObject(name);
        go.transform.SetParent(parent, false);
        var rt = go.AddComponent<RectTransform>();
        rt.anchorMin = new Vector2(0, 1);
        rt.anchorMax = new Vector2(0, 1);
        rt.pivot = new Vector2(0, 1);
        rt.anchoredPosition = anchoredPos;
        rt.sizeDelta = sizeDelta;

        var slider = go.AddComponent<Slider>();
        slider.minValue = 0;
        slider.maxValue = 1;
        slider.value = 1;

        // Background
        var bgGo = new GameObject("Background");
        bgGo.transform.SetParent(go.transform, false);
        var bgRT = bgGo.AddComponent<RectTransform>();
        bgRT.anchorMin = Vector2.zero;
        bgRT.anchorMax = Vector2.one;
        bgRT.sizeDelta = Vector2.zero;
        var bgImg = bgGo.AddComponent<Image>();
        bgImg.color = new Color(0.15f, 0.15f, 0.15f, 0.8f);

        // Fill Area
        var fillAreaGo = new GameObject("Fill Area");
        fillAreaGo.transform.SetParent(go.transform, false);
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
        var fillImg = fillGo.AddComponent<Image>();
        fillImg.color = fillColor;

        slider.fillRect = fillRT;

        return go;
    }

    private static void SetSliderRef(SerializedObject so, string fieldName, GameObject sliderGo)
    {
        var prop = so.FindProperty(fieldName);
        if (prop != null && sliderGo != null)
            prop.objectReferenceValue = sliderGo.GetComponent<Slider>();
    }

    private static void SetTextRef(SerializedObject so, string fieldName, GameObject textGo)
    {
        var prop = so.FindProperty(fieldName);
        if (prop != null && textGo != null)
            prop.objectReferenceValue = textGo.GetComponent<Text>();
    }

    // ━━━ 유틸 ━━━

    private static GameObject CreateManagerObject(string name, System.Type componentType)
    {
        var go = new GameObject(name);
        go.AddComponent(componentType);
        return go;
    }

    /// <summary>
    /// private [SerializeField] 필드를 SerializedObject API로 연결
    /// </summary>
    private static void ConnectPrefabRef(
        GameObject go, System.Type componentType, string fieldName, GameObject prefab)
    {
        if (prefab == null)
        {
            Debug.LogWarning($"  [Ref] {go.name}.{fieldName} — Prefab이 null, 연결 건너뜀");
            return;
        }

        var component = go.GetComponent(componentType);
        if (component == null) return;

        var so = new SerializedObject(component);
        var prop = so.FindProperty(fieldName);
        if (prop != null)
        {
            prop.objectReferenceValue = prefab;
            so.ApplyModifiedPropertiesWithoutUndo();
            Debug.Log($"  [Ref] {go.name}.{fieldName} ← {prefab.name}");
        }
        else
        {
            Debug.LogWarning($"  [Ref] {go.name}에서 필드 '{fieldName}' 찾을 수 없음");
        }
    }
}
