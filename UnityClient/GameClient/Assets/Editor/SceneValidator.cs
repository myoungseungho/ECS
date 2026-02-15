// ━━━ SceneValidator.cs ━━━
// Menu: "ECS Game > Validate Setup"
// ProjectSetup이 만든 에셋/Scene/컴포넌트 상태를 검증
// Console에 PASS/FAIL 출력

using UnityEngine;
using UnityEditor;
using UnityEditor.SceneManagement;
using System.Collections.Generic;

public static class SceneValidator
{
    private static int _pass;
    private static int _fail;
    private static int _warn;

    [MenuItem("ECS Game/Validate Setup", priority = 2)]
    public static void ValidateAll()
    {
        _pass = 0;
        _fail = 0;
        _warn = 0;

        Debug.Log("━━━ [Validate] 검증 시작 ━━━");

        ValidateMaterials();
        ValidatePrefabs();
        ValidateScenes();
        ValidateBuildSettings();

        Debug.Log($"━━━ [Validate] 결과: {_pass} PASS, {_fail} FAIL, {_warn} WARN ━━━");

        if (_fail == 0)
        {
            EditorUtility.DisplayDialog("Validation Passed",
                $"모든 검증 통과! ({_pass} PASS, 0 FAIL)", "OK");
        }
        else
        {
            EditorUtility.DisplayDialog("Validation Failed",
                $"{_fail}개 항목 실패.\nConsole에서 FAIL 항목을 확인하세요.\n({_pass} PASS, {_fail} FAIL)",
                "OK");
        }
    }

    // ━━━ Materials ━━━

    private static void ValidateMaterials()
    {
        Check("Material: LocalPlayer.mat 존재",
            AssetDatabase.LoadAssetAtPath<Material>("Assets/Materials/LocalPlayer.mat") != null);
        Check("Material: RemotePlayer.mat 존재",
            AssetDatabase.LoadAssetAtPath<Material>("Assets/Materials/RemotePlayer.mat") != null);
    }

    // ━━━ Prefabs ━━━

    private static void ValidatePrefabs()
    {
        var localPrefab = AssetDatabase.LoadAssetAtPath<GameObject>("Assets/Prefabs/LocalPlayer.prefab");
        var remotePrefab = AssetDatabase.LoadAssetAtPath<GameObject>("Assets/Prefabs/RemotePlayer.prefab");

        Check("Prefab: LocalPlayer.prefab 존재", localPrefab != null);
        Check("Prefab: RemotePlayer.prefab 존재", remotePrefab != null);

        if (localPrefab != null)
        {
            Check("Prefab: LocalPlayer에 LocalPlayer 컴포넌트",
                localPrefab.GetComponent<LocalPlayer>() != null);
            Check("Prefab: LocalPlayer에 Renderer",
                localPrefab.GetComponent<MeshRenderer>() != null
                || localPrefab.GetComponentInChildren<Renderer>() != null);
            Warn("Prefab: LocalPlayer에 Animator",
                localPrefab.GetComponentInChildren<Animator>() != null);
        }

        if (remotePrefab != null)
        {
            Check("Prefab: RemotePlayer에 RemotePlayer 컴포넌트",
                remotePrefab.GetComponent<RemotePlayer>() != null);
            Check("Prefab: RemotePlayer에 Renderer",
                remotePrefab.GetComponent<MeshRenderer>() != null
                || remotePrefab.GetComponentInChildren<Renderer>() != null);
            Warn("Prefab: RemotePlayer에 Animator",
                remotePrefab.GetComponentInChildren<Animator>() != null);
        }

        var monsterPrefab = AssetDatabase.LoadAssetAtPath<GameObject>("Assets/Prefabs/Monster.prefab");
        Check("Prefab: Monster.prefab 존재", monsterPrefab != null);
        if (monsterPrefab != null)
        {
            Check("Prefab: Monster에 MonsterEntity 컴포넌트",
                monsterPrefab.GetComponent<MonsterEntity>() != null);
            Warn("Prefab: Monster에 Animator",
                monsterPrefab.GetComponentInChildren<Animator>() != null);
        }
    }

    // ━━━ Scenes ━━━

    private static void ValidateScenes()
    {
        Check("Scene: GameScene.unity 존재",
            System.IO.File.Exists("Assets/Scenes/GameScene.unity"));
        Check("Scene: TestScene.unity 존재",
            System.IO.File.Exists("Assets/Scenes/TestScene.unity"));

        // GameScene 내부 검증
        ValidateGameScene();
    }

