// ━━━ ProjectSetup.cs ━━━
// Menu: "ECS Game > Setup All"
// 원클릭으로 Materials, Prefabs, Scenes, Build Settings 자동 구성
// 멱등성 보장 — 이미 존재하는 에셋은 스킵

using UnityEngine;
using UnityEditor;
using UnityEditor.Animations;
using UnityEditor.SceneManagement;
using UnityEngine.SceneManagement;
using UnityEngine.UI;
using UnityEngine.Rendering;
using System.IO;
using System.Linq;

public static class ProjectSetup
{
    // ━━━ 경로 상수 ━━━
    private const string MaterialsDir   = "Assets/Materials";
    private const string PrefabsDir     = "Assets/Prefabs";
    private const string ScenesDir      = "Assets/Scenes";

    private const string AnimControllersDir = "Assets/Art/AnimatorControllers";

    private const string LocalMatPath    = MaterialsDir + "/LocalPlayer.mat";
    private const string RemoteMatPath   = MaterialsDir + "/RemotePlayer.mat";
    private const string MonsterMatPath  = MaterialsDir + "/Monster.mat";
    private const string BossMatPath     = MaterialsDir + "/Boss.mat";
    private const string LocalPrefabPath   = PrefabsDir + "/LocalPlayer.prefab";
    private const string RemotePrefabPath  = PrefabsDir + "/RemotePlayer.prefab";
    private const string MonsterPrefabPath = PrefabsDir + "/Monster.prefab";
    private const string GameScenePath  = ScenesDir + "/GameScene.unity";
    private const string TestScenePath  = ScenesDir + "/TestScene.unity";

    // FBX 경로
    private const string PlayerFBXPath  = "Assets/Art/Characters/X Bot.fbx";
    private const string MonsterFBXPath = "Assets/Art/Characters/Zombiegirl W Kurniawan.fbx";
    private const string AnimControllerPath = AnimControllersDir + "/CharacterAnimator.controller";

    // 애니메이션 FBX 경로
    private const string IdleAnimPath    = "Assets/Art/Animations/Idle.fbx";
    private const string WalkAnimPath    = "Assets/Art/Animations/Walking.fbx";
    private const string AttackAnimPath  = "Assets/Art/Animations/Punching.fbx";
    private const string DeathAnimPath   = "Assets/Art/Animations/Death.fbx";

    // URP Lit 셰이더 이름
    private const string URPLitShader = "Universal Render Pipeline/Lit";

