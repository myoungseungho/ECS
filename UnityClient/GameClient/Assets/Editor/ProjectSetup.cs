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

    // ━━━ ui.yaml 색상 상수 ━━━
    private static readonly Color PanelBg      = HexColor("#16213ECC");
    private static readonly Color HpBarColor   = HexColor("#E74C3C");
    private static readonly Color MpBarColor   = HexColor("#3498DB");
    private static readonly Color ExpBarColor  = HexColor("#F1C40F");
    private static readonly Color GoldText     = HexColor("#FFD700");
    private static readonly Color ChatBg       = new Color(0, 0, 0, 0.3f);
    private static readonly Color SlotBg       = new Color(0.15f, 0.15f, 0.2f, 0.85f);
    private static readonly Color SlotBorder   = HexColor("#3A3A5C");

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

    [MenuItem("ECS Game/Rebuild GameScene (Force)", priority = 3)]
    public static void ForceRebuildGameScene()
    {
        if (File.Exists(GameScenePath))
            File.Delete(GameScenePath);
        AssetDatabase.Refresh();
        CreateGameScene();
        AssetDatabase.SaveAssets();
        Debug.Log("━━━ [ProjectSetup] GameScene 강제 재빌드 완료 ━━━");
    }

    // ━━━ 1. 디렉토리 ━━━

    private static void CreateDirectories()
    {
        EnsureDirectory(MaterialsDir);
        EnsureDirectory(PrefabsDir);
        EnsureDirectory(ScenesDir);
        EnsureDirectory("Assets/Art");
        EnsureDirectory(AnimControllersDir);
        EnsureDirectory("Assets/Settings");
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

        var idleClip = LoadAnimationClip(IdleAnimPath);
        var walkClip = LoadAnimationClip(WalkAnimPath);
        var attackClip = LoadAnimationClip(AttackAnimPath);
        var deathClip = LoadAnimationClip(DeathAnimPath);

        var idleState = rootStateMachine.AddState("Idle");
        idleState.motion = idleClip;
        var walkState = rootStateMachine.AddState("Walk");
        walkState.motion = walkClip;
        walkState.speedParameterActive = true;
        walkState.speedParameter = "Speed";
        var combatIdleState = rootStateMachine.AddState("CombatIdle");
        combatIdleState.motion = idleClip;
        var combatWalkState = rootStateMachine.AddState("CombatWalk");
        combatWalkState.motion = walkClip;
        combatWalkState.speedParameterActive = true;
        combatWalkState.speedParameter = "Speed";

        var attack1State = rootStateMachine.AddState("Attack1");
        attack1State.motion = attackClip;
        var attack2State = rootStateMachine.AddState("Attack2");
        attack2State.motion = attackClip;
        var attack3State = rootStateMachine.AddState("Attack3");
        attack3State.motion = attackClip;
        var attack4State = rootStateMachine.AddState("Attack4");
        attack4State.motion = attackClip;
        var dashState = rootStateMachine.AddState("Dash");
        dashState.motion = walkClip;
        var hitState = rootStateMachine.AddState("HitReact");
        hitState.motion = idleClip;
        var deathState = rootStateMachine.AddState("Death");
        deathState.motion = deathClip;
        var skillState = rootStateMachine.AddState("SkillCast");
        skillState.motion = attackClip;

        rootStateMachine.defaultState = idleState;

        AddTransition(idleState, walkState, "Speed", AnimatorConditionMode.Greater, 0.1f);
        AddTransition(walkState, idleState, "Speed", AnimatorConditionMode.Less, 0.1f);
        AddTransition(idleState, combatIdleState, "InCombat", AnimatorConditionMode.If);
        AddTransition(walkState, combatWalkState, "InCombat", AnimatorConditionMode.If);
        AddTransition(combatIdleState, combatWalkState, "Speed", AnimatorConditionMode.Greater, 0.1f, 0.08f);
        AddTransition(combatWalkState, combatIdleState, "Speed", AnimatorConditionMode.Less, 0.1f, 0.08f);
        AddTransition(combatIdleState, idleState, "InCombat", AnimatorConditionMode.IfNot);
        AddTransition(combatWalkState, walkState, "InCombat", AnimatorConditionMode.IfNot);

        AnimatorState[] attackStates = { attack1State, attack2State, attack3State, attack4State };
        for (int i = 0; i < 4; i++)
        {
            var t = rootStateMachine.AddAnyStateTransition(attackStates[i]);
            t.AddCondition(AnimatorConditionMode.If, 0, "Attack");
            t.AddCondition(AnimatorConditionMode.Equals, i, "AttackIndex");
            t.hasExitTime = false;
            t.duration = 0.08f;

            var toIdle = attackStates[i].AddTransition(combatIdleState);
            toIdle.hasExitTime = true;
            toIdle.exitTime = i < 2 ? 0.9f : 0.85f;
            toIdle.duration = 0.15f;
        }

        var anyToDash = rootStateMachine.AddAnyStateTransition(dashState);
        anyToDash.AddCondition(AnimatorConditionMode.If, 0, "Dash");
        anyToDash.hasExitTime = false;
        anyToDash.duration = 0.05f;
        var dashToIdle = dashState.AddTransition(combatIdleState);
        dashToIdle.hasExitTime = true;
        dashToIdle.exitTime = 0.9f;
        dashToIdle.duration = 0.15f;

        var anyToHit = rootStateMachine.AddAnyStateTransition(hitState);
        anyToHit.AddCondition(AnimatorConditionMode.If, 0, "Hit");
        anyToHit.hasExitTime = false;
        anyToHit.duration = 0.05f;
        var hitToIdle = hitState.AddTransition(combatIdleState);
        hitToIdle.hasExitTime = true;
        hitToIdle.exitTime = 0.8f;
        hitToIdle.duration = 0.15f;

        var anyToSkill = rootStateMachine.AddAnyStateTransition(skillState);
        anyToSkill.AddCondition(AnimatorConditionMode.If, 0, "Skill");
        anyToSkill.hasExitTime = false;
        anyToSkill.duration = 0.08f;
        var skillToIdle = skillState.AddTransition(combatIdleState);
        skillToIdle.hasExitTime = true;
        skillToIdle.exitTime = 0.9f;
        skillToIdle.duration = 0.15f;

        var anyToDeath = rootStateMachine.AddAnyStateTransition(deathState);
        anyToDeath.AddCondition(AnimatorConditionMode.If, 0, "IsDead");
        anyToDeath.hasExitTime = false;
        anyToDeath.duration = 0.15f;

        EditorUtility.SetDirty(controller);
        Debug.Log("  [Animator] CharacterAnimator.controller 생성 완료");
    }

    private static void AddTransition(AnimatorState from, AnimatorState to,
        string param, AnimatorConditionMode mode, float threshold = 0f, float duration = 0.15f)
    {
        var t = from.AddTransition(to);
        t.AddCondition(mode, threshold, param);
        t.hasExitTime = false;
        t.duration = duration;
    }

    private static AnimationClip LoadAnimationClip(string fbxPath)
    {
        var assets = AssetDatabase.LoadAllAssetsAtPath(fbxPath);
        if (assets == null) return null;
        return assets.OfType<AnimationClip>().FirstOrDefault(c => !c.name.StartsWith("__preview__"));
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
        CreatePlayerPrefab(LocalPrefabPath, LocalMatPath, typeof(LocalPlayer), "LocalPlayer", PlayerFBXPath);
        CreatePlayerPrefab(RemotePrefabPath, RemoteMatPath, typeof(RemotePlayer), "RemotePlayer", PlayerFBXPath);
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
            var col = go.AddComponent<CapsuleCollider>();
            col.center = new Vector3(0f, 0.9f, 0f);
            col.height = 1.8f;
            col.radius = 0.3f;
            var animator = go.GetComponent<Animator>();
            if (animator == null) animator = go.AddComponent<Animator>();
            var animController = AssetDatabase.LoadAssetAtPath<AnimatorController>(AnimControllerPath);
            if (animController != null) animator.runtimeAnimatorController = animController;
            var mat = AssetDatabase.LoadAssetAtPath<Material>(MonsterMatPath);
            if (mat != null)
                foreach (var renderer in go.GetComponentsInChildren<Renderer>())
                    renderer.sharedMaterial = mat;
        }
        else
        {
            go = GameObject.CreatePrimitive(PrimitiveType.Cube);
            go.name = "Monster";
            go.transform.localScale = new Vector3(0.8f, 0.8f, 0.8f);
            var mat = AssetDatabase.LoadAssetAtPath<Material>(MonsterMatPath);
            if (mat != null) go.GetComponent<MeshRenderer>().sharedMaterial = mat;
        }

        go.AddComponent<MonsterEntity>();
        PrefabUtility.SaveAsPrefabAsset(go, MonsterPrefabPath);
        Object.DestroyImmediate(go);
    }

    private static void CreatePlayerPrefab(string prefabPath, string matPath,
        System.Type componentType, string label, string fbxPath)
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
            var col = go.AddComponent<CapsuleCollider>();
            col.center = new Vector3(0f, 0.9f, 0f);
            col.height = 1.8f;
            col.radius = 0.3f;
            var animator = go.GetComponent<Animator>();
            if (animator == null) animator = go.AddComponent<Animator>();
            var animController = AssetDatabase.LoadAssetAtPath<AnimatorController>(AnimControllerPath);
            if (animController != null) animator.runtimeAnimatorController = animController;
            var mat = AssetDatabase.LoadAssetAtPath<Material>(matPath);
            if (mat != null)
                foreach (var renderer in go.GetComponentsInChildren<Renderer>())
                    renderer.sharedMaterial = mat;
        }
        else
        {
            go = GameObject.CreatePrimitive(PrimitiveType.Capsule);
            go.name = label;
            var mat = AssetDatabase.LoadAssetAtPath<Material>(matPath);
            if (mat != null) go.GetComponent<MeshRenderer>().sharedMaterial = mat;
        }

        go.AddComponent(componentType);
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

        // --- Floor (터레인 없을 때 폴백) ---
        var floor = GameObject.CreatePrimitive(PrimitiveType.Plane);
        floor.name = "Floor";
        floor.transform.position = new Vector3(50f, 0f, 50f);
        floor.transform.localScale = new Vector3(10f, 1f, 10f);
        var floorRenderer = floor.GetComponent<MeshRenderer>();
        if (floorRenderer != null)
        {
            var floorShader = Shader.Find(URPLitShader) ?? Shader.Find("Standard");
            var floorMat = new Material(floorShader);
            floorMat.SetColor("_BaseColor", new Color(0.35f, 0.65f, 0.25f));
            floorRenderer.sharedMaterial = floorMat;
        }

        // --- Environment (art_style.yaml lighting) ---
        SetupLighting();

        // --- Post-Processing Volume ---
        SetupPostProcessingVolume();

        // --- Main Camera ---
        var camGo = new GameObject("Main Camera");
        camGo.tag = "MainCamera";
        camGo.AddComponent<Camera>();
        camGo.transform.position = new Vector3(50f, 40f, -10f);
        camGo.transform.rotation = Quaternion.Euler(60f, 0f, 0f);

        // --- Environment Setup (terrain, water, buildings, trees) ---
        EnvironmentSetup.SetupEnvironmentInScene();

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
        var npcManagerGo = CreateManagerObject("NpcManager", typeof(NpcManager));
        var enhanceManagerGo = CreateManagerObject("EnhanceManager", typeof(EnhanceManager));
        var tutorialManagerGo = CreateManagerObject("TutorialManager", typeof(TutorialManager));
        var guildManagerGo = CreateManagerObject("GuildManager", typeof(GuildManager));
        var tradeManagerGo = CreateManagerObject("TradeManager", typeof(TradeManager));
        var mailManagerGo = CreateManagerObject("MailManager", typeof(MailManager));
        var dungeonManagerGo = CreateManagerObject("DungeonManager", typeof(DungeonManager));
        var pvpManagerGo = CreateManagerObject("PvPManager", typeof(PvPManager));
        var raidManagerGo = CreateManagerObject("RaidManager", typeof(RaidManager));
        var craftingManagerGo = CreateManagerObject("CraftingManager", typeof(CraftingManager));
        var gatheringManagerGo = CreateManagerObject("GatheringManager", typeof(GatheringManager));
        var gemManagerGo = CreateManagerObject("GemManager", typeof(GemManager));
        var weatherManagerGo = CreateManagerObject("WeatherManager", typeof(WeatherManager));
        var teleportManagerGo = CreateManagerObject("TeleportManager", typeof(TeleportManager));
        var mountManagerGo = CreateManagerObject("MountManager", typeof(MountManager));
        var cashShopManagerGo = CreateManagerObject("CashShopManager", typeof(CashShopManager));
        var battlePassManagerGo = CreateManagerObject("BattlePassManager", typeof(BattlePassManager));
        var attendanceManagerGo = CreateManagerObject("AttendanceManager", typeof(AttendanceManager));
        var storyManagerGo = CreateManagerObject("StoryManager", typeof(StoryManager));
        var auctionManagerGo = CreateManagerObject("AuctionManager", typeof(AuctionManager));
        var tripodManagerGo = CreateManagerObject("TripodManager", typeof(TripodManager));
        var bountyManagerGo = CreateManagerObject("BountyManager", typeof(BountyManager));
        var dailyQuestManagerGo = CreateManagerObject("DailyQuestManager", typeof(DailyQuestManager));
        var reputationManagerGo = CreateManagerObject("ReputationManager", typeof(ReputationManager));
        var titleManagerGo = CreateManagerObject("TitleManager", typeof(TitleManager));
        var collectionManagerGo = CreateManagerObject("CollectionManager", typeof(CollectionManager));
        var jobChangeUIGo = CreateManagerObject("JobChangeUI", typeof(JobChangeUI));
        var engravingManagerGo = CreateManagerObject("EngravingManager", typeof(EngravingManager));
        var transcendUIGo = CreateManagerObject("TranscendUI", typeof(TranscendUI));
        var friendManagerGo = CreateManagerObject("FriendManager", typeof(FriendManager));
        var blockManagerGo = CreateManagerObject("BlockManager", typeof(BlockManager));
        var partyFinderManagerGo = CreateManagerObject("PartyFinderManager", typeof(PartyFinderManager));
        var friendUIGo = CreateManagerObject("FriendUI", typeof(FriendUI));
        var blockUIGo = CreateManagerObject("BlockUI", typeof(BlockUI));
        var partyFinderUIGo = CreateManagerObject("PartyFinderUI", typeof(PartyFinderUI));
        var durabilityManagerGo = CreateManagerObject("DurabilityManager", typeof(DurabilityManager));
        var repairUIGo = CreateManagerObject("RepairUI", typeof(RepairUI));
        var rerollUIGo = CreateManagerObject("RerollUI", typeof(RerollUI));
        var battlegroundManagerGo = CreateManagerObject("BattlegroundManager", typeof(BattlegroundManager));
        var guildWarManagerGo = CreateManagerObject("GuildWarManager", typeof(GuildWarManager));
        var battlegroundUIGo = CreateManagerObject("BattlegroundUI", typeof(BattlegroundUI));
        var guildWarUIGo = CreateManagerObject("GuildWarUI", typeof(GuildWarUI));
        var currencyManagerGo = CreateManagerObject("CurrencyManager", typeof(CurrencyManager));
        var currencyUIGo = CreateManagerObject("CurrencyUI", typeof(CurrencyUI));
        var tokenShopUIGo = CreateManagerObject("TokenShopUI", typeof(TokenShopUI));

        // 신규 매니저
        var soundManagerGo = CreateManagerObject("SoundManager", typeof(SoundManager));
        var skillVFXManagerGo = CreateManagerObject("SkillVFXManager", typeof(SkillVFXManager));

        // --- GameBootstrap ---
        var bootstrapGo = new GameObject("GameBootstrap");
        bootstrapGo.AddComponent<GameBootstrap>();

        // --- UI Canvas (로스트아크 스타일) ---
        CreateLostArkUI(scene);

        // --- Prefab 참조 연결 ---
        var localPrefab = AssetDatabase.LoadAssetAtPath<GameObject>(LocalPrefabPath);
        var remotePrefab = AssetDatabase.LoadAssetAtPath<GameObject>(RemotePrefabPath);
        var monsterPrefab = AssetDatabase.LoadAssetAtPath<GameObject>(MonsterPrefabPath);

        ConnectPrefabRef(entityManagerGo, typeof(EntityManager), "localPlayerPrefab", localPrefab);
        ConnectPrefabRef(entityManagerGo, typeof(EntityManager), "remotePlayerPrefab", remotePrefab);
        ConnectPrefabRef(entityPoolGo, typeof(EntityPool), "prefab", remotePrefab);
        ConnectPrefabRef(monsterManagerGo, typeof(MonsterManager), "monsterPrefab", monsterPrefab);

        EditorSceneManager.SaveScene(scene, GameScenePath);
        Debug.Log("  [Scene] GameScene 생성 완료");
    }

    // ━━━ Lighting (art_style.yaml) ━━━

    private static void SetupLighting()
    {
        // 방향광 (art_style.yaml directional_light)
        var lightGo = new GameObject("Directional Light");
        var light = lightGo.AddComponent<Light>();
        light.type = LightType.Directional;
        light.color = HexColor("#FFFACD");
        light.intensity = 1.2f;
        light.shadows = LightShadows.Soft;
        light.shadowResolution = UnityEngine.Rendering.LightShadowResolution.High;
        lightGo.transform.rotation = Quaternion.Euler(50f, -30f, 0f);

        // 안개 (art_style.yaml fog) — Exp² 밀도 0.005
        RenderSettings.fog = true;
        RenderSettings.fogMode = FogMode.ExponentialSquared;
        RenderSettings.fogDensity = 0.005f;
        RenderSettings.fogColor = HexColor("#B0BEC5");

        // 앰비언트 트라이라이트
        RenderSettings.ambientMode = UnityEngine.Rendering.AmbientMode.Trilight;
        RenderSettings.ambientSkyColor = HexColor("#87CEEB");
        RenderSettings.ambientEquatorColor = HexColor("#DEB887");
        RenderSettings.ambientGroundColor = HexColor("#8B7355");

        // 스카이박스/프로시저럴
        var skyboxMat = RenderSettings.skybox;
        if (skyboxMat == null)
        {
            var skyShader = Shader.Find("Skybox/Procedural");
            if (skyShader != null)
            {
                skyboxMat = new Material(skyShader);
                RenderSettings.skybox = skyboxMat;
            }
        }

        Debug.Log("  [Lighting] 방향광 + 안개(Exp²) + 앰비언트 트라이라이트 설정");
    }

    // ━━━ Post-Processing ━━━

    private static void SetupPostProcessingVolume()
    {
        var volumeGo = new GameObject("GlobalVolume_PostProcess");
        var volume = volumeGo.AddComponent<Volume>();
        volume.isGlobal = true;
        volume.priority = 0;

        var profile = ScriptableObject.CreateInstance<VolumeProfile>();

        AddVolumeOverride(profile, "UnityEngine.Rendering.Universal.Bloom",
            ("intensity", 0.3f), ("threshold", 0.9f), ("scatter", 0.7f));
        AddVolumeOverride(profile, "UnityEngine.Rendering.Universal.Tonemapping",
            ("mode", 2)); // ACES
        AddVolumeOverride(profile, "UnityEngine.Rendering.Universal.ColorAdjustments",
            ("postExposure", 0f), ("contrast", 10f), ("saturation", 10f));
        AddVolumeOverride(profile, "UnityEngine.Rendering.Universal.Vignette",
            ("intensity", 0.2f), ("smoothness", 0.5f));

        const string profilePath = "Assets/Settings/GlobalVolumeProfile.asset";
        AssetDatabase.CreateAsset(profile, profilePath);
        volume.sharedProfile = profile;

        Debug.Log("  [PostProcess] Bloom 0.3, ACES, Vignette 0.2 설정");
    }

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

            var param = fieldInfo.GetValue(component);
            if (param == null) continue;

            var paramType = param.GetType();
            var overrideProp = paramType.GetProperty("overrideState");
            overrideProp?.SetValue(param, true);

            var valueProp = paramType.GetProperty("value");
            if (valueProp != null)
            {
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
        var camGo = new GameObject("Main Camera");
        camGo.tag = "MainCamera";
        camGo.AddComponent<Camera>();
        camGo.transform.position = new Vector3(0f, 5f, -10f);
        CreateManagerObject("NetworkManager", typeof(Network.NetworkManager));
        var testGo = new GameObject("ConnectionTest");
        testGo.AddComponent<ConnectionTest>();

        EditorSceneManager.SaveScene(scene, TestScenePath);
        Debug.Log("  [Scene] TestScene 생성 완료");
    }

    // ━━━ 6. Build Settings ━━━

    private static void RegisterBuildScenes()
    {
        var scenes = EditorBuildSettings.scenes;
        bool hasGame = false, hasTest = false;
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

    // ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    // 7. Lost Ark Style UI (ui.yaml 기반)
    // ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    private static void CreateLostArkUI(Scene scene)
    {
        // Canvas (ui.yaml global: 1920x1080)
        var canvasGo = new GameObject("Canvas");
        var canvas = canvasGo.AddComponent<Canvas>();
        canvas.renderMode = RenderMode.ScreenSpaceOverlay;
        canvas.sortingOrder = 0;
        var scaler = canvasGo.AddComponent<CanvasScaler>();
        scaler.uiScaleMode = CanvasScaler.ScaleMode.ScaleWithScreenSize;
        scaler.referenceResolution = new Vector2(1920, 1080);
        scaler.matchWidthOrHeight = 0.5f;
        canvasGo.AddComponent<GraphicRaycaster>();

        // EventSystem
        var eventSysGo = new GameObject("EventSystem");
        eventSysGo.AddComponent<UnityEngine.EventSystems.EventSystem>();
        eventSysGo.AddComponent<UnityEngine.EventSystems.StandaloneInputModule>();

        // ── 1. 캐릭터 정보 (좌상단) — ui.yaml hud.player_info ──
        CreatePlayerInfoPanel(canvasGo.transform);

        // ── 2. 타겟 정보 (상단 중앙) — ui.yaml hud.target_info ──
        CreateTargetInfoPanel(canvasGo.transform);

        // ── 3. 스킬바 (하단 중앙) — ui.yaml hud.skill_bar (12슬롯) ──
        CreateSkillBarPanel(canvasGo.transform);

        // ── 4. 미니맵 (우상단) — ui.yaml hud.minimap ──
        CreateMinimapPanel(canvasGo.transform);

        // ── 5. 채팅 (좌하단) — ui.yaml hud.chat ──
        CreateChatPanel(canvasGo.transform);

        // ── 6. 버프 아이콘 (좌상단 아래) — ui.yaml hud.buff_bar ──
        CreateBuffPanel(canvasGo.transform);

        // ── 7. 퀵메뉴 (우하단) — ui.yaml hud.quick_menu ──
        CreateQuickMenuPanel(canvasGo.transform);

        // ── 8. 보스HP (상단 특수) — ui.yaml hud.boss_hp ──
        CreateBossHPPanel(canvasGo.transform);

        // ── 9. 사망 패널 ──
        CreateDeathPanel(canvasGo.transform);

        // ── 10. 인벤토리 패널 ──
        CreateInventoryPanel(canvasGo.transform);

        // ── 11. 파티 패널 ──
        CreatePartyPanel(canvasGo.transform);

        // ── 12. 퀘스트 패널 ──
        CreateQuestPanel(canvasGo.transform);

        // ── 13. 키바인드 가이드 ──
        CreateKeybindGuidePanel(canvasGo.transform);

        Debug.Log("  [UI] 로스트아크 스타일 HUD 생성 완료 (12슬롯 스킬바, 미니맵, 채팅, 퀵메뉴, 보스HP)");
    }

    // ── 1. 캐릭터 정보 ──

    private static void CreatePlayerInfoPanel(Transform canvasT)
    {
        var hudGo = CreatePanel(canvasT, "HUDPanel",
            AnchorPreset.TopLeft, new Vector2(20, -20), new Vector2(300, 100),
            new Color(0, 0, 0, 0.53f));

        var hudManager = hudGo.AddComponent<HUDManager>();

        // Portrait placeholder
        var portraitGo = new GameObject("Portrait");
        portraitGo.transform.SetParent(hudGo.transform, false);
        var portraitRT = portraitGo.AddComponent<RectTransform>();
        SetAnchors(portraitRT, AnchorPreset.TopLeft);
        portraitRT.anchoredPosition = new Vector2(10, -20);
        portraitRT.sizeDelta = new Vector2(60, 60);
        var portraitImg = portraitGo.AddComponent<Image>();
        portraitImg.color = new Color(0.3f, 0.3f, 0.4f);

        var nameGo = CreateUIText(hudGo.transform, "NameText", "Player",
            new Vector2(80, -10), new Vector2(150, 20), TextAnchor.MiddleLeft);
        var nameComp = nameGo.GetComponent<Text>();
        nameComp.fontStyle = FontStyle.Bold;
        nameComp.fontSize = 14;

        var levelGo = CreateUIText(hudGo.transform, "LevelText", "Lv.1",
            new Vector2(230, -10), new Vector2(50, 20), TextAnchor.MiddleLeft);
        var levelComp = levelGo.GetComponent<Text>();
        levelComp.fontStyle = FontStyle.Bold;
        levelComp.fontSize = 14;
        levelComp.color = GoldText;

        var hpBarGo = CreateUISlider(hudGo.transform, "HPBar",
            new Vector2(80, -35), new Vector2(200, 16), HpBarColor);
        var hpTextGo = CreateOverlayText(hpBarGo.transform, "HPText", "100/100", 10);

        var mpBarGo = CreateUISlider(hudGo.transform, "MPBar",
            new Vector2(80, -55), new Vector2(200, 14), MpBarColor);
        var mpTextGo = CreateOverlayText(mpBarGo.transform, "MPText", "50/50", 10);

        var expBarGo = CreateUISlider(hudGo.transform, "EXPBar",
            new Vector2(80, -73), new Vector2(200, 8), ExpBarColor);

        // SerializedField 연결
        var hudSO = new SerializedObject(hudManager);
        SetSliderRef(hudSO, "hpSlider", hpBarGo);
        SetSliderRef(hudSO, "mpSlider", mpBarGo);
        SetSliderRef(hudSO, "expSlider", expBarGo);
        SetTextRef(hudSO, "levelText", levelGo);
        SetTextRef(hudSO, "nameText", nameGo);
        SetTextRef(hudSO, "hpText", hpTextGo);
        SetTextRef(hudSO, "mpText", mpTextGo);
        hudSO.ApplyModifiedPropertiesWithoutUndo();
    }

    // ── 2. 타겟 정보 ──

    private static void CreateTargetInfoPanel(Transform canvasT)
    {
        var targetGo = CreatePanel(canvasT, "TargetPanel",
            AnchorPreset.TopCenter, new Vector2(0, -20), new Vector2(350, 70),
            new Color(0, 0, 0, 0.53f));

        var combatUI = targetGo.AddComponent<CombatUI>();

        var targetNameGo = CreateUIText(targetGo.transform, "TargetName", "Target",
            new Vector2(0, 0), new Vector2(200, 25), TextAnchor.MiddleCenter);
        var targetHpGo = CreateUISlider(targetGo.transform, "TargetHPBar",
            new Vector2(0, -25), new Vector2(300, 18), HpBarColor);
        var targetHpText = CreateOverlayText(targetHpGo.transform, "TargetHPText", "", 10);

        // DamageText container
        var dmgParentGo = new GameObject("DamageTextPool");
        dmgParentGo.transform.SetParent(canvasT, false);
        var dmgParentRT = dmgParentGo.AddComponent<RectTransform>();
        dmgParentRT.anchorMin = Vector2.zero;
        dmgParentRT.anchorMax = Vector2.one;
        dmgParentRT.sizeDelta = Vector2.zero;

        var dmgTextGo = new GameObject("DamageText");
        dmgTextGo.transform.SetParent(dmgParentGo.transform, false);
        var dmgText = dmgTextGo.AddComponent<Text>();
        dmgText.text = "0";
        dmgText.fontSize = 24;
        dmgText.fontStyle = FontStyle.Bold;
        dmgText.alignment = TextAnchor.MiddleCenter;
        dmgText.font = Resources.GetBuiltinResource<Font>("LegacyRuntime.ttf");
        dmgTextGo.GetComponent<RectTransform>().sizeDelta = new Vector2(100, 30);
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
    }

    // ── 3. 스킬바 (12슬롯) ──

    private static void CreateSkillBarPanel(Transform canvasT)
    {
        var skillBarGo = CreatePanel(canvasT, "SkillBarPanel",
            AnchorPreset.BottomCenter, new Vector2(0, 20), new Vector2(780, 80),
            PanelBg);

        var skillBarUI = skillBarGo.AddComponent<SkillBarUI>();
        int slotCount = SkillBarUI.SlotCount;
        var slotNameTexts = new Text[slotCount];
        var slotKeyTexts = new Text[slotCount];
        var cooldownOverlays = new Image[slotCount];

        string[] keyLabels = { "LMB", "Q", "W", "E", "R", "V", "A", "S", "D", "F", "1", "2" };

        // 레이아웃: [LMB] | [Q][W][E][R] | [V(64x64)] | [A][S][D][F] | [1][2]
        float slotSize = 56f;
        float gap = 4f;
        float groupGap = 12f;

        // LMB 시작 X
        float totalWidth = slotSize + groupGap                 // LMB + gap
            + (slotSize + gap) * 4 + groupGap                   // QWER + gap
            + 64f + groupGap                                      // V (궁극기) + gap
            + (slotSize + gap) * 4 + groupGap                   // ASDF + gap
            + (slotSize + gap) * 2;                               // 1,2
        float startX = -totalWidth / 2f;
        float curX = startX;

        for (int i = 0; i < slotCount; i++)
        {
            float thisSize = (i == 5) ? 64f : slotSize; // V 슬롯은 64x64

            // 그룹 간격 삽입
            if (i == 1 || i == 5 || i == 6 || i == 10)
                curX += groupGap;

            var slotGo = new GameObject($"Slot_{keyLabels[i]}");
            slotGo.transform.SetParent(skillBarGo.transform, false);
            var slotRT = slotGo.AddComponent<RectTransform>();
            slotRT.anchorMin = new Vector2(0.5f, 0.5f);
            slotRT.anchorMax = new Vector2(0.5f, 0.5f);
            slotRT.anchoredPosition = new Vector2(curX + thisSize / 2f, 0);
            slotRT.sizeDelta = new Vector2(thisSize, thisSize);

            var slotBgImg = slotGo.AddComponent<Image>();
            slotBgImg.color = SlotBg;

            // 테두리 효과 (약간 밝은 외곽)
            var borderGo = new GameObject("Border");
            borderGo.transform.SetParent(slotGo.transform, false);
            var borderRT = borderGo.AddComponent<RectTransform>();
            borderRT.anchorMin = Vector2.zero;
            borderRT.anchorMax = Vector2.one;
            borderRT.sizeDelta = Vector2.zero;
            var borderImg = borderGo.AddComponent<Image>();
            borderImg.color = SlotBorder;
            borderImg.type = Image.Type.Sliced;
            borderImg.raycastTarget = false;

            // 키 레이블
            var keyGo = CreateUIText(slotGo.transform, "Key", keyLabels[i],
                new Vector2(2, -2), new Vector2(28, 14), TextAnchor.UpperLeft);
            var keyComp = keyGo.GetComponent<Text>();
            keyComp.fontSize = 10;
            keyComp.color = new Color(0.7f, 0.7f, 0.8f);
            slotKeyTexts[i] = keyComp;

            // 스킬 이름
            var nameTextGo = CreateUIText(slotGo.transform, "Name", "",
                new Vector2(0, -thisSize + 14), new Vector2(thisSize - 4, 14), TextAnchor.MiddleCenter);
            var nameComp = nameTextGo.GetComponent<Text>();
            nameComp.fontSize = 9;
            slotNameTexts[i] = nameComp;

            // 쿨다운 오버레이 (라디얼 필)
            var cdGo = new GameObject("Cooldown");
            cdGo.transform.SetParent(slotGo.transform, false);
            var cdRT = cdGo.AddComponent<RectTransform>();
            cdRT.anchorMin = Vector2.zero;
            cdRT.anchorMax = Vector2.one;
            cdRT.sizeDelta = Vector2.zero;
            var cdImg = cdGo.AddComponent<Image>();
            cdImg.color = new Color(0, 0, 0, 0.6f);
            cdImg.type = Image.Type.Filled;
            cdImg.fillMethod = Image.FillMethod.Radial360;
            cdImg.fillOrigin = (int)Image.Origin360.Top;
            cdImg.fillClockwise = false;
            cdImg.fillAmount = 0f;
            cdGo.SetActive(false);
            cooldownOverlays[i] = cdImg;

            curX += thisSize + gap;
        }

        var skillBarSO = new SerializedObject(skillBarUI);
        SetArrayRef(skillBarSO, "slotNameTexts", slotNameTexts);
        SetArrayRef(skillBarSO, "slotKeyTexts", slotKeyTexts);
        SetImageArrayRef(skillBarSO, "cooldownOverlays", cooldownOverlays);
        skillBarSO.ApplyModifiedPropertiesWithoutUndo();
    }

    // ── 4. 미니맵 ──

    private static void CreateMinimapPanel(Transform canvasT)
    {
        var minimapGo = CreatePanel(canvasT, "MinimapPanel",
            AnchorPreset.TopRight, new Vector2(-20, -20), new Vector2(200, 220),
            PanelBg);

        var minimapUI = minimapGo.AddComponent<MinimapUI>();

        // RawImage for minimap render
        var rawImgGo = new GameObject("MinimapImage");
        rawImgGo.transform.SetParent(minimapGo.transform, false);
        var rawImgRT = rawImgGo.AddComponent<RectTransform>();
        rawImgRT.anchorMin = new Vector2(0, 0.1f);
        rawImgRT.anchorMax = Vector2.one;
        rawImgRT.offsetMin = new Vector2(5, 5);
        rawImgRT.offsetMax = new Vector2(-5, -5);
        var rawImg = rawImgGo.AddComponent<RawImage>();
        rawImg.color = Color.white;

        // 원형 마스크
        var maskGo = new GameObject("CircleMask");
        maskGo.transform.SetParent(rawImgGo.transform, false);
        var maskRT = maskGo.AddComponent<RectTransform>();
        maskRT.anchorMin = Vector2.zero;
        maskRT.anchorMax = Vector2.one;
        maskRT.sizeDelta = Vector2.zero;
        maskGo.AddComponent<Image>().color = Color.white;
        maskGo.AddComponent<Mask>().showMaskGraphic = false;

        // Zone name
        var zoneGo = CreateUIText(minimapGo.transform, "ZoneName", "Zone 1",
            new Vector2(5, -2), new Vector2(120, 18), TextAnchor.UpperLeft);
        var zoneComp = zoneGo.GetComponent<Text>();
        zoneComp.fontSize = 11;

        // Coordinates
        var coordGo = CreateUIText(minimapGo.transform, "Coords", "(50, 50)",
            new Vector2(130, -2), new Vector2(65, 18), TextAnchor.UpperRight);
        var coordComp = coordGo.GetComponent<Text>();
        coordComp.fontSize = 10;

        var minimapSO = new SerializedObject(minimapUI);
        var imgProp = minimapSO.FindProperty("minimapImage");
        if (imgProp != null) imgProp.objectReferenceValue = rawImg;
        SetTextRef(minimapSO, "zoneNameText", zoneGo);
        SetTextRef(minimapSO, "coordText", coordGo);
        minimapSO.ApplyModifiedPropertiesWithoutUndo();
    }

    // ── 5. 채팅 ──

    private static void CreateChatPanel(Transform canvasT)
    {
        var chatGo = CreatePanel(canvasT, "ChatPanel",
            AnchorPreset.BottomLeft, new Vector2(20, 20), new Vector2(400, 200),
            ChatBg);

        var chatUI = chatGo.AddComponent<ChatUI>();

        // 메시지 영역
        var msgGo = CreateUIText(chatGo.transform, "MessageArea", "",
            new Vector2(10, -10), new Vector2(380, 150), TextAnchor.LowerLeft);
        var msgRT = msgGo.GetComponent<RectTransform>();
        msgRT.anchorMin = new Vector2(0, 0.2f);
        msgRT.anchorMax = Vector2.one;
        msgRT.offsetMin = new Vector2(10, 5);
        msgRT.offsetMax = new Vector2(-10, -5);
        var msgComp = msgGo.GetComponent<Text>();
        msgComp.fontSize = 12;
        msgComp.verticalOverflow = VerticalWrapMode.Truncate;
        msgComp.horizontalOverflow = HorizontalWrapMode.Wrap;
        msgComp.supportRichText = true;

        // 채널 레이블
        var channelGo = CreateUIText(chatGo.transform, "ChannelLabel", "[Zone]",
            new Vector2(10, 0), new Vector2(60, 25), TextAnchor.MiddleLeft);
        var channelRT = channelGo.GetComponent<RectTransform>();
        channelRT.anchorMin = Vector2.zero;
        channelRT.anchorMax = new Vector2(0, 0);
        channelRT.pivot = new Vector2(0, 0);
        channelRT.anchoredPosition = new Vector2(10, 5);
        var channelComp = channelGo.GetComponent<Text>();
        channelComp.fontSize = 12;
        channelComp.color = new Color(0.8f, 0.8f, 0.3f);

        // 입력창
        var inputGo = new GameObject("ChatInput");
        inputGo.transform.SetParent(chatGo.transform, false);
        var inputRT = inputGo.AddComponent<RectTransform>();
        inputRT.anchorMin = Vector2.zero;
        inputRT.anchorMax = new Vector2(1, 0);
        inputRT.pivot = new Vector2(0.5f, 0);
        inputRT.offsetMin = new Vector2(75, 2);
        inputRT.offsetMax = new Vector2(-10, 28);
        var inputBg = inputGo.AddComponent<Image>();
        inputBg.color = new Color(0.1f, 0.1f, 0.15f, 0.8f);
        var inputField = inputGo.AddComponent<InputField>();

        var inputTextGo = CreateUIText(inputGo.transform, "Text", "",
            Vector2.zero, Vector2.zero, TextAnchor.MiddleLeft);
        var inputTextRT = inputTextGo.GetComponent<RectTransform>();
        inputTextRT.anchorMin = Vector2.zero;
        inputTextRT.anchorMax = Vector2.one;
        inputTextRT.offsetMin = new Vector2(5, 0);
        inputTextRT.offsetMax = new Vector2(-5, 0);
        inputField.textComponent = inputTextGo.GetComponent<Text>();
        inputGo.SetActive(false);

        var chatSO = new SerializedObject(chatUI);
        SetTextRef(chatSO, "messageArea", msgGo);
        var inputProp = chatSO.FindProperty("inputField");
        if (inputProp != null) inputProp.objectReferenceValue = inputField;
        SetTextRef(chatSO, "channelLabel", channelGo);
        chatSO.ApplyModifiedPropertiesWithoutUndo();
    }

    // ── 6. 버프 아이콘 ──

    private static void CreateBuffPanel(Transform canvasT)
    {
        var buffPanelGo = CreatePanel(canvasT, "BuffPanel",
            AnchorPreset.TopLeft, new Vector2(20, -130), new Vector2(400, 30),
            Color.clear);

        var buffUI = buffPanelGo.AddComponent<BuffUI>();

        var buffTemplate = new GameObject("BuffTemplate");
        buffTemplate.transform.SetParent(buffPanelGo.transform, false);
        var buffTemplateRT = buffTemplate.AddComponent<RectTransform>();
        buffTemplateRT.sizeDelta = new Vector2(28, 28);
        var buffTemplateBg = buffTemplate.AddComponent<Image>();
        buffTemplateBg.color = new Color(0.3f, 0.2f, 0.5f, 0.8f);
        var buffTemplateText = CreateUIText(buffTemplate.transform, "Text", "B0\n0s",
            Vector2.zero, Vector2.zero, TextAnchor.MiddleCenter);
        var bttRT = buffTemplateText.GetComponent<RectTransform>();
        bttRT.anchorMin = Vector2.zero;
        bttRT.anchorMax = Vector2.one;
        bttRT.sizeDelta = Vector2.zero;
        var btt = buffTemplateText.GetComponent<Text>();
        btt.fontSize = 9;
        buffTemplate.SetActive(false);

        var buffSO = new SerializedObject(buffUI);
        var buffParentProp = buffSO.FindProperty("buffIconParent");
        if (buffParentProp != null) buffParentProp.objectReferenceValue = buffPanelGo.transform;
        var buffTemplateProp = buffSO.FindProperty("buffIconTemplate");
        if (buffTemplateProp != null) buffTemplateProp.objectReferenceValue = buffTemplate;
        buffSO.ApplyModifiedPropertiesWithoutUndo();
    }

    // ── 7. 퀵메뉴 ──

    private static void CreateQuickMenuPanel(Transform canvasT)
    {
        var quickGo = CreatePanel(canvasT, "QuickMenuPanel",
            AnchorPreset.BottomRight, new Vector2(-20, 20), new Vector2(360, 40),
            PanelBg);

        string[] menuItems = { "K:캐릭", "I:인벤", "L:스킬", "J:퀘스트", "M:지도", "G:길드", "O:소셜", "ESC" };
        float btnWidth = 42f;
        float startX = -(menuItems.Length * btnWidth) / 2f;

        for (int i = 0; i < menuItems.Length; i++)
        {
            var btnGo = new GameObject($"QuickBtn_{i}");
            btnGo.transform.SetParent(quickGo.transform, false);
            var btnRT = btnGo.AddComponent<RectTransform>();
            btnRT.anchorMin = new Vector2(0.5f, 0.5f);
            btnRT.anchorMax = new Vector2(0.5f, 0.5f);
            btnRT.anchoredPosition = new Vector2(startX + i * btnWidth + btnWidth / 2f, 0);
            btnRT.sizeDelta = new Vector2(btnWidth - 2, 32);
            var btnImg = btnGo.AddComponent<Image>();
            btnImg.color = new Color(0.2f, 0.25f, 0.35f, 0.8f);
            btnGo.AddComponent<Button>();

            var txtGo = CreateUIText(btnGo.transform, "Label", menuItems[i],
                Vector2.zero, Vector2.zero, TextAnchor.MiddleCenter);
            var txtRT = txtGo.GetComponent<RectTransform>();
            txtRT.anchorMin = Vector2.zero;
            txtRT.anchorMax = Vector2.one;
            txtRT.sizeDelta = Vector2.zero;
            var txtComp = txtGo.GetComponent<Text>();
            txtComp.fontSize = 9;
        }
    }

    // ── 8. 보스 HP ──

    private static void CreateBossHPPanel(Transform canvasT)
    {
        var bossGo = CreatePanel(canvasT, "BossPanel",
            AnchorPreset.TopCenter, new Vector2(0, -100), new Vector2(600, 50),
            new Color(0, 0, 0, 0.6f));

        var bossUI = bossGo.AddComponent<BossUI>();

        var bossNameGo = CreateUIText(bossGo.transform, "BossName", "",
            new Vector2(10, -5), new Vector2(200, 20), TextAnchor.MiddleLeft);
        var bossNameComp = bossNameGo.GetComponent<Text>();
        bossNameComp.fontStyle = FontStyle.Bold;
        bossNameComp.fontSize = 14;

        var phaseGo = CreateUIText(bossGo.transform, "PhaseText", "",
            new Vector2(450, -5), new Vector2(80, 20), TextAnchor.MiddleRight);
        phaseGo.GetComponent<Text>().fontSize = 12;

        var bossHpGo = CreateUISlider(bossGo.transform, "BossHPBar",
            new Vector2(10, -28), new Vector2(500, 16), HpBarColor);
        var bossHpText = CreateOverlayText(bossHpGo.transform, "BossHPText", "", 10);

        var alertGo = CreateUIText(bossGo.transform, "AlertText", "",
            new Vector2(0, 30), new Vector2(400, 40), TextAnchor.MiddleCenter);
        var alertRT = alertGo.GetComponent<RectTransform>();
        alertRT.anchorMin = new Vector2(0.5f, 0.5f);
        alertRT.anchorMax = new Vector2(0.5f, 0.5f);
        var alertComp = alertGo.GetComponent<Text>();
        alertComp.fontSize = 24;
        alertComp.fontStyle = FontStyle.Bold;
        alertComp.color = new Color(1f, 0.3f, 0.3f);
        alertGo.SetActive(false);

        var bossSO = new SerializedObject(bossUI);
        var bpProp = bossSO.FindProperty("bossPanel");
        if (bpProp != null) bpProp.objectReferenceValue = bossGo;
        SetTextRef(bossSO, "bossNameText", bossNameGo);
        SetSliderRef(bossSO, "bossHPBar", bossHpGo);
        SetTextRef(bossSO, "bossHPText", bossHpText);
        SetTextRef(bossSO, "phaseText", phaseGo);
        SetTextRef(bossSO, "alertText", alertGo);
        bossSO.ApplyModifiedPropertiesWithoutUndo();
    }

    // ── 9. 사망 패널 ──

    private static void CreateDeathPanel(Transform canvasT)
    {
        var deathGo = new GameObject("DeathPanel");
        deathGo.transform.SetParent(canvasT, false);
        var deathRT = deathGo.AddComponent<RectTransform>();
        deathRT.anchorMin = Vector2.zero;
        deathRT.anchorMax = Vector2.one;
        deathRT.sizeDelta = Vector2.zero;
        deathGo.AddComponent<Image>().color = new Color(0, 0, 0, 0.6f);

        var deathTextGo = CreateUIText(deathGo.transform, "DeathText", "\xC0AC\xB9DD",
            new Vector2(0, 30), new Vector2(200, 60), TextAnchor.MiddleCenter);
        var deathTextRT = deathTextGo.GetComponent<RectTransform>();
        deathTextRT.anchorMin = deathTextRT.anchorMax = new Vector2(0.5f, 0.5f);
        deathTextGo.GetComponent<Text>().fontSize = 48;

        var respawnBtnGo = new GameObject("RespawnButton");
        respawnBtnGo.transform.SetParent(deathGo.transform, false);
        var respawnRT = respawnBtnGo.AddComponent<RectTransform>();
        respawnRT.anchorMin = respawnRT.anchorMax = new Vector2(0.5f, 0.5f);
        respawnRT.anchoredPosition = new Vector2(0, -40);
        respawnRT.sizeDelta = new Vector2(160, 50);
        respawnBtnGo.AddComponent<Image>().color = new Color(0.3f, 0.6f, 0.3f);
        var respawnBtn = respawnBtnGo.AddComponent<Button>();
        var btnTxt = CreateUIText(respawnBtnGo.transform, "Text", "\xBD80\xD65C",
            Vector2.zero, Vector2.zero, TextAnchor.MiddleCenter);
        var btnTxtRT = btnTxt.GetComponent<RectTransform>();
        btnTxtRT.anchorMin = Vector2.zero;
        btnTxtRT.anchorMax = Vector2.one;
        btnTxtRT.sizeDelta = Vector2.zero;

        var deathUI = deathGo.AddComponent<DeathUI>();
        var deathSO = new SerializedObject(deathUI);
        var dpProp = deathSO.FindProperty("deathPanel");
        if (dpProp != null) dpProp.objectReferenceValue = deathGo;
        var rbProp = deathSO.FindProperty("respawnButton");
        if (rbProp != null) rbProp.objectReferenceValue = respawnBtn;
        deathSO.ApplyModifiedPropertiesWithoutUndo();
    }

    // ── 10. 인벤토리 패널 ──

    private static void CreateInventoryPanel(Transform canvasT)
    {
        var invGo = CreatePanel(canvasT, "InventoryPanel",
            AnchorPreset.RightStretch, new Vector2(-10, 0), new Vector2(250, 0),
            new Color(0.1f, 0.1f, 0.15f, 0.85f));

        var invUI = invGo.AddComponent<InventoryUI>();
        var invCountGo = CreateUIText(invGo.transform, "ItemCount", "Items: 0",
            new Vector2(10, -10), new Vector2(200, 25), TextAnchor.UpperLeft);

        var invListGo = new GameObject("ItemList");
        invListGo.transform.SetParent(invGo.transform, false);
        var invListRT = invListGo.AddComponent<RectTransform>();
        invListRT.anchorMin = Vector2.zero;
        invListRT.anchorMax = Vector2.one;
        invListRT.offsetMin = new Vector2(5, 5);
        invListRT.offsetMax = new Vector2(-5, -40);

        var invTemplate = CreateUIText(invListGo.transform, "ItemTemplate", "[0] Item#0 x1",
            Vector2.zero, new Vector2(230, 25), TextAnchor.MiddleLeft);
        invTemplate.SetActive(false);

        var invSO = new SerializedObject(invUI);
        var invPanelProp = invSO.FindProperty("inventoryPanel");
        if (invPanelProp != null) invPanelProp.objectReferenceValue = invGo;
        var invListProp = invSO.FindProperty("itemListParent");
        if (invListProp != null) invListProp.objectReferenceValue = invListGo.transform;
        var invTemplateProp = invSO.FindProperty("itemSlotTemplate");
        if (invTemplateProp != null) invTemplateProp.objectReferenceValue = invTemplate;
        SetTextRef(invSO, "itemCountText", invCountGo);
        invSO.ApplyModifiedPropertiesWithoutUndo();
    }

    // ── 11. 파티 패널 ──

    private static void CreatePartyPanel(Transform canvasT)
    {
        var partyGo = CreatePanel(canvasT, "PartyPanel",
            AnchorPreset.LeftStretch, new Vector2(10, 0), new Vector2(200, 0),
            new Color(0.1f, 0.12f, 0.15f, 0.85f));
        var partyRT = partyGo.GetComponent<RectTransform>();
        partyRT.anchorMin = new Vector2(0, 0.3f);
        partyRT.anchorMax = new Vector2(0, 0.7f);

        var partyUI = partyGo.AddComponent<PartyUI>();
        var partyStatusGo = CreateUIText(partyGo.transform, "PartyStatus", "No Party",
            new Vector2(10, -10), new Vector2(180, 25), TextAnchor.UpperLeft);

        var memberListGo = new GameObject("MemberList");
        memberListGo.transform.SetParent(partyGo.transform, false);
        var memberListRT = memberListGo.AddComponent<RectTransform>();
        memberListRT.anchorMin = Vector2.zero;
        memberListRT.anchorMax = Vector2.one;
        memberListRT.offsetMin = new Vector2(5, 40);
        memberListRT.offsetMax = new Vector2(-5, -40);

        var memberTemplate = CreateUIText(memberListGo.transform, "MemberTemplate", "Entity#0 Lv.1",
            Vector2.zero, new Vector2(180, 22), TextAnchor.MiddleLeft);
        memberTemplate.SetActive(false);

        var createBtn = CreateSimpleButton(partyGo.transform, "CreateButton",
            new Vector2(0, 5), new Vector2(90, 30), new Color(0.3f, 0.5f, 0.3f), "Create",
            new Vector2(0, 0), new Vector2(0.5f, 0));
        var leaveBtn = CreateSimpleButton(partyGo.transform, "LeaveButton",
            new Vector2(0, 5), new Vector2(90, 30), new Color(0.5f, 0.3f, 0.3f), "Leave",
            new Vector2(0.5f, 0), new Vector2(1, 0));

        var partySO = new SerializedObject(partyUI);
        var ppp = partySO.FindProperty("partyPanel");
        if (ppp != null) ppp.objectReferenceValue = partyGo;
        SetTextRef(partySO, "partyStatusText", partyStatusGo);
        var mlp = partySO.FindProperty("memberListParent");
        if (mlp != null) mlp.objectReferenceValue = memberListGo.transform;
        var mtp = partySO.FindProperty("memberTemplate");
        if (mtp != null) mtp.objectReferenceValue = memberTemplate;
        var cbp = partySO.FindProperty("createButton");
        if (cbp != null) cbp.objectReferenceValue = createBtn;
        var lbp = partySO.FindProperty("leaveButton");
        if (lbp != null) lbp.objectReferenceValue = leaveBtn;
        partySO.ApplyModifiedPropertiesWithoutUndo();
    }

    // ── 12. 퀘스트 패널 ──

    private static void CreateQuestPanel(Transform canvasT)
    {
        var questGo = CreatePanel(canvasT, "QuestPanel",
            AnchorPreset.RightStretch, new Vector2(-10, 0), new Vector2(280, 0),
            new Color(0.12f, 0.1f, 0.1f, 0.85f));
        var questRT = questGo.GetComponent<RectTransform>();
        questRT.anchorMin = new Vector2(1, 0.3f);
        questRT.anchorMax = new Vector2(1, 0.7f);

        var questUI = questGo.AddComponent<QuestUI>();
        var questCountGo = CreateUIText(questGo.transform, "QuestCount", "Quests: 0",
            new Vector2(10, -10), new Vector2(200, 25), TextAnchor.UpperLeft);

        var questListGo = new GameObject("QuestList");
        questListGo.transform.SetParent(questGo.transform, false);
        var questListRT = questListGo.AddComponent<RectTransform>();
        questListRT.anchorMin = Vector2.zero;
        questListRT.anchorMax = Vector2.one;
        questListRT.offsetMin = new Vector2(5, 5);
        questListRT.offsetMax = new Vector2(-5, -40);

        var questTemplate = CreateUIText(questListGo.transform, "QuestTemplate", "[???] Quest#0",
            Vector2.zero, new Vector2(260, 25), TextAnchor.MiddleLeft);
        questTemplate.SetActive(false);

        var questSO = new SerializedObject(questUI);
        var qpp = questSO.FindProperty("questPanel");
        if (qpp != null) qpp.objectReferenceValue = questGo;
        var qlp = questSO.FindProperty("questListParent");
        if (qlp != null) qlp.objectReferenceValue = questListGo.transform;
        var qtp = questSO.FindProperty("questEntryTemplate");
        if (qtp != null) qtp.objectReferenceValue = questTemplate;
        SetTextRef(questSO, "questCountText", questCountGo);
        questSO.ApplyModifiedPropertiesWithoutUndo();
    }

    // ── 13. 키바인드 가이드 ──

    private static void CreateKeybindGuidePanel(Transform canvasT)
    {
        var guideGo = CreatePanel(canvasT, "KeybindGuidePanel",
            AnchorPreset.LeftStretch, new Vector2(20, 0), new Vector2(260, 0),
            new Color(0, 0, 0, 0.6f));
        var guideRT = guideGo.GetComponent<RectTransform>();
        guideRT.anchorMin = new Vector2(0, 0.2f);
        guideRT.anchorMax = new Vector2(0, 0.8f);

        var guideTextGo = CreateUIText(guideGo.transform, "GuideText", "",
            new Vector2(15, -10), new Vector2(230, 280), TextAnchor.UpperLeft);
        var guideTextComp = guideTextGo.GetComponent<Text>();
        guideTextComp.fontSize = 13;
        var guideTextRT = guideTextGo.GetComponent<RectTransform>();
        guideTextRT.anchorMin = Vector2.zero;
        guideTextRT.anchorMax = Vector2.one;
        guideTextRT.offsetMin = new Vector2(15, 10);
        guideTextRT.offsetMax = new Vector2(-10, -10);

        var guideUI = guideGo.AddComponent<KeybindGuideUI>();
        var guideSO = new SerializedObject(guideUI);
        var gpp = guideSO.FindProperty("guidePanel");
        if (gpp != null) gpp.objectReferenceValue = guideGo;
        SetTextRef(guideSO, "guideText", guideTextGo);
        guideSO.ApplyModifiedPropertiesWithoutUndo();
    }

    // ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    // UI 헬퍼
    // ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    private enum AnchorPreset
    {
        TopLeft, TopCenter, TopRight,
        BottomLeft, BottomCenter, BottomRight,
        LeftStretch, RightStretch,
    }

    private static void SetAnchors(RectTransform rt, AnchorPreset preset)
    {
        switch (preset)
        {
            case AnchorPreset.TopLeft:
                rt.anchorMin = new Vector2(0, 1); rt.anchorMax = new Vector2(0, 1);
                rt.pivot = new Vector2(0, 1); break;
            case AnchorPreset.TopCenter:
                rt.anchorMin = new Vector2(0.5f, 1); rt.anchorMax = new Vector2(0.5f, 1);
                rt.pivot = new Vector2(0.5f, 1); break;
            case AnchorPreset.TopRight:
                rt.anchorMin = new Vector2(1, 1); rt.anchorMax = new Vector2(1, 1);
                rt.pivot = new Vector2(1, 1); break;
            case AnchorPreset.BottomLeft:
                rt.anchorMin = new Vector2(0, 0); rt.anchorMax = new Vector2(0, 0);
                rt.pivot = new Vector2(0, 0); break;
            case AnchorPreset.BottomCenter:
                rt.anchorMin = new Vector2(0.5f, 0); rt.anchorMax = new Vector2(0.5f, 0);
                rt.pivot = new Vector2(0.5f, 0); break;
            case AnchorPreset.BottomRight:
                rt.anchorMin = new Vector2(1, 0); rt.anchorMax = new Vector2(1, 0);
                rt.pivot = new Vector2(1, 0); break;
            case AnchorPreset.LeftStretch:
                rt.anchorMin = new Vector2(0, 0); rt.anchorMax = new Vector2(0, 1);
                rt.pivot = new Vector2(0, 0.5f); break;
            case AnchorPreset.RightStretch:
                rt.anchorMin = new Vector2(1, 0); rt.anchorMax = new Vector2(1, 1);
                rt.pivot = new Vector2(1, 0.5f); break;
        }
    }

    private static GameObject CreatePanel(Transform parent, string name,
        AnchorPreset anchor, Vector2 pos, Vector2 size, Color bgColor)
    {
        var go = new GameObject(name);
        go.transform.SetParent(parent, false);
        var rt = go.AddComponent<RectTransform>();
        SetAnchors(rt, anchor);
        rt.anchoredPosition = pos;
        rt.sizeDelta = size;
        if (bgColor.a > 0.001f)
        {
            var img = go.AddComponent<Image>();
            img.color = bgColor;
            img.raycastTarget = false;
        }
        return go;
    }

    private static GameObject CreateOverlayText(Transform parent, string name, string text, int fontSize)
    {
        var go = CreateUIText(parent, name, text, Vector2.zero, Vector2.zero, TextAnchor.MiddleCenter);
        var rt = go.GetComponent<RectTransform>();
        rt.anchorMin = Vector2.zero;
        rt.anchorMax = Vector2.one;
        rt.sizeDelta = Vector2.zero;
        rt.anchoredPosition = Vector2.zero;
        var t = go.GetComponent<Text>();
        t.fontSize = fontSize;
        return go;
    }

    private static Button CreateSimpleButton(Transform parent, string name,
        Vector2 pos, Vector2 size, Color color, string label,
        Vector2 anchorMin, Vector2 anchorMax)
    {
        var go = new GameObject(name);
        go.transform.SetParent(parent, false);
        var rt = go.AddComponent<RectTransform>();
        rt.anchorMin = anchorMin;
        rt.anchorMax = anchorMax;
        rt.pivot = new Vector2(0.5f, 0);
        rt.anchoredPosition = pos;
        rt.sizeDelta = new Vector2(0, size.y);
        go.AddComponent<Image>().color = color;
        var btn = go.AddComponent<Button>();
        var txtGo = CreateUIText(go.transform, "Text", label,
            Vector2.zero, Vector2.zero, TextAnchor.MiddleCenter);
        var txtRT = txtGo.GetComponent<RectTransform>();
        txtRT.anchorMin = Vector2.zero;
        txtRT.anchorMax = Vector2.one;
        txtRT.sizeDelta = Vector2.zero;
        return btn;
    }

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

        var bgGo = new GameObject("Background");
        bgGo.transform.SetParent(go.transform, false);
        var bgRT = bgGo.AddComponent<RectTransform>();
        bgRT.anchorMin = Vector2.zero;
        bgRT.anchorMax = Vector2.one;
        bgRT.sizeDelta = Vector2.zero;
        bgGo.AddComponent<Image>().color = new Color(0.1f, 0.1f, 0.12f, 0.9f);

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
        fillGo.AddComponent<Image>().color = fillColor;

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
            prop.GetArrayElementAtIndex(i).objectReferenceValue = texts[i];
    }

    private static void SetImageArrayRef(SerializedObject so, string fieldName, Image[] images)
    {
        var prop = so.FindProperty(fieldName);
        if (prop == null) return;
        prop.arraySize = images.Length;
        for (int i = 0; i < images.Length; i++)
            prop.GetArrayElementAtIndex(i).objectReferenceValue = images[i];
    }

    // ━━━ 유틸 ━━━

    private static GameObject CreateManagerObject(string name, System.Type componentType)
    {
        var go = new GameObject(name);
        go.AddComponent(componentType);
        return go;
    }

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

    private static Color HexColor(string hex)
    {
        if (ColorUtility.TryParseHtmlString(hex, out var color))
            return color;
        return Color.magenta;
    }
}