    private static void ValidateGameScene()
    {
        var scenePath = "Assets/Scenes/GameScene.unity";
        if (!System.IO.File.Exists(scenePath)) return;

        // 현재 Scene 백업 후 GameScene 열기
        var currentScene = EditorSceneManager.GetActiveScene().path;
        var scene = EditorSceneManager.OpenScene(scenePath, OpenSceneMode.Additive);

        var roots = scene.GetRootGameObjects();
        var objectNames = new HashSet<string>();
        foreach (var root in roots)
            objectNames.Add(root.name);

        Check("GameScene: Floor 오브젝트 존재", objectNames.Contains("Floor"));
        Check("GameScene: Directional Light 존재", objectNames.Contains("Directional Light"));
        Check("GameScene: Main Camera 존재", objectNames.Contains("Main Camera"));
        Check("GameScene: NetworkManager 존재", objectNames.Contains("NetworkManager"));
        Check("GameScene: GameManager 존재", objectNames.Contains("GameManager"));
        Check("GameScene: EntityManager 존재", objectNames.Contains("EntityManager"));
        Check("GameScene: EntityPool 존재", objectNames.Contains("EntityPool"));
        Check("GameScene: StatsManager 존재", objectNames.Contains("StatsManager"));
        Check("GameScene: CombatManager 존재", objectNames.Contains("CombatManager"));
        Check("GameScene: MonsterManager 존재", objectNames.Contains("MonsterManager"));
        Check("GameScene: SkillManager 존재", objectNames.Contains("SkillManager"));
        Check("GameScene: InventoryManager 존재", objectNames.Contains("InventoryManager"));
        Check("GameScene: PartyManager 존재", objectNames.Contains("PartyManager"));
        Check("GameScene: BuffManager 존재", objectNames.Contains("BuffManager"));
        Check("GameScene: QuestManager 존재", objectNames.Contains("QuestManager"));
        Check("GameScene: ChatManager 존재", objectNames.Contains("ChatManager"));
        Check("GameScene: ShopManager 존재", objectNames.Contains("ShopManager"));
        Check("GameScene: BossManager 존재", objectNames.Contains("BossManager"));
        Check("GameScene: SceneFlowManager 존재", objectNames.Contains("SceneFlowManager"));
        Check("GameScene: NpcManager 존재", objectNames.Contains("NpcManager"));
        Check("GameScene: EnhanceManager 존재", objectNames.Contains("EnhanceManager"));
        Check("GameScene: TutorialManager 존재", objectNames.Contains("TutorialManager"));
        Check("GameScene: GuildManager 존재", objectNames.Contains("GuildManager"));
        Check("GameScene: TradeManager 존재", objectNames.Contains("TradeManager"));
        Check("GameScene: MailManager 존재", objectNames.Contains("MailManager"));
        Check("GameScene: DungeonManager 존재", objectNames.Contains("DungeonManager"));
        Check("GameScene: PvPManager 존재", objectNames.Contains("PvPManager"));
        Check("GameScene: RaidManager 존재", objectNames.Contains("RaidManager"));
        Check("GameScene: CraftingManager 존재", objectNames.Contains("CraftingManager"));
        Check("GameScene: GatheringManager 존재", objectNames.Contains("GatheringManager"));
        Check("GameScene: GemManager 존재", objectNames.Contains("GemManager"));
        Check("GameScene: WeatherManager 존재", objectNames.Contains("WeatherManager"));
        Check("GameScene: TeleportManager 존재", objectNames.Contains("TeleportManager"));
        Check("GameScene: MountManager 존재", objectNames.Contains("MountManager"));
        Check("GameScene: CashShopManager 존재", objectNames.Contains("CashShopManager"));
        Check("GameScene: BattlePassManager 존재", objectNames.Contains("BattlePassManager"));
        Check("GameScene: AttendanceManager 존재", objectNames.Contains("AttendanceManager"));
        Check("GameScene: StoryManager 존재", objectNames.Contains("StoryManager"));
        Check("GameScene: AuctionManager 존재", objectNames.Contains("AuctionManager"));
        Check("GameScene: TripodManager 존재", objectNames.Contains("TripodManager"));
        Check("GameScene: BountyManager 존재", objectNames.Contains("BountyManager"));
        Check("GameScene: DailyQuestManager 존재", objectNames.Contains("DailyQuestManager"));
        Check("GameScene: ReputationManager 존재", objectNames.Contains("ReputationManager"));
        Check("GameScene: TitleManager 존재", objectNames.Contains("TitleManager"));
        Check("GameScene: CollectionManager 존재", objectNames.Contains("CollectionManager"));
        Check("GameScene: JobChangeUI 존재", objectNames.Contains("JobChangeUI"));
        Check("GameScene: EngravingManager 존재", objectNames.Contains("EngravingManager"));
        Check("GameScene: TranscendUI 존재", objectNames.Contains("TranscendUI"));
        Check("GameScene: FriendManager 존재", objectNames.Contains("FriendManager"));
        Check("GameScene: BlockManager 존재", objectNames.Contains("BlockManager"));
        Check("GameScene: PartyFinderManager 존재", objectNames.Contains("PartyFinderManager"));
        Check("GameScene: FriendUI 존재", objectNames.Contains("FriendUI"));
        Check("GameScene: BlockUI 존재", objectNames.Contains("BlockUI"));
        Check("GameScene: PartyFinderUI 존재", objectNames.Contains("PartyFinderUI"));
        Check("GameScene: DurabilityManager 존재", objectNames.Contains("DurabilityManager"));
        Check("GameScene: RepairUI 존재", objectNames.Contains("RepairUI"));
        Check("GameScene: RerollUI 존재", objectNames.Contains("RerollUI"));
        Check("GameScene: BattlegroundManager 존재", objectNames.Contains("BattlegroundManager"));
        Check("GameScene: GuildWarManager 존재", objectNames.Contains("GuildWarManager"));
        Check("GameScene: BattlegroundUI 존재", objectNames.Contains("BattlegroundUI"));
        Check("GameScene: GuildWarUI 존재", objectNames.Contains("GuildWarUI"));
        Check("GameScene: CurrencyManager 존재", objectNames.Contains("CurrencyManager"));
        Check("GameScene: CurrencyUI 존재", objectNames.Contains("CurrencyUI"));
        Check("GameScene: TokenShopUI 존재", objectNames.Contains("TokenShopUI"));
        Check("GameScene: SecretRealmManager 존재", objectNames.Contains("SecretRealmManager"));
        Check("GameScene: SecretRealmPortalUI 존재", objectNames.Contains("SecretRealmPortalUI"));
        Check("GameScene: SecretRealmUI 존재", objectNames.Contains("SecretRealmUI"));
        Check("GameScene: MentorManager 존재", objectNames.Contains("MentorManager"));
        Check("GameScene: MentorUI 존재", objectNames.Contains("MentorUI"));
        Check("GameScene: MentorShopUI 존재", objectNames.Contains("MentorShopUI"));
        Check("GameScene: EventManager 존재", objectNames.Contains("EventManager"));
        Check("GameScene: EventUI 존재", objectNames.Contains("EventUI"));
        Check("GameScene: Canvas 존재", objectNames.Contains("Canvas"));

        // EntityManager Prefab 참조 확인
        foreach (var root in roots)
        {
            if (root.name == "EntityManager")
            {
                var em = root.GetComponent<EntityManager>();
                if (em != null)
                {
                    var so = new SerializedObject(em);
                    var localRef = so.FindProperty("localPlayerPrefab");
                    var remoteRef = so.FindProperty("remotePlayerPrefab");
                    Check("GameScene: EntityManager.localPlayerPrefab 연결됨",
                        localRef != null && localRef.objectReferenceValue != null);
                    Check("GameScene: EntityManager.remotePlayerPrefab 연결됨",
                        remoteRef != null && remoteRef.objectReferenceValue != null);
                }
            }

            if (root.name == "EntityPool")
            {
                var ep = root.GetComponent<EntityPool>();
                if (ep != null)
                {
                    var so = new SerializedObject(ep);
                    var prefabRef = so.FindProperty("prefab");
                    Check("GameScene: EntityPool.prefab 연결됨",
                        prefabRef != null && prefabRef.objectReferenceValue != null);
                }
            }
        }

        // Additive Scene 닫기
        EditorSceneManager.CloseScene(scene, true);
    }

    // ━━━ Build Settings ━━━

    private static void ValidateBuildSettings()
    {
        bool hasGame = false;
        bool hasTest = false;

        foreach (var s in EditorBuildSettings.scenes)
        {
            if (s.path == "Assets/Scenes/GameScene.unity") hasGame = true;
            if (s.path == "Assets/Scenes/TestScene.unity") hasTest = true;
        }

        Check("Build Settings: GameScene 등록됨", hasGame);
        Check("Build Settings: TestScene 등록됨", hasTest);
    }

    // ━━━ 유틸 ━━━

    private static void Check(string label, bool condition)
    {
        if (condition)
        {
            Debug.Log($"  [PASS] {label}");
            _pass++;
        }
        else
        {
            Debug.LogError($"  [FAIL] {label}");
            _fail++;
        }
    }

    private static void Warn(string label, bool condition)
    {
        if (condition)
        {
            Debug.Log($"  [PASS] {label}");
            _pass++;
        }
        else
        {
            Debug.LogWarning($"  [WARN] {label} — FBX 없이 프리미티브 사용 중");
            _warn++;
        }
    }
}