    [MenuItem("ECS Game/Setup All", priority = 1)]
    public static void SetupAll()
    {
        Debug.Log("━━━ [ProjectSetup] 시작 ━━━");

        CreateDirectories();
        ConfigureFBXImports();
        CreateMaterials();
        CreateAnimatorControllers();
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
        EnsureDirectory("Assets/Art");
        EnsureDirectory(AnimControllersDir);
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

    // ━━━ 1b. FBX Import 설정 ━━━

    private static void ConfigureFBXImports()
    {
        string[] fbxPaths = { PlayerFBXPath, MonsterFBXPath, IdleAnimPath, WalkAnimPath, AttackAnimPath, DeathAnimPath };

        foreach (var path in fbxPaths)
        {
            var importer = AssetImporter.GetAtPath(path) as ModelImporter;
            if (importer == null)
            {
                Debug.LogWarning($"  [FBX] {path} — 파일 없음, 스킵");
                continue;
            }

            if (importer.animationType != ModelImporterAnimationType.Human)
            {
                importer.animationType = ModelImporterAnimationType.Human;
                importer.SaveAndReimport();
                Debug.Log($"  [FBX] {path} → Humanoid 리깅 설정");
            }
            else
            {
                Debug.Log($"  [FBX] {path} — 이미 Humanoid, 스킵");
            }
        }
    }

    // ━━━ 1c. Animator Controllers ━━━

    private static void CreateAnimatorControllers()
    {
        if (AssetDatabase.LoadAssetAtPath<AnimatorController>(AnimControllerPath) != null)
        {
            Debug.Log("  [Animator] CharacterAnimator — 이미 존재, 스킵");
            return;
        }

        var controller = AnimatorController.CreateAnimatorControllerAtPath(AnimControllerPath);

        // ── animation.yaml 기반 파라미터 ──
        controller.AddParameter("Speed", AnimatorControllerParameterType.Float);
        controller.AddParameter("IsMoving", AnimatorControllerParameterType.Bool);
        controller.AddParameter("InCombat", AnimatorControllerParameterType.Bool);
        controller.AddParameter("IsGrounded", AnimatorControllerParameterType.Bool);
        controller.AddParameter("IsDead", AnimatorControllerParameterType.Bool);
        controller.AddParameter("Attack", AnimatorControllerParameterType.Trigger);
        controller.AddParameter("AttackIndex", AnimatorControllerParameterType.Int);
        controller.AddParameter("Dash", AnimatorControllerParameterType.Trigger);
        controller.AddParameter("Hit", AnimatorControllerParameterType.Trigger);
        controller.AddParameter("HitDirection", AnimatorControllerParameterType.Float);
        controller.AddParameter("SkillIndex", AnimatorControllerParameterType.Int);
        controller.AddParameter("Skill", AnimatorControllerParameterType.Trigger);

        var rootStateMachine = controller.layers[0].stateMachine;

        // 애니메이션 클립 로드
        var idleClip = LoadAnimationClip(IdleAnimPath);
        var walkClip = LoadAnimationClip(WalkAnimPath);
        var attackClip = LoadAnimationClip(AttackAnimPath);
        var deathClip = LoadAnimationClip(DeathAnimPath);

        // ── 기본 상태 ──
        var idleState = rootStateMachine.AddState("Idle");
        idleState.motion = idleClip;

        var walkState = rootStateMachine.AddState("Walk");
        walkState.motion = walkClip;
        walkState.speedParameterActive = true;
        walkState.speedParameter = "Speed";

        // ── 전투 대기 ──
        var combatIdleState = rootStateMachine.AddState("CombatIdle");
        combatIdleState.motion = idleClip;

        // ── 전투 이동 ──
        var combatWalkState = rootStateMachine.AddState("CombatWalk");
        combatWalkState.motion = walkClip;
        combatWalkState.speedParameterActive = true;
        combatWalkState.speedParameter = "Speed";

        // ── 공격 콤보 (4단) ──
        var attack1State = rootStateMachine.AddState("Attack1");
        attack1State.motion = attackClip;
        var attack2State = rootStateMachine.AddState("Attack2");
        attack2State.motion = attackClip;
        var attack3State = rootStateMachine.AddState("Attack3");
        attack3State.motion = attackClip;
        var attack4State = rootStateMachine.AddState("Attack4");
        attack4State.motion = attackClip;

        // ── 대시/회피 ──
        var dashState = rootStateMachine.AddState("Dash");
        dashState.motion = walkClip;

        // ── 피격 ──
        var hitState = rootStateMachine.AddState("HitReact");
        hitState.motion = idleClip;

        // ── 사망 ──
        var deathState = rootStateMachine.AddState("Death");
        deathState.motion = deathClip;

        // ── 스킬 시전 ──
        var skillState = rootStateMachine.AddState("SkillCast");
        skillState.motion = attackClip;

        rootStateMachine.defaultState = idleState;

        // ── 비전투 전환 ──
        var idleToWalk = idleState.AddTransition(walkState);
        idleToWalk.AddCondition(AnimatorConditionMode.Greater, 0.1f, "Speed");
        idleToWalk.hasExitTime = false;
        idleToWalk.duration = 0.15f;

        var walkToIdle = walkState.AddTransition(idleState);
        walkToIdle.AddCondition(AnimatorConditionMode.Less, 0.1f, "Speed");
        walkToIdle.hasExitTime = false;
        walkToIdle.duration = 0.15f;

        var idleToCombat = idleState.AddTransition(combatIdleState);
        idleToCombat.AddCondition(AnimatorConditionMode.If, 0, "InCombat");
        idleToCombat.hasExitTime = false;
        idleToCombat.duration = 0.15f;

        var walkToCombatWalk = walkState.AddTransition(combatWalkState);
        walkToCombatWalk.AddCondition(AnimatorConditionMode.If, 0, "InCombat");
        walkToCombatWalk.hasExitTime = false;
        walkToCombatWalk.duration = 0.15f;

        // ── 전투 상태 전환 ──
        var combatIdleToWalk = combatIdleState.AddTransition(combatWalkState);
        combatIdleToWalk.AddCondition(AnimatorConditionMode.Greater, 0.1f, "Speed");
        combatIdleToWalk.hasExitTime = false;
        combatIdleToWalk.duration = 0.08f;

        var combatWalkToIdle = combatWalkState.AddTransition(combatIdleState);
        combatWalkToIdle.AddCondition(AnimatorConditionMode.Less, 0.1f, "Speed");
        combatWalkToIdle.hasExitTime = false;
        combatWalkToIdle.duration = 0.08f;

        var combatToIdle = combatIdleState.AddTransition(idleState);
        combatToIdle.AddCondition(AnimatorConditionMode.IfNot, 0, "InCombat");
        combatToIdle.hasExitTime = false;
        combatToIdle.duration = 0.15f;

        var combatWalkToWalk = combatWalkState.AddTransition(walkState);
        combatWalkToWalk.AddCondition(AnimatorConditionMode.IfNot, 0, "InCombat");
        combatWalkToWalk.hasExitTime = false;
        combatWalkToWalk.duration = 0.15f;

        // ── 공격 콤보 체인 ──
        var anyToAttack1 = rootStateMachine.AddAnyStateTransition(attack1State);
        anyToAttack1.AddCondition(AnimatorConditionMode.If, 0, "Attack");
        anyToAttack1.AddCondition(AnimatorConditionMode.Equals, 0, "AttackIndex");
        anyToAttack1.hasExitTime = false;
        anyToAttack1.duration = 0.08f;

        var anyToAttack2 = rootStateMachine.AddAnyStateTransition(attack2State);
        anyToAttack2.AddCondition(AnimatorConditionMode.If, 0, "Attack");
        anyToAttack2.AddCondition(AnimatorConditionMode.Equals, 1, "AttackIndex");
        anyToAttack2.hasExitTime = false;
        anyToAttack2.duration = 0.08f;

        var anyToAttack3 = rootStateMachine.AddAnyStateTransition(attack3State);
        anyToAttack3.AddCondition(AnimatorConditionMode.If, 0, "Attack");
        anyToAttack3.AddCondition(AnimatorConditionMode.Equals, 2, "AttackIndex");
        anyToAttack3.hasExitTime = false;
        anyToAttack3.duration = 0.08f;

        var anyToAttack4 = rootStateMachine.AddAnyStateTransition(attack4State);
        anyToAttack4.AddCondition(AnimatorConditionMode.If, 0, "Attack");
        anyToAttack4.AddCondition(AnimatorConditionMode.Equals, 3, "AttackIndex");
        anyToAttack4.hasExitTime = false;
        anyToAttack4.duration = 0.08f;

        AnimatorState[] attackStates = { attack1State, attack2State, attack3State, attack4State };
        float[] exitTimes = { 0.9f, 0.9f, 0.85f, 0.85f };
        for (int i = 0; i < attackStates.Length; i++)
        {
            var toIdle = attackStates[i].AddTransition(combatIdleState);
            toIdle.hasExitTime = true;
            toIdle.exitTime = exitTimes[i];
            toIdle.duration = 0.15f;
        }

        // ── 대시 ──
        var anyToDash = rootStateMachine.AddAnyStateTransition(dashState);
        anyToDash.AddCondition(AnimatorConditionMode.If, 0, "Dash");
        anyToDash.hasExitTime = false;
        anyToDash.duration = 0.05f;

        var dashToIdle = dashState.AddTransition(combatIdleState);
        dashToIdle.hasExitTime = true;
        dashToIdle.exitTime = 0.9f;
        dashToIdle.duration = 0.15f;

        // ── 피격 ──
        var anyToHit = rootStateMachine.AddAnyStateTransition(hitState);
        anyToHit.AddCondition(AnimatorConditionMode.If, 0, "Hit");
        anyToHit.hasExitTime = false;
        anyToHit.duration = 0.05f;

        var hitToIdle = hitState.AddTransition(combatIdleState);
        hitToIdle.hasExitTime = true;
        hitToIdle.exitTime = 0.8f;
        hitToIdle.duration = 0.15f;

        // ── 스킬 시전 ──
        var anyToSkill = rootStateMachine.AddAnyStateTransition(skillState);
        anyToSkill.AddCondition(AnimatorConditionMode.If, 0, "Skill");
        anyToSkill.hasExitTime = false;
        anyToSkill.duration = 0.08f;

        var skillToIdle = skillState.AddTransition(combatIdleState);
        skillToIdle.hasExitTime = true;
        skillToIdle.exitTime = 0.9f;
        skillToIdle.duration = 0.15f;

        // ── 사망 (최고 우선순위) ──
        var anyToDeath = rootStateMachine.AddAnyStateTransition(deathState);
        anyToDeath.AddCondition(AnimatorConditionMode.If, 0, "IsDead");
        anyToDeath.hasExitTime = false;
        anyToDeath.duration = 0.15f;

        EditorUtility.SetDirty(controller);
        Debug.Log("  [Animator] CharacterAnimator.controller 생성 완료 (animation.yaml 기반 확장)");
    }

    private static AnimationClip LoadAnimationClip(string fbxPath)
    {
        var assets = AssetDatabase.LoadAllAssetsAtPath(fbxPath);
        if (assets == null) return null;

        return assets
            .OfType<AnimationClip>()
            .FirstOrDefault(c => !c.name.StartsWith("__preview__"));
    }

    // ━━━ 2. Materials ━━━

    private static void CreateMaterials()
    {
        CreateMaterial(LocalMatPath,  new Color(0.2f, 0.4f, 1.0f), "LocalPlayer (파랑)");
        CreateMaterial(RemoteMatPath, new Color(0.2f, 0.8f, 0.3f), "RemotePlayer (초록)");
        CreateMaterial(MonsterMatPath, new Color(0.9f, 0.2f, 0.2f), "Monster (빨강)");
        CreateMaterial(BossMatPath, new Color(0.3f, 0.05f, 0.05f), "Boss (다크 레드)");
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
            "LocalPlayer",
            PlayerFBXPath
        );

        CreatePlayerPrefab(
            RemotePrefabPath,
            RemoteMatPath,
            typeof(RemotePlayer),
            "RemotePlayer",
            PlayerFBXPath
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

        var fbxAsset = AssetDatabase.LoadAssetAtPath<GameObject>(MonsterFBXPath);

        GameObject go;
        if (fbxAsset != null)
        {
            go = (GameObject)PrefabUtility.InstantiatePrefab(fbxAsset);
            go.name = "Monster";

            // CapsuleCollider 수동 추가
            var col = go.AddComponent<CapsuleCollider>();
            col.center = new Vector3(0f, 0.9f, 0f);
            col.height = 1.8f;
            col.radius = 0.3f;

            // Animator Controller 할당
            var animator = go.GetComponent<Animator>();
            if (animator == null) animator = go.AddComponent<Animator>();
            var animController = AssetDatabase.LoadAssetAtPath<AnimatorController>(AnimControllerPath);
            if (animController != null) animator.runtimeAnimatorController = animController;

            // Material 적용
            var mat = AssetDatabase.LoadAssetAtPath<Material>(MonsterMatPath);
            if (mat != null)
            {
                foreach (var renderer in go.GetComponentsInChildren<Renderer>())
                    renderer.sharedMaterial = mat;
            }

            Debug.Log("  [Prefab] Monster (FBX: Zombiegirl) 생성 완료");
        }
        else
        {
            go = GameObject.CreatePrimitive(PrimitiveType.Cube);
            go.name = "Monster";
            go.transform.localScale = new Vector3(0.8f, 0.8f, 0.8f);

            var mat = AssetDatabase.LoadAssetAtPath<Material>(MonsterMatPath);
            if (mat != null)
                go.GetComponent<MeshRenderer>().sharedMaterial = mat;

            Debug.Log("  [Prefab] Monster (프리미티브 폴백) 생성 완료");
        }

        go.AddComponent<MonsterEntity>();

        PrefabUtility.SaveAsPrefabAsset(go, MonsterPrefabPath);
        Object.DestroyImmediate(go);
    }

    private static void CreatePlayerPrefab(
        string prefabPath, string matPath, System.Type componentType, string label, string fbxPath)
    {
        if (AssetDatabase.LoadAssetAtPath<GameObject>(prefabPath) != null)
        {
            Debug.Log($"  [Prefab] {label} — 이미 존재, 스킵");
            return;
        }

        var fbxAsset = AssetDatabase.LoadAssetAtPath<GameObject>(fbxPath);

        GameObject go;
        if (fbxAsset != null)
        {
            go = (GameObject)PrefabUtility.InstantiatePrefab(fbxAsset);
            go.name = label;

            // CapsuleCollider 수동 추가
            var col = go.AddComponent<CapsuleCollider>();
            col.center = new Vector3(0f, 0.9f, 0f);
            col.height = 1.8f;
            col.radius = 0.3f;

            // Animator Controller 할당
            var animator = go.GetComponent<Animator>();
            if (animator == null) animator = go.AddComponent<Animator>();
            var animController = AssetDatabase.LoadAssetAtPath<AnimatorController>(AnimControllerPath);
            if (animController != null) animator.runtimeAnimatorController = animController;

            // Material 적용
            var mat = AssetDatabase.LoadAssetAtPath<Material>(matPath);
            if (mat != null)
            {
                foreach (var renderer in go.GetComponentsInChildren<Renderer>())
                    renderer.sharedMaterial = mat;
            }

            Debug.Log($"  [Prefab] {label} (FBX) 생성 완료");
        }
        else
        {
            // FBX 없으면 기존 프리미티브 폴백
            go = GameObject.CreatePrimitive(PrimitiveType.Capsule);
            go.name = label;

            var mat = AssetDatabase.LoadAssetAtPath<Material>(matPath);
            if (mat != null)
                go.GetComponent<MeshRenderer>().sharedMaterial = mat;

            Debug.Log($"  [Prefab] {label} (프리미티브 폴백) 생성 완료");
        }

        // 컴포넌트 부착
        go.AddComponent(componentType);

        // Prefab 저장
        PrefabUtility.SaveAsPrefabAsset(go, prefabPath);
        Object.DestroyImmediate(go);
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

        // Floor material — bright green
        var floorRenderer = floor.GetComponent<MeshRenderer>();
        if (floorRenderer != null)
        {
            var floorShader = Shader.Find(URPLitShader) ?? Shader.Find("Standard");
            var floorMat = new Material(floorShader);
            floorMat.SetColor("_BaseColor", new Color(0.35f, 0.65f, 0.25f));
            floorRenderer.sharedMaterial = floorMat;
        }

        // --- Environment (art_style.yaml lighting.time_lighting.day) ---
        RenderSettings.fog = true;
        RenderSettings.fogMode = FogMode.Linear;
        RenderSettings.fogStartDistance = 80f;
        RenderSettings.fogEndDistance = 200f;
        RenderSettings.fogColor = new Color(0.784f, 0.847f, 0.910f); // #C8D8E8
        RenderSettings.ambientMode = UnityEngine.Rendering.AmbientMode.Trilight;
        RenderSettings.ambientSkyColor = new Color(0.529f, 0.808f, 0.922f);     // #87CEEB sky
        RenderSettings.ambientEquatorColor = new Color(0.871f, 0.722f, 0.529f);  // #DEB887 equator
        RenderSettings.ambientGroundColor = new Color(0.545f, 0.451f, 0.333f);   // #8B7355 ground

        // --- Directional Light (art_style.yaml directional_light) ---
        var lightGo = new GameObject("Directional Light");
        var light = lightGo.AddComponent<Light>();
        light.type = LightType.Directional;
        light.color = new Color(1f, 0.980f, 0.804f);  // #FFFACD (day sun_color)
        light.intensity = 1.2f;
        light.shadows = LightShadows.Soft;
        light.shadowResolution = UnityEngine.Rendering.LightShadowResolution.High;
        lightGo.transform.rotation = Quaternion.Euler(50f, -30f, 0f);

        // --- Post-Processing Volume (art_style.yaml post_processing.global_volume) ---
        SetupPostProcessingVolume();

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
        var skillManagerGo = CreateManagerObject("SkillManager", typeof(SkillManager));
        var inventoryManagerGo = CreateManagerObject("InventoryManager", typeof(InventoryManager));
        var partyManagerGo = CreateManagerObject("PartyManager", typeof(PartyManager));
        var buffManagerGo = CreateManagerObject("BuffManager", typeof(BuffManager));
        var questManagerGo = CreateManagerObject("QuestManager", typeof(QuestManager));
        var chatManagerGo = CreateManagerObject("ChatManager", typeof(ChatManager));
        var shopManagerGo = CreateManagerObject("ShopManager", typeof(ShopManager));
        var bossManagerGo = CreateManagerObject("BossManager", typeof(BossManager));
        var hitVFXManagerGo = CreateManagerObject("HitVFXManager", typeof(HitVFXManager));
        var sceneFlowManagerGo = CreateManagerObject("SceneFlowManager", typeof(SceneFlowManager));

        // --- GameBootstrap (auto-connect on Play) ---
        var bootstrapGo = new GameObject("GameBootstrap");
        bootstrapGo.AddComponent<GameBootstrap>();

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

    /// <summary>
    /// art_style.yaml post_processing.global_volume 기반 URP Volume 생성
    /// Bloom, Tonemapping, ColorAdjustments, Vignette
    /// </summary>
    private static void SetupPostProcessingVolume()
    {
        var volumeGo = new GameObject("GlobalVolume_PostProcess");
        var volume = volumeGo.AddComponent<Volume>();
        volume.isGlobal = true;
        volume.priority = 0;

        var profile = ScriptableObject.CreateInstance<VolumeProfile>();

        // Bloom (intensity 0.3, threshold 0.9, scatter 0.7)
        AddVolumeOverride(profile, "UnityEngine.Rendering.Universal.Bloom",
            ("intensity", 0.3f), ("threshold", 0.9f), ("scatter", 0.7f));

        // Tonemapping (ACES = 2)
        AddVolumeOverride(profile, "UnityEngine.Rendering.Universal.Tonemapping",
            ("mode", 2));  // TonemappingMode.ACES = 2

        // Color Adjustments (postExposure 0, contrast 10, saturation 10)
        AddVolumeOverride(profile, "UnityEngine.Rendering.Universal.ColorAdjustments",
            ("postExposure", 0f), ("contrast", 10f), ("saturation", 10f));

        // Vignette (intensity 0.2, smoothness 0.5)
        AddVolumeOverride(profile, "UnityEngine.Rendering.Universal.Vignette",
            ("intensity", 0.2f), ("smoothness", 0.5f));

        // Save profile as asset
        const string profilePath = "Assets/Settings/GlobalVolumeProfile.asset";
        AssetDatabase.CreateAsset(profile, profilePath);
        volume.sharedProfile = profile;

        Debug.Log("  [PostProcess] Global Volume 생성 완료");
    }

    /// <summary>
    /// Reflection 기반 VolumeComponent 추가 — URP 어셈블리 직접 참조 없이 동적 설정
    /// </summary>
    private static void AddVolumeOverride(VolumeProfile profile, string typeName,
        params (string field, object value)[] overrides)
    {
        var type = System.Type.GetType(typeName + ", Unity.RenderPipelines.Universal.Runtime");
        if (type == null)
        {
            Debug.LogWarning($"  [PostProcess] Type not found: {typeName}");
            return;
        }

        var component = (VolumeComponent)ScriptableObject.CreateInstance(type);
        component.active = true;

        foreach (var (field, value) in overrides)
        {
            var fieldInfo = type.GetField(field,
                System.Reflection.BindingFlags.Public | System.Reflection.BindingFlags.Instance);
            if (fieldInfo == null) continue;

            // VolumeParameter의 실제 값 설정 — overrideState + value
            var param = fieldInfo.GetValue(component);
            if (param == null) continue;

            var paramType = param.GetType();

            // overrideState = true
            var overrideProp = paramType.GetProperty("overrideState");
            overrideProp?.SetValue(param, true);

            // value 설정
            var valueProp = paramType.GetProperty("value");
            if (valueProp != null)
            {
                // Enum 타입 (TonemappingMode 등)은 int→enum 변환 필요
                if (valueProp.PropertyType.IsEnum && value is int intVal)
                    valueProp.SetValue(param, System.Enum.ToObject(valueProp.PropertyType, intVal));
                else if (value is float f && valueProp.PropertyType == typeof(float))
                    valueProp.SetValue(param, f);
                else
                    valueProp.SetValue(param, value);
            }
        }

        profile.components.Add(component);
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
        // Canvas (ui.yaml global 스펙: 1920x1080 기준)
        var canvasGo = new GameObject("Canvas_HUD");
        var canvas = canvasGo.AddComponent<Canvas>();
        canvas.renderMode = RenderMode.ScreenSpaceOverlay;
        canvas.sortingOrder = 0;
        var scaler = canvasGo.AddComponent<CanvasScaler>();
        scaler.uiScaleMode = CanvasScaler.ScaleMode.ScaleWithScreenSize;
        scaler.referenceResolution = new Vector2(1920, 1080);
        scaler.matchWidthOrHeight = 0.5f;
        canvasGo.AddComponent<GraphicRaycaster>();

        // --- HUD Panel (좌상단, ui.yaml player_info 스펙) ---
        var hudGo = new GameObject("HUDPanel");
        hudGo.transform.SetParent(canvasGo.transform, false);
        var hudRT = hudGo.AddComponent<RectTransform>();
        hudRT.anchorMin = new Vector2(0, 1);
        hudRT.anchorMax = new Vector2(0, 1);
        hudRT.pivot = new Vector2(0, 1);
        hudRT.anchoredPosition = new Vector2(20, -20);
        hudRT.sizeDelta = new Vector2(300, 100);
        var hudBg = hudGo.AddComponent<Image>();
        hudBg.color = new Color(0, 0, 0, 0.53f); // #00000088

        var hudManager = hudGo.AddComponent<HUDManager>();

        // Name (좌상단 80, -10)
        var nameGo = CreateUIText(hudGo.transform, "NameText", "Player",
            new Vector2(80, -10), new Vector2(150, 20), TextAnchor.MiddleLeft);
        var nameComp = nameGo.GetComponent<Text>();
        if (nameComp != null) { nameComp.fontStyle = FontStyle.Bold; nameComp.fontSize = 14; }

        // Level (230, -10)
        var levelGo = CreateUIText(hudGo.transform, "LevelText", "Lv.1",
            new Vector2(230, -10), new Vector2(50, 20), TextAnchor.MiddleLeft);
        var levelComp = levelGo.GetComponent<Text>();
        if (levelComp != null) { levelComp.fontStyle = FontStyle.Bold; levelComp.fontSize = 14;
            levelComp.color = new Color(1f, 0.843f, 0f); } // #FFD700

        // HP Bar (80, -35, 200x16) — #E74C3C
        var hpBarGo = CreateUISlider(hudGo.transform, "HPBar",
            new Vector2(80, -35), new Vector2(200, 16), new Color(0.906f, 0.298f, 0.235f));
        // HP Text overlay
        var hpTextGo = CreateUIText(hpBarGo.transform, "HPText", "100/100",
            Vector2.zero, Vector2.zero, TextAnchor.MiddleCenter);
        var hpTextRT = hpTextGo.GetComponent<RectTransform>();
        hpTextRT.anchorMin = Vector2.zero; hpTextRT.anchorMax = Vector2.one;
        hpTextRT.sizeDelta = Vector2.zero; hpTextRT.anchoredPosition = Vector2.zero;
        var hpTextComp = hpTextGo.GetComponent<Text>();
        if (hpTextComp != null) hpTextComp.fontSize = 10;

        // MP Bar (80, -55, 200x14) — #3498DB
        var mpBarGo = CreateUISlider(hudGo.transform, "MPBar",
            new Vector2(80, -55), new Vector2(200, 14), new Color(0.204f, 0.596f, 0.859f));
        var mpTextGo = CreateUIText(mpBarGo.transform, "MPText", "50/50",
            Vector2.zero, Vector2.zero, TextAnchor.MiddleCenter);
        var mpTextRT = mpTextGo.GetComponent<RectTransform>();
        mpTextRT.anchorMin = Vector2.zero; mpTextRT.anchorMax = Vector2.one;
        mpTextRT.sizeDelta = Vector2.zero; mpTextRT.anchoredPosition = Vector2.zero;
        var mpTextComp = mpTextGo.GetComponent<Text>();
        if (mpTextComp != null) mpTextComp.fontSize = 10;

        // EXP Bar (80, -73, 200x8) — #F1C40F
        var expBarGo = CreateUISlider(hudGo.transform, "EXPBar",
            new Vector2(80, -73), new Vector2(200, 8), new Color(0.945f, 0.769f, 0.059f));

        // HUDManager SerializedField 연결
        var hudSO = new SerializedObject(hudManager);
        SetSliderRef(hudSO, "hpSlider", hpBarGo);
        SetSliderRef(hudSO, "mpSlider", mpBarGo);
        SetSliderRef(hudSO, "expSlider", expBarGo);
        SetTextRef(hudSO, "levelText", levelGo);
        SetTextRef(hudSO, "nameText", nameGo);
        SetTextRef(hudSO, "hpText", hpTextGo);
        SetTextRef(hudSO, "mpText", mpTextGo);
        hudSO.ApplyModifiedPropertiesWithoutUndo();

        // --- Target Panel (상단 중앙, ui.yaml target_info: 350x70) ---
        var targetGo = new GameObject("TargetPanel");
        targetGo.transform.SetParent(canvasGo.transform, false);
        var targetRT = targetGo.AddComponent<RectTransform>();
        targetRT.anchorMin = new Vector2(0.5f, 1f);
        targetRT.anchorMax = new Vector2(0.5f, 1f);
        targetRT.pivot = new Vector2(0.5f, 1f);
        targetRT.anchoredPosition = new Vector2(0, -20);
        targetRT.sizeDelta = new Vector2(350, 70);

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

        // --- Skill Bar (하단 중앙, ui.yaml skill_bar: 700x80) ---
        var skillBarGo = new GameObject("SkillBarPanel");
        skillBarGo.transform.SetParent(canvasGo.transform, false);
        var skillBarRT = skillBarGo.AddComponent<RectTransform>();
        skillBarRT.anchorMin = new Vector2(0.5f, 0f);
        skillBarRT.anchorMax = new Vector2(0.5f, 0f);
        skillBarRT.pivot = new Vector2(0.5f, 0f);
        skillBarRT.anchoredPosition = new Vector2(0, 20);
        skillBarRT.sizeDelta = new Vector2(700, 80);

        var skillBarUI = skillBarGo.AddComponent<SkillBarUI>();
        var slotNameTexts = new Text[4];
        var slotKeyTexts = new Text[4];
        var cooldownOverlays = new Image[4];

        for (int i = 0; i < 4; i++)
        {
            float xOff = -150 + i * 100;
            var slotGo = new GameObject($"Slot{i + 1}");
            slotGo.transform.SetParent(skillBarGo.transform, false);
            var slotRT = slotGo.AddComponent<RectTransform>();
            slotRT.anchorMin = new Vector2(0.5f, 0.5f);
            slotRT.anchorMax = new Vector2(0.5f, 0.5f);
            slotRT.anchoredPosition = new Vector2(xOff, 0);
            slotRT.sizeDelta = new Vector2(80, 50);
            var slotBg = slotGo.AddComponent<Image>();
            slotBg.color = new Color(0.2f, 0.2f, 0.2f, 0.8f);

            var keyGo = CreateUIText(slotGo.transform, "Key", $"{i + 1}",
                new Vector2(2, -2), new Vector2(20, 16), TextAnchor.UpperLeft);
            slotKeyTexts[i] = keyGo.GetComponent<Text>();

            var nameGo = CreateUIText(slotGo.transform, "Name", "",
                new Vector2(0, -18), new Vector2(76, 16), TextAnchor.MiddleCenter);
            slotNameTexts[i] = nameGo.GetComponent<Text>();

            var cdGo = new GameObject("Cooldown");
            cdGo.transform.SetParent(slotGo.transform, false);
            var cdRT = cdGo.AddComponent<RectTransform>();
            cdRT.anchorMin = Vector2.zero;
            cdRT.anchorMax = Vector2.one;
            cdRT.sizeDelta = Vector2.zero;
            var cdImg = cdGo.AddComponent<Image>();
            cdImg.color = new Color(0, 0, 0, 0.6f);
            cdImg.type = Image.Type.Filled;
            cdImg.fillMethod = Image.FillMethod.Vertical;
            cdImg.fillAmount = 0f;
            cdGo.SetActive(false);
            cooldownOverlays[i] = cdImg;
        }

        var skillBarSO = new SerializedObject(skillBarUI);
        SetArrayRef(skillBarSO, "slotNameTexts", slotNameTexts);
        SetArrayRef(skillBarSO, "slotKeyTexts", slotKeyTexts);
        SetImageArrayRef(skillBarSO, "cooldownOverlays", cooldownOverlays);
        skillBarSO.ApplyModifiedPropertiesWithoutUndo();

        // --- Inventory Panel (우측, I키 토글) ---
        var invPanelGo = new GameObject("InventoryPanel");
        invPanelGo.transform.SetParent(canvasGo.transform, false);
        var invPanelRT = invPanelGo.AddComponent<RectTransform>();
        invPanelRT.anchorMin = new Vector2(1f, 0f);
        invPanelRT.anchorMax = new Vector2(1f, 1f);
        invPanelRT.pivot = new Vector2(1f, 0.5f);
        invPanelRT.anchoredPosition = new Vector2(-10, 0);
        invPanelRT.sizeDelta = new Vector2(250, 0);
        var invBg = invPanelGo.AddComponent<Image>();
        invBg.color = new Color(0.1f, 0.1f, 0.15f, 0.85f);

        var invUI = invPanelGo.AddComponent<InventoryUI>();
        var invCountGo = CreateUIText(invPanelGo.transform, "ItemCount", "Items: 0",
            new Vector2(10, -10), new Vector2(200, 25), TextAnchor.UpperLeft);

        var invListGo = new GameObject("ItemList");
        invListGo.transform.SetParent(invPanelGo.transform, false);
        var invListRT = invListGo.AddComponent<RectTransform>();
        invListRT.anchorMin = new Vector2(0, 0);
        invListRT.anchorMax = new Vector2(1, 1);
        invListRT.offsetMin = new Vector2(5, 5);
        invListRT.offsetMax = new Vector2(-5, -40);

        var invTemplate = CreateUIText(invListGo.transform, "ItemTemplate", "[0] Item#0 x1",
            new Vector2(0, 0), new Vector2(230, 25), TextAnchor.MiddleLeft);
        invTemplate.SetActive(false);

        var invSO = new SerializedObject(invUI);
        var invPanelProp = invSO.FindProperty("inventoryPanel");
        if (invPanelProp != null) invPanelProp.objectReferenceValue = invPanelGo;
        var invListProp = invSO.FindProperty("itemListParent");
        if (invListProp != null) invListProp.objectReferenceValue = invListGo.transform;
        var invTemplateProp = invSO.FindProperty("itemSlotTemplate");
        if (invTemplateProp != null) invTemplateProp.objectReferenceValue = invTemplate;
        SetTextRef(invSO, "itemCountText", invCountGo);
        invSO.ApplyModifiedPropertiesWithoutUndo();

        // --- Party Panel (좌측, P키 토글) ---
        var partyPanelGo = new GameObject("PartyPanel");
        partyPanelGo.transform.SetParent(canvasGo.transform, false);
        var partyPanelRT = partyPanelGo.AddComponent<RectTransform>();
        partyPanelRT.anchorMin = new Vector2(0f, 0.3f);
        partyPanelRT.anchorMax = new Vector2(0f, 0.7f);
        partyPanelRT.pivot = new Vector2(0f, 0.5f);
        partyPanelRT.anchoredPosition = new Vector2(10, 0);
        partyPanelRT.sizeDelta = new Vector2(200, 0);
        var partyBg = partyPanelGo.AddComponent<Image>();
        partyBg.color = new Color(0.1f, 0.12f, 0.15f, 0.85f);

        var partyUI = partyPanelGo.AddComponent<PartyUI>();
        var partyStatusGo = CreateUIText(partyPanelGo.transform, "PartyStatus", "No Party",
            new Vector2(10, -10), new Vector2(180, 25), TextAnchor.UpperLeft);

        var memberListGo = new GameObject("MemberList");
        memberListGo.transform.SetParent(partyPanelGo.transform, false);
        var memberListRT = memberListGo.AddComponent<RectTransform>();
        memberListRT.anchorMin = new Vector2(0, 0);
        memberListRT.anchorMax = new Vector2(1, 1);
        memberListRT.offsetMin = new Vector2(5, 40);
        memberListRT.offsetMax = new Vector2(-5, -40);

        var memberTemplate = CreateUIText(memberListGo.transform, "MemberTemplate", "Entity#0 Lv.1",
            new Vector2(0, 0), new Vector2(180, 22), TextAnchor.MiddleLeft);
        memberTemplate.SetActive(false);

        var createBtnGo = new GameObject("CreateButton");
        createBtnGo.transform.SetParent(partyPanelGo.transform, false);
        var createBtnRT = createBtnGo.AddComponent<RectTransform>();
        createBtnRT.anchorMin = new Vector2(0, 0);
        createBtnRT.anchorMax = new Vector2(0.5f, 0);
        createBtnRT.pivot = new Vector2(0.5f, 0);
        createBtnRT.anchoredPosition = new Vector2(0, 5);
        createBtnRT.sizeDelta = new Vector2(0, 30);
        createBtnGo.AddComponent<Image>().color = new Color(0.3f, 0.5f, 0.3f);
        var createBtn = createBtnGo.AddComponent<Button>();
        var createTxt = CreateUIText(createBtnGo.transform, "Text", "Create",
            Vector2.zero, Vector2.zero, TextAnchor.MiddleCenter);
        var createTxtRT = createTxt.GetComponent<RectTransform>();
        createTxtRT.anchorMin = Vector2.zero; createTxtRT.anchorMax = Vector2.one;
        createTxtRT.sizeDelta = Vector2.zero;

        var leaveBtnGo = new GameObject("LeaveButton");
        leaveBtnGo.transform.SetParent(partyPanelGo.transform, false);
        var leaveBtnRT = leaveBtnGo.AddComponent<RectTransform>();
        leaveBtnRT.anchorMin = new Vector2(0.5f, 0);
        leaveBtnRT.anchorMax = new Vector2(1, 0);
        leaveBtnRT.pivot = new Vector2(0.5f, 0);
        leaveBtnRT.anchoredPosition = new Vector2(0, 5);
        leaveBtnRT.sizeDelta = new Vector2(0, 30);
        leaveBtnGo.AddComponent<Image>().color = new Color(0.5f, 0.3f, 0.3f);
        var leaveBtn = leaveBtnGo.AddComponent<Button>();
        var leaveTxt = CreateUIText(leaveBtnGo.transform, "Text", "Leave",
            Vector2.zero, Vector2.zero, TextAnchor.MiddleCenter);
        var leaveTxtRT = leaveTxt.GetComponent<RectTransform>();
        leaveTxtRT.anchorMin = Vector2.zero; leaveTxtRT.anchorMax = Vector2.one;
        leaveTxtRT.sizeDelta = Vector2.zero;

        var partySO = new SerializedObject(partyUI);
        var partyPanelProp = partySO.FindProperty("partyPanel");
        if (partyPanelProp != null) partyPanelProp.objectReferenceValue = partyPanelGo;
        SetTextRef(partySO, "partyStatusText", partyStatusGo);
        var memberListProp = partySO.FindProperty("memberListParent");
        if (memberListProp != null) memberListProp.objectReferenceValue = memberListGo.transform;
        var memberTemplateProp = partySO.FindProperty("memberTemplate");
        if (memberTemplateProp != null) memberTemplateProp.objectReferenceValue = memberTemplate;
        var createBtnProp = partySO.FindProperty("createButton");
        if (createBtnProp != null) createBtnProp.objectReferenceValue = createBtn;
        var leaveBtnProp = partySO.FindProperty("leaveButton");
        if (leaveBtnProp != null) leaveBtnProp.objectReferenceValue = leaveBtn;
        partySO.ApplyModifiedPropertiesWithoutUndo();

        // --- Buff Icons (좌상단, player_info 아래, ui.yaml buff_bar: [20, -130]) ---
        var buffPanelGo = new GameObject("BuffPanel");
        buffPanelGo.transform.SetParent(canvasGo.transform, false);
        var buffPanelRT = buffPanelGo.AddComponent<RectTransform>();
        buffPanelRT.anchorMin = new Vector2(0f, 1f);
        buffPanelRT.anchorMax = new Vector2(0f, 1f);
        buffPanelRT.pivot = new Vector2(0f, 1f);
        buffPanelRT.anchoredPosition = new Vector2(20, -130);
        buffPanelRT.sizeDelta = new Vector2(400, 30);

        var buffUI = buffPanelGo.AddComponent<BuffUI>();

        var buffTemplate = new GameObject("BuffTemplate");
        buffTemplate.transform.SetParent(buffPanelGo.transform, false);
        var buffTemplateRT = buffTemplate.AddComponent<RectTransform>();
        buffTemplateRT.sizeDelta = new Vector2(50, 50);
        var buffTemplateBg = buffTemplate.AddComponent<Image>();
        buffTemplateBg.color = new Color(0.3f, 0.2f, 0.5f, 0.8f);
        var buffTemplateText = CreateUIText(buffTemplate.transform, "Text", "B0\n0s",
            new Vector2(0, 0), new Vector2(50, 50), TextAnchor.MiddleCenter);
        var bttRT = buffTemplateText.GetComponent<RectTransform>();
        bttRT.anchorMin = Vector2.zero; bttRT.anchorMax = Vector2.one;
        bttRT.sizeDelta = Vector2.zero; bttRT.anchoredPosition = Vector2.zero;
        var btt = buffTemplateText.GetComponent<Text>();
        if (btt != null) btt.fontSize = 11;
        buffTemplate.SetActive(false);

        var buffSO = new SerializedObject(buffUI);
        var buffParentProp = buffSO.FindProperty("buffIconParent");
        if (buffParentProp != null) buffParentProp.objectReferenceValue = buffPanelGo.transform;
        var buffTemplateProp = buffSO.FindProperty("buffIconTemplate");
        if (buffTemplateProp != null) buffTemplateProp.objectReferenceValue = buffTemplate;
        buffSO.ApplyModifiedPropertiesWithoutUndo();

        // --- Quest Panel (우측, Q키 토글) ---
        var questPanelGo = new GameObject("QuestPanel");
        questPanelGo.transform.SetParent(canvasGo.transform, false);
        var questPanelRT = questPanelGo.AddComponent<RectTransform>();
        questPanelRT.anchorMin = new Vector2(1f, 0.3f);
        questPanelRT.anchorMax = new Vector2(1f, 0.7f);
        questPanelRT.pivot = new Vector2(1f, 0.5f);
        questPanelRT.anchoredPosition = new Vector2(-10, 0);
        questPanelRT.sizeDelta = new Vector2(280, 0);
        var questBg = questPanelGo.AddComponent<Image>();
        questBg.color = new Color(0.12f, 0.1f, 0.1f, 0.85f);

        var questUI = questPanelGo.AddComponent<QuestUI>();
        var questCountGo = CreateUIText(questPanelGo.transform, "QuestCount", "Quests: 0",
            new Vector2(10, -10), new Vector2(200, 25), TextAnchor.UpperLeft);

        var questListGo = new GameObject("QuestList");
        questListGo.transform.SetParent(questPanelGo.transform, false);
        var questListRT = questListGo.AddComponent<RectTransform>();
        questListRT.anchorMin = new Vector2(0, 0);
        questListRT.anchorMax = new Vector2(1, 1);
        questListRT.offsetMin = new Vector2(5, 5);
        questListRT.offsetMax = new Vector2(-5, -40);

        var questTemplate = CreateUIText(questListGo.transform, "QuestTemplate", "[???] Quest#0",
            new Vector2(0, 0), new Vector2(260, 25), TextAnchor.MiddleLeft);
        questTemplate.SetActive(false);

        var questSO = new SerializedObject(questUI);
        var questPanelProp = questSO.FindProperty("questPanel");
        if (questPanelProp != null) questPanelProp.objectReferenceValue = questPanelGo;
        var questListProp = questSO.FindProperty("questListParent");
        if (questListProp != null) questListProp.objectReferenceValue = questListGo.transform;
        var questTemplateProp = questSO.FindProperty("questEntryTemplate");
        if (questTemplateProp != null) questTemplateProp.objectReferenceValue = questTemplate;
        SetTextRef(questSO, "questCountText", questCountGo);
        questSO.ApplyModifiedPropertiesWithoutUndo();

        // --- Keybind Guide (화면 중앙 왼쪽) ---
        var guidePanelGo = new GameObject("KeybindGuidePanel");
        guidePanelGo.transform.SetParent(canvasGo.transform, false);
        var guidePanelRT = guidePanelGo.AddComponent<RectTransform>();
        guidePanelRT.anchorMin = new Vector2(0f, 0.2f);
        guidePanelRT.anchorMax = new Vector2(0f, 0.8f);
        guidePanelRT.pivot = new Vector2(0f, 0.5f);
        guidePanelRT.anchoredPosition = new Vector2(20, 0);
        guidePanelRT.sizeDelta = new Vector2(260, 0);
        var guideBg = guidePanelGo.AddComponent<Image>();
        guideBg.color = new Color(0, 0, 0, 0.6f);

        var guideTextGo = CreateUIText(guidePanelGo.transform, "GuideText", "",
            new Vector2(15, -10), new Vector2(230, 280), TextAnchor.UpperLeft);
        var guideTextComp = guideTextGo.GetComponent<Text>();
        if (guideTextComp != null) guideTextComp.fontSize = 13;
        var guideTextRT = guideTextGo.GetComponent<RectTransform>();
        guideTextRT.anchorMin = Vector2.zero;
        guideTextRT.anchorMax = Vector2.one;
        guideTextRT.offsetMin = new Vector2(15, 10);
        guideTextRT.offsetMax = new Vector2(-10, -10);

        var guideUI = guidePanelGo.AddComponent<KeybindGuideUI>();
        var guideSO = new SerializedObject(guideUI);
        var guidePanelProp = guideSO.FindProperty("guidePanel");
        if (guidePanelProp != null) guidePanelProp.objectReferenceValue = guidePanelGo;
        SetTextRef(guideSO, "guideText", guideTextGo);
        guideSO.ApplyModifiedPropertiesWithoutUndo();

        Debug.Log("  [UI] Canvas_HUD + HUD + Target + Death + DamageText + SkillBar + Inventory + Party + Buff + Quest + KeybindGuide 생성 완료");
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

    private static void SetArrayRef(SerializedObject so, string fieldName, Text[] texts)
    {
        var prop = so.FindProperty(fieldName);
        if (prop == null) return;
        prop.arraySize = texts.Length;
        for (int i = 0; i < texts.Length; i++)
        {
            var elem = prop.GetArrayElementAtIndex(i);
            elem.objectReferenceValue = texts[i];
        }
    }

    private static void SetImageArrayRef(SerializedObject so, string fieldName, Image[] images)
    {
        var prop = so.FindProperty(fieldName);
        if (prop == null) return;
        prop.arraySize = images.Length;
        for (int i = 0; i < images.Length; i++)
        {
            var elem = prop.GetArrayElementAtIndex(i);
            elem.objectReferenceValue = images[i];
        }
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
